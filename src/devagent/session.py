from __future__ import annotations
from .sandbox import Sandbox

class Session:
    def __init__(self, sandbox: Sandbox):
        self.sb = sandbox
        self.data = self.sb.load_session()

    def inc(self, k: str, v):
        self.data[k] = type(v)(self.data.get(k, 0)) + v
        self.sb.save_session(self.data)

    def get(self, k: str, default=None):
        return self.data.get(k, default)
