from typer.testing import CliRunner
from devagent.cli import app

def test_cli_scan_and_approve_error(tmp_path):
    runner = CliRunner()
    r1 = runner.invoke(app, ["scan","-w", tmp_path.as_posix()])
    assert r1.exit_code == 0
    r2 = runner.invoke(app, ["approve","--code","X","-w", tmp_path.as_posix()])
    assert r2.exit_code != 0
