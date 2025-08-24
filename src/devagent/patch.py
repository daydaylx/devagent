"""Patch management and application."""
from __future__ import annotations
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
class PatchManager:
    """Manages patch creation, validation, and application."""

    def __init__(self, repo_path: Path) -> None:
        """Initialize patch manager."""
        self.repo_path = repo_path.resolve()
        self.patches_dir = self.repo_path / "patches"
        self.patches_dir.mkdir(exist_ok=True)

    def save_patch(self, patch_content: str, commit_message: str) -> Path:
        """Save patch to file with timestamp."""
        # Ensure patch has proper unified diff format
        if not patch_content.startswith(("---", "diff", "Index:")):
            # Try to extract file paths and add proper headers
            patch_content = self._normalize_patch(patch_content)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        patch_file = self.patches_dir / f"{timestamp}.patch"
        
        # Write patch with metadata
        with open(patch_file, "w", encoding="utf-8") as f:
            f.write(f"# Commit message: {commit_message}\n")
            f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
            f.write(patch_content)
        
        # Create/update latest.patch symlink
        latest_patch = self.patches_dir / "latest.patch"
        if latest_patch.exists():
            latest_patch.unlink()
        
        try:
            latest_patch.symlink_to(patch_file.name)
        except OSError:
            # Fallback for systems that don't support symlinks
            with open(latest_patch, "w", encoding="utf-8") as f:
                f.write(patch_file.read_text(encoding="utf-8"))
        
        return patch_file

    def validate_patch(self, patch_file: Path) -> None:
        """Validate patch can be applied without actually applying it."""
        result = subprocess.run(
            ["git", "apply", "--check", str(patch_file)],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            raise ValueError(f"Patch validation failed: {result.stderr}")

    def apply_patch(self, patch_file: Path) -> List[str]:
        """Apply patch and return list of affected files."""
        # First validate
        self.validate_patch(patch_file)
        
        # Apply patch
        result = subprocess.run(
            ["git", "apply", str(patch_file)],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
        )
        
        if result.returncode != 0:
            raise RuntimeError(f"Patch application failed: {result.stderr}")
        
        # Extract affected files from patch
        affected_files = self._extract_affected_files(patch_file)
        
        return affected_files

    def commit_changes(self, message: str) -> None:
        """Commit changes to git."""
        # Add all changes
        subprocess.run(
            ["git", "add", "-A"],
            cwd=self.repo_path,
            check=True,
        )
        
        # Commit
        subprocess.run(
            ["git", "commit", "-m", message],
            cwd=self.repo_path,
            check=True,
        )

    def revert_files(self, file_paths: List[str]) -> None:
        """Revert specific files to HEAD."""
        if file_paths:
            subprocess.run(
                ["git", "restore", "--source", "HEAD", "--"] + file_paths,
                cwd=self.repo_path,
                check=True,
            )

    def _normalize_patch(self, patch_content: str) -> str:
        """Normalize patch content to proper unified diff format."""
        lines = patch_content.split("\n")
        normalized_lines = []
        current_file = None
        
        for line in lines:
            # Detect file changes
            if line.startswith("--- ") or line.startswith("+++ "):
                normalized_lines.append(line)
                if line.startswith("--- "):
                    current_file = line[4:].split("\t")[0]
            elif line.startswith("@@"):
                normalized_lines.append(line)
            elif line.startswith(("+", "-", " ")):
                normalized_lines.append(line)
            elif line.strip() and not line.startswith("#"):
                # Try to detect if this is a diff line without proper prefix
                if current_file and ("+" in line or "-" in line):
                    # This might be a change without proper diff formatting
                    # Skip for now to avoid corrupting the patch
                    continue
        
        return "\n".join(normalized_lines)

    def _extract_affected_files(self, patch_file: Path) -> List[str]:
        """Extract list of files affected by patch."""
        content = patch_file.read_text(encoding="utf-8")
        files = []
        
        # Find all --- and +++ lines
        for line in content.split("\n"):
            if line.startswith("--- "):
                file_path = line[4:].split("\t")[0]
                if file_path != "/dev/null" and not file_path.startswith("a/"):
                    files.append(file_path)
                elif file_path.startswith("a/"):
                    files.append(file_path[2:])  # Remove a/ prefix
            elif line.startswith("+++ "):
                file_path = line[4:].split("\t")[0]
                if file_path != "/dev/null" and not file_path.startswith("b/"):
                    if file_path not in files:
                        files.append(file_path)
                elif file_path.startswith("b/"):
                    clean_path = file_path[2:]  # Remove b/ prefix
                    if clean_path not in files:
                        files.append(clean_path)
        
        return files
