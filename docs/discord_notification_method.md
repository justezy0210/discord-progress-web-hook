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

This sends exactly one completion message for the wrapped command or pipeline.
The message status is derived from the final exit code.

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
The local `.env` file is ignored by `.gitignore` and should stay untracked.

## Validation

After creating `.env`, send a direct test message:

```bash
python3 discord_notify.py \
  --job "direct webhook test" \
  --status info \
  --message "Discord webhook is configured"
```

Then test the wrapper:

```bash
./notify_run.sh "wrapper test" -- bash -lc 'echo wrapper test completed'
```

To inspect the payload without sending a Discord message:

```bash
python3 discord_notify.py --dry-run --job "payload check" --exit-code 0 --seconds 60
```

## Behavior

- Sends SUCCESS when the wrapped command exits with code 0.
- Sends FAILED when the wrapped command exits with any non-zero code.
- Includes exit code, duration, host, working directory, UTC start/end times,
  command, and optional log path.
- Returns the original command exit code.
- Notification failure does not replace the original command exit code.
- The webhook request sets a simple User-Agent because Discord or network
  filters may reject default Python urllib requests.

## Recommended User Pattern

For a single long-running command:

```bash
nohup ./notify_run.sh --log run.log "Job name" -- command arg1 arg2 > run.log 2>&1 &
```

For a multi-step sequence analysis pipeline:

```bash
nohup ./notify_run.sh --log pipeline.log "Sequence pipeline" -- bash -lc '
  makeblastdb -in proteins.fa -dbtype prot &&
  blastp -query proteins.fa -db proteins.fa -out all.blast &&
  MCScanX all
' > pipeline.log 2>&1 &
```

## Files to Reuse

- `notify_run.sh` is the main wrapper for users and future sessions.
- `discord_notify.py` can be called directly from shell or Python workflows.
- `.env.example` documents the required local secret.

## Troubleshooting

- `DISCORD_WEBHOOK_URL is not set`: create `.env` or export the variable.
- `Temporary failure in name resolution`: the runtime environment cannot reach
  Discord.
- HTTP 401 or 404: the webhook URL is invalid, deleted, or copied incorrectly.
- HTTP 403: Discord or a network layer blocked the request.

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
