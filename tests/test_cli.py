import json
from datetime import datetime

import pytest

from taskbook import storage
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


# --- history ----------------------------------------------------------------------


def write_v2(path, tasks):
    path.write_text(json.dumps({"version": 2, "tasks": tasks}), encoding="utf-8")


def entry(task_id, title, completed_at, done=True, priority="normal"):
    return {
        "id": task_id,
        "title": title,
        "priority": priority,
        "done": done,
        "completed_at": completed_at,
    }


def shown(stamp):
    return datetime.fromisoformat(stamp).astimezone().strftime("%Y-%m-%d %H:%M")


OLD = "2026-11-01T09:00:00+03:00"
NEW = "2026-11-05T18:30:00+03:00"


@pytest.fixture
def history_file(tmp_path, monkeypatch):
    path = tmp_path / "t.json"
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    write_v2(
        path,
        [
            entry(1, "old", OLD),
            entry(2, "new", NEW, priority="high"),
            entry(3, "legacy", None),
            entry(4, "pending", None, done=False),
        ],
    )
    return path


def test_history_lists_newest_first_with_undated_last(history_file, capsys):
    before = history_file.read_bytes()
    assert main(["history"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        f"{shown(NEW)}  2. new (high)",
        f"{shown(OLD)}  1. old (normal)",
        "date unknown      3. legacy (normal)",
    ]
    assert history_file.read_bytes() == before


def test_history_since_filters_by_day(history_file, capsys):
    assert main(["history", "--since", "2026-11-03"]) == 0
    assert capsys.readouterr().out.splitlines() == [f"{shown(NEW)}  2. new (high)"]
    assert main(["history", "--since", "2026-12-01"]) == 0
    assert capsys.readouterr().out == "no completed tasks\n"


@pytest.mark.parametrize("value", ["05.11.2026", "2026-13-01", "2026-1-5", "yesterday"])
def test_history_rejects_bad_date(history_file, capsys, value):
    with pytest.raises(SystemExit) as info:
        main(["history", "--since", value])
    assert info.value.code == 2
    assert "date must be YYYY-MM-DD" in capsys.readouterr().err


def test_history_on_missing_file_creates_nothing(tmp_path, monkeypatch, capsys):
    path = tmp_path / "t.json"
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    assert main(["history"]) == 0
    assert capsys.readouterr().out == "no completed tasks\n"
    assert not path.exists()


def test_done_then_history_shows_today(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TASKBOOK_FILE", str(tmp_path / "t.json"))
    assert main(["add", "a"]) == 0
    assert main(["done", "1"]) == 0
    capsys.readouterr()
    assert main(["history", "--since", datetime.now().date().isoformat()]) == 0
    out = capsys.readouterr().out
    assert out.endswith("  1. a (normal)\n")
    assert out.startswith(datetime.now().strftime("%Y-%m-%d "))


def test_done_twice_returns_error(tmp_path, monkeypatch, capsys):
    path = tmp_path / "t.json"
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    assert main(["add", "a"]) == 0
    assert main(["done", "1"]) == 0
    before = path.read_bytes()
    capsys.readouterr()
    assert main(["done", "1"]) == 1
    assert "error: task 1 is already done" in capsys.readouterr().err
    assert path.read_bytes() == before


# --- task files from the earlier release and damaged files ------------------------

V1 = [
    {"id": 1, "title": "buy milk", "priority": "high", "done": True},
    {"id": 2, "title": "call mom", "priority": "normal", "done": False},
]


def test_v1_file_works_and_is_not_rewritten_by_reads(tmp_path, monkeypatch, capsys):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(V1), encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    assert main(["list", "--all"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "[x] 1. buy milk (high)",
        "[ ] 2. call mom (normal)",
        "1 pending",
    ]
    assert main(["history"]) == 0
    assert capsys.readouterr().out == "date unknown      1. buy milk (high)\n"
    assert path.read_bytes() == before
    assert not storage.backup_path(path).exists()


def test_v1_file_is_upgraded_on_first_change(tmp_path, monkeypatch, capsys):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(V1), encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    assert main(["done", "2"]) == 0
    assert storage.backup_path(path).read_bytes() == before
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 2
    capsys.readouterr()
    assert main(["history"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].endswith("  2. call mom (normal)")
    assert lines[1] == "date unknown      1. buy milk (high)"


def test_existing_backup_blocks_upgrade_with_error(tmp_path, monkeypatch, capsys):
    path = tmp_path / "t.json"
    path.write_text(json.dumps(V1), encoding="utf-8")
    storage.backup_path(path).write_text("keep", encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    assert main(["add", "x"]) == 1
    assert "t.json.v1.bak already exists" in capsys.readouterr().err
    assert path.read_bytes() == before


@pytest.mark.parametrize("command", [["list"], ["history"], ["add", "x"], ["done", "1"]])
@pytest.mark.parametrize(
    ("content", "message"),
    [
        ('{"version": 2, "tasks": [', "not valid JSON"),
        ('{"version": 3, "tasks": []}', "unsupported format version 3"),
        ('{"version": 2, "tasks": [{"id": 1}]}', "task entry #1 is missing field"),
    ],
)
def test_damaged_file_is_an_error_not_empty(
    tmp_path, monkeypatch, capsys, command, content, message
):
    path = tmp_path / "t.json"
    path.write_text(content, encoding="utf-8")
    monkeypatch.setenv("TASKBOOK_FILE", str(path))
    assert main(command) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert message in captured.err
    assert path.read_text(encoding="utf-8") == content
