"""Generate a test-connections DAG with automatic backup."""

from __future__ import annotations

import re
import shutil
from pathlib import Path


def _sanitize_task_name(conn_id: str) -> str:
    """Convert a conn_id to a valid Python identifier prefixed with ``test_``."""
    return "test_" + re.sub(r"[^a-zA-Z0-9]", "_", conn_id)


def generate_test_dag_code(connections: list[dict]) -> str:
    """Build complete Python source for a TaskFlow DAG that tests *connections*.

    Each connection becomes a ``@task`` that calls ``_test_connection(conn_id)``.
    Handles zero connections (emits ``pass``) and deduplicates task names with a
    numeric suffix.
    """
    header = '''\
"""Auto-generated DAG to test mock infrastructure connections."""
from __future__ import annotations

from datetime import datetime

from airflow.decorators import dag, task
from airflow.hooks.base import BaseHook


def _test_connection(conn_id: str) -> str:
    conn = BaseHook.get_connection(conn_id)
    hook = conn.get_hook()
    if hasattr(hook, "test_connection"):
        status, msg = hook.test_connection()
        if not status:
            raise Exception(f"Connection test failed for {conn_id!r}: {msg}")
        return f"{conn_id}: {msg}"
    return f"{conn_id}: hook loaded ({type(hook).__name__})"


@dag(
    dag_id="test_mock_connections",
    schedule=None,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=["mock", "test"],
)
def test_mock_connections():
'''

    if not connections:
        body = "    pass\n"
        invocations = ""
    else:
        # Deduplicate task names
        seen: dict[str, int] = {}
        task_defs: list[str] = []
        invocation_lines: list[str] = []

        for conn in connections:
            conn_id = conn.get("conn_id", "unknown")
            base_name = _sanitize_task_name(conn_id)

            if base_name in seen:
                seen[base_name] += 1
                task_name = f"{base_name}_{seen[base_name]}"
            else:
                seen[base_name] = 0
                task_name = base_name

            task_defs.append(
                f"    @task\n"
                f"    def {task_name}():\n"
                f"        return _test_connection({conn_id!r})\n"
            )
            invocation_lines.append(f"    {task_name}()")

        body = "\n".join(task_defs) + "\n"
        invocations = "\n".join(invocation_lines) + "\n"

    footer = "\n\ntest_mock_connections()\n"

    return header + body + invocations + footer


def write_test_dag(
    path: str | Path,
    connections: list[dict],
    dry_run: bool = False,
) -> tuple[str, str]:
    """Generate and write the test-connections DAG.

    Returns ``(path_str, source)`` — the written path and the generated code.
    Backs up an existing file before overwriting.
    """
    p = Path(path)
    source = generate_test_dag_code(connections)

    if dry_run:
        return (str(p), source)

    if p.exists():
        bak = p.with_suffix(p.suffix + ".bak")
        shutil.copy2(p, bak)

    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(source)
    return (str(p), source)
