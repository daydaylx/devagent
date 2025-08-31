import stat
from devagent.hooks import run_hooks

def test_pretooluse_timeout(tmp_path):
    ws = tmp_path
    d = ws / ".devagent" / "hooks" / "PreToolUse"
    d.mkdir(parents=True, exist_ok=True)
    h = d / "sleep.sh"
    h.write_text("#!/usr/bin/env bash\nsleep 1\n", encoding="utf-8")
    h.chmod(h.stat().st_mode | stat.S_IXUSR)
    allowed, msgs = run_hooks(ws.as_posix(), "PreToolUse", {"x": 1}, timeout=0.01)
    assert allowed is False
    assert len(msgs) >= 0  # wir wollen nur durch den Timeout-Zweig
