from __future__ import annotations
import os
import json
import hashlib
import shutil
import subprocess
from pathlib import Path

from .logging import get_logger

log = get_logger(__name__)

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 180) -> tuple[int, str, str]:
    """Run a shell command safely and return (code, stdout, stderr)."""
    p = subprocess.Popen(cmd, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        p.kill()
        out, err = p.communicate()
        return 124, out, err + "\n[devagent] command timed out"
    return p.returncode, out, err

def ensure_git_root(start: Path) -> Path:
    """Ascend to the repository root (where .git exists)."""
    p = start.resolve()
    for _ in range(20):
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    raise SystemExit("Not inside a Git repository (no .git found in parents)")

def is_safe_path(root: Path, target: Path) -> bool:
    """Ensure target is within root and not a symlink."""
    try:
        root = root.resolve()
        target = target.resolve()
    except FileNotFoundError:
        target = target.parent.resolve() / target.name
    if not str(target).startswith(str(root)):
        return False
    cur = target
    while True:
        if cur.is_symlink():
            return False
        if cur.parent == cur:
            break
        if cur == root:
            break
        cur = cur.parent
    return True

def sha256_of_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:8]

def write_text_safe(root: Path, rel: Path, content: str) -> None:
    target = (root / rel).resolve()
    if not is_safe_path(root, target):
        raise SystemExit(f"Refusing to write outside repo or via symlink: {rel}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, target)

def read_text_safe(root: Path, rel: Path) -> str:
    target = (root / rel).resolve()
    if not is_safe_path(root, target):
        raise SystemExit(f"Refusing to read outside repo or via symlink: {rel}")
    return target.read_text(encoding="utf-8")

def which(name: str) -> str | None:
    return shutil.which(name)

def json_dump(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False)

def confirm_token(prompt: str) -> None:
    token = sha256_of_text(prompt)
    print(f"\n[CONFIRM] {prompt}\nType token to continue: {token}")
    try:
        user = input("> ").strip()
    except EOFError:
        raise SystemExit("Aborted: no input")
    if user != token:
        raise SystemExit("Aborted: token mismatch")

def load_json(path: Path) -> dict:
    """Load JSON from file."""
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError) as e:
        log.error(f"Failed to load JSON from {path}: {e}")
        return {}

def save_json(path: Path, data: dict) -> None:
    """Save data to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json_dump(data), encoding="utf-8")
    except Exception as e:
        log.error(f"Failed to save JSON to {path}: {e}")

def is_text_file(path: Path) -> bool:
    """Check if file is likely a text file."""
    try:
        # Check file extension
        text_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.html', 
            '.css', '.scss', '.less', '.json', '.xml', '.yaml', '.yml',
            '.toml', '.ini', '.cfg', '.conf', '.sh', '.bat', '.ps1',
            '.sql', '.csv', '.log', '.dockerfile', '.makefile'
        }
        if path.suffix.lower() in text_extensions:
            return True
        
        # For files without extension or unknown extensions, try to read a small sample
        if path.is_file() and path.stat().st_size > 0:
            try:
                with open(path, 'rb') as f:
                    sample = f.read(1024)
                # Check if sample contains mostly printable ASCII/UTF-8 characters
                try:
                    sample.decode('utf-8')
                    # Check for null bytes (common in binary files)
                    return b'\x00' not in sample
                except UnicodeDecodeError:
                    return False
            except Exception:
                return False
        return False
    except Exception:
        return False

def is_ignored_file(path: Path, project_root: Path) -> bool:
    """Check if file should be ignored based on common patterns."""
    # Convert to relative path from project root
    try:
        rel_path = path.relative_to(project_root)
    except ValueError:
        return True  # Outside project root
    
    # Check common ignore patterns
    ignore_patterns = {
        '.git', '__pycache__', '.pytest_cache', 'node_modules', '.venv', 'venv',
        '.env', '.DS_Store', '.vscode', '.idea', 'dist', 'build', '.agentcache',
        'coverage', 'htmlcov', '.coverage', '.mypy_cache', '.tox'
    }
    
    # Check if any part of the path matches ignore patterns
    for part in rel_path.parts:
        if part in ignore_patterns or part.startswith('.'):
            return True
    
    # Check file extensions to ignore
    ignore_extensions = {
        '.pyc', '.pyo', '.pyd', '.so', '.dylib', '.dll', '.exe', '.bin',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.ico', '.svg',
        '.mp3', '.mp4', '.avi', '.mov', '.wav', '.flac',
        '.zip', '.tar', '.gz', '.bz2', '.xz', '.rar', '.7z'
    }
    
    if path.suffix.lower() in ignore_extensions:
        return True
    
    return False

def get_file_summary(path: Path, content: str = None) -> str:
    """Generate a brief summary of a file's content."""
    try:
        if content is None:
            if not is_text_file(path):
                return f"Binary file ({format_file_size(path.stat().st_size)})"
            content = path.read_text(encoding="utf-8", errors="ignore")
        
        lines = content.splitlines()
        line_count = len(lines)
        
        if line_count == 0:
            return "Empty file"
        
        # Get first few non-empty lines as summary
        summary_lines = []
        for line in lines[:10]:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('//'):
                summary_lines.append(line[:80])
                if len(summary_lines) >= 3:
                    break
        
        summary = "; ".join(summary_lines)
        if len(summary) > 200:
            summary = summary[:197] + "..."
        
        size_info = format_file_size(len(content.encode('utf-8')))
        return f"{summary} ({line_count} lines, {size_info})"
    except Exception as e:
        log.warning(f"Failed to summarize {path}: {e}")
        return f"Could not read file: {e}"

def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

def truncate_content(content: str, max_length: int = 5000) -> str:
    """Truncate content to maximum length."""
    if len(content) <= max_length:
        return content
    
    lines = content.splitlines()
    if len(lines) <= 10:
        # For short files, just truncate
        return content[:max_length] + "\n... [truncated]"
    
    # For longer files, try to keep beginning and end
    half_length = max_length // 2
    beginning = content[:half_length]
    ending = content[-half_length:]
    
    return beginning + "\n\n... [middle content truncated] ...\n\n" + ending

def safe_filename(name: str) -> str:
    """Convert string to safe filename."""
    # Replace unsafe characters
    safe = "".join(c if c.isalnum() or c in '-_.' else '_' for c in name)
    # Limit length and remove leading/trailing dots
    safe = safe[:100].strip('.')
    # Ensure not empty
    return safe if safe else "unnamed"
