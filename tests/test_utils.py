"""Tests for utility functions."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from devagent.utils import (
    format_file_size,
    get_file_summary,
    is_ignored_file,
    is_text_file,
    load_json,
    safe_filename,
    save_json,
    truncate_content,
)


class TestLoadJson:
    """Test JSON loading functionality."""

    def test_load_valid_json(self, temp_dir):
        """Test loading valid JSON file."""
        data = {"key": "value", "number": 42}
        json_file = temp_dir / "test.json"
        json_file.write_text(json.dumps(data))
        
        result = load_json(json_file)
        assert result == data

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading nonexistent file."""
        nonexistent = temp_dir / "missing.json"
        
        with pytest.raises(FileNotFoundError):
            load_json(nonexistent)

    def test_load_invalid_json(self, temp_dir):
        """Test loading invalid JSON."""
        invalid_json = temp_dir / "invalid.json"
        invalid_json.write_text("not valid json {")
        
        with pytest.raises(json.JSONDecodeError):
            load_json(invalid_json)

    def test_load_with_orjson(self, temp_dir):
        """Test loading with orjson when available."""
        data = {"test": "data"}
        json_file = temp_dir / "test.json"
        json_file.write_text(json.dumps(data))
        
        # Mock orjson availability
        with patch('devagent.utils.HAS_ORJSON', True), \
             patch('devagent.utils.orjson') as mock_orjson:
            mock_orjson.loads.return_value = data
            
            result = load_json(json_file)
            assert result == data
            mock_orjson.loads.assert_called_once()


class TestSaveJson:
    """Test JSON saving functionality."""

    def test_save_valid_data(self, temp_dir):
        """Test saving valid data."""
        data = {"key": "value", "list": [1, 2, 3]}
        json_file = temp_dir / "output.json"
        
        save_json(json_file, data)
        
        # Verify file was created and contains correct data
        assert json_file.exists()
        loaded = json.loads(json_file.read_text())
        assert loaded == data

    def test_save_creates_directory(self, temp_dir):
        """Test that save_json creates parent directories."""
        data = {"test": "data"}
        nested_file = temp_dir / "nested" / "dir" / "file.json"
        
        save_json(nested_file, data)
        
        assert nested_file.exists()
        loaded = json.loads(nested_file.read_text())
        assert loaded == data

    def test_save_with_orjson(self, temp_dir):
        """Test saving with orjson when available."""
        data = {"test": "data"}
        json_file = temp_dir / "test.json"
        
        with patch('devagent.utils.HAS_ORJSON', True), \
             patch('devagent.utils.orjson') as mock_orjson:
            mock_orjson.dumps.return_value = b'{"test": "data"}'
            
            save_json(json_file, data)
            
            mock_orjson.dumps.assert_called_once()
            assert json_file.exists()


class TestIsIgnoredFile:
    """Test file ignoring logic."""

    def test_ignore_patterns(self, temp_dir):
        """Test ignore patterns work correctly."""
        project_path = temp_dir
        ignore_patterns = {".git/", "node_modules/", "__pycache__/"}
        ignore_extensions = {".pyc"}
        
        # Should be ignored
        git_file = project_path / ".git" / "config"
        assert is_ignored_file(git_file, project_path, ignore_patterns, ignore_extensions)
        
        node_file = project_path / "node_modules" / "package.json"  
        assert is_ignored_file(node_file, project_path, ignore_patterns, ignore_extensions)
        
        # Should not be ignored
        normal_file = project_path / "src" / "main.py"
        assert not is_ignored_file(normal_file, project_path, ignore_patterns, ignore_extensions)

    def test_ignore_extensions(self, temp_dir):
        """Test ignoring by file extension."""
        project_path = temp_dir
        ignore_patterns = set()
        ignore_extensions = {".pyc", ".min.js"}
        
        pyc_file = project_path / "module.pyc"
        assert is_ignored_file(pyc_file, project_path, ignore_patterns, ignore_extensions)
        
        py_file = project_path / "module.py"
        assert not is_ignored_file(py_file, project_path, ignore_patterns, ignore_extensions)

    def test_ignore_minified_files(self, temp_dir):
        """Test ignoring minified files."""
        project_path = temp_dir
        ignore_patterns = set()
        ignore_extensions = set()
        
        minified_file = project_path / "script.min.js"
        assert is_ignored_file(minified_file, project_path, ignore_patterns, ignore_extensions)
        
        normal_file = project_path / "script.js"
        assert not is_ignored_file(normal_file, project_path, ignore_patterns, ignore_extensions)

    def test_ignore_hidden_files(self, temp_dir):
        """Test ignoring hidden files."""
        project_path = temp_dir
        ignore_patterns = set()
        ignore_extensions = set()
        
        # Should be ignored
        hidden_file = project_path / ".hidden_file"
        assert is_ignored_file(hidden_file, project_path, ignore_patterns, ignore_extensions)
        
        # Should not be ignored (special cases)
        env_file = project_path / ".env"
        assert not is_ignored_file(env_file, project_path, ignore_patterns, ignore_extensions)
        
        gitignore_file = project_path / ".gitignore"
        assert not is_ignored_file(gitignore_file, project_path, ignore_patterns, ignore_extensions)

    def test_file_outside_project(self, temp_dir):
        """Test handling files outside project path."""
        project_path = temp_dir / "project"
        outside_file = temp_dir / "outside.txt"
        
        ignore_patterns = set()
        ignore_extensions = set()
        
        # File outside project should be ignored
        assert is_ignored_file(outside_file, project_path, ignore_patterns, ignore_extensions)


