import pytest
from devagent.jail import ensure_inside

def test_ensure_inside_ok(tmp_path):
    ws = tmp_path.as_posix()
    p = ensure_inside(ws, "a/b/c.txt")
    assert p.startswith(ws)

def test_ensure_inside_block_abs(tmp_path):
    ws = tmp_path.as_posix()
    with pytest.raises(ValueError):
        ensure_inside(ws, "/etc/passwd")

def test_ensure_inside_block_dotdot(tmp_path):
    ws = tmp_path.as_posix()
    with pytest.raises(ValueError):
        ensure_inside(ws, "../x.txt")
