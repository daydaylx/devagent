from __future__ import annotations
import os, json, time, uuid
from typing import Optional
from .constants import SESSIONS_DIR

class Transcript:
    def __init__(self, workspace: str, session_id: Optional[str] = None):
        self.workspace = os.path.realpath(workspace)
        self.session_id = session_id or uuid.uuid4().hex[:10]
        self.path = os.path.join(self.workspace, SESSIONS_DIR, f"{self.session_id}.jsonl")
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

    def write(self, event: str, payload: dict) -> None:
        rec = {"ts": int(time.time()), "event": event, "payload": payload}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    def info(self) -> str:
        return self.path
