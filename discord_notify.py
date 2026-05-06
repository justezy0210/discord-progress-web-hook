#!/usr/bin/env python3
"""Send a Discord webhook notification for a completed command."""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional


SUCCESS_COLOR = 0x2ECC71
FAILURE_COLOR = 0xE74C3C
INFO_COLOR = 0x3498DB


def load_env_file(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value

    return values


def truncate(value: object, limit: int) -> str:
    text = str(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 3)] + "..."


def redact_secrets(text: str) -> str:
    return re.sub(
        r"https://(?:canary\.|ptb\.)?discord(?:app)?\.com/api/webhooks/\S+",
        "[redacted-discord-webhook]",
        text,
    )


def format_duration(seconds: Optional[float]) -> str:
    if seconds is None:
        return "unknown"

    total = max(0, int(round(seconds)))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, secs = divmod(rem, 60)

    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def infer_status(exit_code: Optional[int], requested_status: str) -> str:
    if exit_code is None:
        return requested_status
    return "success" if exit_code == 0 else "failure"


def find_webhook_url(args: argparse.Namespace) -> Optional[str]:
    env_file_values = load_env_file(Path(args.env_file))
    return (
        args.webhook_url
        or os.environ.get("DISCORD_WEBHOOK_URL")
        or env_file_values.get("DISCORD_WEBHOOK_URL")
    )


def add_field(fields: list, name: str, value: Optional[object], inline: bool = False) -> None:
    if value is None:
        return
    fields.append(
        {
            "name": truncate(name, 256),
            "value": truncate(value, 1024) or "-",
            "inline": inline,
        }
    )


def build_payload(args: argparse.Namespace) -> Dict[str, object]:
    status = infer_status(args.exit_code, args.status)
    label = {
        "success": "SUCCESS",
        "failure": "FAILED",
        "info": "INFO",
    }[status]
    color = {
        "success": SUCCESS_COLOR,
        "failure": FAILURE_COLOR,
        "info": INFO_COLOR,
    }[status]

    fields = []
    if args.exit_code is not None:
        add_field(fields, "Exit code", args.exit_code, inline=True)
    add_field(fields, "Duration", format_duration(args.seconds), inline=True)
    add_field(fields, "Host", args.host, inline=True)
    add_field(fields, "Workdir", args.workdir)
    add_field(fields, "Started", args.started_at, inline=True)
    add_field(fields, "Finished", args.finished_at, inline=True)
    add_field(fields, "Log", args.log)
    if args.command:
        add_field(fields, "Command", redact_secrets(args.command))

    embed: Dict[str, object] = {
        "title": truncate(f"{label}: {args.job}", 256),
        "color": color,
        "fields": fields,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }
    if args.message:
        embed["description"] = truncate(args.message, 4096)

    return {
        "username": args.username,
        "allowed_mentions": {"parse": []},
        "embeds": [embed],
    }


def post_webhook(webhook_url: str, payload: Dict[str, object], timeout: float) -> None:
    request = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "discord-progress-web-hook/1.0",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        response.read()
        if response.status < 200 or response.status >= 300:
            raise RuntimeError(f"Discord webhook returned HTTP {response.status}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a Discord webhook notification for a completed command."
    )
    parser.add_argument("--job", required=True, help="Human-readable job name.")
    parser.add_argument("--exit-code", type=int, help="Completed command exit code.")
    parser.add_argument("--seconds", type=float, help="Elapsed runtime in seconds.")
    parser.add_argument(
        "--status",
        choices=["success", "failure", "info"],
        default="info",
        help="Status to use when --exit-code is not provided.",
    )
    parser.add_argument("--command", help="Command that was executed.")
    parser.add_argument("--log", help="Log file path to include in the notification.")
    parser.add_argument("--message", help="Extra message text.")
    parser.add_argument("--started-at", help="UTC start time to display.")
    parser.add_argument("--finished-at", help="UTC finish time to display.")
    parser.add_argument("--workdir", default=os.getcwd(), help="Working directory.")
    parser.add_argument("--host", default=socket.gethostname(), help="Host name.")
    parser.add_argument(
        "--env-file",
        default=".env",
        help="File containing DISCORD_WEBHOOK_URL. Default: .env",
    )
    parser.add_argument(
        "--webhook-url",
        help="Discord webhook URL. Prefer DISCORD_WEBHOOK_URL or .env for regular use.",
    )
    parser.add_argument(
        "--username",
        default="Pipeline Notifier",
        help="Webhook display name.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the webhook payload instead of sending it.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(args)

    if args.dry_run:
        print(json.dumps(payload, indent=2))
        return 0

    webhook_url = find_webhook_url(args)
    if not webhook_url:
        print(
            "DISCORD_WEBHOOK_URL is not set. Put it in .env or export it.",
            file=sys.stderr,
        )
        return 2

    try:
        post_webhook(webhook_url, payload, args.timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(
            f"Discord webhook failed with HTTP {exc.code}: {truncate(body, 300)}",
            file=sys.stderr,
        )
        return 1
    except (urllib.error.URLError, TimeoutError, RuntimeError, OSError, ValueError) as exc:
        print(f"Discord webhook failed: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
