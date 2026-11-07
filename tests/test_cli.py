import pytest

from taskbook.cli import main


def test_add_list_done(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "buy milk", "--priority", "high"]) == 0
    assert main(["done", "1"]) == 0
    capsys.readouterr()
    assert main(["list", "--all"]) == 0
    assert "[x] 1. buy milk (high)" in capsys.readouterr().out


def test_missing_env_fails(monkeypatch):
    monkeypatch.delenv("TASKBOOK_FILE", raising=False)
    with pytest.raises(SystemExit, match="TASKBOOK_FILE"):
        main(["list"])


def test_done_unknown_id_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["done", "5"]) == 1
    assert "no task with id 5" in capsys.readouterr().err


def test_list_prints_pending_count(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    for title in ("a", "b", "c"):
        assert main(["add", title]) == 0
    assert main(["done", "2"]) == 0
    capsys.readouterr()
    assert main(["list"]) == 0
    assert capsys.readouterr().out.splitlines()[-1] == "2 pending"
    assert main(["list", "--all"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 4
    assert lines[-1] == "2 pending"
