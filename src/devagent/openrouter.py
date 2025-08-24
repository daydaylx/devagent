from __future__ import annotations
import os
import httpx
from .logging import get_logger

log = get_logger(__name__)

OPENROUTER_BASE = os.environ.get("OPENROUTER_BASE", "https://openrouter.ai/api/v1")

class ORClient:
    def __init__(self, api_key: str | None = None, model: str | None = None, title: str = "DevAgent CLI"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise SystemExit("Missing OPENROUTER_API_KEY (set ENV or .env)")
        self.model = model
        self.title = title
        self.client = httpx.Client(timeout=60)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.devagent",
            "X-Title": self.title,
        }

    def list_models(self) -> list[dict]:
        r = self.client.get(f"{OPENROUTER_BASE}/models", headers=self._headers())
        r.raise_for_status()
        data = r.json()
        return data.get("data", [])

    def chat(self, messages: list[dict], model: str | None = None, max_tokens: int | None = None) -> dict:
        payload = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        r = self.client.post(f"{OPENROUTER_BASE}/chat/completions", headers=self._headers(), json=payload)
        r.raise_for_status()
        return r.json()
