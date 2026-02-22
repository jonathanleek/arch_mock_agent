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
