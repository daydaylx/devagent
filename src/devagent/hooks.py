from __future__ import annotations
import os, json, stat, subprocess, shlex, time
from typing import Tuple, List
from .constants import HOOKS_DIR

def _exec_file(path: str, payload: dict, timeout: int = 5) -> Tuple[int, str, str]:
    # Führt beliebige Hook-Executables aus (Shell-Skripte, Python etc.).
    # Payload (JSON) via STDIN.
    proc = subprocess.Popen([path], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        out, err = proc.communicate(json.dumps(payload), timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        out, err = proc.communicate()
        return 124, out, err
    return proc.returncode, out, err

def run_hooks(workspace: str, event: str, payload: dict, timeout: int = 5) -> Tuple[bool, List[str]]:
    """Sucht ausführbare Dateien unter .devagent/hooks/<event>/* und führt sie aus.
    Exit-Code 0 => allow, !=0 => block.
    Gibt (allowed, messages) zurück.
    """
    base = os.path.join(workspace, HOOKS_DIR, event)
    msgs: List[str] = []
    allowed = True
    if not os.path.isdir(base):
        return True, msgs
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        try:
            st = os.stat(path)
            if not (st.st_mode & stat.S_IXUSR):
                continue
            code, out, err = _exec_file(path, payload, timeout=timeout)
            if out.strip():
                msgs.append(f"[hook:{event}:{name}] {out.strip()}")
            if err.strip():
                msgs.append(f"[hook:{event}:{name}:stderr] {err.strip()}")
            if code != 0:
                allowed = False
        except Exception as e:
            msgs.append(f"[hook:{event}:{name}] ERROR {e}")
            allowed = False
    return allowed, msgs
