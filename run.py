"""keel entry point. Subcommands: setup, init, schedule, chat, task, measure, status."""
from __future__ import annotations

import logging
import os
import sys
from datetime import date
from pathlib import Path

import click
import sqlite_utils
import yaml

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from agent.init import apply_migrations, reconcile_identity, seed_identity  # noqa: E402
from agent.store import JsonStore  # noqa: E402

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)
log = logging.getLogger("keel")


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def _bootstrap():
    if sys.version_info < (3, 11):
        click.echo("Python 3.11+ required", err=True)
        sys.exit(2)
    config = _load_yaml(ROOT / "config" / "config.yaml") or _load_yaml(ROOT / "config" / "config.yaml.example")
    prefs = _load_yaml(ROOT / "config" / "preferences.yaml") or _load_yaml(ROOT / "config" / "preferences.yaml.example")
    sources_cfg = _load_yaml(ROOT / "config" / "sources.yaml") or _load_yaml(ROOT / "config" / "sources.yaml.example")
    store_dir = ROOT / "store"
    store_dir.mkdir(parents=True, exist_ok=True)
    db_path = store_dir / "keel.db"
    apply_migrations(str(db_path))
    db = sqlite_utils.Database(str(db_path))
    store = JsonStore(store_dir / "identity.json")
    tmp_path = Path(str(store.path) + ".tmp.json")
    if tmp_path.exists():
        tmp_path.unlink()
    reconcile_identity(db, store)
    return config, prefs, sources_cfg, db, store


def _build_sources(sources_cfg: dict) -> list:
    from agent.sources.hn import HNSource
    from agent.sources.reddit import RedditSource
    from agent.sources.rss import RSSSource
    from agent.sources.url import URLSource
    out = []
    for entry in sources_cfg.get("sources", []) or []:
        if not entry.get("enabled", True):
            continue
        t = entry.get("type")
        name = entry.get("name")
        if t == "rss":
            out.append(RSSSource(name, entry["url"]))
        elif t == "hn":
            out.append(HNSource(name, int(entry.get("min_points", 100))))
        elif t == "reddit":
            out.append(RedditSource(name, entry["subreddit"]))
        elif t == "url":
            out.append(URLSource(name, entry["url"]))
    return out


def _build_llm(config: dict):
    llm_cfg = (config or {}).get("llm", {})
    provider = llm_cfg.get("provider", "ollama")
    if provider == "ollama":
        from agent.llm import OllamaLLM
        from agent.resources import OllamaResourceManager
        return OllamaLLM(model=llm_cfg.get("model", "llama3.2"), resource_manager=OllamaResourceManager())
    if provider == "anthropic":
        from agent.llm import AnthropicLLM
        return AnthropicLLM(api_key=llm_cfg.get("api_key") or os.environ.get("ANTHROPIC_API_KEY", ""))
    if provider == "openai":
        from agent.llm import OpenAILLM
        return OpenAILLM(
            api_key=llm_cfg.get("api_key") or os.environ.get("OPENAI_API_KEY", ""),
            base_url=llm_cfg.get("base_url"),
        )
    raise click.ClickException(f"unknown llm provider: {provider}")


def _build_embedder(config: dict):
    llm_cfg = (config or {}).get("llm", {})
    em = llm_cfg.get("embed_model", "nomic-embed-text")
    if em.startswith("nomic") or em.startswith("mxbai"):
        from agent.embedders import OllamaEmbedder
        return OllamaEmbedder(model=em)
    from agent.embedders import SentenceTransformerEmbedder
    return SentenceTransformerEmbedder()


@click.group()
def cli() -> None:
    pass


@cli.command()
def setup():
    """Hardware detection, model pull, config optimisation."""
    from agent.setup.benchmark import suggest_config
    from agent.setup.detect import detect_hardware
    profile = detect_hardware()
    click.echo(f"hardware: {profile}")
    click.echo(f"suggested config: {suggest_config(profile)}")


@cli.command()
def init():
    """Cold-start identity seed."""
    config, prefs, sources_cfg, db, store = _bootstrap()
    topics = click.prompt("Seed topics (comma-separated)", default="technology, philosophy")
    seed_identity(store, [t.strip() for t in topics.split(",") if t.strip()])
    click.echo("identity seeded.")


