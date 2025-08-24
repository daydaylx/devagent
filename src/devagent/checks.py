"""Project health checks (TypeScript, Python, linting, tests)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

from .logging import get_logger
from .utils import load_json, save_json


class ProjectChecker:
    """Runs project health checks and validation with proper error handling."""
    
    def __init__(self, project_path: Path) -> None:
        """Initialize checker with project path.
        
        Args:
            project_path: Path to the project directory to check
            
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
        
        # Get timeouts from environment
        self.default_timeout = int(os.getenv("CHECK_TIMEOUT", "120"))
        self.build_timeout = int(os.getenv("BUILD_TIMEOUT", "300"))
    
    def run_checks(self) -> Dict[str, Any]:
        """Run all applicable project checks."""
        results = {
            "overall_status": "success",
            "checks_run": [],
            "results": {},
            "summary": "",
        }
        
        errors = []
        
        # Node.js/TypeScript checks
        if self._has_nodejs_project():
            try:
                ts_result = self._run_typescript_check()
                results["checks_run"].append("typescript")
                results["results"]["typescript"] = ts_result
                
                if not ts_result["success"]:
                    errors.append(f"TypeScript: {ts_result['summary']}")
                
            except Exception as e:
                self.logger.error(f"TypeScript check failed: {e}")
                errors.append(f"TypeScript check failed: {str(e)}")
            
            # Optional build check
            try:
                build_result = self._run_build_check()
                if build_result:
                    results["checks_run"].append("build")
                    results["results"]["build"] = build_result
                    
                    if not build_result["success"]:
                        errors.append(f"Build: {build_result['summary']}")
                
            except Exception as e:
                self.logger.debug(f"Build check skipped: {e}")
            
            # Optional lint check
            try:
                lint_result = self._run_lint_check()
                if lint_result:
                    results["checks_run"].append("lint")
                    results["results"]["lint"] = lint_result
                    
                    if not lint_result["success"]:
                        errors.append(f"Lint: {lint_result['summary']}")
                
            except Exception as e:
                self.logger.debug(f"Lint check skipped: {e}")
        
        # Python checks
        if self._has_python_project():
            try:
                pytest_result = self._run_pytest()
                if pytest_result:
                    results["checks_run"].append("pytest")
                    results["results"]["pytest"] = pytest_result
                    
                    if not pytest_result["success"]:
                        errors.append(f"Pytest: {pytest_result['summary']}")
                
            except Exception as e:
                self.logger.debug(f"Pytest skipped: {e}")
            
            try:
                pyright_result = self._run_pyright()
                if pyright_result:
                    results["checks_run"].append("pyright")
                    results["results"]["pyright"] = pyright_result
                    
                    if not pyright_result["success"]:
                        errors.append(f"Pyright: {pyright_result['summary']}")
                
            except Exception as e:
                self.logger.debug(f"Pyright skipped: {e}")
        
        if errors:
            results["overall_status"] = "failure"
            results["summary"] = "; ".join(errors)
        
        # Save results
        save_json(self.cache_dir / "checks.json", results)
        
        return results
    
    def _has_nodejs_project(self) -> bool:
        """Check if project has Node.js configuration."""
        return (self.project_path / "package.json").exists()
    
    def _has_python_project(self) -> bool:
        """Check if project has Python configuration."""
        return (
            (self.project_path / "pyproject.toml").exists() or
            (self.project_path / "requirements.txt").exists()
        )
    
    def _run_typescript_check(self) -> Dict[str, Any]:
        """Run TypeScript type checking."""
        try:
            # Try npm run typecheck first
            result = subprocess.run(
                ["npm", "run", "typecheck"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
            )
            
            if result.returncode == 0:
                return {"success": True, "output": result.stdout, "summary": "No type errors"}
            
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass
        
        # Fallback to tsc --noEmit
        try:
            result = subprocess.run(
                ["npx", "-y", "tsc", "--noEmit"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
            )
            
            success = result.returncode == 0
            summary = "No type errors" if success else "Type errors found"
            
            return {
                "success": success,
                "output": result.stdout + result.stderr,
                "summary": summary,
            }
            
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "summary": f"TypeScript check failed: {str(e)}",
            }
    
    def _run_build_check(self) -> Optional[Dict[str, Any]]:
        """Run build check if npm run build exists."""
        try:
            # Check if build script exists
            package_json_path = self.project_path / "package.json"
            if package_json_path.exists():
                package_json = load_json(package_json_path)
                scripts = package_json.get("scripts", {})
                
                if "build" in scripts:
                    result = subprocess.run(
                        ["npm", "run", "build"],
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                        timeout=self.build_timeout,
                    )
                    
                    success = result.returncode == 0
                    summary = "Build successful" if success else "Build failed"
                    
                    return {
                        "success": success,
                        "output": result.stdout + result.stderr,
                        "summary": summary,
                    }
        
        except Exception:
            pass
        
        return None
    
    def _run_lint_check(self) -> Optional[Dict[str, Any]]:
        """Run linting if npm run lint exists."""
        try:
            # Check if lint script exists
            package_json_path = self.project_path / "package.json"
            if package_json_path.exists():
                package_json = load_json(package_json_path)
                scripts = package_json.get("scripts", {})
                
                if "lint" in scripts:
                    result = subprocess.run(
                        ["npm", "run", "lint"],
                        cwd=self.project_path,
                        capture_output=True,
                        text=True,
                        timeout=self.default_timeout,
                    )
                    
                    success = result.returncode == 0
                    summary = "No lint errors" if success else "Lint errors found"
                    
                    return {
                        "success": success,
                        "output": result.stdout + result.stderr,
                        "summary": summary,
                    }
        
        except Exception:
            pass
        
        return None
    
    def _run_pytest(self) -> Optional[Dict[str, Any]]:
        """Run pytest if configuration exists."""
        try:
            has_pytest_config = (
                (self.project_path / "pytest.ini").exists() or
                (self.project_path / "pyproject.toml").exists()
            )
            
            if has_pytest_config:
                result = subprocess.run(
                    ["pytest", "-q"],
                    cwd=self.project_path,
                    capture_output=True,
                    text=True,
                    timeout=self.default_timeout,
                )
                
                success = result.returncode == 0
                summary = "All tests passed" if success else "Some tests failed"
                
                return {
                    "success": success,
                    "output": result.stdout + result.stderr,
                    "summary": summary,
                }
        
        except Exception:
            pass
        
        return None
    
    def _run_pyright(self) -> Optional[Dict[str, Any]]:
        """Run pyright type checking."""
        try:
            result = subprocess.run(
                ["pyright"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=self.default_timeout,
            )
            
            success = result.returncode == 0
            summary = "No type errors" if success else "Type errors found"
            
            return {
                "success": success,
                "output": result.stdout + result.stderr,
                "summary": summary,
            }
            
        except Exception:
            pass
        
        return None
