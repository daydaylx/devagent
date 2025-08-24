from __future__ import annotations
from pathlib import Path
from unidiff import PatchSet
from .utils import is_safe_path, write_text_safe

class PatchValidationError(Exception):
    pass

def parse_unified_diff(diff_text: str) -> PatchSet:
    try:
        ps = PatchSet(diff_text.splitlines(True))
    except Exception as e:
        raise PatchValidationError(f"Invalid unified diff: {e}")
    if len(ps) == 0:
        raise PatchValidationError("Empty diff")
    return ps

def apply_patch(root: Path, diff_text: str, dry_run: bool = True) -> list[str]:
    ps = parse_unified_diff(diff_text)
    changed: list[str] = []
    for f in ps:
        rel = Path(f.path)
        target = root / rel
        if not is_safe_path(root, target):
            raise PatchValidationError(f"Unsafe path in patch: {rel}")

        original = ""
        if not f.is_removed_file and target.exists():
            original = target.read_text(encoding="utf-8")
        lines = original.splitlines(True)

        for h in f:
            new_lines = []
            idx = h.source_start - 1 if h.source_start else 0
            if idx < 0:
                idx = 0
            new_lines.extend(lines[:idx])
            for l in h:
                if l.is_added:
                    new_lines.append(l.value)
                elif l.is_removed:
                    if idx < len(lines):
                        idx += 1
                else:
                    if idx >= len(lines) or lines[idx] != l.value:
                        raise PatchValidationError("Context mismatch while applying hunk")
                    new_lines.append(l.value)
                    idx += 1
            new_lines.extend(lines[idx:])
            lines = new_lines

        content = "".join(lines)
        changed.append(str(rel))
        if not dry_run:
            write_text_safe(root, rel, content)
    return changed
