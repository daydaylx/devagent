import os
from devagent.schemas import Plan, Action
from devagent.executor import execute

def test_delete_moves_to_trash(tmp_path):
    ws = tmp_path
    f = ws / "data.txt"
    f.write_text("hello", encoding="utf-8")
    plan = Plan(actions=[Action(type="delete", file="data.txt")])
    ok, msgs = execute(plan, ws.as_posix(), run_id="testrun", require_git_for_patches=False)
    assert ok
    assert "DELETE data.txt -> trash" in "\n".join(msgs)
    trash = ws / ".devagent" / "trash" / "testrun" / "data.txt"
    assert trash.exists()
