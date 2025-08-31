from __future__ import annotations
import httpx, json
from typing import Tuple
from .schemas import Plan, Action
from .creds import get_openrouter_key
from .utils import hash_str

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
SYSTEM_TAG = "system"
USER_TAG = "user"

class LLMClient:
    def __init__(self, model: str, workspace: str | None = None):
        self.model = model
        self.workspace = workspace or "."

    def _headers(self) -> dict:
        key = get_openrouter_key(self.workspace)
        if not key:
            raise RuntimeError("Kein OpenRouter API-Key gefunden. Nutze 'devagent key set' oder /key set.")
        return {
            "Authorization": f"Bearer {key}",
            "HTTP-Referer": "https://devagent.local",
            "X-Title": "devagent",
            "Content-Type": "application/json",
        }

    def generate_plan(self, system_prompt: str, user_prompt: str) -> Tuple[Plan, str]:
        body = {
            "model": self.model,
            "messages": [
                {"role": SYSTEM_TAG, "content": system_prompt},
                {"role": USER_TAG, "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": { "type": "json_schema", "json_schema": {
                "name": "action_plan",
                "schema": {
                    "type": "object",
                    "properties": {
                        "actions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "type": {"enum": ["run","edit","create","delete"]},
                                    "cmd": {"type":"array","items":{"type":"string"}},
                                    "file": {"type":"string"},
                                    "patch": {"type":"string"},
                                    "content": {"type":"string"},
                                },
                                "required": ["type"],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["actions"],
                    "additionalProperties": False
                }
            }},
        }
        with httpx.Client(timeout=60) as client:
            r = client.post(OPENROUTER_URL, headers=self._headers(), json=body)
            r.raise_for_status()
            data = r.json()

        content = data["choices"][0]["message"]["content"]
        payload = json.loads(content) if isinstance(content, str) else content
        actions_raw = payload.get("actions") or []
        actions = [Action.model_validate(a) for a in actions_raw]
        plan = Plan(actions=actions)
        plan_hash = hash_str(json.dumps(actions_raw, ensure_ascii=False, sort_keys=True))
        return plan, plan_hash
