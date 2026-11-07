"""Command-line interface: taskbook add|list|done|edit|rm|history."""

from __future__ import annotations

import argparse
import os
import re
import sys
from datetime import date, datetime, time
from pathlib import Path

from taskbook import storage
from taskbook.model import VALID_PRIORITIES, TaskError

WRITING_COMMANDS = ("add", "done", "edit", "rm")
_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _db_path() -> Path:
    value = os.environ.get("TASKBOOK_FILE")
    if not value:
        raise SystemExit("TASKBOOK_FILE is not set: point it at the JSON file to store tasks in")
    return Path(value)


def parse_day(value: str) -> date:
    """argparse type for --since: a calendar date written as YYYY-MM-DD."""
    if not _DATE_RE.fullmatch(value):
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD, got {value!r}")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"date must be YYYY-MM-DD, got {value!r}") from exc


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="taskbook")
    sub = parser.add_subparsers(dest="command", required=True)
    add = sub.add_parser("add", help="add a task")
    add.add_argument("title")
    add.add_argument("--priority", choices=VALID_PRIORITIES, default="normal")
    lst = sub.add_parser("list", help="list tasks")
    lst.add_argument("--all", action="store_true", help="include completed tasks")
    done = sub.add_parser("done", help="mark a task completed")
    done.add_argument("id", type=int)
    edit = sub.add_parser("edit", help="change the title or priority of a task")
    edit.add_argument("id", type=int)
    edit.add_argument("--title")
    edit.add_argument("--priority", choices=VALID_PRIORITIES)
    rm = sub.add_parser("rm", help="remove a task")
    rm.add_argument("id", type=int)
    history = sub.add_parser("history", help="list completed tasks with dates, newest first")
    history.add_argument(
        "--since",
        type=parse_day,
        metavar="YYYY-MM-DD",
        help="only tasks completed on or after this day (local time)",
    )
    return parser


def format_task(task) -> str:
    mark = "x" if task.done else " "
    return f"[{mark}] {task.id}. {task.title} ({task.priority})"


def format_history_entry(task) -> str:
    if task.completed_at is None:
        when = "date unknown"
    else:
        when = task.completed_at.astimezone().strftime("%Y-%m-%d %H:%M")
    return f"{when:<16}  {task.id}. {task.title} ({task.priority})"


def _run(args: argparse.Namespace, path: Path) -> None:
    tasks = storage.load(path)
    if args.command == "add":
        task = tasks.add(args.title, args.priority)
        print(f"added {task.id}")
    elif args.command == "list":
        shown = tasks.tasks if args.all else tasks.pending()
        for task in shown:
            print(format_task(task))
        print(f"{len(tasks.pending())} pending")
    elif args.command == "done":
        print(f"completed {tasks.complete(args.id).id}")
    elif args.command == "edit":
        if args.title is None and args.priority is None:
            raise TaskError("nothing to edit: pass --title and/or --priority")
        print(f"edited {tasks.edit(args.id, args.title, args.priority).id}")
    elif args.command == "rm":
        print(f"removed {tasks.remove(args.id).id}")
    elif args.command == "history":
        since = None
        if args.since is not None:
            since = datetime.combine(args.since, time()).astimezone()
        entries = tasks.history(since)
        if not entries:
            print("no completed tasks")
        for task in entries:
            print(format_history_entry(task))
    if args.command in WRITING_COMMANDS:
        storage.save(tasks, path)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    path = _db_path()
    try:
        _run(args, path)
    except (TaskError, storage.StorageError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
