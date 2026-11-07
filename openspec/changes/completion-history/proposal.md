# Proposal

## Why

Users want to see which tasks were completed and when, over a chosen period
(issue #3). Today `taskbook done` only flips a `done` flag; the completion time is
not stored anywhere, so the history cannot be shown. Adding it changes the task
file format, so the storage choice and the migration of existing files must be
agreed in an ADD before work starts.

## What Changes

- `taskbook done <id>` records the date and time of completion.
- **BREAKING (behavior)**: `taskbook done` on a task that is already done now fails
  with exit code 1 instead of silently succeeding, so a recorded completion time is
  never overwritten.
- New command `taskbook history [--since YYYY-MM-DD]`: lists completed tasks with
  their completion date and time, newest first; `--since` keeps only tasks
  completed on or after that date.
- The task file gets an explicit format version. Files written by the current
  release (a bare JSON list, no version) keep opening with no action from the user
  and are upgraded on the next write; a copy of the original is kept.
- A damaged or unrecognised task file (invalid JSON, unknown format version, task
  entries with missing or wrong fields) fails with an explicit error naming the
  file and the problem, never as an empty list.
- Read-only commands (`list`, `history`) stop rewriting the task file.

## Capabilities

### New Capabilities
- `task-history`: recording when a task is completed and listing completed tasks
  by completion time, optionally since a date.
- `task-storage`: the on-disk task file: format versioning, opening files written
  by earlier releases, and explicit errors for damaged or unknown files.

### Modified Capabilities

None: `openspec/specs/` has no capabilities yet.

## Impact

- Code: `src/taskbook/model.py` (completion time on a task), `src/taskbook/storage.py`
  (versioned format, migration, validation, backup), `src/taskbook/cli.py`
  (`history` command, no write on read-only commands).
- Data: task files are rewritten in the new format on the first write after
  upgrade. An older `taskbook` release cannot read the new format (it stops with
  its existing "must contain a JSON list" error).
- Docs: README gets a `history` section and a note on the file format upgrade.
- No new dependencies.
