#!/usr/bin/env python3
"""Backwards-compatible shim — delegates to agent.cli.main()."""

from agent.cli import main

if __name__ == "__main__":
    main()
