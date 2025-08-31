from __future__ import annotations
import os, shutil
from typing import Tuple

def real(path: str) -> str:
    return os.path.realpath(path)

def ensure_inside(workspace: str, relpath: str) -> str:
    if relpath.startswith("/") or relpath.startswith("~"):
        raise ValueError("Absolute Pfade sind verboten")
    if ".." in relpath.split(os.sep):
        raise ValueError("Pfad darf kein '..' enthalten")
    root = real(workspace)
    target = real(os.path.join(root, relpath))
    if not target.startswith(root + os.sep) and target != root:
        raise ValueError("Pfad verlässt das Workspace-Jail")
    return target

def ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    os.makedirs(parent, exist_ok=True)

def trash_path(workspace: str, run_id: str, relpath: str) -> str:
    t = os.path.join(workspace, ".devagent", "trash", run_id, relpath)
    os.makedirs(os.path.dirname(t), exist_ok=True)
    return t

def move_to_trash(abs_path: str, trash_abs: str) -> None:
    if os.path.isdir(abs_path):
        raise ValueError("Ordner-Löschung ist blockiert (nur Dateien).")
    shutil.move(abs_path, trash_abs)
