from __future__ import annotations
from pathlib import Path
from .openrouter import ORClient
from .policies import CostGuard

def make_diff_for_goal(root: Path, goal: str, repo_summary: str, model: str, client: ORClient, cost: CostGuard) -> str:
    sys_prompt = (Path(__file__).parent / "prompts" / "planner.md").read_text(encoding="utf-8")
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": f"REPO SUMMARY:\n{repo_summary}\n\nGOAL:\n{goal}"},
    ]
    resp = client.chat(messages, model=model)
    choice = resp["choices"][0]
    content = choice["message"]["content"]
    usage = resp.get("usage", {})
    cost.check_and_record(usage)
    return content
