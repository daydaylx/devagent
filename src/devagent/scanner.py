"""Project scanning and file analysis."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .logging import get_logger
from .utils import get_file_summary, is_ignored_file, is_text_file, load_json, save_json


class ProjectScanner:
    """Scans project directories and builds context indexes."""
    
    IGNORE_PATTERNS = {
        ".git/", "node_modules/", ".venv/", "dist/", "build/", 
        ".next/", "out/", ".agentcache/", "patches/", "__pycache__/",
        ".pytest_cache/", "coverage/", ".coverage/"
    }
    
    IGNORE_EXTENSIONS = {
        ".lock", ".min.js", ".min.css", ".map", 
        ".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg",
        ".pyc", ".pyo", ".pyd", ".so", ".dll", ".dylib"
    }
    
    TEXT_EXTENSIONS = {
        ".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".scss",
        ".md", ".py", ".toml", ".yml", ".yaml", ".html", ".txt",
        ".sh", ".bat", ".ps1", ".sql", ".env", ".gitignore"
    }
    
    def __init__(self, project_path: Path) -> None:
        """Initialize scanner with project path.
        
        Args:
            project_path: Path to the project directory to scan
            
        Raises:
            ValueError: If project path doesn't exist or isn't a directory
        """
        if not project_path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")
        if not project_path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")
            
        self.project_path = project_path.resolve()
        self.cache_dir = self.project_path / ".agentcache"
        self.cache_dir.mkdir(exist_ok=True)
        self.logger = get_logger(__name__)
    
    def scan(self) -> Dict[str, Any]:
        """Scan project and create index files."""
        index_data = {
            "project_path": str(self.project_path),
            "files": [],
            "total_files": 0,
            "total_lines": 0,
        }
        
        summaries = {}
        files_scanned = 0
        
        for file_path in self._iter_project_files():
            try:
                relative_path = str(file_path.relative_to(self.project_path))
                
                if is_text_file(file_path, self.TEXT_EXTENSIONS):
                    content = file_path.read_text(encoding="utf-8", errors="ignore")
                    lines = content.count("\n") + 1 if content else 0
                    
                    file_info = {
                        "path": relative_path,
                        "size": file_path.stat().st_size,
                        "lines": lines,
                        "extension": file_path.suffix,
                    }
                    
                    # Generate summary for code files
                    if file_path.suffix in {".ts", ".tsx", ".js", ".jsx", ".py"}:
                        summary = get_file_summary(file_path, content)
                        summaries[relative_path] = summary
                        file_info["has_summary"] = True
                    else:
                        file_info["has_summary"] = False
                    
                    index_data["files"].append(file_info)
                    index_data["total_lines"] += lines
                    files_scanned += 1
                
            except Exception as e:
                self.logger.warning(
                    f"Failed to process file {relative_path}: {e}",
                    extra={"file_path": relative_path, "error": str(e)}
                )
                continue
        
        index_data["total_files"] = len(index_data["files"])
        
        # Save index and summaries
        save_json(self.cache_dir / "index.json", index_data)
        save_json(self.cache_dir / "summaries.json", summaries)
        
        return {
            "files_scanned": files_scanned,
            "file_summaries": summaries,
            "index": index_data,
        }
    
    def _iter_project_files(self) -> List[Path]:
        """Iterate through project files, respecting ignore patterns."""
        for file_path in self.project_path.rglob("*"):
            if file_path.is_file() and not is_ignored_file(
                file_path, self.project_path, self.IGNORE_PATTERNS, self.IGNORE_EXTENSIONS
            ):
                yield file_path
