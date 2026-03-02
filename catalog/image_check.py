"""Lightweight Docker image validation via registry metadata."""

from __future__ import annotations

import subprocess


def check_image_exists(image: str) -> bool:
    """Return *True* if *image* exists on its registry, *False* otherwise.

    Uses ``docker manifest inspect`` which performs a HEAD-level registry
    check without pulling any layers.  A 10-second timeout prevents network
    hiccups from blocking the tool.
    """
    try:
        result = subprocess.run(
            ["docker", "manifest", "inspect", image],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
