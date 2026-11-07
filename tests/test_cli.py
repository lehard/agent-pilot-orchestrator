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


def test_edit_title_and_priority_keeps_id(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "first"]) == 0
    assert main(["add", "buy mlik", "--priority", "low"]) == 0
    assert main(["done", "2"]) == 0
    capsys.readouterr()
    assert main(["edit", "2", "--title", "buy milk"]) == 0
    assert capsys.readouterr().out == "edited 2\n"
    assert main(["edit", "2", "--priority", "high"]) == 0
    capsys.readouterr()
    assert main(["list", "--all"]) == 0
    out = capsys.readouterr().out
    assert "[ ] 1. first (normal)" in out
    assert "[x] 2. buy milk (high)" in out


def test_edit_both_options_at_once(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "a"]) == 0
    assert main(["edit", "1", "--title", "b", "--priority", "high"]) == 0
    capsys.readouterr()
    assert main(["list"]) == 0
    assert "[ ] 1. b (high)" in capsys.readouterr().out


def test_edit_without_options_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "a"]) == 0
    capsys.readouterr()
    assert main(["edit", "1"]) == 1
    assert "nothing to edit: pass --title and/or --priority" in capsys.readouterr().err


def test_edit_unknown_id_returns_error(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["edit", "5", "--title", "x"]) == 1
    assert "no task with id 5" in capsys.readouterr().err


@pytest.mark.parametrize("title", ["", "   "])
def test_edit_rejects_empty_title(tmp_path, monkeypatch, capsys, title):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "keep me"]) == 0
    capsys.readouterr()
    assert main(["edit", "1", "--title", title]) == 1
    assert "task title must not be empty" in capsys.readouterr().err
    assert main(["list"]) == 0
    assert "[ ] 1. keep me (normal)" in capsys.readouterr().out


def test_edit_rejects_unknown_priority(tmp_path, monkeypatch):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "a"]) == 0
    with pytest.raises(SystemExit):
        main(["edit", "1", "--priority", "urgent"])
