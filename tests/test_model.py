import pytest

from taskbook.model import Task, TaskError, TaskList


def test_add_assigns_increasing_ids():
    tl = TaskList()
    assert tl.add("a").id == 1
    assert tl.add("b").id == 2


def test_empty_title_rejected():
    with pytest.raises(TaskError, match="title"):
        TaskList().add("   ")


def test_unknown_priority_rejected():
    with pytest.raises(TaskError, match="priority"):
        Task(id=1, title="x", priority="urgent")


def test_complete_and_pending():
    tl = TaskList()
    tl.add("a")
    tl.add("b")
    tl.complete(1)
    assert [t.id for t in tl.pending()] == [2]


def test_remove_missing_raises():
    with pytest.raises(TaskError, match="no task with id 9"):
        TaskList().remove(9)


def test_edit_keeps_id_and_status():
    tl = TaskList()
    tl.add("a")
    tl.add("b")
    tl.complete(2)
    edited = tl.edit(2, title="c", priority="high")
    assert (edited.id, edited.title, edited.priority, edited.done) == (2, "c", "high", True)
    assert [t.id for t in tl.tasks] == [1, 2]
    assert tl.get(2) is edited


def test_edit_empty_title_leaves_task_unchanged():
    tl = TaskList()
    tl.add("a", "low")
    with pytest.raises(TaskError, match="title"):
        tl.edit(1, title="  ", priority="high")
    assert (tl.get(1).title, tl.get(1).priority) == ("a", "low")
