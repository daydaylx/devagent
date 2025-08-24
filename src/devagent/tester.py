from __future__ import annotations
from pathlib import Path
from .utils import run

def run_tests(root: Path, cmd: str | None, timeout: int = 900) -> int:
    if not cmd:
        return 0
    argv = cmd.split()
    code, out, err = run(argv, cwd=root, timeout=timeout)
    if out:
        print(out)
    if err:
        print(err)
    return code
