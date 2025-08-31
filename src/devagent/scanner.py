from __future__ import annotations
import os
from typing import List
from .constants import DEFAULT_IGNORES, SENSITIVE_NAMES, MAX_FILE_BYTES
from .utils import read_text_limited, is_text_bytes

def should_ignore(name: str, extra_ignores: List[str]) -> bool:
    names = set(DEFAULT_IGNORES + extra_ignores)
    return name in names

def is_sensitive(path: str) -> bool:
    base = os.path.basename(path)
    return base in SENSITIVE_NAMES or base.lower().endswith(".key")

def scan_tree(workspace: str, extra_ignores: List[str]) -> List[str]:
    out: List[str] = []
    root = os.path.realpath(workspace)
    for d, dirs, files in os.walk(root):
        # Filter ig
        dirs[:] = [x for x in dirs if not should_ignore(x, extra_ignores)]
        rel_dir = os.path.relpath(d, root)
        if rel_dir == ".":
            rel_dir = ""
        for f in files:
            rel = os.path.join(rel_dir, f) if rel_dir else f
            out.append(rel)
    out.sort()
    return out

def project_card(workspace: str, extra_ignores: List[str], max_files: int = 400) -> str:
    files = scan_tree(workspace, extra_ignores)
    lines: List[str] = []
    lines.append("Files:")
    for i, rel in enumerate(files[:max_files]):
        lines.append(f"- {rel}")
    if len(files) > max_files:
        lines.append(f"... (+{len(files)-max_files} weitere)")

    lines.append("\nSamples:")
    root = os.path.realpath(workspace)
    for rel in files[:60]:
        abs_path = os.path.join(root, rel)
        if is_sensitive(rel):
            lines.append(f"--- {rel} (masked: sensitive) ---")
            continue
        try:
            with open(abs_path, "rb") as f:
                b = f.read(MAX_FILE_BYTES)
            if not is_text_bytes(b):
                lines.append(f"--- {rel} (binary or non-utf8, skipped) ---")
                continue
            txt = b.decode("utf-8", errors="replace")
            head = "\n".join(txt.splitlines()[:120])
            lines.append(f"--- {rel} ---\n{head}")
        except Exception as e:
            lines.append(f"--- {rel} (read error: {e}) ---")
    return "\n".join(lines)
