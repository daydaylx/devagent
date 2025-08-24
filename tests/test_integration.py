"""Integration tests for DevAgent CLI."""

import json
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def test_scan_command(self, sample_project):
        """Test the scan command end-to-end."""
        # Run scan command
        result = subprocess.run(
            ["python", "-m", "devagent.cli", "scan", str(sample_project)],
            capture_output=True,
            text=True,
            cwd=sample_project.parent
        )
        
        assert result.returncode == 0
        assert "Scanned" in result.stdout or "Scanning" in result.stdout
        
        # Verify cache files were created
        cache_dir = sample_project / ".agentcache"
        assert cache_dir.exists()
        assert (cache_dir / "index.json").exists()
        assert (cache_dir / "summaries.json").exists()
        
        # Verify cache content
        index_data = json.loads((cache_dir / "index.json").read_text())
        assert "files" in index_data
        assert len(index_data["files"]) > 0

    def test_check_command(self, sample_project):
        """Test the check command."""
        # First ensure we have a basic setup
        result = subprocess.run(
            ["python", "-m", "devagent.cli", "check", str(sample_project)],
            capture_output=True,
            text=True,
            cwd=sample_project.parent
        )
        
        # Command should complete (may pass or fail checks, that's OK)
        assert result.returncode in [0, 1]
        
        # Should show some check results
        assert "Check" in result.stdout or "Running" in result.stdout

    def test_propose_command_missing_api_key(self, sample_project):
        """Test propose command fails without API key."""
        # Make sure no API key is set
        env = {"PATH": "/usr/bin:/bin"}  # Minimal env without API key
        
        result = subprocess.run(
            [
                "python", "-m", "devagent.cli", "propose",
                "--goal", "test goal",
                "--touch", "src/index.ts",
                str(sample_project)
            ],
            capture_output=True,
            text=True,
            cwd=sample_project.parent,
            env=env
        )
        
        assert result.returncode != 0
        assert "OPENROUTER_API_KEY" in result.stderr or "required" in result.stderr.lower()

    @patch('devagent.llm.httpx.Client')
    def test_propose_command_success(self, mock_client, sample_project, mock_openrouter_response):
        """Test successful propose command."""
        # Mock the HTTP client
        mock_response = Mock()
        mock_response.json.return_value = mock_openrouter_response
        mock_response.raise_for_status.return_value = None
        mock_client.return_value.__enter__.return_value.post.return_value = mock_response
        
        # Set required environment
        env = {
            "OPENROUTER_API_KEY": "test-key",
            "PATH": "/usr/bin:/bin"
        }
        
        # First scan the project
        subprocess.run(
            ["python", "-m", "devagent.cli", "scan", str(sample_project)],
            env=env,
            cwd=sample_project.parent
        )
        
        # Then run propose
        result = subprocess.run(
            [
                "python", "-m", "devagent.cli", "propose",
                "--goal", "Add error handling",
                "--touch", "src/index.ts",
                str(sample_project)
            ],
            capture_output=True,
            text=True,
            env=env,
            cwd=sample_project.parent
        )
        
        # Should succeed and create patch files
        assert result.returncode == 0
        
        patches_dir = sample_project / "patches"
        assert patches_dir.exists()
        
        # Should have created patch files
        patch_files = list(patches_dir.glob("*.patch"))
        assert len(patch_files) > 0
        
        # Should have latest.patch
        assert (patches_dir / "latest.patch").exists()

    def test_apply_command_missing_patch(self, sample_project):
        """Test apply command with missing patch file."""
        result = subprocess.run(
            [
                "python", "-m", "devagent.cli", "apply",
                "nonexistent.patch"
            ],
            capture_output=True,
            text=True,
            cwd=sample_project
        )
        
        assert result.returncode != 0
        assert "does not exist" in result.stderr or "Error" in result.stderr

    def test_workflow_integration(self, sample_project, mock_openrouter_response):
        """Test complete workflow: scan -> check -> propose -> apply."""
        env = {
            "OPENROUTER_API_KEY": "test-key",
            "PATH": "/usr/bin:/bin"
        }
        
        with patch('devagent.llm.httpx.Client') as mock_client:
            # Mock successful API response
            mock_response = Mock()
            mock_response.json.return_value = mock_openrouter_response
            mock_response.raise_for_status.return_value = None
            mock_client.return_value.__enter__.return_value.post.return_value = mock_response
            
            # Step 1: Scan project
            result = subprocess.run(
                ["python", "-m", "devagent.cli", "scan", str(sample_project)],
                env=env,
                cwd=sample_project.parent
            )
            assert result.returncode == 0
            
            # Step 2: Run checks
            result = subprocess.run(
                ["python", "-m", "devagent.cli", "check", str(sample_project)],
                env=env,
                cwd=sample_project.parent
            )
            # Checks may pass or fail, that's OK for this test
            assert result.returncode in [0, 1]
            
            # Step 3: Generate proposal
            result = subprocess.run(
                [
                    "python", "-m", "devagent.cli", "propose",
                    "--goal", "Add error handling",
                    "--touch", "src/index.ts",
                    str(sample_project)
                ],
                capture_output=True,
                text=True,
                env=env,
                cwd=sample_project.parent
            )
            assert result.returncode == 0
            
            # Verify patch was created
            latest_patch = sample_project / "patches" / "latest.patch"
            assert latest_patch.exists()

    def test_help_commands(self):
        """Test help output for all commands."""
        commands = ["scan", "check", "propose", "apply"]
        
        for command in commands:
            result = subprocess.run(
                ["python", "-m", "devagent.cli", command, "--help"],
                capture_output=True,
                text=True
            )
            
            assert result.returncode == 0
            assert "Usage:" in result.stdout
            assert command in result.stdout.lower()

    def test_invalid_path_handling(self):
        """Test handling of invalid paths."""
        invalid_path = "/nonexistent/path/that/does/not/exist"
        
        result = subprocess.run(
            ["python", "-m", "devagent.cli", "scan", invalid_path],
            capture_output=True,
            text=True
        )
        
        assert result.returncode != 0
        assert "Error" in result.stderr

    def test_python_project_support(self, python_project):
        """Test scanning and checking Python projects."""
        # Test scan
        result = subprocess.run(
            ["python", "-m", "devagent.cli", "scan", str(python_project)],
            capture_output=True,
            text=True,
            cwd=python_project.parent
        )
        
        assert result.returncode == 0
        
        # Verify Python files were scanned
        cache_dir = python_project / ".agentcache"
        summaries_file = cache_dir / "summaries.json"
        assert summaries_file.exists()
        
        summaries = json.loads(summaries_file.read_text())
        python_files = [path for path in summaries.keys() if path.endswith('.py')]
        assert len(python_files) > 0
        
        # Test check (may find Python tools or not, both are OK)
        result = subprocess.run(
            ["python", "-m", "devagent.cli", "check", str(python_project)],
            capture_output=True,
            text=True,
            cwd=python_project.parent
        )
        
        # Should complete without crashing
        assert result.returncode in [0, 1]

    def test_concurrent_operations(self, sample_project):
        """Test that concurrent operations don't interfere."""
        import threading
        import time
        
        results = []
        
        def scan_project():
            result = subprocess.run(
                ["python", "-m", "devagent.cli", "scan", str(sample_project)],
                capture_output=True,
                text=True,
                cwd=sample_project.parent
            )
            results.append(result.returncode)
        
        # Run multiple scans concurrently
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=scan_project)
            threads.append(thread)
            thread.start()
            time.sleep(0.1)  # Slight delay to avoid exact simultaneity
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All scans should have succeeded
        assert all(code == 0 for code in results)
        
        # Cache should exist and be valid
        cache_dir = sample_project / ".agentcache"
        assert cache_dir.exists()
        assert (cache_dir / "index.json").exists()

    def test_error_recovery(self, temp_dir):
        """Test error recovery scenarios."""
        # Create a project with permission issues (simulated)
        problem_project = temp_dir / "problem_project"
        problem_project.mkdir()
        
        # Create a file with problematic content
        bad_file = problem_project / "bad.json"
        bad_file.write_text("{ invalid json content")
        
        # Scan should handle the bad file gracefully
        result = subprocess.run(
            ["python", "-m", "devagent.cli", "scan", str(problem_project)],
            capture_output=True,
            text=True,
            cwd=temp_dir
        )
        
        # Should complete (may have warnings but shouldn't crash)
        assert result.returncode == 0