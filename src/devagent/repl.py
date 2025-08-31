from __future__ import annotations
import os, getpass
from typing import List
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from .config import load_config, Config
from .scanner import project_card
from .planner import save_plan, save_approval_code
from .llm import LLMClient
from .verifier import verify_plan
from .executor import preview as preview_actions, execute as execute_actions
from .utils import is_git_repo, rand_code, json_dump, json_load
from .constants import PREVIEW_CODE_FILE, STATE_FILE
from .transcript import Transcript
from .res import read_template
from .creds import get_openrouter_key, set_openrouter_key, unset_openrouter_key, mask_key

console = Console()

def _help_text() -> str:
    return """Befehle:
/help                 – diese Hilfe
/status               – Status (Model, Mode, Workspaces)
/mode <normal|plan|auto>
/model <id>          – Modell für OpenRouter setzen (nur Session)
/scan                 – Projektkarte knapp ausgeben
/plan <ziel>          – Plan generieren (LLM)
/lint-fix [hinweis]   – Stack-sensitiver Lint/Type/Build-Fix-Plan
/test [hinweis]       – Testlauf + Fix-Plan
/conflicts [hinweis]  – Merge-Konflikte erkennen & minimal lösen
/review [hinweis]     – Code-Review & kleine Fixes
/preview              – Diffs/Commands anzeigen + Approve-Code erzeugen
/approve <code>       – Code aus Preview übernehmen
/execute              – Plan ausführen
/config               – aktive Konfiguration anzeigen
/key show|set|unset [--project] – OpenRouter API-Key verwalten
/add-dir <PATH>       – weiteren Read-Only-Kontext hinzufügen (Session)
/quit | /exit         – REPL beenden

Eingaben ohne Slash werden als Zielbeschreibung für /plan behandelt.
"""

