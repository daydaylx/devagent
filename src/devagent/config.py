from __future__ import annotations
import os
import tomllib
from dataclasses import dataclass
from pathlib import Path
from .constants import DEFAULT_MODEL, DEFAULT_MAX_USD

@dataclass
class Config:
    model: str = DEFAULT_MODEL
    max_usd: float = DEFAULT_MAX_USD
    test_cmd: str | None = None

    @classmethod
    def load(cls, config_path: Path) -> "Config":
        data = {}
        if config_path.exists():
            with config_path.open("rb") as f:
                data = tomllib.load(f)
        # ENV overrides
        model = os.environ.get("DEVAGENT_MODEL", data.get("model", DEFAULT_MODEL))
        max_usd = float(os.environ.get("DEVAGENT_MAX_USD", data.get("max_usd", DEFAULT_MAX_USD)))
        test_cmd = os.environ.get("DEVAGENT_TEST_CMD", data.get("test_cmd"))
        return cls(model=model, max_usd=max_usd, test_cmd=test_cmd)

    def dump(self) -> dict:
        out = {
            "model": self.model,
            "max_usd": self.max_usd,
        }
        if self.test_cmd:
            out["test_cmd"] = self.test_cmd
        return out

    def to_toml(self) -> str:
        lines = [f'model = "{self.model}"', f"max_usd = {self.max_usd}"]
        if self.test_cmd:
            esc = self.test_cmd.replace('"', '\\"')
            lines.append(f'test_cmd = "{esc}"')
        return "\n".join(lines) + "\n"
