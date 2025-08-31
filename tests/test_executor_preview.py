from devagent.schemas import Plan, Action
from devagent.executor import preview

def test_preview_create(tmp_path):
    ws = tmp_path.as_posix()
    plan = Plan(actions=[Action(type="create", file="x.txt", content="hello")])
    items = preview(plan, ws)
    assert items and items[0].kind == "create"
