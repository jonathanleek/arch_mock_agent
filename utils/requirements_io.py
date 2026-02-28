"""Read and append to a pip requirements.txt file."""

from __future__ import annotations

from pathlib import Path


def read_requirements(path: str | Path) -> list[str]:
    """Read a requirements file and return its lines, or ``[]`` if missing."""
    p = Path(path)
    if not p.exists():
        return []
    return p.read_text().splitlines()


def _normalize_package_name(name: str) -> str:
    """Normalize a package name for comparison (PEP 503)."""
    return name.lower().replace("-", "_").replace(".", "_")


def _existing_package_names(lines: list[str]) -> set[str]:
    """Extract normalized package names from requirements lines.

    Handles version specifiers (``>=``, ``==``, ``~=``, ``!=``, ``<``, ``>``)
    and ignores comments / blank lines.
    """
    names: set[str] = set()
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        # Split on the first version specifier character.
        for sep in (">=", "==", "~=", "!=", "<=", "<", ">", "["):
            idx = stripped.find(sep)
            if idx != -1:
                stripped = stripped[:idx]
                break
        pkg = stripped.strip()
        if pkg:
            names.add(_normalize_package_name(pkg))
    return names


def add_packages(
    path: str | Path,
    packages: list[str],
    dry_run: bool = False,
) -> list[str]:
    """Append *packages* not already present in the requirements file.

    Returns the list of packages that were (or would be) added.
    Duplicate detection is case-insensitive and tolerates version specifiers
    in existing lines.
    """
    p = Path(path)
    existing_lines = read_requirements(p)
    already = _existing_package_names(existing_lines)

    to_add = [
        pkg for pkg in packages
        if _normalize_package_name(pkg) not in already
    ]

    if to_add and not dry_run:
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open("a") as f:
            # Ensure we start on a new line if file doesn't end with one.
            if existing_lines and existing_lines[-1] != "":
                f.write("\n")
            for pkg in to_add:
                f.write(pkg + "\n")

    return to_add


def remove_packages(
    path: str | Path,
    packages: list[str],
    dry_run: bool = False,
) -> list[str]:
    """Remove *packages* from the requirements file.

    Returns the list of package names that were (or would be) removed.
    Matching is case-insensitive and ignores version specifiers.
    Comments and blank lines are preserved.
    """
    p = Path(path)
    if not p.exists():
        return []

    lines = p.read_text().splitlines()
    to_remove = {_normalize_package_name(pkg) for pkg in packages}

    kept: list[str] = []
    removed: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            kept.append(line)
            continue

        # Extract the package name portion (before version specifiers).
        pkg_name = stripped
        for sep in (">=", "==", "~=", "!=", "<=", "<", ">", "["):
            idx = pkg_name.find(sep)
            if idx != -1:
                pkg_name = pkg_name[:idx]
                break
        pkg_name = pkg_name.strip()

        if _normalize_package_name(pkg_name) in to_remove:
            removed.append(pkg_name)
        else:
            kept.append(line)

    if removed and not dry_run:
        p.write_text("\n".join(kept) + "\n" if kept else "")

    return removed
