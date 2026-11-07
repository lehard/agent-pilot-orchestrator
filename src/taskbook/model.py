"""Task model and in-memory operations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

VALID_PRIORITIES = ("low", "normal", "high")


class TaskError(ValueError):
    """Raised when a task operation receives invalid input."""


def local_now() -> datetime:
    """Current local time with its UTC offset, truncated to seconds."""
    return datetime.now().astimezone().replace(microsecond=0)


@dataclass
class Task:
    id: int
    title: str
    priority: str = "normal"
    done: bool = False
    completed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise TaskError("task title must not be empty")
        if self.priority not in VALID_PRIORITIES:
            raise TaskError(
                f"unknown priority {self.priority!r}; expected one of {', '.join(VALID_PRIORITIES)}"
            )
        if self.completed_at is not None:
            if not self.done:
                raise TaskError(f"task {self.id} is not done but has a completion time")
            if self.completed_at.tzinfo is None:
                raise TaskError(f"task {self.id} completion time has no UTC offset")


@dataclass
class TaskList:
    tasks: list[Task] = field(default_factory=list)
    clock: Callable[[], datetime] = field(default=local_now, repr=False, compare=False)

    def add(self, title: str, priority: str = "normal") -> Task:
        next_id = max((t.id for t in self.tasks), default=0) + 1
        task = Task(id=next_id, title=title, priority=priority)
        self.tasks.append(task)
        return task

    def get(self, task_id: int) -> Task:
        for task in self.tasks:
            if task.id == task_id:
                return task
        raise TaskError(f"no task with id {task_id}")

    def complete(self, task_id: int) -> Task:
        """Mark a pending task done and record when; a done task is an error."""
        task = self.get(task_id)
        if task.done:
            raise TaskError(f"task {task_id} is already done")
        completed_at = self.clock()
        if completed_at.tzinfo is None:
            raise TaskError("clock returned a time without a UTC offset")
        task.done = True
        task.completed_at = completed_at
        return task

    def edit(self, task_id: int, title: str | None = None, priority: str | None = None) -> Task:
        """Change the title and/or priority of a task, keeping its id, status and completion."""
        task = self.get(task_id)
        edited = Task(
            id=task.id,
            title=task.title if title is None else title,
            priority=task.priority if priority is None else priority,
            done=task.done,
            completed_at=task.completed_at,
        )
        self.tasks[self.tasks.index(task)] = edited
        return edited

    def remove(self, task_id: int) -> Task:
        task = self.get(task_id)
        self.tasks.remove(task)
        return task

    def pending(self) -> list[Task]:
        return [t for t in self.tasks if not t.done]

    def history(self, since: datetime | None = None) -> list[Task]:
        """Completed tasks, newest first.

        Tasks completed without a recorded time (from files written before completion
        times existed) come last; they are left out when ``since`` is given, because
        they cannot be compared with it.
        """
        dated = [t for t in self.tasks if t.done and t.completed_at is not None]
        if since is not None:
            if since.tzinfo is None:
                raise TaskError("history start time has no UTC offset")
            dated = [t for t in dated if t.completed_at >= since]
        dated.sort(key=lambda t: t.completed_at, reverse=True)
        if since is not None:
            return dated
        undated = [t for t in self.tasks if t.done and t.completed_at is None]
        return dated + undated
