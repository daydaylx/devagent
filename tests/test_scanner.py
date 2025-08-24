"""Tests for ProjectScanner."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from devagent.scanner import ProjectScanner


class TestProjectScanner:
    """Test ProjectScanner functionality."""

    def test_init_valid_path(self, sample_project):
        """Test scanner initialization with valid path."""
        scanner = ProjectScanner(sample_project)
        
        assert scanner.project_path == sample_project.resolve()
        assert scanner.cache_dir == sample_project / ".agentcache"
        assert scanner.cache_dir.exists()

    def test_init_invalid_path(self, temp_dir):
        """Test scanner initialization with invalid path."""
        invalid_path = temp_dir / "nonexistent"
        
        with pytest.raises(ValueError, match="Project path does not exist"):
            ProjectScanner(invalid_path)

    def test_init_file_instead_of_directory(self, temp_dir):
        """Test scanner initialization with file instead of directory."""
        file_path = temp_dir / "file.txt"
        file_path.write_text("content")
        
        with pytest.raises(ValueError, match="Project path is not a directory"):
            ProjectScanner(file_path)

    def test_scan_project(self, sample_project):
        """Test scanning a project."""
        scanner = ProjectScanner(sample_project)
        result = scanner.scan()
        
        assert "files_scanned" in result
        assert "file_summaries" in result
        assert "index" in result
        
        # Should have scanned some files
        assert result["files_scanned"] > 0
        
        # Should have created summaries for code files
        assert len(result["file_summaries"]) > 0
        
        # Check index structure
        index = result["index"]
        assert "project_path" in index
        assert "files" in index
        assert "total_files" in index
        assert "total_lines" in index

    def test_scan_creates_cache_files(self, sample_project):
        """Test that scan creates cache files."""
        scanner = ProjectScanner(sample_project)
        scanner.scan()
        
        cache_dir = sample_project / ".agentcache"
        assert (cache_dir / "index.json").exists()
        assert (cache_dir / "summaries.json").exists()

    def test_scan_ignores_patterns(self, sample_project):
        """Test that scan ignores specified patterns."""
        # Create files that should be ignored
        (sample_project / "node_modules").mkdir()
        (sample_project / "node_modules" / "package.json").write_text("{}")
        (sample_project / ".git").mkdir()
        (sample_project / ".git" / "config").write_text("config")
        (sample_project / "file.min.js").write_text("minified")
        
        scanner = ProjectScanner(sample_project)
        result = scanner.scan()
        
        # Check that ignored files are not in the index
        index_files = [f["path"] for f in result["index"]["files"]]
        
        assert not any("node_modules" in path for path in index_files)
        assert not any(".git" in path for path in index_files)
        assert "file.min.js" not in index_files

    def test_scan_handles_unreadable_files(self, sample_project):
        """Test that scan handles files that can't be read."""
        # Create a file and make it unreadable (mock this since we can't actually do it)
        unreadable_file = sample_project / "unreadable.txt"
        unreadable_file.write_text("content")
        
        scanner = ProjectScanner(sample_project)
        
        # Mock file reading to raise an exception
        original_read_text = Path.read_text
        
        def mock_read_text(self, *args, **kwargs):
            if self.name == "unreadable.txt":
                raise PermissionError("Permission denied")
            return original_read_text(self, *args, **kwargs)
        
        with patch.object(Path, 'read_text', mock_read_text):
            result = scanner.scan()
        
        # Should still complete successfully
        assert "files_scanned" in result

    def test_ignore_patterns(self):
        """Test ignore patterns are comprehensive."""
        scanner = ProjectScanner(Path.cwd())  # Just for accessing patterns
        
        expected_patterns = {
            ".git/", "node_modules/", ".venv/", "dist/", "build/",
            ".next/", "out/", ".agentcache/", "patches/", "__pycache__/",
            ".pytest_cache/", "coverage/", ".coverage/"
        }
        
        assert expected_patterns.issubset(scanner.IGNORE_PATTERNS)

    def test_text_extensions(self):
        """Test text extensions are comprehensive."""
        scanner = ProjectScanner(Path.cwd())
        
        expected_extensions = {
            ".ts", ".tsx", ".js", ".jsx", ".json", ".css", ".scss",
            ".md", ".py", ".toml", ".yml", ".yaml", ".html", ".txt",
            ".sh", ".bat", ".ps1", ".sql", ".env", ".gitignore"
        }
        
        assert expected_extensions.issubset(scanner.TEXT_EXTENSIONS)

    def test_file_summary_generation(self, sample_project):
        """Test that file summaries are generated correctly."""
        scanner = ProjectScanner(sample_project)
        result = scanner.scan()
        
        summaries = result["file_summaries"]
        
        # Should have summaries for TypeScript files
        ts_files = [path for path in summaries.keys() if path.endswith('.ts')]
        assert len(ts_files) > 0
        
        # Check summary content
        for ts_file in ts_files:
            summary = summaries[ts_file]
            assert isinstance(summary, str)
            assert len(summary) > 0

    def test_scan_empty_project(self, temp_dir):
        """Test scanning an empty project."""
        empty_project = temp_dir / "empty"
        empty_project.mkdir()
        
        scanner = ProjectScanner(empty_project)
        result = scanner.scan()
        
        assert result["files_scanned"] == 0
        assert len(result["file_summaries"]) == 0
        assert result["index"]["total_files"] == 0