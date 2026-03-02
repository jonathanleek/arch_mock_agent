"""Tool definitions for the Astro Mock Infrastructure Agent."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from anthropic.lib.tools import beta_tool

from catalog.image_check import check_image_exists
from catalog.ports import allocate_port
from catalog.providers import get_provider_packages
from catalog.services import SERVICE_CATALOG, apply_overrides, find_service
from utils.requirements_io import add_packages, read_requirements, remove_packages
from utils.dag_writer import write_test_dag
from utils.yaml_io import read_yaml, write_yaml
from utils.yaml_merge import (
    merge_airflow_settings,
    merge_docker_compose,
    remove_airflow_connections,
    remove_docker_services,
)

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


def _requirements_path() -> Path:
    return _project_dir / "requirements.txt"


def _dags_path() -> Path:
    return _project_dir / "dags" / "test_connections.py"


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

    req_lines = read_requirements(_requirements_path())
    provider_lines = [
        l for l in req_lines
        if l.strip() and not l.strip().startswith("#")
        and "apache-airflow-providers" in l.lower()
    ]
    if provider_lines:
        lines.append("\nProvider packages (requirements.txt):")
        for pl in provider_lines:
            lines.append(f"  - {pl.strip()}")
    else:
        lines.append("\nNo Airflow provider packages in requirements.txt yet.")

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
        lines.append(f"  Default conn_login: {spec['conn_login']}")
        lines.append(f"  Default conn_password: {spec['conn_password']}")
        lines.append(f"  Default conn_schema: {spec['conn_schema']}")
        cred_map = spec.get("credential_map", {})
        if cred_map:
            lines.append(f"  Overridable fields: {', '.join(cred_map.keys())}")
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

    Optional credential overrides (applied to both Docker env and connection):
    - db_name: override the default database/schema name
    - username: override the default username
    - password: override the default password

    Returns a JSON object with status and effective connection details per
    service, so downstream tools can use authoritative credentials.

    Args:
        services_json: JSON array of service spec objects.
    """
    try:
        specs: list[dict[str, Any]] = json.loads(services_json)
    except json.JSONDecodeError as e:
        return json.dumps({"status": "error", "message": f"Invalid JSON: {e}"})

    new_services: dict[str, Any] = {}
    new_volumes: dict[str, Any] = {}
    result_services: list[dict[str, Any]] = []

    for spec in specs:
        stype = spec.get("service_type", "")
        sname = spec.get("service_name", f"mock_{stype}")
        conn_id = spec.get("conn_id", f"{sname}_default")

        if stype not in SERVICE_CATALOG:
            result_services.append({"service_name": sname, "error": f"unknown service_type '{stype}'"})
            continue

        cat = SERVICE_CATALOG[stype]

        if not check_image_exists(cat["image"]):
            result_services.append({
                "service_name": sname,
                "error": f"image '{cat['image']}' not found on registry",
            })
            continue

        host_port = allocate_port(cat["default_port"])

        # Build overrides dict from optional spec keys.
        overrides: dict[str, str] = {}
        for key in ("db_name", "username", "password"):
            if key in spec:
                overrides[key] = spec[key]

        env, command, conn_fields = apply_overrides(stype, overrides or None)

        service_def: dict[str, Any] = {
            "image": cat["image"],
            "ports": [f"{host_port}:{cat['container_port']}"],
            "environment": env,
            "networks": ["airflow"],
        }

        # Substitute placeholders in command.
        if command:
            command = command.replace("{service_name}", sname)
            command = command.replace("{container_port}", str(cat["container_port"]))
            service_def["command"] = command

        # Collect named volumes.
        for vol_name, mount_path in cat.get("volumes", {}).items():
            service_def.setdefault("volumes", []).append(f"{vol_name}:{mount_path}")
            new_volumes[vol_name] = None

        new_services[sname] = service_def

        # Substitute placeholders in conn_extra.
        conn_extra = dict(cat.get("conn_extra", {}))
        for ek, ev in conn_extra.items():
            if isinstance(ev, str):
                conn_extra[ek] = ev.replace("{service_name}", sname).replace(
                    "{container_port}", str(cat["container_port"])
                )

        result_services.append({
            "service_name": sname,
            "conn_id": conn_id,
            "conn_type": cat["conn_type"],
            "conn_host": sname,
            "conn_port": cat["container_port"],
            "conn_schema": conn_fields["conn_schema"],
            "conn_login": conn_fields["conn_login"],
            "conn_password": conn_fields["conn_password"],
            "conn_extra": conn_extra,
        })

    if not new_services:
        return json.dumps({"status": "error", "message": "No valid services to add.", "services": result_services})

    existing = read_yaml(_compose_path())
    merged = merge_docker_compose(existing, new_services, new_volumes)

    # Resolve provider packages for the conn_types being added.
    conn_types = [s["conn_type"] for s in result_services if "conn_type" in s]
    provider_packages = get_provider_packages(conn_types)

    if _dry_run:
        import yaml
        preview = yaml.dump(merged, default_flow_style=False, sort_keys=False)
        would_add = add_packages(_requirements_path(), provider_packages, dry_run=True)
        return json.dumps({
            "status": "dry_run",
            "compose_preview": preview,
            "services": result_services,
            "providers_would_add": would_add,
        })

    write_yaml(_compose_path(), merged)
    providers_added = add_packages(_requirements_path(), provider_packages)
    result: dict[str, Any] = {"status": "ok", "services": result_services}
    if providers_added:
        result["providers_added"] = providers_added
    return json.dumps(result)


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
        all_conns = merged.get("airflow", {}).get("connections", [])
        _, dag_source = write_test_dag(_dags_path(), all_conns, dry_run=True)
        return (
            "DRY RUN — would write airflow_settings.yaml:\n\n" + preview
            + f"\n\nWould regenerate test DAG with {len(all_conns)} task(s)."
        )

    write_yaml(_settings_path(), merged)

    # Regenerate the test DAG to include all connections.
    all_conns = merged.get("airflow", {}).get("connections", [])
    dag_path_str, _ = write_test_dag(_dags_path(), all_conns, dry_run=False)

    ids = [c.get("conn_id", "?") for c in conns]
    return (
        f"Updated airflow_settings.yaml with connections: {', '.join(ids)}\n"
        f"Regenerated {dag_path_str} with {len(all_conns)} task(s)."
    )


