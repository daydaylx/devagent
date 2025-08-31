import textwrap
from devagent.config import load_config

def test_load_config_overrides(tmp_path):
    ws = tmp_path
    (ws / ".devagent").mkdir(parents=True, exist_ok=True)
    (ws / ".devagent" / "config.toml").write_text(textwrap.dedent("""
    model = "foo/bar"
    allow_commands = ["pytest","git"]
    disallow_commands = ["python"]
    max_actions = 7
    net_allowed = true
    enforce_git_for_patches = false
    permission_mode = "plan"
    dangerously_skip_permissions = true
    extra_workspaces = ["../other"]
    ignores = ["build"]
    """), encoding="utf-8")

    cfg = load_config(ws.as_posix())
    assert cfg.model == "foo/bar"
    assert "git" in cfg.allow_commands
    assert "python" in cfg.disallow_commands
    assert cfg.max_actions == 7
    assert cfg.net_allowed is True
    assert cfg.enforce_git_for_patches is False
    assert cfg.permission_mode == "plan"
    assert cfg.dangerously_skip_permissions is True
    assert cfg.extra_workspaces == ["../other"]
    assert cfg.ignores == ["build"]
