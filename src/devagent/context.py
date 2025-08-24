"""Context building for AI requests."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .utils import load_json, truncate_content


class ContextBuilder:
    """Builds structured context for AI requests."""
    
    MAX_TOUCH_FILES = 6
    MAX_LINES_PER_FILE = 250
    MAX_SUMMARY_LENGTH = 200
    
    def __init__(self, project_path: Path) -> None:
        """Initialize context builder."""
        self.project_path = project_path.resolve()
        self.cache_dir = self.project_path / ".agentcache"
    
    def build_context(self, touch_files: List[str], goal: str) -> Dict[str, Any]:
        """Build context for AI request."""
        context = {
            "goal": goal,
            "project_structure": self._get_project_structure(),
            "checks": self._get_checks(),
            "touch_files": self._get_touch_files_content(touch_files),
            "relevant_summaries": self._get_relevant_summaries(touch_files),
        }
        
        return context
    
    def _get_project_structure(self) -> Dict[str, Any]:
        """Get truncated project structure."""
        index_path = self.cache_dir / "index.json"
        if not index_path.exists():
            return {"error": "No index found. Run 'devagent scan' first."}
        
        index = load_json(index_path)
        
        # Truncate file list if too long
        files = index.get("files", [])
        if len(files) > 50:
            files = files[:50]
            index["files"] = files
            index["truncated"] = True
        
        return index
    
    def _get_checks(self) -> Dict[str, Any]:
        """Get project checks results."""
        checks_path = self.cache_dir / "checks.json"
        if not checks_path.exists():
            return {"error": "No checks found. Run 'devagent check' first."}
        
        return load_json(checks_path)
    
    def _get_touch_files_content(self, touch_files: List[str]) -> Dict[str, Any]:
        """Get content of touch files with limits."""
        if len(touch_files) > self.MAX_TOUCH_FILES:
            return {
                "error": f"Too many touch files ({len(touch_files)}). Maximum allowed: {self.MAX_TOUCH_FILES}"
            }
        
        files_content = {}
        total_lines = 0
        
        for file_path_str in touch_files:
            file_path = self.project_path / file_path_str
            
            if not file_path.exists():
                files_content[file_path_str] = {"error": "File not found"}
                continue
            
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                lines = content.count("\n") + 1
                
                if total_lines + lines > self.MAX_LINES_PER_FILE * self.MAX_TOUCH_FILES:
                    remaining_lines = self.MAX_LINES_PER_FILE * self.MAX_TOUCH_FILES - total_lines
                    content = truncate_content(content, remaining_lines)
                    lines = remaining_lines
                
                files_content[file_path_str] = {
                    "content": content,
                    "lines": lines,
                    "size": file_path.stat().st_size,
                }
                
                total_lines += lines
                
                if total_lines >= self.MAX_LINES_PER_FILE * self.MAX_TOUCH_FILES:
                    break
                
            except Exception as e:
                files_content[file_path_str] = {"error": f"Could not read file: {str(e)}"}
        
        return files_content
    
    def _get_relevant_summaries(self, touch_files: List[str]) -> Dict[str, str]:
        """Get summaries for files related to touch files."""
        summaries_path = self.cache_dir / "summaries.json"
        if not summaries_path.exists():
            return {}
        
        all_summaries = load_json(summaries_path)
        
        # Include summaries for touch files and files in same directory
        relevant_summaries = {}
        touch_dirs = set()
        
        for file_path in touch_files:
            # Add direct summary if exists
            if file_path in all_summaries:
                summary = all_summaries[file_path]
                if isinstance(summary, str) and len(summary) > self.MAX_SUMMARY_LENGTH:
                    summary = summary[:self.MAX_SUMMARY_LENGTH] + "..."
                relevant_summaries[file_path] = summary
            
            # Track directories
            touch_dirs.add(str(Path(file_path).parent))
        
        # Add summaries from same directories (limited)
        count = 0
        for file_path, summary in all_summaries.items():
            if count >= 20:  # Limit total summaries
                break
                
            file_dir = str(Path(file_path).parent)
            if file_dir in touch_dirs and file_path not in relevant_summaries:
                if isinstance(summary, str) and len(summary) > self.MAX_SUMMARY_LENGTH:
                    summary = summary[:self.MAX_SUMMARY_LENGTH] + "..."
                relevant_summaries[file_path] = summary
                count += 1
        
        return relevant_summaries
