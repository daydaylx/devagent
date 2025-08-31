from __future__ import annotations
import os, sys, yaml, json, typer, getpass
from typing import Optional, List
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from .config import load_config
from .scanner import project_card
from .llm import LLMClient
from .planner import save_plan, load_plan, save_approval_code
from .verifier import verify_plan
from .utils import is_git_repo, json_load, json_dump, rand_code
from .constants import PREVIEW_CODE_FILE, PLAN_FILE, STATE_FILE
from .executor import preview as preview_actions, execute as execute_actions
from .audit import log_event
from .repl import run_repl
from .res import read_template
from .creds import get_openrouter_key, set_openrouter_key, unset_openrouter_key, mask_key

console = Console()
app = typer.Typer(invoke_without_command=True, no_args_is_help=False)

def _build_prompts(ws: str, goal: str):
    cfg = load_config(ws)
    system_prompt = read_template("system_plan.txt")
    user_prompt = read_template("user_plan.txt")
    card = project_card(ws, cfg.ignores)
    user_prompt = user_prompt \
        .replace("{{GOAL}}", goal)\
        .replace("{{WORKSPACE}}", ws)\
        .replace("{{ALLOWLIST}}", ", ".join(sorted(cfg.allow_commands)))\
        .replace("{{HAS_GIT}}", str(is_git_repo(ws)))\
        .replace("{{PROJECT_CARD}}", card)
    return system_prompt, user_prompt, cfg

@app.callback()
def main(
    ctx: typer.Context,
    workspace: str = typer.Option(".", "--workspace", "-w", help="Projektwurzel"),
    prompt: Optional[str] = typer.Option(None, "--prompt", "-p", help="Headless: Zielbeschreibung (Plan in YAML)"),
    output_format: str = typer.Option("yaml", "--output-format", "-o", help="text|yaml|json"),
):
    ws = os.path.realpath(workspace)
    if ctx.invoked_subcommand is not None:
        return
    if prompt is not None:
        system_prompt, user_prompt, cfg = _build_prompts(ws, prompt)
        client = LLMClient(model=cfg.model, workspace=ws)
        plan, _ = client.generate_plan(system_prompt, user_prompt)
        if output_format == "json":
            typer.echo(json.dumps({"actions": [a.model_dump() for a in plan.actions]}, ensure_ascii=False, indent=2))
        elif output_format in ("yaml","text"):
            out = {"actions": [a.model_dump() for a in plan.actions]}
            typer.echo(yaml.safe_dump(out, sort_keys=False, allow_unicode=True))
        else:
            typer.echo("unknown output-format", err=True); raise typer.Exit(2)
        raise typer.Exit()
    else:
        run_repl(ws); raise typer.Exit()

@app.command()
def scan(workspace: str = typer.Option(".", "--workspace", "-w", help="Projektwurzel")):
    ws = os.path.realpath(workspace)
    cfg = load_config(ws)
    card = project_card(ws, cfg.ignores)
    console.print(Panel(card, title="Project Card (gekürzt)"))

@app.command()
def summarize(workspace: str = typer.Option(".", "--workspace", "-w")):
    ws = os.path.realpath(workspace)
    cfg = load_config(ws)
    card = project_card(ws, cfg.ignores)
    console.print(card)

@app.command()
def plan(
    goal: str = typer.Option(..., "--goal", "-g", help="Zielbeschreibung für Änderungen"),
    workspace: str = typer.Option(".", "--workspace", "-w"),
    add_dir: List[str] = typer.Option([], "--add-dir", help="Zusätzliche Read-Only-Verzeichnisse"),
):
    ws = os.path.realpath(workspace)
    system_prompt, user_prompt, cfg = _build_prompts(ws, goal)
    client = LLMClient(model=cfg.model, workspace=ws)
    plan, _ = client.generate_plan(system_prompt, user_prompt)
    save_plan(ws, plan)
    console.print("[green]Plan gespeichert:[/green] " + os.path.join(ws, PLAN_FILE))
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[yellow]Plan enthält Probleme:[/yellow]")
        for e in errs: console.print(f" - {e}")
    else:
        console.print("[green]Plan OK[/green]")

