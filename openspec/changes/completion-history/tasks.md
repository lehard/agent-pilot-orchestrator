# Tasks

## 1. Model: completion time

- [x] 1.1 Add `completed_at` (aware datetime or None) to `Task`, validated against `done`; verify with model tests
- [x] 1.2 `TaskList.complete` stores the current local time with offset from an injectable clock and raises `TaskError` for an already done task; verify with model tests
- [x] 1.3 `TaskList.edit` keeps `completed_at`; add `TaskList.history(since)` ordering newest first with undated tasks last and excluded when `since` is given; verify with model tests

## 2. Storage: versioned format and migration

- [x] 2.1 `load` reads version 1 (bare list) and version 2 (`{"version": 2, "tasks": [...]}`) with strict per-entry validation raising `StorageError` naming file, entry and field; verify with storage tests for each malformed case
- [x] 2.2 `save` writes version 2 atomically (temp file + `os.replace`) and, when the file on disk is version 1, first copies it to `<file>.v1.bak`, refusing if the backup exists; verify with storage tests

## 3. CLI

- [x] 3.1 Add `taskbook history [--since YYYY-MM-DD]` with the spec output format and `no completed tasks`; verify with CLI tests with and without `--since` and for an invalid date
- [x] 3.2 Save only after `add`, `done`, `edit`, `rm`; print `StorageError` as `error: ...` with exit 1; verify with CLI tests (v1 file unchanged by `list`, damaged file errors)
- [x] 3.3 Document `history`, the second-`done` error and the file format upgrade/backup in README; verify the documented commands run as written
