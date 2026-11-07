import json
import os
from datetime import datetime, timedelta, timezone

import pytest

from taskbook import storage
from taskbook.model import Task, TaskList

MSK = timezone(timedelta(hours=3))

V1_TASKS = [
    {"id": 1, "title": "buy milk", "priority": "high", "done": True},
    {"id": 2, "title": "call mom", "priority": "normal", "done": False},
]


def write_json(path, data):
    path.write_text(json.dumps(data), encoding="utf-8")


def v2_entry(**overrides):
    entry = {"id": 1, "title": "a", "priority": "normal", "done": False, "completed_at": None}
    entry.update(overrides)
    return entry


def test_missing_file_is_empty_list(tmp_path):
    assert storage.load(tmp_path / "none.json").tasks == []


def test_roundtrip(tmp_path):
    path = tmp_path / "t.json"
    moment = datetime(2026, 11, 7, 14, 5, tzinfo=MSK)
    tl = TaskList(clock=lambda: moment)
    tl.add("write tests", "high")
    tl.add("later")
    tl.complete(1)
    storage.save(tl, path)
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 2
    assert raw["tasks"][0]["completed_at"] == "2026-11-07T14:05:00+03:00"
    assert raw["tasks"][1]["completed_at"] is None
    loaded = storage.load(path)
    assert loaded.tasks[0].title == "write tests"
    assert loaded.tasks[0].done is True
    assert loaded.tasks[0].completed_at == moment
    assert loaded.tasks[1].completed_at is None


def test_invalid_json_raises(tmp_path):
    path = tmp_path / "t.json"
    path.write_text("{oops", encoding="utf-8")
    with pytest.raises(storage.StorageError, match="not valid JSON"):
        storage.load(path)


def test_v1_file_loads(tmp_path):
    path = tmp_path / "t.json"
    write_json(path, V1_TASKS)
    tasks = storage.load(path).tasks
    assert [(t.id, t.title, t.priority, t.done, t.completed_at) for t in tasks] == [
        (1, "buy milk", "high", True, None),
        (2, "call mom", "normal", False, None),
    ]


def test_saving_v1_file_keeps_backup_and_upgrades(tmp_path):
    path = tmp_path / "t.json"
    write_json(path, V1_TASKS)
    original = path.read_bytes()
    tl = storage.load(path)
    tl.add("new")
    storage.save(tl, path)
    assert storage.backup_path(path).read_bytes() == original
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["version"] == 2
    assert [t["id"] for t in raw["tasks"]] == [1, 2, 3]
    # the next save is a v2 -> v2 write and does not touch the backup again
    storage.save(storage.load(path), path)
    assert storage.backup_path(path).read_bytes() == original


def test_existing_backup_blocks_upgrade(tmp_path):
    path = tmp_path / "t.json"
    write_json(path, V1_TASKS)
    backup = storage.backup_path(path)
    backup.write_text("older backup", encoding="utf-8")
    original = path.read_bytes()
    with pytest.raises(storage.StorageError, match=r"t\.json\.v1\.bak already exists"):
        storage.save(storage.load(path), path)
    assert path.read_bytes() == original
    assert backup.read_text(encoding="utf-8") == "older backup"


def test_save_leaves_no_temp_files_and_keeps_mode(tmp_path):
    path = tmp_path / "t.json"
    storage.save(TaskList(tasks=[Task(id=1, title="a")]), path)
    os.chmod(path, 0o640)
    storage.save(storage.load(path), path)
    assert sorted(p.name for p in tmp_path.iterdir()) == ["t.json"]
    assert path.stat().st_mode & 0o777 == 0o640


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"version": 3, "tasks": []}, "unsupported format version 3"),
        ({"version": "2", "tasks": []}, "unsupported format version '2'"),
        ({"version": 1, "tasks": []}, "unsupported format version 1"),
        ({"tasks": []}, "exactly the keys 'version' and 'tasks'"),
        ({"version": 2, "tasks": {}}, "'tasks' must be a JSON list"),
        ("tasks", "must contain a JSON object or a JSON list"),
        ({"version": 2, "tasks": [1]}, "task entry #1 must be a JSON object"),
        ({"version": 2, "tasks": [{"id": 1}]}, "task entry #1 is missing field"),
        ({"version": 2, "tasks": [v2_entry(extra=1)]}, "unknown field"),
        ({"version": 2, "tasks": [v2_entry(id="1")]}, "'id' must be an integer"),
        ({"version": 2, "tasks": [v2_entry(id=True)]}, "'id' must be an integer"),
        ({"version": 2, "tasks": [v2_entry(title=5)]}, "'title' must be a string"),
        ({"version": 2, "tasks": [v2_entry(title=" ")]}, "title must not be empty"),
        ({"version": 2, "tasks": [v2_entry(priority="urgent")]}, "'priority' must be one of"),
        ({"version": 2, "tasks": [v2_entry(done="yes")]}, "'done' must be true or false"),
        (
            {
                "version": 2,
                "tasks": [v2_entry(), v2_entry(id=2, done=True, completed_at="yesterday")],
            },
            "task entry #2: field 'completed_at' is not an ISO-8601 timestamp",
        ),
        (
            {"version": 2, "tasks": [v2_entry(done=True, completed_at=20261107)]},
            "'completed_at' must be a timestamp or null",
        ),
        (
            {"version": 2, "tasks": [v2_entry(done=True, completed_at="2026-11-07T14:05:00")]},
            "'completed_at' has no UTC offset",
        ),
        (
            {"version": 2, "tasks": [v2_entry(completed_at="2026-11-07T14:05:00+03:00")]},
            "not done but has a completion time",
        ),
        ({"version": 2, "tasks": [v2_entry(), v2_entry()]}, "duplicate task id 1"),
        (
            [{"id": 1, "title": "a", "priority": "normal", "done": False, "completed_at": None}],
            "unknown field",
        ),
        ([{"id": 1, "title": "a", "priority": "normal"}], "missing field(s) done"),
    ],
)
def test_malformed_files_raise(tmp_path, data, message):
    path = tmp_path / "t.json"
    write_json(path, data)
    with pytest.raises(storage.StorageError) as info:
        storage.load(path)
    assert message in str(info.value)
    assert str(path) in str(info.value)