def run_repl(workspace: str) -> None:
    ws = os.path.realpath(workspace)
    cfg = load_config(ws)
    tr = Transcript(ws)
    tr.write("SessionStart", {"session": tr.session_id, "workspace": ws})

    console.print(Panel(f"devagent REPL – Workspace: [bold]{ws}[/bold]\nSession: {tr.session_id}", title="Willkommen"))
    console.print(_help_text())

    session_model = cfg.model
    session_mode = cfg.permission_mode
    extra_dirs: List[str] = list(cfg.extra_workspaces)

    while True:
        try:
            line = input("devagent> ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Session beendet[/yellow]")
            tr.write("SessionEnd", {})
            break

        if not line:
            continue

        tr.write("UserInput", {"text": line})

        if line in ("/quit","/exit"):
            tr.write("SessionEnd", {})
            break

        if line == "/help":
            console.print(_help_text()); continue

        if line == "/status":
            console.print(Panel(
                f"Model: {session_model}\nMode: {session_mode}\nExtra Dirs: {', '.join(extra_dirs) or '-'}",
                title="Status"
            ))
            continue

        if line.startswith("/mode "):
            _, m = line.split(" ", 1)
            m = m.strip()
            if m not in ("normal","plan","auto"):
                console.print("[red]Ungültiger Modus[/red]"); continue
            session_mode = m
            console.print(f"[green]Mode gesetzt:[/green] {m}")
            tr.write("ModeChange", {"mode": m})
            continue

        if line.startswith("/model "):
            _, m = line.split(" ", 1)
            session_model = m.strip()
            console.print(f"[green]Model gesetzt:[/green] {session_model}")
            tr.write("ModelChange", {"model": session_model})
            continue

        if line.startswith("/add-dir "):
            _, p = line.split(" ", 1)
            p = os.path.realpath(p.strip())
            if not os.path.isdir(p):
                console.print("[red]Kein Verzeichnis[/red]"); continue
            if p not in extra_dirs:
                extra_dirs.append(p)
            console.print(f"[green]Kontextordner hinzugefügt:[/green] {p}")
            continue

        if line == "/config":
            console.print(f"[bold]Config (laufende Session):[/bold]\n"
                          f" model={session_model}\n mode={session_mode}\n extra_dirs={extra_dirs}\n"
                          f" allow={sorted(cfg.allow_commands)}\n disallow={sorted(cfg.disallow_commands)}")
            continue

        if line.startswith("/key"):
            parts = line.split()
            sub = parts[1] if len(parts) > 1 else "show"
            project = ("--project" in parts) or ("-p" in parts)
            scope = "project" if project else "user"
            if sub == "show":
                k = get_openrouter_key(ws)
                console.print(Panel(f"OpenRouter Key: [bold]{mask_key(k)}[/bold]", title="API-Key"))
            elif sub == "unset":
                ok = unset_openrouter_key(scope, ws)
                console.print("[green]Key entfernt[/green]" if ok else "[yellow]Kein Key vorhanden[/yellow]")
            elif sub == "set":
                console.print("Gib deinen OpenRouter API-Key ein (Eingabe unsichtbar).")
                k = getpass.getpass("Key: ")
                try:
                    path = set_openrouter_key(k, scope=scope, workspace=ws)
                    console.print(f"[green]Key gespeichert:[/green] {path} (0600)")
                except Exception as e:
                    console.print(f"[red]Fehler:[/red] {e}")
            else:
                console.print("[red]Nutze: /key show | /key set | /key unset [--project][/red]")
            continue

        if line == "/scan":
            card = project_card(ws, cfg.ignores)
            console.print(Panel(card[:4000], title="Project Card (gekürzt)"))
            continue

        if line.startswith("/lint-fix"):
            extra = line.replace("/lint-fix", "", 1).strip()
            _handle_special_goal(ws, cfg, session_model, extra_dirs, "goal_lint_fix.txt", extra, tr)
            _maybe_auto(ws, cfg, session_mode, tr)
            continue

        if line.startswith("/test"):
            extra = line.replace("/test", "", 1).strip()
            _handle_special_goal(ws, cfg, session_model, extra_dirs, "goal_test.txt", extra, tr)
            _maybe_auto(ws, cfg, session_mode, tr)
            continue

        if line.startswith("/conflicts"):
            extra = line.replace("/conflicts", "", 1).strip()
            _handle_special_goal(ws, cfg, session_model, extra_dirs, "goal_conflicts.txt", extra, tr)
            _maybe_auto(ws, cfg, session_mode, tr)
            continue

        if line.startswith("/review"):
            extra = line.replace("/review", "", 1).strip()
            _handle_special_goal(ws, cfg, session_model, extra_dirs, "goal_review.txt", extra, tr)
            _maybe_auto(ws, cfg, session_mode, tr)
            continue

        if line.startswith("/plan "):
            goal = line[len("/plan "):].strip()
            _handle_plan(ws, cfg, session_model, extra_dirs, goal, tr)
            _maybe_auto(ws, cfg, session_mode, tr)
            continue

        if line == "/preview":
            _handle_preview(ws, cfg); continue

        if line.startswith("/approve "):
            code = line.split(" ",1)[1].strip()
            _handle_approve(ws, code); continue

        if line == "/execute":
            _handle_execute(ws, cfg, tr); continue

        goal = line
        _handle_plan(ws, cfg, session_model, extra_dirs, goal, tr)
        _maybe_auto(ws, cfg, session_mode, tr)

def _maybe_auto(ws: str, cfg: Config, mode: str, tr: Transcript):
    if mode == "auto" and cfg.dangerously_skip_permissions:
        ok = _handle_preview(ws, cfg)
        if ok:
            _handle_auto_approve(ws)
            _handle_execute(ws, cfg, tr)

def _render_prompts(ws: str, cfg: Config, model: str, extra_dirs: List[str], goal_text: str) -> tuple[str,str]:
    system_prompt = read_template("system_plan.txt")
    user_prompt = read_template("user_plan.txt")

    card = project_card(ws, cfg.ignores)
    extra_info = ""
    if extra_dirs:
        extra_info = "\n\nAdditional read-only dirs:\n" + "\n".join(f"- {p}" for p in extra_dirs)

    user_prompt = user_prompt.replace("{{GOAL}}", goal_text)\
        .replace("{{WORKSPACE}}", ws)\
        .replace("{{ALLOWLIST}}", ", ".join(sorted(cfg.allow_commands)))\
        .replace("{{HAS_GIT}}", str(is_git_repo(ws)))\
        .replace("{{PROJECT_CARD}}", card + extra_info)
    return system_prompt, user_prompt

