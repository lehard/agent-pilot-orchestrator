# Spec Delta

## Purpose

Defines the on-disk task file: its versioned format, how files written by earlier
releases keep working, and how damaged or unknown files are reported.

## ADDED Requirements

### Requirement: Task file carries a format version
The system SHALL write the task file as a JSON object with an integer `version`
field and a `tasks` list. Each task entry SHALL hold `id`, `title`, `priority`,
`done` and `completed_at` (an ISO-8601 timestamp with UTC offset, or `null`).

#### Scenario: Saving writes the versioned format
- **WHEN** any command that changes tasks saves the file
- **THEN** the file is a JSON object with `"version": 2` and a `tasks` list

### Requirement: Files from the earlier release open without user action
A task file that is a bare JSON list of tasks (the format written before this
change, treated as version 1) SHALL open and work with every command. Its done
tasks get `completed_at: null`; its pending tasks are unchanged.

#### Scenario: Listing tasks from a version 1 file
- **GIVEN** a task file written by the earlier release
- **WHEN** the user runs `taskbook list --all`
- **THEN** all its tasks are listed as before and the exit code is 0

### Requirement: Upgrading a version 1 file keeps a copy of the original
The first time a version 1 file is saved in the new format, the system SHALL first
copy the original file next to it as `<file>.v1.bak`, and SHALL fail without
writing if that backup path already exists.

#### Scenario: First write after upgrade
- **GIVEN** a version 1 file `tasks.json`
- **WHEN** the user runs `taskbook add "x"`
- **THEN** `tasks.json.v1.bak` holds the original content and `tasks.json` is in version 2 format

#### Scenario: Backup already exists
- **GIVEN** a version 1 file `tasks.json` and an existing `tasks.json.v1.bak`
- **WHEN** the user runs `taskbook add "x"`
- **THEN** the command fails with an error naming `tasks.json.v1.bak`, and neither file is changed

### Requirement: Read-only commands do not rewrite the task file
`taskbook list` and `taskbook history` SHALL NOT write the task file, so reading
a version 1 file does not upgrade it.

#### Scenario: Listing a version 1 file
- **GIVEN** a version 1 file
- **WHEN** the user runs `taskbook list`
- **THEN** the file content is byte-for-byte unchanged

### Requirement: Damaged or unknown task files fail explicitly
Every command SHALL stop with exit code 1 and an error naming the file and the
problem when the task file is not valid JSON, has an unsupported `version`, or
has a task entry with a missing, unknown or wrongly typed field or an invalid
`completed_at`. It SHALL NOT treat such a file as an empty task list.

#### Scenario: Invalid JSON
- **GIVEN** a task file containing `{"version": 2, "tasks": [`
- **WHEN** the user runs `taskbook history`
- **THEN** the command exits with code 1 and the error says the file is not valid JSON

#### Scenario: Unsupported version
- **GIVEN** a task file with `"version": 3`
- **WHEN** the user runs `taskbook list`
- **THEN** the command exits with code 1 and the error names version 3 and the supported versions

#### Scenario: Malformed task entry
- **GIVEN** a version 2 file whose second task has `"completed_at": "yesterday"`
- **WHEN** the user runs `taskbook history`
- **THEN** the command exits with code 1 and the error names the file, the task entry and the field `completed_at`

#### Scenario: Done flag and completion time disagree
- **GIVEN** a version 2 file with a task where `done` is `false` and `completed_at` is set
- **WHEN** the user runs `taskbook list`
- **THEN** the command exits with code 1 and the error names that task entry

### Requirement: A missing task file means a new empty task list
When the file named by `TASKBOOK_FILE` does not exist, the system SHALL treat it
as an empty task list and create it in version 2 format on the first write.

#### Scenario: First use
- **GIVEN** `TASKBOOK_FILE` points to a path that does not exist
- **WHEN** the user runs `taskbook history`
- **THEN** the output is `no completed tasks`, the exit code is 0, and no file is created
