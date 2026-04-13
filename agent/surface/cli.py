"""Rich REPL with async event draining via prompt_toolkit."""
from __future__ import annotations

import json
import re
import threading
from datetime import date, datetime

from rich.console import Console

from agent.ledger import write_updates
from agent.runtime import Runtime
from agent.surface.thread import read_history, write_message
from core.identity.updater import apply_interaction, nuance_interest
from core.expansion.mood import MOODS

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
    if ll.startswith("mood "):
        return "mood", None, line[5:].strip()
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


def _set_mood(store, new_mood: str) -> str:
    new_mood = new_mood.strip().lower()
    if new_mood not in MOODS:
        return f"unknown mood: {new_mood} (valid: {', '.join(sorted(MOODS))})"
    with store.lock():
        from dataclasses import replace
        model = store.load()
        model = replace(model, mood=new_mood, mood_set_at=datetime.now(), mood_inferred=False)
        store.save(model)
    return f"mood → {new_mood}"


def _drain_events(runtime: Runtime | None) -> None:
    if runtime is None:
        return
    for ev in runtime.drain():
        if ev.type == "new_message":
            console.print(
                f"\n[bold cyan]↪ new surface message[/bold cyan] "
                f"([dim]{ev.payload.get('count', 0)} items[/dim])"
            )
            console.print(ev.payload.get("content", ""))
        elif ev.type == "task_start":
            console.print(f"[dim]• {ev.payload.get('task', '?')} started[/dim]")
        elif ev.type == "task_complete":
            console.print(
                f"[dim]• {ev.payload.get('task', '?')} complete "
                f"({ev.payload.get('count', 0)})[/dim]"
            )
        elif ev.type == "error":
            console.print(f"[red]✗ {ev.payload.get('task', '?')}: {ev.payload.get('error', '')}[/red]")


def _get_session():
    from prompt_toolkit import PromptSession
    from prompt_toolkit.patch_stdout import patch_stdout
    return PromptSession(), patch_stdout


TASK_COMMANDS = {"fetch": "fetch_and_score", "score": "fetch_and_score", "surface": "surface", "silence": "silence", "reflect": "reflect"}

SUMMARIZE_ALIASES = ("summarize", "summarise", "sum", "tldr")


def _fetch_article_body(url: str) -> str:
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if not downloaded:
            return ""
        return trafilatura.extract(downloaded) or ""
    except Exception:
        return ""


def _summarize_item(db, llm, item: dict) -> str:
    row = next(iter(db.query("SELECT content FROM articles WHERE id = ?", [item["id"]])), None)
    body = (row or {}).get("content") or ""
    if len(body) < 200:
        fetched = _fetch_article_body(item["url"])
        if fetched:
            body = fetched
            try:
                db["articles"].update(int(item["id"]), {"content": body})
            except Exception:
                pass
    if not body:
        return f"(could not retrieve body of {item['url']})"
    body = body[:8000]
    system = (
        "You summarize articles for a reader who has not opened the link. "
        "Return 3-6 bullet points covering the core claims, evidence, and any "
        "surprising or non-obvious points. No preamble, no meta-commentary, "
        "no 'the article says'. If the text is too thin to summarize, say so in one line."
    )
    prompt = f"Title: {item['title']}\nURL: {item['url']}\n\n---\n{body}\n---"
    try:
        return llm.complete(system, prompt, max_tokens=400).strip()
    except Exception as e:
        return f"(summarization failed: {e})"



