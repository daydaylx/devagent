from __future__ import annotations
import os, yaml
from typing import Any, Dict, List
from .constants import PLAN_FILE, PREVIEW_CODE_FILE
from .schemas import Plan, Action

def _plan_path(workspace: str) -> str:
    return os.path.join(workspace, PLAN_FILE)

def save_plan(workspace: str, plan: Plan) -> None:
    path = _plan_path(workspace)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = {"actions": [a.model_dump() for a in plan.actions]}
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)

def load_plan(workspace: str) -> Plan:
    path = _plan_path(workspace)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    actions_raw: List[Dict[str, Any]] = data.get("actions") or []
    actions = [Action.model_validate(a) for a in actions_raw]
    return Plan(actions=actions)

def save_approval_code(workspace: str, code: str) -> None:
    ap = os.path.join(workspace, PREVIEW_CODE_FILE)
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    with open(ap, "w", encoding="utf-8") as f:
        f.write(code.strip() + "\n")
