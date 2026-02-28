"""Deep-merge helpers for docker-compose and airflow_settings YAML files."""

from __future__ import annotations

import copy
from typing import Any


def merge_docker_compose(
    existing: dict[str, Any] | None,
    new_services: dict[str, Any],
    new_volumes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Merge *new_services* (and optional *new_volumes*) into an existing
    docker-compose override dict.

    - Never removes existing entries.
    - Auto-injects ``networks: [airflow]`` on every service.
    - Ensures the top-level ``networks`` key declares the airflow network.
    """
    base: dict[str, Any] = copy.deepcopy(existing) if existing else {}

    base.setdefault("version", "3.1")
    base.setdefault("services", {})
    base.setdefault("volumes", {})
    base.setdefault("networks", {})

    # Merge services
    for name, spec in new_services.items():
        spec.setdefault("networks", ["airflow"])
        if name in base["services"]:
            # Update existing service — overlay new keys but don't drop old ones
            _deep_update(base["services"][name], spec)
        else:
            base["services"][name] = spec

    # Merge volumes
    if new_volumes:
        for vol_name, vol_spec in new_volumes.items():
            base["volumes"].setdefault(vol_name, vol_spec)

    # Ensure airflow network is declared
    base["networks"].setdefault("airflow", None)

    return base


def merge_airflow_settings(
    existing: dict[str, Any] | None,
    new_connections: list[dict[str, Any]],
) -> dict[str, Any]:
    """Merge *new_connections* into an existing ``airflow_settings.yaml`` dict.

    - Matches by ``conn_id`` to update or append.
    - Preserves existing pools and variables.
    """
    base: dict[str, Any] = copy.deepcopy(existing) if existing else {}

    base.setdefault("airflow", {})
    base["airflow"].setdefault("connections", [])
    base["airflow"].setdefault("pools", [])
    base["airflow"].setdefault("variables", [])

    conn_list: list[dict[str, Any]] = base["airflow"]["connections"]

    # Index existing connections by conn_id for fast lookup
    idx = {c["conn_id"]: i for i, c in enumerate(conn_list) if "conn_id" in c}

    for conn in new_connections:
        cid = conn.get("conn_id")
        if cid and cid in idx:
            conn_list[idx[cid]].update(conn)
        else:
            conn_list.append(conn)

    return base


# ---------------------------------------------------------------------------
# Removal helpers
# ---------------------------------------------------------------------------

def _extract_volume_names(service_spec: dict[str, Any]) -> set[str]:
    """Return named volume names from a service's ``volumes`` list.

    Entries look like ``"vol_name:/mount/path"``.  Bind mounts (starting
    with ``./`` or ``/``) are skipped.
    """
    names: set[str] = set()
    for entry in service_spec.get("volumes", []):
        if isinstance(entry, str) and ":" in entry:
            left = entry.split(":")[0]
            if not left.startswith(("./", "/")):
                names.add(left)
    return names


def remove_docker_services(
    existing: dict[str, Any] | None,
    service_names: list[str],
    remove_orphaned_volumes: bool = True,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Remove *service_names* from a docker-compose dict.

    Returns ``(updated_compose, removed_services, removed_volumes)``.
    Services not present in *existing* are silently skipped (the caller
    can diff against *service_names* to find ``not_found`` entries).
    """
    base: dict[str, Any] = copy.deepcopy(existing) if existing else {}
    services = base.get("services", {})
    volumes_section = base.get("volumes", {})

    removed_services: list[str] = []
    orphaned_volumes: set[str] = set()

    for name in service_names:
        if name not in services:
            continue
        spec = services.pop(name)
        removed_services.append(name)
        orphaned_volumes |= _extract_volume_names(spec)

    # Determine which volumes are still referenced by remaining services.
    if remove_orphaned_volumes and orphaned_volumes:
        still_used: set[str] = set()
        for spec in services.values():
            still_used |= _extract_volume_names(spec)
        orphaned_volumes -= still_used

    removed_volumes: list[str] = []
    for vol in list(orphaned_volumes):
        if vol in volumes_section:
            del volumes_section[vol]
            removed_volumes.append(vol)

    return base, removed_services, removed_volumes


def remove_airflow_connections(
    existing: dict[str, Any] | None,
    conn_ids: list[str] | None = None,
    conn_hosts: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """Remove connections matching *conn_ids* or *conn_hosts*.

    Returns ``(updated_settings, removed_conn_ids)``.
    """
    base: dict[str, Any] = copy.deepcopy(existing) if existing else {}
    conn_list: list[dict[str, Any]] = (
        base.get("airflow", {}).get("connections", [])
    )

    id_set = set(conn_ids or [])
    host_set = set(conn_hosts or [])

    kept: list[dict[str, Any]] = []
    removed_ids: list[str] = []

    for conn in conn_list:
        cid = conn.get("conn_id", "")
        chost = conn.get("conn_host", "")
        if cid in id_set or chost in host_set:
            removed_ids.append(cid)
        else:
            kept.append(conn)

    base.setdefault("airflow", {})["connections"] = kept
    return base, removed_ids


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _deep_update(target: dict, source: dict) -> dict:
    """Recursively update *target* with *source* (mutates target)."""
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            _deep_update(target[key], value)
        else:
            target[key] = value
    return target
