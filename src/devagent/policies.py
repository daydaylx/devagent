from __future__ import annotations
from .sandbox import Sandbox
from .config import Config

class CostGuard:
    def __init__(self, sandbox: Sandbox, cfg: Config):
        self.sandbox = sandbox
        self.cfg = cfg

    def check_and_record(self, usage: dict) -> None:
        # OpenAI-compatible usage: {"prompt_tokens": int, "completion_tokens": int, "total_tokens": int}
        session = self.sandbox.load_session()
        pt = float(usage.get("prompt_tokens", 0))
        ct = float(usage.get("completion_tokens", 0))
        # konservative Schätzung: $0.01 / 1k Token
        est_usd = (pt + ct) / 1000.0 * 0.01
        session["spent_usd"] = float(session.get("spent_usd", 0.0)) + est_usd
        session["calls"] = int(session.get("calls", 0)) + 1
        self.sandbox.save_session(session)
        if session["spent_usd"] > self.cfg.max_usd:
            raise SystemExit(f"Cost cap exceeded: ${session['spent_usd']:.4f} > ${self.cfg.max_usd:.2f}")