@app.command()
def lint_fix(
    workspace: str = typer.Option(".", "--workspace", "-w"),
    hint: str = typer.Option("", "--hint", help="Zusätzlicher Hinweis für den Fix-Plan"),
):
    ws = os.path.realpath(workspace)
    base_goal = read_template("goal_lint_fix.txt")
    goal = base_goal + ("\n\nZusätzlicher Hinweis:\n" + hint if hint else "")
    system_prompt, user_prompt, cfg = _build_prompts(ws, goal)
    client = LLMClient(model=cfg.model, workspace=ws)
    plan, _ = client.generate_plan(system_prompt, user_prompt)
    save_plan(ws, plan)
    console.print("[green]Plan gespeichert:[/green] " + os.path.join(ws, PLAN_FILE))
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[yellow]Plan enthält Probleme:[/yellow]")
        for e in errs: console.print(f" - {e}")
    else:
        console.print("[green]Plan OK[/green]")

@app.command()
def test(
    workspace: str = typer.Option(".", "--workspace", "-w"),
    hint: str = typer.Option("", "--hint", help="Zusätzlicher Hinweis für den Test-Plan"),
):
    ws = os.path.realpath(workspace)
    base_goal = read_template("goal_test.txt")
    goal = base_goal + ("\n\nZusätzlicher Hinweis:\n" + hint if hint else "")
    system_prompt, user_prompt, cfg = _build_prompts(ws, goal)
    client = LLMClient(model=cfg.model, workspace=ws)
    plan, _ = client.generate_plan(system_prompt, user_prompt)
    save_plan(ws, plan)
    console.print("[green]Plan gespeichert:[/green] " + os.path.join(ws, PLAN_FILE))
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[yellow]Plan enthält Probleme:[/yellow]")
        for e in errs: console.print(f" - {e}")
    else:
        console.print("[green]Plan OK[/green]")

@app.command()
def conflicts(
    workspace: str = typer.Option(".", "--workspace", "-w"),
    hint: str = typer.Option("", "--hint", help="Zusätzlicher Hinweis für den Konflikt-Plan"),
):
    ws = os.path.realpath(workspace)
    base_goal = read_template("goal_conflicts.txt")
    goal = base_goal + ("\n\nZusätzlicher Hinweis:\n" + hint if hint else "")
    system_prompt, user_prompt, cfg = _build_prompts(ws, goal)
    client = LLMClient(model=cfg.model, workspace=ws)
    plan, _ = client.generate_plan(system_prompt, user_prompt)
    save_plan(ws, plan)
    console.print("[green]Plan gespeichert:[/green] " + os.path.join(ws, PLAN_FILE))
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[yellow]Plan enthält Probleme:[/yellow]")
        for e in errs: console.print(f" - {e}")
    else:
        console.print("[green]Plan OK[/green]")

@app.command()
def review(
    workspace: str = typer.Option(".", "--workspace", "-w"),
    hint: str = typer.Option("", "--hint", help="Zusätzlicher Hinweis für das Review"),
):
    ws = os.path.realpath(workspace)
    base_goal = read_template("goal_review.txt")
    goal = base_goal + ("\n\nZusätzlicher Hinweis:\n" + hint if hint else "")
    system_prompt, user_prompt, cfg = _build_prompts(ws, goal)
    client = LLMClient(model=cfg.model, workspace=ws)
    plan, _ = client.generate_plan(system_prompt, user_prompt)
    save_plan(ws, plan)
    console.print("[green]Plan gespeichert:[/green] " + os.path.join(ws, PLAN_FILE))
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[yellow]Plan enthält Probleme:[/yellow]")
        for e in errs: console.print(f" - {e}")
    else:
        console.print("[green]Plan OK[/green]")

@app.command()
def preview(workspace: str = typer.Option(".", "--workspace", "-w")):
    ws = os.path.realpath(workspace)
    cfg = load_config(ws)
    plan = load_plan(ws)
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[red]Plan-Fehler:[/red]")
        for e in errs: console.print(" - " + e); raise typer.Exit(2)
    items = preview_actions(plan, ws)
    for it in items:
        header = f"[bold]{it.kind.upper()}[/bold] {it.relpath or ''} - {it.summary}"
        console.rule(header)
        if it.cmd: console.print(" ".join(it.cmd))
        if it.diff: console.print(Syntax(it.diff, "diff", theme="ansi_dark"))
    code = rand_code()
    save_approval_code(ws, code)
    console.print(Panel(f"Bestätigungscode:\n[bold]{code}[/bold]\nNutze: devagent approve -w {ws} --code {code}", title="Approve"))

