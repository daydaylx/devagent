from devagent.schemas import Plan, Action
from devagent.executor import execute

def test_run_nonzero_fails(tmp_path):
    ws = tmp_path
    plan = Plan(actions=[Action(type="run", cmd=["python","-c","import sys; sys.exit(3)"])])
    ok, msgs = execute(plan, ws.as_posix(), run_id="r", require_git_for_patches=False)
    assert not ok
    assert any("exit 3" in m for m in msgs)

def test_edit_via_content(tmp_path):
    ws = tmp_path
    plan = Plan(actions=[Action(type="edit", file="x.txt", content="abc\n")])
    ok, msgs = execute(plan, ws.as_posix(), run_id="e", require_git_for_patches=False)
    assert ok
    assert (ws / "x.txt").read_text(encoding="utf-8") == "abc\n"