# ---------------------------------------------------------------------------
# Tool 6: generate_test_dag
# ---------------------------------------------------------------------------

@beta_tool
def generate_test_dag() -> str:
    """Generate a test DAG at dags/test_connections.py that verifies every
    Airflow connection in airflow_settings.yaml.

    The DAG contains one task per connection. Each task calls
    ``BaseHook.get_connection()`` → ``get_hook()`` → ``test_connection()``
    to confirm the connection is reachable.

    No arguments are needed — connections are read from airflow_settings.yaml.
    """
    settings = read_yaml(_settings_path())
    conns = (settings or {}).get("airflow", {}).get("connections", [])

    if not conns:
        return (
            "No connections found in airflow_settings.yaml. "
            "Add connections first with add_airflow_connections, then re-run."
        )

    path_str, source = write_test_dag(_dags_path(), conns, dry_run=_dry_run)

    if _dry_run:
        return (
            f"DRY RUN — would write {path_str} with {len(conns)} task(s).\n\n"
            f"Preview:\n{source}"
        )

    return (
        f"Wrote {path_str} with {len(conns)} task(s) testing connections: "
        + ", ".join(c.get("conn_id", "?") for c in conns)
    )


# ---------------------------------------------------------------------------
# Tool 7: remove_mock_services
# ---------------------------------------------------------------------------

