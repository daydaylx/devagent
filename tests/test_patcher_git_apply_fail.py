import subprocess, textwrap
from devagent.schemas import Plan, Action
from devagent.executor import execute

def _run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)

def test_edit_via_bad_patch_fails(tmp_path):
    ws = tmp_path
    (ws / "a.txt").write_text("L1\nL2\n", encoding="utf-8")
    _run(["git","init"], ws); _run(["git","add","-A"], ws)
    _run(["git","-c","user.email=t@example.com","-c","user.name=T","commit","-m","init"], ws)

    # Hunk passt NICHT -> git apply muss scheitern
    bad_patch = textwrap.dedent("""\
    --- a/a.txt
    +++ b/a.txt
    @@ -1,2 +1,2 @@
     L1
    -L2
    +CHANGED
    @@ -10,12 +10,12 @@
    -doesnotexist
    +nope
    """)
    plan = Plan(actions=[Action(type="edit", file="a.txt", patch=bad_patch)])
    ok, msgs = execute(plan, ws.as_posix(), run_id="badpatch", require_git_for_patches=True)
    assert not ok
    assert any("git apply fehlgeschlagen" in m for m in msgs)
