# taskbook

Tiny command-line task tracker, used as a fixture for an autonomous-agent pilot.

    pip install -e . && export TASKBOOK_FILE=~/tasks.json
    taskbook add "buy milk" --priority high && taskbook list --all

## Editing a task

    taskbook edit <id> [--title TEXT] [--priority low|normal|high]

Changes the title and/or priority of a task; its id and done status stay the same.
Pass at least one of `--title` and `--priority`, otherwise the command fails.
An unknown id or an empty title is an error with exit code 1, as for `done` and `add`.

Development: `ruff check . && python -m pytest -q`.
Larger changes go through OpenSpec (schema `add-gated`, OpenSpec CLI pinned to 1.16.0):
proposal → specs → design → `add.md` (Architecture Decision Doc) → tasks.
CI job `test` refuses tasks or implementation of a change whose `add.md` lacks the
owner's line `Approved-by: lehard`. Small edits without an OpenSpec change need no ADD.
