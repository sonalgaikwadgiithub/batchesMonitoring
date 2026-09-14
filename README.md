# Batch Status Monitor

Queries Oracle for batch status, flags any row that reports a failure, and emails
the result to stakeholders. Designed to run unattended on a weekly schedule
(Monday 10:00 IST).

## What it does

1. Connects to Oracle with `oracledb` (thin mode, no Oracle Client install needed).
2. Runs the SQL in `sql/batch_status.sql`.
3. Marks a row as failed when its status column contains a failure word
   (`FAILED`, `ERROR`, `ABORTED`, ...).
4. Emails an HTML report. Failures are highlighted and listed first.
5. Exits `0` when healthy, `1` when failures were found, `2` when the job itself
   broke (bad config, DB unreachable, mail rejected).

## Setup

```powershell
cd D:\work_dsi\1.Work\cursor\batchstatusautomation
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Then edit `.env` with your real Oracle DSN, credentials, and SMTP host, and
replace the placeholder query in `sql/batch_status.sql` with the real batch
status table or view.

`.env` is git-ignored on purpose. Never commit credentials.

## Run it

```powershell
.\run_check.ps1 -DryRun   # query + print the report, sends nothing
.\run_check.ps1           # query + send the email
```

Always use `-DryRun` first after changing the SQL, so you can confirm the rows
and the failure classification before stakeholders receive anything.

## Configuration reference

| Setting | Purpose |
|---|---|
| `ORACLE_USER` / `ORACLE_PASSWORD` | Read-only DB account |
| `ORACLE_DSN` | `host:port/service_name` or a `tnsnames.ora` alias |
| `BATCH_SQL_FILE` | Path to the `.sql` file to run (wins over `BATCH_SQL`) |
| `BATCH_SQL` | Inline SQL, used only when `BATCH_SQL_FILE` is unset |
| `BATCH_STATUS_COLUMN` | Column to inspect. Leave empty to scan every column |
| `BATCH_FAILURE_VALUES` | Comma-separated words that mean "failed" |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_STARTTLS` | Mail relay |
| `SMTP_USERNAME` / `SMTP_PASSWORD` | Leave blank for an open internal relay |
| `MAIL_FROM` / `MAIL_TO` | Sender and comma-separated recipients |
| `SEND_WHEN_HEALTHY` | `false` to email only when something failed |
| `ENVIRONMENT_LABEL` | Appears in the subject, e.g. `PROD` |
| `MAX_ROWS_IN_EMAIL` | Caps the table size in the email |

## Schedule it: Windows Task Scheduler

Runs on your machine, which already has Oracle and SMTP reachability.

```powershell
$action  = New-ScheduledTaskAction -Execute "powershell.exe" `
  -Argument "-NoProfile -ExecutionPolicy Bypass -File `"D:\work_dsi\1.Work\cursor\batchstatusautomation\run_check.ps1`"" `
  -WorkingDirectory "D:\work_dsi\1.Work\cursor\batchstatusautomation"

$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 10:00

Register-ScheduledTask -TaskName "BatchStatusMonitor" -Action $action `
  -Trigger $trigger -Description "Weekly Oracle batch status report" -RunLevel Limited
```

The trigger uses the machine's local time, so 10:00 IST needs the machine set to
IST. Tick "Run whether user is logged on or not" in the Task Scheduler UI if the
report must arrive when you are away.

Verify without waiting a week:

```powershell
Start-ScheduledTask -TaskName "BatchStatusMonitor"
Get-ScheduledTaskInfo -TaskName "BatchStatusMonitor"
```

## Logs

`run_check.ps1` writes one log per day to `logs\batch_status_<date>.log`.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Missing required setting ...` | `.env` absent or incomplete |
| `DPY-6005` / `DPY-4011` | DSN wrong, or no network route / VPN to the DB |
| `ORA-01017` | Bad Oracle username or password |
| `ORA-00933` | Trailing semicolon or multiple statements in the SQL file |
| `BATCH_STATUS_COLUMN ... not in the result columns` | Column name differs from the query's alias (names are upper-cased) |
| Mail never arrives | Relay rejected the sender; check the log and confirm `MAIL_FROM` is allowed |
| Exit code 1 | Working as designed: failures were found and reported |
