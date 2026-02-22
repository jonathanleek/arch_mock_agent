#!/usr/bin/env python3
"""CLI entry point for the Astro Mock Infrastructure Agent."""

from __future__ import annotations

import argparse

from rich.console import Console
from rich.markdown import Markdown

from agent.loop import DEFAULT_MODEL, interactive_loop, run_agent

console = Console()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Astro Mock Infrastructure Agent — generate mock Docker services "
        "and Airflow connections for local Astro CLI development.",
    )
    parser.add_argument(
        "request",
        nargs="?",
        default=None,
        help="Natural-language request (omit for interactive mode).",
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Path to the Astro project directory (default: current dir).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without writing files.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"Claude model to use (default: {DEFAULT_MODEL}).",
    )

    args = parser.parse_args()

    if args.request:
        # One-shot mode
        reply = run_agent(
            request=args.request,
            project_dir=args.project_dir,
            dry_run=args.dry_run,
            model=args.model,
        )
        if reply:
            console.print(Markdown(reply))
    else:
        # Interactive mode
        interactive_loop(
            project_dir=args.project_dir,
            dry_run=args.dry_run,
            model=args.model,
        )


if __name__ == "__main__":
    main()