def run_repl(db, store, llm=None, runtime: Runtime | None = None, jobs: dict | None = None) -> None:
    console.print("[bold cyan]keel[/bold cyan] — type 'help' for commands, 'quit' to exit")
    items = _last_surface_items(db)
    if items:
        console.print("[dim]last surface:[/dim]")
        _show_items(items)

    session, patch_stdout = _get_session()
    while True:
        _drain_events(runtime)
        try:
            with patch_stdout():
                line = session.prompt("> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        _drain_events(runtime)
        if not line:
            continue
        if line in {"quit", "exit", ":q"}:
            break
        if line == "help":
            console.print("[bold]keel commands[/bold]")
            console.print("")
            console.print("[bold cyan]reacting to surfaced items[/bold cyan] [dim](N = item number from last surface)[/dim]")
            console.print("  [bold]engage N[/bold]       weak positive — you read it (+0.03)")
            console.print("  [bold]go further N[/bold]   stronger positive — want more like this (+0.10)")
            console.print("  [bold]worth N[/bold]        strongest positive — this was worth the attention (+0.15)")
            console.print("  [bold]noted N[/bold]        acknowledged, no signal either way")
            console.print("  [bold]dismiss N[/bold]      weak negative — not for me right now (-0.02)")
            console.print("  [bold]regret N[/bold]       strong negative — wasted my time (-0.15)")
            console.print("  [bold]nuance N <text>[/bold]  refine the matched interest in natural language")
            console.print("  [bold]summarize N[/bold]    LLM summary of item N ([dim]aliases: sum, tldr[/dim])")
            console.print("[dim]  aliases: read/skim=engage, more=go further, drop=dismiss, ack=noted[/dim]")
            console.print("")
            console.print("[bold cyan]inspecting state[/bold cyan]")
            console.print("  [bold]list[/bold]           show items from the last surface")
            console.print("  [bold]status[/bold]         interest count, total interactions, current mood")
            console.print("  [bold]mood <name>[/bold]    set mood (curious, restless, focused, tired, open, ...)")
            console.print("")
            console.print("[bold cyan]triggering tasks[/bold cyan] [dim](dispatched on a background thread)[/dim]")
            console.print("  [bold]fetch[/bold]          pull new items from all sources and score them")
            console.print("  [bold]score[/bold]          same as fetch (fetch+score are one job)")
            console.print("  [bold]surface[/bold]        select + render a new surface message now")
            console.print("  [bold]silence[/bold]        apply weak negative to items left unanswered past window")
            console.print("  [bold]reflect[/bold]        decay weights, transition interest states, write summary")
            console.print("")
            console.print("[bold cyan]session[/bold cyan]")
            console.print("  [bold]help[/bold]           this message")
            console.print("  [bold]quit[/bold]           exit ([dim]also: exit, :q[/dim])")
            continue
        if line in TASK_COMMANDS:
            if not jobs:
                console.print("[red]tasks unavailable (no job runner)[/red]")
                continue
            job_name = TASK_COMMANDS[line]
            job = jobs.get(job_name)
            if job is None:
                console.print(f"[red]no such job: {job_name}[/red]")
                continue
            threading.Thread(target=job, daemon=True).start()
            console.print(f"[dim]• {line} dispatched[/dim]")
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
        ll = line.lower().strip()
        sum_match = None
        for kw in SUMMARIZE_ALIASES:
            if ll.startswith(kw):
                rest = line[len(kw):].strip()
                m = re.match(r"(\d+)", rest)
                if m:
                    sum_match = int(m.group(1))
                break
        if sum_match is not None:
            if llm is None:
                console.print("[red]summarize requires an LLM[/red]")
                continue
            if not items:
                items = _last_surface_items(db)
            if sum_match < 1 or sum_match > len(items):
                console.print(f"[red]need an item number 1..{len(items)}[/red]")
                continue
            target = items[sum_match - 1]
            console.print(f"[dim]summarizing {target['title']}...[/dim]")
            console.print(_summarize_item(db, llm, target))
            continue
        itype, idx, tail = _parse(line)
        if itype is None:
            console.print("[dim]noted (freeform).[/dim]")
            continue
        if itype == "mood":
            console.print(f"[green]{_set_mood(store, tail)}[/green]")
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

    if runtime is not None:
        runtime.shutdown.set()
    console.print("bye.")
