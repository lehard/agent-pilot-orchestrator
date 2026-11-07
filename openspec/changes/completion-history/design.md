# Design

## Context

See proposal.md - Why. Current state:

- `storage.load` reads `TASKBOOK_FILE` as a bare JSON list of
  `{id, title, priority, done}`; `storage.save` overwrites it in place with
  `path.write_text` (not atomic).
- `cli.main` calls `storage.save` after every command, including `list`.
- `load` builds tasks with `Task(**item)`: an entry with a missing or extra key
  raises a raw `TypeError` instead of `StorageError`, and field types are not checked.
- No undo command exists; `rm` deletes a task entirely.
- Only the standard library is used; Python >= 3.12 (see pyproject.toml).

The storage option itself (versioned JSON vs SQLite vs separate journal) is the
decision recorded in add.md. This design describes the recommended option
(versioned JSON) in enough detail to estimate and review it.

## Goals / Non-Goals

**Goals:**
- Store a completion timestamp per task and show history with `--since`.
- Open every file the current release writes, without user action.
- Turn every malformed file into an explicit `StorageError`.

**Non-Goals:**
- An undo/reopen command, or keeping history of tasks removed with `rm`.
- Downgrade support: an older release does not read version 2 files.
- Guessing completion times for tasks completed before the upgrade.
- Concurrent writers (two `taskbook` processes at once).

## Decisions

### File format: JSON object with `version`
`{"version": 2, "tasks": [{"id", "title", "priority", "done", "completed_at"}]}`.
A top-level list is version 1 by definition (that is all the current release
writes); a top-level object must carry an integer `version` in the supported set
`{2}`. Anything else is a `StorageError`. Alternatives (SQLite, journal file) are
compared in add.md.

### Migration: in memory on read, persisted on next write, with a backup
Version 1 entries are validated
with the version 1 field set and get `completed_at = None`. `save` writes version 2;
if the file currently on disk is version 1 it first copies the original to `<file>.v1.bak`
(refusing if that exists). Rejected alternative: rewrite the file during `load` -
a read would then mutate data and make `list` unsafe on a file the user wants to
keep for an older release.

### Atomic write
`save` writes to a temporary file in the same directory and `os.replace`s it onto
the target, so an interrupted write cannot leave a half-written file that the next
run would reject.

### Strict validation
Per entry, keys must equal the expected set for the version; `id` int (not bool),
`title` non-empty str, `priority` in `VALID_PRIORITIES`, `done` bool,
`completed_at` null or an ISO-8601 string with UTC offset (`datetime.fromisoformat`
and `tzinfo is not None`); `done` false requires `completed_at` null; ids are unique.
Each failure raises `StorageError` naming file, entry index and field. The CLI
catches `StorageError`, prints `error: ...` and exits 1.

### Timestamps
`complete` stores `datetime.now().astimezone()` truncated to seconds (local time
with its offset). Sorting uses the aware datetime, so entries written in different
time zones order correctly. Display converts to the current local time zone,
`YYYY-MM-DD HH:MM`. `--since` is parsed with `date.fromisoformat` restricted to the
`YYYY-MM-DD` form in argparse (usage error, exit 2) and compared as
local midnight of that day. A clock source is injectable in the model for tests.

### Read-only commands
`cli.main` saves only after `add`, `done`, `edit`, `rm`.

### Already done
`TaskList.complete` raises `TaskError("task N is already done")` for a done task.

## Risks / Trade-offs

- [Older release cannot read a migrated file] → `<file>.v1.bak` keeps the original;
  README documents it. The old release fails loudly ("must contain a JSON list"),
  it does not lose data.
- [Legacy done tasks have no date] → shown as `date unknown` without `--since`,
  never invented.
- [`rm` loses history of a completed task] → accepted, out of scope; option C in
  add.md would keep it.
- [Stricter validation rejects hand-edited files the current release accepted, e.g.
  `"done": "yes"`] → the error names the entry and field so the user can fix it.
- [Second `done` now fails] → behavior change listed in proposal.md and README.

## Migration Plan

No user step. First write after the upgrade creates `<file>.v1.bak` and rewrites
the file as version 2. Rollback: restore `<file>.v1.bak` over the file and install
the previous release; every change made after the upgrade is lost in that restore.
