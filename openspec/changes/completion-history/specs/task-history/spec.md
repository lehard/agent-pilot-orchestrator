# Spec Delta

## Purpose

Lets users see which tasks they completed and when, for all time or since a
chosen date, by recording the moment each task is marked done.

## ADDED Requirements

### Requirement: Completion time is recorded
When a pending task is marked done, the system SHALL store the date and time of
completion with the task, and keep it unchanged by later edits of title or priority.

#### Scenario: Marking a task done stores the completion time
- **WHEN** the user runs `taskbook done 3` for pending task 3 at 2026-11-07 14:05 local time
- **THEN** task 3 is stored as done with completion time 2026-11-07 14:05 (with its UTC offset)

#### Scenario: Editing a completed task keeps its completion time
- **GIVEN** task 3 was completed at 2026-11-07 14:05
- **WHEN** the user runs `taskbook edit 3 --title "new title"`
- **THEN** task 3 still has completion time 2026-11-07 14:05

### Requirement: Completing an already completed task is an error
The system SHALL refuse to mark done a task that is already done, so the recorded
completion time is never silently overwritten.

#### Scenario: Second done on the same task
- **GIVEN** task 3 is already done
- **WHEN** the user runs `taskbook done 3`
- **THEN** the command prints `error: task 3 is already done` to stderr, exits with code 1, and the completion time is unchanged

### Requirement: History lists completed tasks newest first
`taskbook history` SHALL print every completed task with a known completion time,
one per line as `YYYY-MM-DD HH:MM  <id>. <title> (<priority>)` in local time,
ordered by completion time from newest to oldest, and exit with code 0.

#### Scenario: History without options
- **GIVEN** task 1 completed 2026-11-01 09:00 and task 2 completed 2026-11-05 18:30
- **WHEN** the user runs `taskbook history`
- **THEN** the output lists task 2 first and task 1 second, each with its date and time

#### Scenario: Pending tasks are not listed
- **GIVEN** task 4 is pending
- **WHEN** the user runs `taskbook history`
- **THEN** task 4 does not appear in the output

#### Scenario: No completed tasks
- **WHEN** the user runs `taskbook history` and no task is completed
- **THEN** the output is the line `no completed tasks` and the exit code is 0

### Requirement: History can be limited by a start date
`taskbook history --since YYYY-MM-DD` SHALL list only tasks completed on or after
the start of that day in local time. A value that is not a valid date in that
form SHALL be rejected with a usage error naming the expected format.

#### Scenario: Filtering by date
- **GIVEN** task 1 completed 2026-11-01 09:00 and task 2 completed 2026-11-05 18:30
- **WHEN** the user runs `taskbook history --since 2026-11-05`
- **THEN** only task 2 is listed

#### Scenario: Invalid date
- **WHEN** the user runs `taskbook history --since 05.11.2026`
- **THEN** the command exits with code 2 and an error saying the date must be YYYY-MM-DD

### Requirement: Tasks completed before this feature are shown without a date
Tasks that were already done in a file written by an earlier release have no
known completion time. `taskbook history` without `--since` SHALL list them after
all dated tasks with `date unknown` in place of the date; with `--since` they
SHALL NOT be listed, because they cannot be compared with the date.

#### Scenario: Legacy completed task without --since
- **GIVEN** a file from the earlier release where task 5 is done
- **WHEN** the user runs `taskbook history`
- **THEN** task 5 is listed after every dated task as `date unknown      5. <title> (<priority>)`

#### Scenario: Legacy completed task with --since
- **GIVEN** a file from the earlier release where task 5 is done
- **WHEN** the user runs `taskbook history --since 2026-01-01`
- **THEN** task 5 is not listed
