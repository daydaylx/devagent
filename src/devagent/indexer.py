from __future__ import annotations
import os
from pathlib import Path
from typing import List
from .constants import EXCLUDE_DIRS

_TEXT_EXT = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".md", ".toml", ".yaml", ".yml",
    ".css", ".scss", ".html", ".txt", ".ini", ".cfg"
}

def should_skip_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS or (name.startswith(".") and name not in {".github"})

def build_index(root: Path) -> dict:
    files: List[dict] = []
    for base, dirs, filenames in os.walk(root):
        dirs[:] = [d for d in dirs if not should_skip_dir(d)]
        for fn in filenames:
            p = Path(base) / fn
            if (root / ".devagent") in p.parents:
                continue
            rel = p.relative_to(root)
            size = p.stat().st_size
            is_text = p.suffix in _TEXT_EXT
            files.append({"path": str(rel), "size": size, "text": is_text})
    summary = {
        "files": files,
        "count": len(files),
        "text_files": sum(1 for f in files if f["text"]),
        "bytes": sum(f["size"] for f in files),
    }
    return summary
