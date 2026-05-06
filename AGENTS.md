# Agent Notes

For long-running sequence analysis commands in this workspace, use the Discord
notification wrapper so the user does not need to poll manually.

Standard pattern:

```bash
./notify_run.sh "Job name" -- command arg1 arg2
```

Background pattern:

```bash
nohup ./notify_run.sh --log run.log "Job name" -- command arg1 arg2 > run.log 2>&1 &
```

Use `bash -lc` when the wrapped command needs shell features such as pipes,
redirection, semicolons, or `&&`.

The Discord webhook URL belongs in `.env` as `DISCORD_WEBHOOK_URL`. Do not paste
or expose the real webhook URL in chat, logs, committed files, or docs.

Detailed reference: `docs/discord_notification_method.md`.
