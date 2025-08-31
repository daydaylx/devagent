from __future__ import annotations
import os, tempfile
from .utils import run_cmd

def apply_patch_git(workspace: str, patch_text: str) -> bool:
    # sichere Anwendung via git apply --check, dann git apply
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".patch") as tf:
        tf.write(patch_text)
        tmp = tf.name
    try:
        code, _, err = run_cmd(["git", "apply", "--check", tmp], cwd=workspace)
        if code != 0:
            return False
        code, _, err = run_cmd(["git", "apply", tmp], cwd=workspace)
        return code == 0
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass
