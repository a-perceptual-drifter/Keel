"""Minimal rich REPL for chat interactions."""
from __future__ import annotations

import sys

from rich.console import Console

from agent.surface.thread import read_history, write_message

console = Console()


def run_repl(db, store, llm=None) -> None:
    console.print("[bold cyan]keel[/bold cyan] — type 'quit' to exit")
    for m in read_history(db, 20):
        role = m["role"]
        console.print(f"[dim]{role}:[/dim] {m['content']}")
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in {"quit", "exit", ":q"}:
            break
        write_message(db, "user", line, task="qa")
        console.print(f"[dim]noted.[/dim]")
    console.print("bye.")
