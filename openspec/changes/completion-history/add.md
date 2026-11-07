# ADD: Completion history with dates

## Context

`done` must record a completion time and `taskbook history [--since]` must list
completed tasks newest first (proposal.md). Decide where that time lives and how
existing task files (a bare JSON list, no version) keep opening. Constraints:
existing files must work with no user action; a damaged or unknown file must fail
explicitly, never read as empty; standard library only; one file named by
`TASKBOOK_FILE`; single user, no concurrent writers.

## Options

### Option A: Versioned JSON (extend the current file)

File becomes `{"version": 2, "tasks": [...]}`, each task gains `completed_at`.
A bare list is read as version 1, upgraded in memory, written as version 2 on the
next change after saving `<file>.v1.bak`. Atomic write via temp file + replace.
Cost: small (storage + validation + CLI, ~1 day). Later: whole-file rewrite per
change stays O(n); a further format change repeats the same versioned migration;
history of `rm`-ed tasks is not kept; an older release cannot read the new file.

### Option B: SQLite

`TASKBOOK_FILE` becomes an SQLite database (`sqlite3` from stdlib) with a `tasks`
table and `completed_at` column; a JSON file found there is imported once and
replaced. Cost: highest - rewrite of storage, content sniffing to tell JSON from
SQLite, schema-migration table, test fixtures. Later: file is no longer readable
or editable by hand; gains (queries, transactions, concurrency) are not needed by
a single-user list of tasks.

### Option C: Separate completion journal

Task file stays as is; `done` also appends `{id, title, priority, completed_at}`
as a line to `<file>.history.jsonl`; `history` reads only the journal. Cost: low,
old file untouched, older release still works. Later: two files written by one
command can diverge (crash between writes, user deletes or copies one); edits and
`rm` are not reflected (the journal keeps old titles, which is either a feature or
confusion); a second set of format/validation rules; "which file is the truth"
must be defined for every future feature.

## Decision

Option A. It keeps one human-readable file as the single source of truth, so
`done` and its timestamp are written in one atomic step and cannot drift, and it
introduces the format version the project lacks today, which every later format
change will need anyway. It costs far less than B, whose benefits this tool does
not need. C avoids migration but buys it with two files that must stay
consistent forever. Legacy done tasks get `completed_at: null` and are shown as
`date unknown` (not dated, not hidden); read-only commands stop writing the file;
a second `done` on a done task becomes an error.

## Risks

- Migration corrupts or loses data → backup `<file>.v1.bak` before the first v2
  write (refuse if it exists), atomic replace; tests round-trip real v1 files.
- User downgrades to an older release → it stops with its existing "must contain
  a JSON list" error, no silent data loss; README tells how to restore the backup.
- Stricter validation rejects hand-edited files the old code tolerated → error
  names file, entry and field; covered by tests per field.
- Time-zone shifts mis-order or mis-filter entries → timestamps stored with UTC
  offset, compared as aware datetimes; tests use fixed clocks in two offsets.
- `rm` drops a completed task from history → accepted; revisit with option C's
  journal only if the owner wants history to survive deletion.

## Approval

Approved-by:
