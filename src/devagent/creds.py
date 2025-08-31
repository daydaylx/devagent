from __future__ import annotations
import os, stat, tomllib
from typing import Literal, Optional

def _xdg_config_home() -> str:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return base
    return os.path.join(os.path.expanduser("~"), ".config")

def _user_creds_path() -> str:
    return os.path.join(_xdg_config_home(), "devagent", "credentials.toml")

def _project_creds_path(workspace: str) -> str:
    return os.path.join(os.path.realpath(workspace), ".devagent", "credentials.toml")

def _ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)

def _chmod_600(path: str) -> None:
    try:
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except PermissionError:
        pass

def _toml_load(path: str) -> dict:
    with open(path, "rb") as f:
        return tomllib.load(f)

def _toml_save(path: str, data: dict) -> None:
    _ensure_parent(path)
    lines = []
    for k, v in data.items():
        if not isinstance(v, str):
            continue
        esc = v.replace("\\", "\\\\").replace('"', '\\"')
        lines.append(f'{k} = "{esc}"\n')
    with open(path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    _chmod_600(path)

def _read_key_from_file(path: str) -> Optional[str]:
    if not os.path.exists(path):
        return None
    try:
        data = _toml_load(path)
        key = data.get("openrouter_api_key")
        if isinstance(key, str) and key.strip():
            return key.strip()
    except Exception:
        return None
    return None

def get_openrouter_key(workspace: str) -> Optional[str]:
    k = os.environ.get("OPENROUTER_API_KEY")
    if isinstance(k, str) and k.strip():
        return k.strip()
    k = _read_key_from_file(_project_creds_path(workspace))
    if k:
        return k
    return _read_key_from_file(_user_creds_path())

def set_openrouter_key(key: str, scope: Literal["project","user"], workspace: str) -> str:
    key = key.strip()
    if not key:
        raise ValueError("Leerer Key")
    path = _project_creds_path(workspace) if scope == "project" else _user_creds_path()
    _toml_save(path, {"openrouter_api_key": key})
    return path

def unset_openrouter_key(scope: Literal["project","user"], workspace: str) -> bool:
    path = _project_creds_path(workspace) if scope == "project" else _user_creds_path()
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False

def mask_key(key: Optional[str]) -> str:
    if not key:
        return "(kein Key)"
    s = key.strip()
    if len(s) <= 8:
        return "*" * len(s)
    return s[:6] + "…" + s[-4:]
