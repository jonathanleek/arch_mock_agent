"""Port reservation and allocation for mock infrastructure services."""

# Ports reserved by Astro CLI / Airflow itself — never allocate these
RESERVED_PORTS: dict[int, str] = {
    5432: "airflow-metadata-db (postgres)",
    8080: "airflow-webserver",
    6379: "airflow-triggerer (redis)",
    8793: "airflow-worker (log server)",
    5555: "flower (celery monitor)",
}

# Track ports allocated during this session to avoid collisions
_allocated: set[int] = set()


def allocate_port(default: int) -> int:
    """Return *default* if available, otherwise increment until a free port is found.

    A port is considered unavailable if it is in RESERVED_PORTS or was
    already handed out by a previous call in the same process.
    """
    port = default
    while port in RESERVED_PORTS or port in _allocated:
        port += 1
    _allocated.add(port)
    return port


def reset_allocated() -> None:
    """Clear the session allocation set (useful between test runs)."""
    _allocated.clear()
