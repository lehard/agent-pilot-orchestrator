# taskbook

Tiny command-line task tracker, used as a fixture for an autonomous-agent pilot.

    pip install -e . && export TASKBOOK_FILE=~/tasks.json
    taskbook add "buy milk" --priority high && taskbook list --all

## Editing a task

    taskbook edit <id> [--title TEXT] [--priority low|normal|high]

Changes the title and/or priority of a task; its id and done status stay the same.
Pass at least one of `--title` and `--priority`, otherwise the command fails.
An unknown id or an empty title is an error with exit code 1, as for `done` and `add`.

## Completion history

    taskbook history [--since YYYY-MM-DD]

`taskbook done <id>` records the date and time of completion; running it again on a
completed task is an error (exit code 1). `history` lists completed tasks newest
first as `YYYY-MM-DD HH:MM  <id>. <title> (<priority>)` in local time, or
`no completed tasks`. `--since` keeps tasks completed on or after that day.
Tasks completed before this release have no recorded time: they are listed last as
`date unknown` and are left out when `--since` is given.

## Task file format

The file is `{"version": 2, "tasks": [...]}`. Files written by earlier releases (a
bare JSON list) open as they are; `list` and `history` never write the file. The
first command that changes tasks copies the old file to `<file>.v1.bak` and rewrites
it in the new format; it refuses if that backup already exists. Earlier releases
cannot read the new format: to go back, restore `<file>.v1.bak` (changes made since
the upgrade are lost). A damaged file, an unknown version or a malformed task entry
is an error naming the file and the problem, never an empty list.

Development: `ruff check . && python -m pytest -q`.
Larger changes go through OpenSpec (schema `add-gated`, OpenSpec CLI pinned to 1.16.0):
proposal → specs → design → `add.md` (Architecture Decision Doc) → tasks.
CI job `test` refuses tasks or implementation of a change whose `add.md` lacks the
owner's line `Approved-by: lehard`. Small edits without an OpenSpec change need no ADD.