@beta_tool
def remove_mock_services(services_json: str) -> str:
    """Remove mock Docker services, their Airflow connections, orphaned
    volumes, and optionally unused provider packages.

    Accepts a JSON object with:
    - service_names: list of Docker service names to remove
    - cleanup_providers: bool (default false) — remove provider packages
      no longer needed by any remaining connection

    Args:
        services_json: JSON object with service_names and optional cleanup_providers.
    """
    try:
        payload: dict[str, Any] = json.loads(services_json)
    except json.JSONDecodeError as e:
        return json.dumps({"status": "error", "message": f"Invalid JSON: {e}"})

    service_names: list[str] = payload.get("service_names", [])
    cleanup_providers: bool = payload.get("cleanup_providers", False)

    if not service_names:
        return json.dumps({"status": "error", "message": "service_names is required and must be non-empty."})

    # --- 1. Remove Docker services and orphaned volumes ---
    compose = read_yaml(_compose_path())
    updated_compose, removed_services, removed_volumes = remove_docker_services(
        compose, service_names, remove_orphaned_volumes=True,
    )

    not_found = [n for n in service_names if n not in removed_services]

    # --- 2. Remove Airflow connections whose conn_host matches a removed service ---
    settings = read_yaml(_settings_path())
    updated_settings, removed_conn_ids = remove_airflow_connections(
        settings, conn_hosts=removed_services,
    )

    # --- 3. Optionally clean up provider packages ---
    providers_removed: list[str] = []
    if cleanup_providers and removed_conn_ids:
        # Determine conn_types of removed connections.
        old_conns = (settings or {}).get("airflow", {}).get("connections", [])
        removed_conn_types: set[str] = set()
        for conn in old_conns:
            if conn.get("conn_id") in removed_conn_ids:
                ct = conn.get("conn_type", "")
                if ct:
                    removed_conn_types.add(ct)

        # Determine conn_types still in use by remaining connections.
        remaining_conns = updated_settings.get("airflow", {}).get("connections", [])
        remaining_types: set[str] = {
            c.get("conn_type", "") for c in remaining_conns if c.get("conn_type")
        }

        # Only remove providers for types no longer in use.
        orphaned_types = removed_conn_types - remaining_types
        if orphaned_types:
            packages_to_remove = get_provider_packages(list(orphaned_types))
            if packages_to_remove:
                providers_removed = remove_packages(
                    _requirements_path(), packages_to_remove, dry_run=_dry_run,
                )

    # --- 4. Write files and regenerate test DAG (unless dry run) ---
    if _dry_run:
        import yaml
        # Preview what the test DAG would look like after removal.
        remaining_conns = updated_settings.get("airflow", {}).get("connections", [])
        dag_preview: str | None = None
        if remaining_conns:
            _, source = write_test_dag(_dags_path(), remaining_conns, dry_run=True)
            dag_preview = source
        return json.dumps({
            "status": "dry_run",
            "compose_preview": yaml.dump(updated_compose, default_flow_style=False, sort_keys=False),
            "settings_preview": yaml.dump(updated_settings, default_flow_style=False, sort_keys=False),
            "removed_services": removed_services,
            "removed_connections": removed_conn_ids,
            "removed_volumes": removed_volumes,
            "not_found": not_found,
            "providers_removed": providers_removed,
            "test_dag_preview": dag_preview,
        })

    if removed_services:
        write_yaml(_compose_path(), updated_compose)
    if removed_conn_ids:
        write_yaml(_settings_path(), updated_settings)

    # --- 5. Regenerate test DAG to reflect remaining connections ---
    remaining_conns = updated_settings.get("airflow", {}).get("connections", [])
    test_dag_info: str | None = None
    if remaining_conns:
        path_str, _ = write_test_dag(_dags_path(), remaining_conns, dry_run=_dry_run)
        test_dag_info = f"Regenerated {path_str} with {len(remaining_conns)} task(s)."
    else:
        # No connections left — remove the test DAG if it exists.
        dag_path = _dags_path()
        if dag_path.exists() and not _dry_run:
            dag_path.unlink()
            test_dag_info = f"Removed {dag_path} (no connections remain)."

    result: dict[str, Any] = {
        "status": "ok",
        "removed_services": removed_services,
        "removed_connections": removed_conn_ids,
        "removed_volumes": removed_volumes,
        "not_found": not_found,
        "providers_removed": providers_removed,
    }
    if test_dag_info:
        result["test_dag"] = test_dag_info
    return json.dumps(result)


# ---------------------------------------------------------------------------
# Convenience: all tools as a list for the runner
# ---------------------------------------------------------------------------

ALL_TOOLS = [
    list_existing_services,
    get_service_catalog,
    read_current_config,
    add_docker_services,
    add_airflow_connections,
    generate_test_dag,
    remove_mock_services,
]
