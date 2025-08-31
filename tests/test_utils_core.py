from devagent.utils import (
    hash_str, rand_code, json_dump, json_load, normalize_cmd,
    ensure_no_pipes_redirs, read_text_limited, is_git_repo, git_commit_all
)

def test_utils_basics(tmp_path):
    # hash_str stabil & unterscheidbar
    assert hash_str("abc") == hash_str("abc")
    assert hash_str("abc") != hash_str("abcd")

    # rand_code: mehrere eindeutig/mit Länge
    codes = {rand_code() for _ in range(20)}
    assert len(codes) >= 10
    assert all(isinstance(c, str) and len(c) >= 6 for c in codes)

    # json dump/load
    p = tmp_path / "x.json"
    json_dump(p.as_posix(), {"a": 1})
    assert json_load(p.as_posix())["a"] == 1

    # normalize & pipe/redir-check
    assert normalize_cmd(["python","-V"]) == ["python","-V"]
    assert ensure_no_pipes_redirs(["python","-V"]) is True
    assert ensure_no_pipes_redirs(["echo","hi","|","grep","h"]) is False

    # read_text_limited
    big = tmp_path / "big.txt"
    big.write_text("x"*1000, encoding="utf-8")
    txt = read_text_limited(big.as_posix(), 100)
    assert len(txt) <= 100

    # git helpers (kein Repo)
    assert is_git_repo(tmp_path.as_posix()) is False
    assert git_commit_all(tmp_path.as_posix(), "msg") is None
