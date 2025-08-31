from __future__ import annotations
import os, json, hashlib, base64, re, subprocess, shlex, time, pathlib
from typing import Iterable, List, Tuple

def is_text_bytes(b: bytes) -> bool:
    if not b:
        return True
    if b.startswith(b"\x00"):
        return False
    try:
        b.decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False

def read_text_limited(path: str, max_bytes: int) -> str:
    with open(path, "rb") as f:
        data = f.read(max_bytes)
    if not is_text_bytes(data):
        return ""
    text = data.decode("utf-8", errors="replace")
    return text

def hash_str(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12]

def rand_code() -> str:
    raw = os.urandom(9)
    return base64.b32encode(raw).decode("ascii").strip("=").lower()

def json_dump(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

def json_load(path: str) -> dict | None:
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def which(cmd: str) -> str | None:
    for p in os.environ.get("PATH", "").split(os.pathsep):
        cand = os.path.join(p, cmd)
        if os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
    return None

def run_cmd(args: List[str], cwd: str | None = None, timeout: int | None = None) -> Tuple[int, str, str]:
    proc = subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return 124, out, err
    return proc.returncode, out, err

def is_git_repo(path: str) -> bool:
    code, _, _ = run_cmd(["git", "rev-parse", "--is-inside-work-tree"], cwd=path)
    return code == 0

def git_top(path: str) -> str | None:
    code, out, _ = run_cmd(["git", "rev-parse", "--show-toplevel"], cwd=path)
    return out.strip() if code == 0 else None

def git_commit_all(path: str, message: str) -> str | None:
    code, _, _ = run_cmd(["git", "add", "-A"], cwd=path)
    if code != 0:
        return None
    code, out, _ = run_cmd(["git", "commit", "-m", message], cwd=path)
    if code != 0:
        return None
    code, out, _ = run_cmd(["git", "rev-parse", "HEAD"], cwd=path)
    return out.strip() if code == 0 else None

def ensure_no_pipes_redirs(argv: List[str]) -> bool:
    forbidden = {"|", ">", ">>", "<", "2>", "2>>", "&&", "||", ";"}
    return not any(token in forbidden for token in argv)

def normalize_cmd(argv: List[str]) -> List[str]:
    # flatten possible whitespace weirdness
    flat: List[str] = []
    for a in argv:
        flat += shlex.split(a) if isinstance(a, str) else [a]
    return flat
