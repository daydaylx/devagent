from typer.testing import CliRunner
from devagent.cli import app
from devagent.schemas import Plan, Action

class DummyLLM:
    def __init__(self, model): pass
    def generate_plan(self, system_prompt, user_prompt):
        p = Plan(actions=[Action(type="create", file="foo.txt", content="hi\n")])
        return p, "hash123"

def test_cli_lintfix_flow(tmp_path, monkeypatch):
    # LLM faken
    monkeypatch.setattr("devagent.cli.LLMClient", DummyLLM)
    runner = CliRunner()
    ws = tmp_path.as_posix()

    r = runner.invoke(app, ["lint-fix","-w", ws])
    assert r.exit_code == 0

    r = runner.invoke(app, ["preview","-w", ws])
    assert r.exit_code == 0
    code = (tmp_path/".devagent"/"approval_code.txt").read_text().strip()

    r = runner.invoke(app, ["approve","--code", code, "-w", ws])
    assert r.exit_code == 0

    r = runner.invoke(app, ["execute","-w", ws])
    assert r.exit_code == 0
    assert (tmp_path/"foo.txt").read_text(encoding="utf-8") == "hi\n"
