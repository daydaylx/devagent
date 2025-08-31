from __future__ import annotations
import os, difflib
from typing import List, Tuple
from .schemas import Plan, Action
from .jail import ensure_inside, ensure_parent, trash_path, move_to_trash
from .utils import read_text_limited, run_cmd, is_git_repo, git_commit_all
from .patcher import apply_patch_git
from .hooks import run_hooks

class PreviewItem:
    def __init__(self, kind: str, relpath: str | None, summary: str, diff: str | None = None, cmd: List[str] | None = None):
        self.kind = kind
        self.relpath = relpath
        self.summary = summary
        self.diff = diff
        self.cmd = cmd

def preview(plan: Plan, workspace: str) -> List[PreviewItem]:
    items: List[PreviewItem] = []
    root = os.path.realpath(workspace)
    for a in plan.actions:
        if a.type == "create":
            target = ensure_inside(workspace, a.file or "")
            before = ""
            after = a.content or ""
            df = "\n".join(difflib.unified_diff(
                before.splitlines(), after.splitlines(),
                fromfile=f"a/{a.file}", tofile=f"b/{a.file}", lineterm=""
            ))
            items.append(PreviewItem("create", a.file, f"Create file ({len(after.splitlines())} lines)", df))
        elif a.type == "delete":
            target = ensure_inside(workspace, a.file or "")
            exists = os.path.exists(target)
            size = os.path.getsize(target) if exists and os.path.isfile(target) else 0
            items.append(PreviewItem("delete", a.file, f"Delete file (exists={exists}, bytes={size})"))
        elif a.type == "edit":
            target = ensure_inside(workspace, a.file or "")
            before = ""
            if os.path.exists(target):
                before = read_text_limited(target, 1024*1024)
            if a.content is not None:
                after = a.content
                df = "\n".join(difflib.unified_diff(
                    before.splitlines(), after.splitlines(),
                    fromfile=f"a/{a.file}", tofile=f"b/{a.file}", lineterm=""
                ))
                items.append(PreviewItem("edit", a.file, f"Edit file via content ({len((a.content or '').splitlines())} lines)", df))
            else:
                items.append(PreviewItem("edit", a.file, "Edit via patch", diff=a.patch))
        elif a.type == "run":
            cmd = a.cmd or []
            items.append(PreviewItem("run", None, "Run command", cmd=cmd))
    return items

def execute(plan: Plan, workspace: str, run_id: str, require_git_for_patches: bool = True) -> Tuple[bool, List[str]]:
    root = os.path.realpath(workspace)
    msgs: List[str] = []
    had_error = False

    # Git-Snapshot vor Ausführung
    if is_git_repo(root):
        sha = git_commit_all(root, f"devagent pre: {run_id}")
        msgs.append(f"Git snapshot: {sha or 'failed'}")

    for a in plan.actions:
        try:
            # PreToolUse Hooks
            allowed, hook_msgs = run_hooks(workspace, "PreToolUse", {"action": a.model_dump(), "run_id": run_id})
            msgs.extend(hook_msgs)
            if not allowed:
                raise RuntimeError("Aktion durch PreToolUse-Hook blockiert")

            if a.type == "create":
                target = ensure_inside(workspace, a.file or "")
                ensure_parent(target)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(a.content or "")
                msgs.append(f"CREATE {a.file}")
            elif a.type == "delete":
                target = ensure_inside(workspace, a.file or "")
                if os.path.exists(target) and os.path.isfile(target):
                    trash_abs = trash_path(workspace, run_id, a.file or "")
                    ensure_parent(trash_abs)
                    move_to_trash(target, trash_abs)
                    msgs.append(f"DELETE {a.file} -> trash")
                else:
                    msgs.append(f"DELETE {a.file} (skip: not a file)")
            elif a.type == "edit":
                target = ensure_inside(workspace, a.file or "")
                if a.content is not None:
                    ensure_parent(target)
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(a.content)
                    msgs.append(f"EDIT {a.file} (content)")
                else:
                    if require_git_for_patches and not is_git_repo(root):
                        raise RuntimeError("patch-edit ohne Git-Repo verboten")
                    ok = apply_patch_git(root, a.patch or "")
                    if not ok:
                        raise RuntimeError("git apply fehlgeschlagen")
                    msgs.append(f"EDIT {a.file} (patch)")
            elif a.type == "run":
                code, out, err = run_cmd(a.cmd or [], cwd=root, timeout=1800)
                msgs.append(f"RUN {' '.join(a.cmd or [])} -> code={code}")
                if out.strip():
                    msgs.append(f"STDOUT:\n{out.strip()}")
                if err.strip():
                    msgs.append(f"STDERR:\n{err.strip()}")
                if code != 0:
                    raise RuntimeError(f"Command exit {code}")

            # PostToolUse Hooks
            _, hook_msgs2 = run_hooks(workspace, "PostToolUse", {"action": a.model_dump(), "run_id": run_id})
            msgs.extend(hook_msgs2)

        except Exception as e:
            msgs.append(f"ERROR {a.type} {getattr(a,'file',None)}: {e}")
            had_error = True
            break

    return (not had_error), msgs
