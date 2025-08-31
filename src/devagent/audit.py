from __future__ import annotations
import os, time, json
from .constants import LOG_DIR
from .utils import json_dump

def log_event(workspace: str, run_id: str, event: str, payload: dict) -> None:
    ts = int(time.time())
    rec = {"ts": ts, "event": event, "payload": payload}
    path = os.path.join(workspace, LOG_DIR, f"{run_id}.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
