from typer.testing import CliRunner
from devagent.cli import app
from devagent.schemas import Plan, Action

class DummyLLM2:
    def __init__(self, model): pass
    def generate_plan(self, system_prompt, user_prompt):
        p = Plan(actions=[Action(type="run", cmd=["python","-V"])])
        return p, "h2"

def test_headless_prompt_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr("devagent.cli.LLMClient", DummyLLM2)
    runner = CliRunner()
    ws = tmp_path.as_posix()
    r = runner.invoke(app, ["-w", ws, "-p", "just do something", "-o", "yaml"])
    assert r.exit_code == 0
    assert "actions:" in r.stdout
