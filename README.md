# CARIAD Jira TestJob Mirror

`cariad_tj_mirror.py` mirrors CARIAD Jira TestJobs into an internal Jira project. The CARIAD client is read-only. The internal Jira is dry-run by default; use `--apply` to create tickets and transition existing tickets.

## Requirements

- Python 3
- `requests` (`python -m pip install -r requirements.txt`)

## Configuration

Set these environment variables in the shell or CI secret store. Do not commit tokens or `.env` files.

| Variable | Purpose |
| --- | --- |
| `CARIAD_URL` | CARIAD Jira base URL |
| `CARIAD_TOKEN` | CARIAD token |
| `CARIAD_USER` | Optional username/email for basic authentication |
| `CARIAD_CLOUD` | Set to `1` for Jira Cloud pagination |
| `CARIAD_JQL` | JQL selecting the TestJobs to mirror |
| `INT_URL` | Internal Jira base URL |
| `INT_TOKEN` | Internal Jira token |
| `INT_USER` | Optional username/email for basic authentication |
| `INT_CLOUD` | Set to `1` for Jira Cloud pagination |
| `INT_PROJECT` | Destination project key |
| `INT_ISSUETYPE` | Destination issue type, default `Task` |

With a `*_USER` value, the script uses basic authentication. Without it, the token is sent as a bearer token.

## Usage

Run a dry run first:

```powershell
python .\cariad_tj_mirror.py
```

Apply changes to the internal Jira only after reviewing the dry-run output:

```powershell
python .\cariad_tj_mirror.py --apply
```

## Tests

The tests use mocked HTTP behavior and never contact Jira:

```powershell
python -m unittest discover -s tests -v
```
