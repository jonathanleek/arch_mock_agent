"""Agent loop — orchestrates Claude + tool_runner for infrastructure requests."""

from __future__ import annotations

from pathlib import Path

from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from agent.system_prompt import SYSTEM_PROMPT
from agent.tools import ALL_TOOLS, configure

console = Console()

DEFAULT_MODEL = "claude-sonnet-4-5-20250929"


def run_agent(
    request: str,
    project_dir: str | Path = ".",
    dry_run: bool = False,
    model: str = DEFAULT_MODEL,
) -> str:
    """Send a single request through the agent and return Claude's final text."""
    configure(project_dir, dry_run)
    client = Anthropic()

    messages = [{"role": "user", "content": request}]

    runner = client.beta.messages.tool_runner(
        model=model,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=messages,
        tools=ALL_TOOLS,
        max_iterations=15,
    )

    final = runner.until_done()

    # Extract text from the final response
    text_parts = [
        block.text for block in final.content if hasattr(block, "text")
    ]
    return "\n".join(text_parts)


def interactive_loop(
    project_dir: str | Path = ".",
    dry_run: bool = False,
    model: str = DEFAULT_MODEL,
) -> None:
    """Run an interactive REPL that preserves conversation history."""
    configure(project_dir, dry_run)
    client = Anthropic()

    messages: list[dict] = []

    console.print(
        Panel(
            "[bold]Astro Mock Infrastructure Agent[/bold]\n"
            "Describe the infrastructure you need in plain English.\n"
            "Type [bold]quit[/bold] or [bold]exit[/bold] to stop.",
            title="Welcome",
            border_style="blue",
        )
    )

    if dry_run:
        console.print("[yellow]Dry-run mode — no files will be written.[/yellow]\n")

    while True:
        try:
            user_input = console.input("[bold green]> [/bold green]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            console.print("Goodbye!")
            break

        messages.append({"role": "user", "content": user_input})

        with console.status("[bold cyan]Thinking...[/bold cyan]"):
            runner = client.beta.messages.tool_runner(
                model=model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                messages=messages,
                tools=ALL_TOOLS,
                max_iterations=15,
            )
            final = runner.until_done()

        # Extract and display text
        text_parts = [
            block.text for block in final.content if hasattr(block, "text")
        ]
        reply = "\n".join(text_parts)

        if reply:
            console.print()
            console.print(Markdown(reply))
            console.print()

        # Append assistant reply to history for multi-turn conversation
        messages.append({"role": "assistant", "content": final.content})
