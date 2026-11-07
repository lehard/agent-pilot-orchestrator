"""JSON file persistence for a TaskList.

Format version 2 (written): ``{"version": 2, "tasks": [{"id", "title", "priority",
"done", "completed_at"}]}`` where ``completed_at`` is an ISO-8601 timestamp with UTC
offset or null. Format version 1 (read only): a bare JSON list of ``{"id", "title",
"priority", "done"}``, as written by releases before completion times existed.
Saving over a version 1 file first copies it to ``<file>.v1.bak``.
"""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from taskbook.model import VALID_PRIORITIES, Task, TaskError, TaskList

CURRENT_VERSION = 2
_FIELDS = {
    1: ("id", "title", "priority", "done"),
    2: ("id", "title", "priority", "done", "completed_at"),
}


class StorageError(RuntimeError):
    """Raised when the task file cannot be read or has an invalid shape."""


def backup_path(path: Path) -> Path:
    return path.with_name(path.name + ".v1.bak")


def _read(path: Path) -> tuple[int, list]:
    """Parse the file and return its format version and raw task entries."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StorageError(f"task file {path} is not valid JSON: {exc}") from exc
    if isinstance(raw, list):
        return 1, raw
    if not isinstance(raw, dict):
        raise StorageError(f"task file {path} must contain a JSON object or a JSON list")
    if set(raw) != {"version", "tasks"}:
        raise StorageError(
            f"task file {path} must have exactly the keys 'version' and 'tasks', "
            f"found {sorted(raw)}"
        )
    version = raw["version"]
    if type(version) is not int or version != CURRENT_VERSION:
        raise StorageError(
            f"task file {path} has unsupported format version {version!r}; "
            f"supported versions: 1 (a bare JSON list) and {CURRENT_VERSION}"
        )
    if not isinstance(raw["tasks"], list):
        raise StorageError(f"task file {path}: 'tasks' must be a JSON list")
    return version, raw["tasks"]


def _parse_task(item: object, version: int, where: str) -> Task:
    if not isinstance(item, dict):
        raise StorageError(f"{where} must be a JSON object")
    expected = _FIELDS[version]
    missing = [k for k in expected if k not in item]
    unknown = sorted(k for k in item if k not in expected)
    if missing:
        raise StorageError(f"{where} is missing field(s) {', '.join(missing)}")
    if unknown:
        raise StorageError(f"{where} has unknown field(s) {', '.join(unknown)}")
    if type(item["id"]) is not int:
        raise StorageError(f"{where}: field 'id' must be an integer")
    if not isinstance(item["title"], str):
        raise StorageError(f"{where}: field 'title' must be a string")
    if item["priority"] not in VALID_PRIORITIES:
        raise StorageError(
            f"{where}: field 'priority' must be one of {', '.join(VALID_PRIORITIES)}"
        )
    if type(item["done"]) is not bool:
        raise StorageError(f"{where}: field 'done' must be true or false")
    completed_at = None
    if version >= 2 and item["completed_at"] is not None:
        value = item["completed_at"]
        if not isinstance(value, str):
            raise StorageError(f"{where}: field 'completed_at' must be a timestamp or null")
        try:
            completed_at = datetime.fromisoformat(value)
        except ValueError as exc:
            raise StorageError(
                f"{where}: field 'completed_at' is not an ISO-8601 timestamp: {value!r}"
            ) from exc
        if completed_at.tzinfo is None:
            raise StorageError(f"{where}: field 'completed_at' has no UTC offset: {value!r}")
    try:
        return Task(
            id=item["id"],
            title=item["title"],
            priority=item["priority"],
            done=item["done"],
            completed_at=completed_at,
        )
    except TaskError as exc:
        raise StorageError(f"{where}: {exc}") from exc


def load(path: Path) -> TaskList:
    """Read a task file; a file that does not exist is a new, empty task list."""
    if not path.exists():
        return TaskList()
    version, items = _read(path)
    tasks = []
    seen: set[int] = set()
    for index, item in enumerate(items):
        task = _parse_task(item, version, f"task file {path}: task entry #{index + 1}")
        if task.id in seen:
            raise StorageError(f"task file {path}: duplicate task id {task.id}")
        seen.add(task.id)
        tasks.append(task)
    return TaskList(tasks=tasks)


def _serialize(task: Task) -> dict:
    return {
        "id": task.id,
        "title": task.title,
        "priority": task.priority,
        "done": task.done,
        "completed_at": None if task.completed_at is None else task.completed_at.isoformat(),
    }


def _backup_v1(path: Path) -> None:
    backup = backup_path(path)
    try:
        with backup.open("xb") as out:
            out.write(path.read_bytes())
    except FileExistsError as exc:
        raise StorageError(
            f"cannot upgrade task file {path}: backup {backup} already exists; "
            "move it away and run the command again"
        ) from exc


def save(task_list: TaskList, path: Path) -> None:
    """Write the task list in the current format, atomically.

    A version 1 file being replaced is first copied to ``<file>.v1.bak``.
    """
    exists = path.exists()
    if exists and _read(path)[0] == 1:
        _backup_v1(path)
    if exists:
        mode = path.stat().st_mode & 0o777
    else:
        umask = os.umask(0)
        os.umask(umask)
        mode = 0o666 & ~umask
    data = {"version": CURRENT_VERSION, "tasks": [_serialize(t) for t in task_list.tasks]}
    text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    fd, tmp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            out.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
