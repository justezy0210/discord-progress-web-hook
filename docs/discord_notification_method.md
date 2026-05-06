# Discord Notification Method

Use this method whenever a long-running command should report completion to
Discord without requiring manual polling.

## Standard Command

```bash
./notify_run.sh "Job name" -- command arg1 arg2
```

For background execution:

```bash
nohup ./notify_run.sh --log run.log "Job name" -- command arg1 arg2 > run.log 2>&1 &
```

For shell features such as pipes, redirects, or `&&`:

```bash
./notify_run.sh "Pipeline name" -- bash -lc 'step1 && step2 && step3'
```

## Required Configuration

The webhook URL must be available as `DISCORD_WEBHOOK_URL`.

Preferred local setup:

```bash
cp .env.example .env
vim .env
```

`.env`:

```bash
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

Do not expose the real webhook URL in chat, committed files, or logs.

## Behavior

- Sends SUCCESS when the wrapped command exits with code 0.
- Sends FAILED when the wrapped command exits with any non-zero code.
- Includes exit code, duration, host, working directory, UTC start/end times,
  command, and optional log path.
- Returns the original command exit code.
- Notification failure does not replace the original command exit code.

## Files to Reuse

- `notify_run.sh` is the main wrapper for users and future sessions.
- `discord_notify.py` can be called directly from shell or Python workflows.
- `.env.example` documents the required local secret.

## Example Sequence Analysis Jobs

```bash
nohup ./notify_run.sh --log blast.log "BLASTP all-vs-all" -- \
  blastp -query proteins.fa -db proteins.fa -out all.blast \
  > blast.log 2>&1 &
```

```bash
nohup ./notify_run.sh --log mcscanx.log "MCScanX run" -- \
  bash -lc 'MCScanX all' \
  > mcscanx.log 2>&1 &
```