def _wire_jobs(config, sources_cfg, db, store, runtime=None):
    from agent.tasks.fetch import fetch_all
    from agent.tasks.reflect import run_reflect
    from agent.tasks.score import score_pending
    from agent.tasks.silence import apply_silence
    from agent.tasks.surface import run_surface

    sources = _build_sources(sources_cfg)
    llm = _build_llm(config)
    embedder = _build_embedder(config)

    def _emit(task, **payload):
        if runtime is not None:
            runtime.emit(task, payload)

    def _wrap(name, fn):
        def _w():
            _emit("task_start", task=name)
            try:
                n = fn()
                _emit("task_complete", task=name, count=n or 0)
            except Exception as e:
                _emit("error", task=name, error=str(e))
                log.exception("task %s failed", name)
        return _w

    def _fetch_and_score():
        fetch_all(db, sources)
        return score_pending(db, store.load(), embedder, llm=llm)

    jobs = {
        "fetch_and_score": _wrap("fetch_and_score", _fetch_and_score),
        "surface": _wrap("surface", lambda: run_surface(db, store, llm, runtime=runtime)),
        "silence": _wrap("silence", lambda: apply_silence(db, store)),
        "reflect": _wrap("reflect", lambda: run_reflect(db, store, llm)),
    }
    return jobs, llm


@cli.command()
def schedule():
    """Start APScheduler only (blocking; no REPL)."""
    from agent.scheduler import build_scheduler
    config, prefs, sources_cfg, db, store = _bootstrap()
    jobs, _ = _wire_jobs(config, sources_cfg, db, store)
    sched = build_scheduler(jobs, background=False)
    try:
        sched.start()
    except (KeyboardInterrupt, SystemExit):
        pass


@cli.command()
def run():
    """Unified mode: background scheduler + interactive REPL in one process."""
    from agent.runtime import Runtime
    from agent.scheduler import build_scheduler
    from agent.surface.cli import run_repl

    config, prefs, sources_cfg, db, store = _bootstrap()
    runtime = Runtime()
    jobs, llm = _wire_jobs(config, sources_cfg, db, store, runtime)
    sched = build_scheduler(jobs, background=True)
    sched.start()
    try:
        run_repl(db, store, llm, runtime=runtime, jobs=jobs)
    finally:
        try:
            sched.shutdown(wait=False)
        except Exception:
            pass


@cli.command()
def chat():
    """Open CLI REPL without scheduler."""
    from agent.surface.cli import run_repl
    config, prefs, sources_cfg, db, store = _bootstrap()
    try:
        llm = _build_llm(config) if config.get("llm") else None
    except Exception:
        llm = None
    run_repl(db, store, llm)


@cli.command()
@click.option("--task", "task_name", type=click.Choice(["fetch", "score", "surface", "silence", "reflect"]), required=True)
def task(task_name):
    """Run a single task manually."""
    config, prefs, sources_cfg, db, store = _bootstrap()
    if task_name == "fetch":
        from agent.tasks.fetch import fetch_all
        n = fetch_all(db, _build_sources(sources_cfg))
        click.echo(f"fetched {n}")
    elif task_name == "score":
        from agent.tasks.score import score_pending
        n = score_pending(db, store.load(), _build_embedder(config), llm=_build_llm(config))
        click.echo(f"scored {n}")
    elif task_name == "surface":
        from agent.tasks.surface import run_surface
        n = run_surface(db, store, _build_llm(config))
        click.echo(f"surfaced {n}")
    elif task_name == "silence":
        from agent.tasks.silence import apply_silence
        n = apply_silence(db, store)
        click.echo(f"silenced {n}")
    elif task_name == "reflect":
        from agent.tasks.reflect import run_reflect
        n = run_reflect(db, store, _build_llm(config))
        click.echo(f"reflected {n}")


@cli.command()
def status():
    """Show DB + model summary."""
    config, prefs, sources_cfg, db, store = _bootstrap()
    model = store.load()
    click.echo(f"interests: {len(model.interests)} (active: {sum(1 for i in model.interests if i.state=='active')})")
    click.echo(f"articles: {db['articles'].count if 'articles' in db.table_names() else 0}")


if __name__ == "__main__":
    cli()
