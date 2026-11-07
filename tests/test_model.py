from datetime import datetime, timedelta, timezone

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


# --- completion times and history -------------------------------------------------

MSK = timezone(timedelta(hours=3))
NYC = timezone(timedelta(hours=-5))


def clock_at(*moments):
    times = iter(moments)
    return lambda: next(times)


def test_complete_records_clock_time():
    moment = datetime(2026, 11, 7, 14, 5, tzinfo=MSK)
    tl = TaskList(clock=clock_at(moment))
    tl.add("a")
    assert tl.complete(1).completed_at == moment
    assert tl.get(1).done is True


def test_complete_twice_is_error_and_keeps_time():
    moment = datetime(2026, 11, 7, 14, 5, tzinfo=MSK)
    tl = TaskList(clock=clock_at(moment, moment + timedelta(days=1)))
    tl.add("a")
    tl.complete(1)
    with pytest.raises(TaskError, match="task 1 is already done"):
        tl.complete(1)
    assert tl.get(1).completed_at == moment


def test_complete_rejects_naive_clock():
    tl = TaskList(clock=clock_at(datetime(2026, 11, 7, 14, 5)))
    tl.add("a")
    with pytest.raises(TaskError, match="UTC offset"):
        tl.complete(1)
    assert tl.get(1).done is False


def test_edit_keeps_completion_time():
    moment = datetime(2026, 11, 7, 14, 5, tzinfo=MSK)
    tl = TaskList(clock=clock_at(moment))
    tl.add("a")
    tl.complete(1)
    assert tl.edit(1, title="b", priority="high").completed_at == moment


def test_pending_task_with_completion_time_rejected():
    with pytest.raises(TaskError, match="not done but has a completion time"):
        Task(id=1, title="x", completed_at=datetime(2026, 1, 1, tzinfo=MSK))


def test_history_newest_first_across_offsets_with_undated_last():
    early = datetime(2026, 11, 1, 9, 0, tzinfo=MSK)  # 06:00 UTC
    late = datetime(2026, 11, 1, 2, 0, tzinfo=NYC)  # 07:00 UTC
    tl = TaskList(
        tasks=[
            Task(id=1, title="legacy", done=True),
            Task(id=2, title="early", done=True, completed_at=early),
            Task(id=3, title="pending"),
            Task(id=4, title="late", done=True, completed_at=late),
        ]
    )
    assert [t.id for t in tl.history()] == [4, 2, 1]


def test_history_since_filters_and_drops_undated():
    tl = TaskList(
        tasks=[
            Task(id=1, title="legacy", done=True),
            Task(id=2, title="old", done=True, completed_at=datetime(2026, 11, 1, tzinfo=MSK)),
            Task(id=3, title="new", done=True, completed_at=datetime(2026, 11, 5, tzinfo=MSK)),
        ]
    )
    since = datetime(2026, 11, 5, tzinfo=MSK)
    assert [t.id for t in tl.history(since)] == [3]
    assert tl.history(datetime(2026, 12, 1, tzinfo=MSK)) == []


def test_history_rejects_naive_since():
    with pytest.raises(TaskError, match="UTC offset"):
        TaskList().history(datetime(2026, 11, 5))
