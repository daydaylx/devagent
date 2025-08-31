from __future__ import annotations
from typing import List
import os, re
from .schemas import Plan, Action
from .jail import ensure_inside
from .config import Config
from .utils import normalize_cmd, ensure_no_pipes_redirs

FORBIDDEN_RE = re.compile(r"(?:^|/)\.\.(?:/|$)")

def verify_plan(plan: Plan, workspace: str, cfg: Config, has_git: bool) -> List[str]:
    errs: List[str] = []
    if len(plan.actions) == 0:
        errs.append("Plan enthält keine Aktionen.")
    if len(plan.actions) > cfg.max_actions:
        errs.append(f"Zu viele Aktionen: {len(plan.actions)} > {cfg.max_actions}")

    for i, a in enumerate(plan.actions):
        if a.type in ("create","edit","delete"):
            if not a.file:
                errs.append(f"[{i}] file fehlt")
                continue
            if FORBIDDEN_RE.search(a.file):
                errs.append(f"[{i}] '..' im Pfad verboten: {a.file}")
                continue
            try:
                ensure_inside(workspace, a.file)
            except Exception as e:
                errs.append(f"[{i}] Pfad ungültig: {e}")
            if a.type == "edit" and (not a.content and not a.patch):
                errs.append(f"[{i}] edit benötigt content oder patch")
            if a.type == "edit" and a.patch and cfg.enforce_git_for_patches and not has_git:
                errs.append(f"[{i}] patch benötigt Git-Repo (enforce_git_for_patches=true)")
        elif a.type == "run":
            argv = normalize_cmd(a.cmd or [])
            if not argv:
                errs.append(f"[{i}] run ohne cmd")
                continue
            if not ensure_no_pipes_redirs(argv):
                errs.append(f"[{i}] Pipes/Redirections/Shell-Operatoren verboten")
            base = os.path.basename(argv[0])
            if base in cfg.disallow_commands:
                errs.append(f"[{i}] Befehl explizit verboten: {base}")
            if base not in cfg.allow_commands:
                errs.append(f"[{i}] Befehl nicht erlaubt: {base}")
            if any(x in ("sudo",) for x in argv):
                errs.append(f"[{i}] 'sudo' verboten")
        else:
            errs.append(f"[{i}] unbekannter Typ: {a.type}")
    return errs
