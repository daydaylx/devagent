from __future__ import annotations
import os, tomllib
from dataclasses import dataclass, field
from typing import List, Set

DEFAULT_ALLOW = [
    "pytest", "python", "ruff", "black", "mypy",
    "eslint", "tsc", "npm", "pnpm", "yarn", "make",
    "git"
]

@dataclass
class Config:
    model: str = "deepseek/deepseek-coder"
    allow_commands: Set[str] = field(default_factory=lambda: set(DEFAULT_ALLOW))
    disallow_commands: Set[str] = field(default_factory=set)
    max_actions: int = 20
    net_allowed: bool = False
    enforce_git_for_patches: bool = True
    ignores: List[str] = field(default_factory=list)

    # Phase-1-Erweiterungen
    permission_mode: str = "normal"  # normal|plan|auto
    dangerously_skip_permissions: bool = False
    extra_workspaces: List[str] = field(default_factory=list)  # read-only Kontext

def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        if os.path.exists(p):
            return p
    return None

def load_config(workspace: str) -> Config:
    paths = []
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        paths.append(os.path.join(xdg, "devagent", "config.toml"))
    paths.append(os.path.join(workspace, ".devagent", "config.toml"))

    data = {}
    p = _first_existing(paths)
    if p:
        with open(p, "rb") as f:
            data = tomllib.load(f)

    cfg = Config()
    # einfache Zuordnungen
    if "model" in data: cfg.model = str(data["model"])
    if "max_actions" in data: cfg.max_actions = int(data["max_actions"])
    if "net_allowed" in data: cfg.net_allowed = bool(data["net_allowed"])
    if "enforce_git_for_patches" in data: cfg.enforce_git_for_patches = bool(data["enforce_git_for_patches"])
    if "ignores" in data and isinstance(data["ignores"], list): cfg.ignores = [str(x) for x in data["ignores"]]

    # Sets
    if "allow_commands" in data and isinstance(data["allow_commands"], list):
        cfg.allow_commands = set(str(x) for x in data["allow_commands"])
    if "disallow_commands" in data and isinstance(data["disallow_commands"], list):
        cfg.disallow_commands = set(str(x) for x in data["disallow_commands"])

    # Phase-1
    if "permission_mode" in data: cfg.permission_mode = str(data["permission_mode"])
    if "dangerously_skip_permissions" in data: cfg.dangerously_skip_permissions = bool(data["dangerously_skip_permissions"])
    if "extra_workspaces" in data and isinstance(data["extra_workspaces"], list):
        cfg.extra_workspaces = [str(x) for x in data["extra_workspaces"]]

    return cfg
