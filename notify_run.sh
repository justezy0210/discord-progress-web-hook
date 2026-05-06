#!/usr/bin/env bash

set -u

usage() {
  cat <<'USAGE'
Usage:
  ./notify_run.sh [options] "Job name" -- command [args...]

Options:
  --env-file PATH   Read DISCORD_WEBHOOK_URL from PATH. Default: .env
  --log PATH        Include a log file path in the Discord message.
  -h, --help        Show this help.

Examples:
  ./notify_run.sh "test sleep" -- bash -lc 'sleep 3; echo done'
  nohup ./notify_run.sh --log blast.log "BLAST search" -- blastp -query q.fa -db db -out result.tsv > blast.log 2>&1 &

Notes:
  The wrapper exits with the original command exit code.
  For pipelines with pipes, redirects, or && chains, run them through bash -lc.
USAGE
}

die() {
  echo "notify_run.sh: $*" >&2
  exit 64
}

env_file=".env"
log_path=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      [[ $# -ge 2 ]] || die "--env-file requires a path"
      env_file="$2"
      shift 2
      ;;
    --log)
      [[ $# -ge 2 ]] || die "--log requires a path"
      log_path="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      die "missing job name before --"
      ;;
    *)
      job_name="$1"
      shift
      break
      ;;
  esac
done

[[ -n "${job_name:-}" ]] || die "missing job name"
[[ "${1:-}" == "--" ]] || die "expected -- before the command"
shift
[[ $# -gt 0 ]] || die "missing command"

cmd=("$@")

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
notify_py="${script_dir}/discord_notify.py"
[[ -f "$notify_py" ]] || die "cannot find discord_notify.py next to notify_run.sh"

if command -v python3 >/dev/null 2>&1; then
  python_bin="python3"
elif command -v python >/dev/null 2>&1; then
  python_bin="python"
else
  echo "notify_run.sh: python3 or python is required for notification" >&2
  "${cmd[@]}"
  exit $?
fi

start_epoch="$(date +%s)"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

"${cmd[@]}"
exit_code=$?

end_epoch="$(date +%s)"
finished_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
duration=$((end_epoch - start_epoch))
command_text="$(printf '%q ' "${cmd[@]}")"
command_text="${command_text% }"

notify_args=(
  "$notify_py"
  --job "$job_name"
  --exit-code "$exit_code"
  --seconds "$duration"
  --command "$command_text"
  --started-at "$started_at"
  --finished-at "$finished_at"
  --env-file "$env_file"
)

if [[ -n "$log_path" ]]; then
  notify_args+=(--log "$log_path")
fi

if ! "$python_bin" "${notify_args[@]}"; then
  echo "notify_run.sh: warning: failed to send Discord notification" >&2
fi

exit "$exit_code"
