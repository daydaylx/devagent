from devagent.schemas import Plan, Action
from devagent.verifier import verify_plan
from devagent.config import Config

def test_verify_run_allowlist(tmp_path):
    ws = tmp_path.as_posix()
    cfg = Config()
    plan = Plan(actions=[Action(type="run", cmd=["pytest","-q"])])
    errs = verify_plan(plan, ws, cfg, has_git=False)
    assert not errs

def test_verify_run_forbidden(tmp_path):
    ws = tmp_path.as_posix()
    cfg = Config()
    plan = Plan(actions=[Action(type="run", cmd=["sudo","rm","-rf","/"])])
    errs = verify_plan(plan, ws, cfg, has_git=False)
    assert errs
