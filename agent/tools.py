"""Tool definitions for the Astro Mock Infrastructure Agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anthropic.lib.tools import beta_tool

from catalog.ports import allocate_port
from catalog.services import SERVICE_CATALOG, find_service
from utils.yaml_io import read_yaml, write_yaml
from utils.yaml_merge import merge_airflow_settings, merge_docker_compose

# These module-level variables are set by the agent loop before tools run.
_project_dir: Path = Path(".")
_dry_run: bool = False


def configure(project_dir: str | Path, dry_run: bool = False) -> None:
    """Set the project directory and dry-run flag for all tools."""
    global _project_dir, _dry_run
    _project_dir = Path(project_dir)
    _dry_run = dry_run


def _compose_path() -> Path:
    return _project_dir / "docker-compose.override.yml"


def _settings_path() -> Path:
    return _project_dir / "airflow_settings.yaml"


# ---------------------------------------------------------------------------
# Tool 1: list_existing_services
# ---------------------------------------------------------------------------

@beta_tool
def list_existing_services() -> str:
    """List Docker services in docker-compose.override.yml and Airflow
    connections in airflow_settings.yaml for the current project.

    Returns a summary of what is already configured.
    """
    lines: list[str] = []

    compose = read_yaml(_compose_path())
    if compose and compose.get("services"):
        lines.append("Docker services (docker-compose.override.yml):")
        for name, spec in compose["services"].items():
            image = spec.get("image", "unknown")
            ports = spec.get("ports", [])
            lines.append(f"  - {name}: {image} (ports: {ports})")
    else:
        lines.append("No Docker services configured yet.")

    settings = read_yaml(_settings_path())
    conns = (settings or {}).get("airflow", {}).get("connections", [])
    if conns:
        lines.append("\nAirflow connections (airflow_settings.yaml):")
        for c in conns:
            cid = c.get("conn_id", "?")
            ctype = c.get("conn_type", "?")
            host = c.get("conn_host", "?")
            lines.append(f"  - {cid}: type={ctype}, host={host}")
    else:
        lines.append("No Airflow connections configured yet.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2: get_service_catalog
# ---------------------------------------------------------------------------

@beta_tool
def get_service_catalog(query: str) -> str:
    """Search the built-in service catalog for infrastructure matching *query*.

    Args:
        query: Service type to search for (e.g. 'postgres', 's3', 'redis').

    Returns catalog entries with image, ports, and connection details.
    """
    matches = find_service(query)
    if not matches:
        return (
            f"No catalog entry found for '{query}'. "
            f"Available types: {', '.join(SERVICE_CATALOG.keys())}"
        )

    lines: list[str] = []
    for key, spec in matches:
        lines.append(f"Service type: {key}")
        lines.append(f"  Image: {spec['image']}")
        lines.append(f"  Default host port: {spec['default_port']}")
        lines.append(f"  Container port: {spec['container_port']}")
        lines.append(f"  Conn type: {spec['conn_type']}")
        lines.append(f"  Aliases: {spec.get('aliases', [])}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 3: read_current_config
# ---------------------------------------------------------------------------

@beta_tool
def read_current_config(file_type: str) -> str:
    """Read the raw YAML of a configuration file.

    Args:
        file_type: Either 'docker-compose' or 'airflow-settings'.
    """
    if file_type in ("docker-compose", "docker_compose", "compose"):
        path = _compose_path()
    elif file_type in ("airflow-settings", "airflow_settings", "settings"):
        path = _settings_path()
    else:
        return f"Unknown file_type '{file_type}'. Use 'docker-compose' or 'airflow-settings'."

    data = read_yaml(path)
    if data is None:
        return f"File does not exist yet: {path}"

    import yaml
    return yaml.dump(data, default_flow_style=False, sort_keys=False)


# ---------------------------------------------------------------------------
# Tool 4: add_docker_services
# ---------------------------------------------------------------------------

@beta_tool
def add_docker_services(services_json: str) -> str:
    """Add Docker services to docker-compose.override.yml.

    Accepts a JSON array of service specs. Each spec must include:
    - service_type: key from the catalog (e.g. 'postgres', 'localstack')
    - service_name: Docker service name (e.g. 'mock_postgres')
    - conn_id: Airflow connection ID (used for labeling only)

    Args:
        services_json: JSON array of service spec objects.
    """
    try:
        specs: list[dict[str, Any]] = json.loads(services_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    new_services: dict[str, Any] = {}
    new_volumes: dict[str, Any] = {}
    summary: list[str] = []

    for spec in specs:
        stype = spec.get("service_type", "")
        sname = spec.get("service_name", f"mock_{stype}")

        if stype not in SERVICE_CATALOG:
            summary.append(f"SKIP: unknown service_type '{stype}'")
            continue

        cat = SERVICE_CATALOG[stype]
        host_port = allocate_port(cat["default_port"])

        service_def: dict[str, Any] = {
            "image": cat["image"],
            "ports": [f"{host_port}:{cat['container_port']}"],
            "environment": dict(cat["environment"]),
            "networks": ["airflow"],
        }

        if cat.get("command"):
            service_def["command"] = cat["command"]

        # Collect named volumes
        for vol_name, mount_path in cat.get("volumes", {}).items():
            service_def.setdefault("volumes", []).append(f"{vol_name}:{mount_path}")
            new_volumes[vol_name] = None

        new_services[sname] = service_def
        summary.append(
            f"Added {sname} ({cat['image']}) — "
            f"host port {host_port} -> container port {cat['container_port']}"
        )

    if not new_services:
        return "No valid services to add.\n" + "\n".join(summary)

    existing = read_yaml(_compose_path())
    merged = merge_docker_compose(existing, new_services, new_volumes)

    if _dry_run:
        import yaml
        preview = yaml.dump(merged, default_flow_style=False, sort_keys=False)
        return "DRY RUN — would write docker-compose.override.yml:\n\n" + preview

    write_yaml(_compose_path(), merged)
    return "Updated docker-compose.override.yml:\n" + "\n".join(summary)


# ---------------------------------------------------------------------------
# Tool 5: add_airflow_connections
# ---------------------------------------------------------------------------

@beta_tool
def add_airflow_connections(connections_json: str) -> str:
    """Add Airflow connections to airflow_settings.yaml.

    Accepts a JSON array of connection specs. Each spec should include:
    - conn_id, conn_type, conn_host, conn_port, conn_schema,
      conn_login, conn_password, conn_extra

    Args:
        connections_json: JSON array of connection spec objects.
    """
    try:
        conns: list[dict[str, Any]] = json.loads(connections_json)
    except json.JSONDecodeError as e:
        return f"Invalid JSON: {e}"

    # Normalise conn_extra to string if given as dict
    for c in conns:
        extra = c.get("conn_extra")
        if isinstance(extra, dict):
            c["conn_extra"] = json.dumps(extra)

    existing = read_yaml(_settings_path())
    merged = merge_airflow_settings(existing, conns)

    if _dry_run:
        import yaml
        preview = yaml.dump(merged, default_flow_style=False, sort_keys=False)
        return "DRY RUN — would write airflow_settings.yaml:\n\n" + preview

    write_yaml(_settings_path(), merged)

    ids = [c.get("conn_id", "?") for c in conns]
    return f"Updated airflow_settings.yaml with connections: {', '.join(ids)}"


# ---------------------------------------------------------------------------
# Convenience: all tools as a list for the runner
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    list_existing_services,
    get_service_catalog,
    read_current_config,
    add_docker_services,
    add_airflow_connections,
]