@app.command()
def approve(code: str = typer.Option(..., "--code"), workspace: str = typer.Option(".", "--workspace", "-w")):
    ws = os.path.realpath(workspace)
    path = os.path.join(ws, PREVIEW_CODE_FILE)
    if not os.path.exists(path):
        console.print("[red]Kein Preview-Code vorhanden. Erst 'preview' ausführen.[/red]"); raise typer.Exit(2)
    with open(path, "r", encoding="utf-8") as f:
        expected = f.read().strip()
    if code.strip() != expected:
        console.print("[red]Code falsch.[/red]"); raise typer.Exit(2)
    json_dump(os.path.join(ws, STATE_FILE), {"approved_code": code.strip()})
    console.print("[green]Plan freigegeben.[/green] Jetzt 'execute' ausführen.")

@app.command()
def execute(workspace: str = typer.Option(".", "--workspace", "-w")):
    ws = os.path.realpath(workspace)
    cfg = load_config(ws)
    state = json_load(os.path.join(ws, STATE_FILE)) or {}
    approved = state.get("approved_code")
    if not approved:
        console.print("[red]Kein Approve gefunden. Erst 'preview' und 'approve'.[/red]"); raise typer.Exit(2)
    plan = load_plan(ws)
    ok, msgs = execute_actions(plan, ws, approved, require_git_for_patches=cfg.enforce_git_for_patches)
    for m in msgs:
        console.print(m)
        log_event(ws, approved, "step", {"msg": m})
    if ok:
        console.print("[green]Ausführung abgeschlossen.[/green]")
        log_event(ws, approved, "done", {})
        try: os.remove(os.path.join(ws, STATE_FILE))
        except FileNotFoundError: pass
    else:
        console.print("[red]Fehler. Siehe Logs.[/red]")
        log_event(ws, approved, "failed", {})

@app.command()
def logs(workspace: str = typer.Option(".", "--workspace", "-w"), run_id: str = typer.Option(None, "--run-id")):
    ws = os.path.realpath(workspace)
    logdir = os.path.join(ws, ".devagent", "logs")
    if run_id:
        p = os.path.join(logdir, f"{run_id}.jsonl")
        if not os.path.exists(p):
            console.print("[red]Keine Logs für run_id[/red]"); raise typer.Exit(2)
        with open(p, "r", encoding="utf-8") as f:
            console.print(f.read())
        raise typer.Exit()
    from glob import glob
    files = sorted(glob(os.path.join(logdir, "*.jsonl")))
    from rich.table import Table
    table = Table("run_id", "size")
    for f in files:
        rid = os.path.basename(f).split(".")[0]
        size = os.path.getsize(f)
        table.add_row(rid, str(size))
    console.print(table)

@app.command()
def repl(workspace: str = typer.Option(".", "--workspace", "-w")):
    ws = os.path.realpath(workspace)
    run_repl(ws)

@app.command("key")
def key_cmd(
    workspace: str = typer.Option(".", "--workspace", "-w"),
    action: str = typer.Argument(..., metavar="[set|show|unset]"),
    scope: str = typer.Option("user", "--scope", help="user|project"),
):
    ws = os.path.realpath(workspace)
    scope = scope.lower().strip()
    if scope not in ("user","project"):
        console.print("[red]scope muss 'user' oder 'project' sein[/red]"); raise typer.Exit(2)
    action = action.lower().strip()
    if action == "show":
        k = get_openrouter_key(ws)
        console.print(f"OpenRouter Key: [bold]{mask_key(k)}[/bold]")
        return
    if action == "unset":
        ok = unset_openrouter_key(scope, ws)
        console.print("[green]Key entfernt[/green]" if ok else "[yellow]Kein Key vorhanden[/yellow]")
        return
    if action == "set":
        console.print("Gib deinen OpenRouter API-Key ein (wird nicht angezeigt):")
        key = getpass.getpass("Key: ")
        try:
            path = set_openrouter_key(key, scope=scope, workspace=ws)
            console.print(f"[green]Key gespeichert in[/green] {path} (0600).")
        except Exception as e:
            console.print(f"[red]Fehler:[/red] {e}"); raise typer.Exit(2)
        return
    console.print("[red]Unbekannte Aktion. Nutze set|show|unset[/red]"); raise typer.Exit(2)

if __name__ == "__main__":
    app()