def _handle_special_goal(ws: str, cfg: Config, model: str, extra_dirs: List[str], template_name: str, extra_hint: str, tr: Transcript) -> None:
    base_goal = read_template(template_name)
    goal = base_goal + ("\n\nZusätzlicher Hinweis:\n" + extra_hint if extra_hint else "")
    _handle_plan(ws, cfg, model, extra_dirs, goal, tr)

def _handle_plan(ws: str, cfg: Config, model: str, extra_dirs: List[str], goal: str, tr: Transcript) -> None:
    console.print(f"[bold]Plan wird erstellt[/bold]")
    sys_p, usr_p = _render_prompts(ws, cfg, model, extra_dirs, goal)
    client = LLMClient(model=model, workspace=ws)
    plan, plan_hash = client.generate_plan(sys_p, usr_p)
    save_plan(ws, plan)
    tr.write("PlanCreated", {"hash": plan_hash, "actions": len(plan.actions)})
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[yellow]Plan enthält Probleme:[/yellow]")
        for e in errs: console.print(" - " + e)
    else:
        console.print("[green]Plan OK[/green] -> .devagent/plan.yaml")

def _handle_preview(ws: str, cfg: Config) -> bool:
    from .planner import load_plan
    plan = load_plan(ws)
    errs = verify_plan(plan, ws, cfg, is_git_repo(ws))
    if errs:
        console.print("[red]Plan-Fehler:[/red]")
        for e in errs: console.print(" - " + e)
        return False
    items = preview_actions(plan, ws)
    for it in items:
        header = f"[bold]{it.kind.upper()}[/bold] {it.relpath or ''} - {it.summary}"
        console.rule(header)
        if it.cmd: console.print(" ".join(it.cmd))
        if it.diff: console.print(Syntax(it.diff, "diff", theme="ansi_dark"))
    code = rand_code()
    save_approval_code(ws, code)
    console.print(Panel(f"Bestätigungscode:\n[bold]{code}[/bold]\nNutze: /approve {code}", title="Approve"))
    return True

def _handle_approve(ws: str, code: str) -> None:
    p = os.path.join(ws, PREVIEW_CODE_FILE)
    if not os.path.exists(p):
        console.print("[red]Kein Preview-Code vorhanden.[/red]"); return
    exp = open(p,"r",encoding="utf-8").read().strip()
    if code.strip() != exp:
        console.print("[red]Code falsch[/red]"); return
    json_dump(os.path.join(ws, STATE_FILE), {"approved_code": code.strip()})
    console.print("[green]Plan freigegeben.[/green] -> /execute")

def _handle_auto_approve(ws: str) -> None:
    code = rand_code()
    json_dump(os.path.join(ws, STATE_FILE), {"approved_code": code})

def _handle_execute(ws: str, cfg: Config, tr: Transcript) -> None:
    from .planner import load_plan
    state = json_load(os.path.join(ws, STATE_FILE)) or {}
    if not state.get("approved_code"):
        console.print("[red]Kein Approve. Erst /preview und /approve.[/red]"); return
    plan = load_plan(ws)
    ok, msgs = execute_actions(plan, ws, state["approved_code"], require_git_for_patches=cfg.enforce_git_for_patches)
    for m in msgs: console.print(m); tr.write("ExecMsg", {"msg": m})
    if ok:
        console.print("[green]Ausführung abgeschlossen[/green]")
        tr.write("ExecDone", {})
        try: os.remove(os.path.join(ws, STATE_FILE))
        except FileNotFoundError: pass
    else:
        console.print("[red]Fehler bei Ausführung[/red]")
        tr.write("ExecFailed", {})
