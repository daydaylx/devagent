from __future__ import annotations
from pathlib import Path
from .utils import run

def ensure_clean_tree(root: Path) -> None:
    code, out, err = run(["git", "status", "--porcelain"], cwd=root)
    if code != 0:
        raise SystemExit("git status failed: " + err.strip())
    # Warnungen optional – kein Hard-Stop.

def make_branch(root: Path, name: str) -> None:
    run(["git", "checkout", "-B", name], cwd=root)

def add_all(root: Path) -> None:
    run(["git", "add", "-A"], cwd=root)

def commit(root: Path, message: str) -> None:
    code, out, err = run(["git", "commit", "-m", message], cwd=root)
    if code != 0:
        raise SystemExit("git commit failed: " + (err.strip() or out.strip()))

def revert_last(root: Path) -> None:
    code, out, err = run(["git", "revert", "--no-edit", "HEAD"], cwd=root)
    if code != 0:
        raise SystemExit("git revert failed: " + err.strip())
