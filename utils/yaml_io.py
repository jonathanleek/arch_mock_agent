"""Safe YAML read / write with automatic backup."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

import yaml


def read_yaml(path: str | Path) -> dict[str, Any] | None:
    """Read a YAML file and return its contents as a dict, or None if missing."""
    p = Path(path)
    if not p.exists():
        return None
    with p.open("r") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else None


def write_yaml(path: str | Path, data: dict[str, Any]) -> Path:
    """Write *data* to a YAML file, backing up any existing file first.

    Returns the path that was written.
    """
    p = Path(path)
    if p.exists():
        bak = p.with_suffix(p.suffix + ".bak")
        shutil.copy2(p, bak)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    return p
