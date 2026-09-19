# Workspace Instructions

## Project

This workspace contains `cariad_tj_mirror.py`, a Python 3 command-line utility that mirrors CARIAD Jira TestJobs into an internal Jira instance.

## Development

- Keep the script compatible with Python 3 and use the standard library plus the existing `requests` dependency.
- Preserve dry-run behavior: writes to the internal Jira must require `--apply`.
- Treat the CARIAD Jira client as read-only; do not add write calls through that client.
- Read credentials and deployment configuration from environment variables. Never hard-code secrets.
- Preserve the existing Jira API, authentication, pagination, status mapping, and logging behavior unless a task explicitly changes it.
- Keep edits focused and avoid adding dependencies without a clear need.

## Validation

- Run `python -m py_compile cariad_tj_mirror.py` after Python changes.
- When changing Jira behavior, prefer a focused test or mocked request check; do not perform live Jira writes during validation.
