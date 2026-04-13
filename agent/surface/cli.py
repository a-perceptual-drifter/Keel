"""Minimal rich REPL with interaction parsing."""
from __future__ import annotations

import json
import re
from datetime import date, datetime

from rich.console import Console

from agent.ledger import write_updates
from agent.surface.thread import read_history, write_message
from core.identity.updater import apply_interaction, nuance_interest

console = Console()

COMMANDS = {
    "engage": "engage",
    "read": "engage",
    "skim": "engage",
    "noted": "acknowledged",
    "ack": "acknowledged",
    "go further": "go_further",
    "more": "go_further",
    "worth": "worth_it",
    "dismiss": "dismiss_article",
    "drop": "dismiss_article",
    "regret": "regret",
}


def _last_surface_items(db) -> list[dict]:
    row = list(
        db.query(
            "SELECT id FROM messages WHERE task='surface' ORDER BY id DESC LIMIT 1"
        )
    )
    if not row:
        return []
    msg_id = row[0]["id"]
    return list(
        db.query(
            "SELECT id, title, url, match_reason FROM articles "
            "WHERE surfaced_msg_id = ? ORDER BY id",
            [msg_id],
        )
    )


def _show_items(items: list[dict]) -> None:
    if not items:
        console.print("[dim]no items from last surface.[/dim]")
        return
    for i, it in enumerate(items, 1):
        console.print(f"  [bold]{i}[/bold]. {it['title']}")
        console.print(f"     [dim]{it['url']}[/dim]")


def _parse(line: str) -> tuple[str | None, int | None, str]:
    """Return (interaction_type, item_index, rest_text)."""
    ll = line.lower().strip()
    for kw, itype in sorted(COMMANDS.items(), key=lambda x: -len(x[0])):
        if ll.startswith(kw):
            rest = line[len(kw):].strip()
            m = re.match(r"(\d+)\b(.*)", rest)
            idx = int(m.group(1)) if m else None
            tail = m.group(2).strip() if m else rest
            return itype, idx, tail
    if ll.startswith("nuance "):
        m = re.match(r"nuance\s+(\d+)\s+(.+)", line, re.IGNORECASE)
        if m:
            return "nuance", int(m.group(1)), m.group(2)
    return None, None, line


def _apply(db, store, item: dict, interaction_type: str) -> str:
    try:
        mr = json.loads(item.get("match_reason") or "[]")
    except Exception:
        mr = []
    topic_id = mr[0]["topic_id"] if mr else None
    with store.lock():
        model = store.load()
        model, updates = apply_interaction(
            model, topic_id, interaction_type, date.today(), article_id=item["id"]
        )
        write_updates(db, updates)
        store.save(model)
    db["interactions"].insert(
        {
            "article_id": item["id"],
            "message_id": None,
            "type": interaction_type,
            "detail": None,
            "timestamp": datetime.now().isoformat(),
        }
    )
    topic = mr[0]["topic"] if mr else "(no topic)"
    return f"{interaction_type} → {topic}"


def run_repl(db, store, llm=None) -> None:
    console.print("[bold cyan]keel[/bold cyan] — type 'help' for commands, 'quit' to exit")
    items = _last_surface_items(db)
    if items:
        console.print("[dim]last surface:[/dim]")
        _show_items(items)
    while True:
        try:
            line = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line:
            continue
        if line in {"quit", "exit", ":q"}:
            break
        if line == "help":
            console.print(
                "commands: engage N | go further N | worth N | dismiss N | "
                "noted N | regret N | nuance N <text> | list | status | quit"
            )
            continue
        if line == "list":
            items = _last_surface_items(db)
            _show_items(items)
            continue
        if line == "status":
            model = store.load()
            console.print(
                f"interests: {len(model.interests)} | "
                f"interactions: {model.total_interactions} | mood: {model.mood}"
            )
            continue
        write_message(db, "user", line, task="qa")
        itype, idx, tail = _parse(line)
        if itype is None:
            console.print("[dim]noted (freeform).[/dim]")
            continue
        if not items:
            items = _last_surface_items(db)
        if idx is None or idx < 1 or idx > len(items):
            console.print(f"[red]need an item number 1..{len(items)}[/red]")
            continue
        target = items[idx - 1]
        if itype == "nuance":
            if llm is None:
                console.print("[red]nuance requires an LLM[/red]")
                continue
            try:
                mr = json.loads(target.get("match_reason") or "[]")
                interest_id = mr[0]["topic_id"] if mr else None
            except Exception:
                interest_id = None
            if not interest_id:
                console.print("[red]no interest to nuance[/red]")
                continue
            with store.lock():
                model = store.load()
                model, updates = nuance_interest(
                    model, interest_id, tail, llm, date.today()
                )
                write_updates(db, updates)
                store.save(model)
            console.print(f"[green]nuanced interest {interest_id}[/green]")
            continue
        summary = _apply(db, store, target, itype)
        console.print(f"[green]{summary}[/green]")
    console.print("bye.")
