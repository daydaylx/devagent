from devagent.schemas import Plan, Action
from devagent.verifier import verify_plan
from devagent.config import Config

def test_run_with_pipe_forbidden(tmp_path):
    ws = tmp_path.as_posix()
    cfg = Config()
    plan = Plan(actions=[Action(type="run", cmd=["python", "-c", "print(1)", "|", "grep", "1"])])
    errs = verify_plan(plan, ws, cfg, has_git=False)
    assert any("Pipes/Redirections" in e for e in errs)

def test_run_disallow_command(tmp_path):
    ws = tmp_path.as_posix()
    cfg = Config()
    cfg.disallow_commands = {"python"}
    plan = Plan(actions=[Action(type="run", cmd=["python","-V"])])
    errs = verify_plan(plan, ws, cfg, has_git=False)
    assert any("explizit verboten" in e for e in errs)
