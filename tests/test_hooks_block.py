import os, stat
from devagent.schemas import Plan, Action
from devagent.executor import execute

def test_pretooluse_hook_blocks(tmp_path):
    ws = tmp_path
    hook_dir = ws / ".devagent" / "hooks" / "PreToolUse"
    hook_dir.mkdir(parents=True, exist_ok=True)
    hook = hook_dir / "deny.sh"
    hook.write_text("#!/usr/bin/env bash\nread payload; echo blocked >&2; exit 1\n", encoding="utf-8")
    hook.chmod(hook.stat().st_mode | stat.S_IXUSR)

    plan = Plan(actions=[Action(type="create", file="x.txt", content="x")])
    ok, msgs = execute(plan, ws.as_posix(), run_id="hookrun", require_git_for_patches=False)
    assert not ok
    assert any("blockiert" in m for m in msgs)
    assert not (ws / "x.txt").exists()
