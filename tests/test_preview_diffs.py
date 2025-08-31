from devagent.schemas import Plan, Action
from devagent.executor import preview

def test_preview_create_shows_diff(tmp_path):
    ws = tmp_path.as_posix()
    plan = Plan(actions=[Action(type="create", file="note.txt", content="hello\n")])
    items = preview(plan, ws)
    assert items and items[0].diff and "--- a/note.txt" in items[0].diff
