from __future__ import annotations
import difflib
from pathlib import Path

def preview_changes(root: Path, paths: list[str]) -> str:
    out = []
    for rel in paths:
        p = root / rel
        before = p.read_text(encoding="utf-8") if p.exists() else ""
        after = before
        diff = difflib.unified_diff(
            before.splitlines(), after.splitlines(),
            fromfile=f"a/{rel}", tofile=f"b/{rel}", lineterm=""
        )
        out.extend(list(diff))
    return "\n".join(out)
