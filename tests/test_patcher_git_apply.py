import subprocess, textwrap
from devagent.schemas import Plan, Action
from devagent.executor import execute

def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)

def test_edit_via_patch_in_git(tmp_path):
    ws = tmp_path
    (ws / "a.txt").write_text("line1\nline2\n", encoding="utf-8")
    _run(["git","init"], ws)
    _run(["git","add","-A"], ws)
    _run(["git","-c","user.email=test@example.com","-c","user.name=Test","commit","-m","init"], ws)

    patch = textwrap.dedent("""\
    --- a/a.txt
    +++ b/a.txt
    @@ -1,2 +1,2 @@
     line1
    -line2
    +line2-mod
    """)

    plan = Plan(actions=[Action(type="edit", file="a.txt", patch=patch)])
    ok, msgs = execute(plan, ws.as_posix(), run_id="patchrun", require_git_for_patches=True)
    assert ok, "\n".join(msgs)
    assert (ws / "a.txt").read_text(encoding="utf-8").endswith("line2-mod\n")
