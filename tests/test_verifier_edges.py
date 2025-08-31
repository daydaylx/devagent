from devagent.schemas import Plan, Action
from devagent.verifier import verify_plan
from devagent.config import Config

def test_max_actions_and_missing_fields(tmp_path):
    ws = tmp_path.as_posix()
    cfg = Config()
    cfg.max_actions = 1
    plan = Plan(actions=[
        Action(type="run", cmd=["python","-V"]),                 # erlaubt
        Action(type="run", cmd=["bash","-lc","echo hi"]),        # NICHT in Allowlist -> Verifier-Fehler
    ])
    errs = verify_plan(plan, ws, cfg, has_git=False)
    assert any("Zu viele Aktionen" in e for e in errs)
    assert any("Befehl nicht erlaubt" in e for e in errs)