class TestIsTextFile:
    """Test text file detection."""

    def test_text_extensions(self):
        """Test detection of text files by extension."""
        text_extensions = {".py", ".js", ".txt", ".md"}
        
        assert is_text_file(Path("script.py"), text_extensions)
        assert is_text_file(Path("app.js"), text_extensions)
        assert not is_text_file(Path("image.png"), text_extensions)

    def test_files_without_extension(self):
        """Test handling files without extension."""
        text_extensions = {".py", ".js"}
        
        # Special files should be considered text
        assert is_text_file(Path("README"), text_extensions)
        assert is_text_file(Path("Makefile"), text_extensions)
        assert is_text_file(Path("Dockerfile"), text_extensions)
        assert is_text_file(Path("LICENSE"), text_extensions)
        
        # Other files without extension should not
        assert not is_text_file(Path("binary_file"), text_extensions)


class TestGetFileSummary:
    """Test file summary generation."""

    def test_typescript_summary(self):
        """Test summary for TypeScript file."""
        content = '''
import React from 'react';
import { useState } from 'react';

export class Calculator {
    add(a: number, b: number): number {
        return a + b;
    }
}

export function Component() {
    return <div>Hello</div>;
}

const helper = () => {
    return "help";
};
'''
        
        summary = get_file_summary(Path("test.ts"), content)
        
        assert "2 imports" in summary
        assert "classes" in summary.lower() or "1 classes" in summary
        assert "functions" in summary.lower()
        assert "ts" in summary

    def test_python_summary(self):
        """Test summary for Python file."""
        content = '''
import json
from pathlib import Path

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def process(self, item):
        return item.upper()

def helper_function():
    pass

async def async_function():
    await something()
'''
        
        summary = get_file_summary(Path("test.py"), content)
        
        assert "2 imports" in summary
        assert "1 classes" in summary
        assert "functions" in summary.lower()
        assert "py" in summary

    def test_empty_file_summary(self):
        """Test summary for empty file."""
        summary = get_file_summary(Path("empty.py"), "")
        assert "Empty py" in summary

    def test_whitespace_only_summary(self):
        """Test summary for file with only whitespace."""
        summary = get_file_summary(Path("whitespace.js"), "   \n  \n  ")
        assert "Empty js" in summary


class TestTruncateContent:
    """Test content truncation."""

    def test_no_truncation_needed(self):
        """Test content that doesn't need truncation."""
        content = "line 1\nline 2\nline 3"
        result = truncate_content(content, max_lines=10)
        assert result == content

    def test_truncation_applied(self):
        """Test content that gets truncated."""
        lines = [f"line {i}" for i in range(20)]
        content = "\n".join(lines)
        
        result = truncate_content(content, max_lines=10)
        result_lines = result.split("\n")
        
        assert len(result_lines) == 12  # 10 lines + truncation message + empty line
        assert "truncated 10 lines" in result

    def test_empty_content(self):
        """Test truncation of empty content."""
        result = truncate_content("", max_lines=10)
        assert result == ""


class TestFormatFileSize:
    """Test file size formatting."""

    def test_bytes(self):
        """Test formatting bytes."""
        assert format_file_size(512) == "512.0 B"
        assert format_file_size(1023) == "1023.0 B"

    def test_kilobytes(self):
        """Test formatting kilobytes."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(2048) == "2.0 KB"
        assert format_file_size(1536) == "1.5 KB"

    def test_megabytes(self):
        """Test formatting megabytes."""
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 2.5) == "2.5 MB"

    def test_gigabytes(self):
        """Test formatting gigabytes."""
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_terabytes(self):
        """Test formatting terabytes."""
        assert format_file_size(1024 * 1024 * 1024 * 1024) == "1.0 TB"


class TestSafeFilename:
    """Test safe filename generation."""

    def test_valid_filename(self):
        """Test already valid filename."""
        assert safe_filename("valid_file.txt") == "valid_file.txt"

    def test_invalid_characters(self):
        """Test replacement of invalid characters."""
        unsafe = "file<>:\"/\\|?*.txt"
        safe = safe_filename(unsafe)
        
        # All invalid characters should be replaced with underscores
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            assert char not in safe
        
        assert safe.endswith(".txt")

    def test_leading_trailing_dots(self):
        """Test removal of leading/trailing dots and spaces."""
        assert safe_filename("  .file.  ") == "file."
        assert safe_filename("...file...") == "file"

    def test_empty_filename(self):
        """Test handling of empty filename."""
        assert safe_filename("") == "untitled"
        assert safe_filename("  ") == "untitled"
        assert safe_filename("...") == "untitled"

    def test_long_filename(self):
        """Test truncation of long filenames."""
        long_name = "x" * 250
        safe = safe_filename(long_name)
        assert len(safe) <= 200