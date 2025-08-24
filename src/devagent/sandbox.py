from __future__ import annotations
from pathlib import Path
import json
from .constants import STATE_DIR_NAME, CONFIG_FILE_NAME, LAST_PLAN_FILE, LAST_PATCH_FILE, INDEX_FILE, SESSION_FILE

class Sandbox:
    def __init__(self, root: Path):
        self.root = root
        self.state_dir = root / STATE_DIR_NAME
        self.config_file = self.state_dir / CONFIG_FILE_NAME
        self.last_plan = self.state_dir / LAST_PLAN_FILE
        self.last_patch = self.state_dir / LAST_PATCH_FILE
        self.index_file = self.state_dir / INDEX_FILE
        self.session_file = self.state_dir / SESSION_FILE

    def ensure(self) -> None:
        self.state_dir.mkdir(exist_ok=True)

    def exists(self) -> bool:
        return self.state_dir.exists()

    def load_session(self) -> dict:
        if self.session_file.exists():
            return json.loads(self.session_file.read_text(encoding="utf-8"))
        return {"spent_usd": 0.0, "calls": 0}

    def save_session(self, data: dict) -> None:
        self.session_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
