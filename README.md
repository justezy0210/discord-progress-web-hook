# Discord Pipeline Notifications

Reusable Discord webhook notifications for long-running sequence analysis jobs.

The intended pattern is:

```bash
./notify_run.sh "Job name" -- long_running_command arg1 arg2
```

When the command finishes, Discord receives a SUCCESS or FAILED message with the
exit code, runtime, host, working directory, and command. The wrapper exits with
the original command exit code, so it can be used inside larger scripts.

## Setup

Create `.env` from the example and put the Discord webhook URL there:

```bash
cp .env.example .env
vim .env
```

The file should contain:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Do not paste the real webhook URL into prompts, logs, shared docs, or committed
files. Treat it like a password.

## Quick Test

```bash
./notify_run.sh "test sleep" -- bash -lc 'sleep 3; echo done'
```

Expected behavior:

- terminal prints `done`
- Discord receives a SUCCESS notification
- the wrapper exits with code 0

Failure test:

```bash
./notify_run.sh "test failure" -- bash -lc 'sleep 3; exit 7'
echo $?
```

Expected behavior:

- Discord receives a FAILED notification
- `echo $?` prints `7`

## Background Jobs

Use `nohup` and redirect output to a log file:

```bash
nohup ./notify_run.sh --log blast.log "BLAST search" -- \
  blastp -query q.fa -db db -out result.tsv \
  > blast.log 2>&1 &
```

The Discord message will include `blast.log` as the log path. The script does
not upload log contents.

## Pipelines, Pipes, and Redirection

If the command uses pipes, redirects, semicolons, or `&&`, run it through
`bash -lc`:

```bash
./notify_run.sh "MCScanX pipeline" -- bash -lc '
  makeblastdb -in proteins.fa -dbtype prot &&
  blastp -query proteins.fa -db proteins.fa -out all.blast &&
  MCScanX all
'
```

This reports one notification for the whole pipeline. If you want notification
after each stage, wrap each stage separately.

## Direct Python Notification

Use `discord_notify.py` directly when another script already has the exit code
and runtime:

```bash
python3 discord_notify.py \
  --job "manual notification" \
  --exit-code 0 \
  --seconds 120 \
  --command "example command"
```

`discord_notify.py` reads `DISCORD_WEBHOOK_URL` from the environment first, then
from `.env` unless `--env-file` points to another file.

## Files

- `notify_run.sh`: runs a command, measures time, sends completion notification
- `discord_notify.py`: sends the Discord webhook payload
- `.env.example`: template for local webhook configuration
- `docs/discord_notification_method.md`: short method reference for future sessions
