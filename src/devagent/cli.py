from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

from .logging import get_logger
from .utils import ensure_git_root, json_dump, confirm_token
from .sandbox import Sandbox
from .config import Config
from .indexer import build_index
from .openrouter import ORClient
from .policies import CostGuard
from .patcher import apply_patch, PatchValidationError
from .gitops import add_all, commit as git_commit
from .tester import run_tests
from .constants import STATE_DIR_NAME
from .tasks import make_diff_for_goal

app = typer.Typer(add_completion=False, help="DevAgent CLI — OpenRouter-based, safe patching")
log = get_logger(__name__)

@app.callback()
def main() -> None:
    load_dotenv(override=False)

@app.command()
def init():
    """Initialize .devagent in the current Git repository."""
    root = ensure_git_root(Path.cwd())
    sb = Sandbox(root)
    sb.ensure()
    cfg = Config.load(sb.config_file)
    if not sb.config_file.exists():
        sb.config_file.write_text(cfg.to_toml(), encoding="utf-8")
        print(f"Created [bold]{STATE_DIR_NAME}/config.toml[/bold]")
    else:
        print(f"{STATE_DIR_NAME} already exists")

@app.command()
def config(
    show: bool = typer.Option(False, help="Show current config"),
    set_model: str | None = typer.Option(None, help="Set model id"),
    set_max_usd: float | None = typer.Option(None, help="Set session USD cap"),
    set_test_cmd: str | None = typer.Option(None, help="Set test/build command"),
):
    root = ensure_git_root(Path.cwd())
    sb = Sandbox(root)
    sb.ensure()
    cfg = Config.load(sb.config_file)
    changed = False
    if set_model:
        cfg.model = set_model
        changed = True
    if set_max_usd is not None:
        cfg.max_usd = float(set_max_usd)
        changed = True
    if set_test_cmd is not None:
        cfg.test_cmd = set_test_cmd
        changed = True
    if changed:
        sb.config_file.write_text(cfg.to_toml(), encoding="utf-8")
        print("Saved config")
    if show or not changed:
        print(json_dump(cfg.dump()))

@app.command()
def models():
    """List OpenRouter models (id + pricing if present)."""
    client = ORClient()
    data = client.list_models()
    tbl = Table(title="OpenRouter Models", show_lines=False)
    tbl.add_column("id")
    tbl.add_column("name")
    tbl.add_column("pricing")
    for m in data[:200]:
        pid = m.get("id", "?")
        name = m.get("name", "?")
        price = m.get("pricing", {})
        pr = f"in: {price.get('prompt', '?')}, out: {price.get('completion', '?')}" if price else "-"
        tbl.add_row(pid, name, pr)
    print(tbl)

@app.command()
def index(save: bool = typer.Option(True, help="Save to .devagent/index.json")):
    root = ensure_git_root(Path.cwd())
    sb = Sandbox(root)
    sb.ensure()
    idx = build_index(root)
    if save:
        sb.index_file.write_text(json_dump(idx), encoding="utf-8")
        print(f"Index saved to {sb.index_file}")
    else:
        print(json_dump(idx))

@app.command()
def plan(goal: str = typer.Argument(..., help="What should be changed? e.g. 'Fix TS errors'")):
    root = ensure_git_root(Path.cwd())
    sb = Sandbox(root)
    sb.ensure()
    cfg = Config.load(sb.config_file)

    if sb.index_file.exists():
        repo_summary = sb.index_file.read_text(encoding="utf-8")
    else:
        repo_summary = json_dump(build_index(root))
        sb.index_file.write_text(repo_summary, encoding="utf-8")

    client = ORClient(model=cfg.model)
    guard = CostGuard(sb, cfg)

    diff_text = make_diff_for_goal(root, goal, repo_summary, cfg.model, client, guard)
    sb.last_plan.write_text(f"GOAL: {goal}\n\n", encoding="utf-8")
    sb.last_patch.write_text(diff_text, encoding="utf-8")
    print(Panel.fit("Plan & diff generated. Review .devagent/last_patch.diff", title="PLAN"))

@app.command()
def apply(yes: bool = typer.Option(False, help="Actually write files (default: dry-run)")):
    root = ensure_git_root(Path.cwd())
    sb = Sandbox(root)
    if not sb.last_patch.exists():
        raise SystemExit("No .devagent/last_patch.diff found. Run 'devagent plan' first.")
    diff_text = sb.last_patch.read_text(encoding="utf-8")

    if not yes:
        print("Dry-run mode. No files will be written. Use --yes to apply.")
        try:
            changed = apply_patch(root, diff_text, dry_run=True)
            print("Patch validates for files:\n- " + "\n- ".join(changed))
        except PatchValidationError as e:
            raise SystemExit(f"Patch invalid: {e}")
        return

    confirm_token("Apply patch to working tree")
    try:
        changed = apply_patch(root, diff_text, dry_run=False)
    except PatchValidationError as e:
        raise SystemExit(f"Patch failed: {e}")
    add_all(root)
    print("Applied and staged changes:\n- " + "\n- ".join(changed))

@app.command()
def test(cmd: str | None = typer.Option(None, help="Override test/build command")):
    root = ensure_git_root(Path.cwd())
    sb = Sandbox(root)
    cfg = Config.load(sb.config_file)
    rc = run_tests(root, cmd or cfg.test_cmd)
    raise SystemExit(rc)

@app.command()
def commit(m: str = typer.Option(..., "-m", "--message", help="Commit message")):
    root = ensure_git_root(Path.cwd())
    git_commit(root, m)
    print("Committed.")
