#!/usr/bin/env bash

set -euo pipefail

INPUT="$(cat)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Blocked: python3 is required to validate Bash commands safely." >&2
  exit 2
fi

COMMAND="$(
  printf '%s' "$INPUT" |
    python3 -c '
import json
import sys

payload = json.load(sys.stdin)
print(payload.get("tool_input", {}).get("command", ""))
'
)"

block() {
  echo "Blocked by RiskGate project policy: $1" >&2
  exit 2
}

# Block recursive forced deletion.
if printf '%s\n' "$COMMAND" |
  grep -Eiq '(^|[;&|][[:space:]]*)rm[[:space:]]+(-[a-z]*r[a-z]*f|-+[a-z]*f[a-z]*r|--recursive[[:space:]]+--force|--force[[:space:]]+--recursive)([[:space:]]|$)'; then
  block "recursive forced deletion is not allowed"
fi

# Block Terraform destruction.
if printf '%s\n' "$COMMAND" |
  grep -Eiq '(^|[;&|][[:space:]]*)terraform([[:space:]]+-chdir=[^[:space:]]+)?[[:space:]]+destroy([[:space:]]|$)'; then
  block "terraform destroy is not allowed"
fi

# Block force-pushing protected branches regardless of argument order.
if printf '%s\n' "$COMMAND" | grep -Eiq 'git[[:space:]]+push' &&
  printf '%s\n' "$COMMAND" | grep -Eiq '(^|[[:space:]])(-f|--force|--force-with-lease)([=[:space:]]|$)' &&
  printf '%s\n' "$COMMAND" | grep -Eiq '(^|[[:space:]/:])(main|master)([[:space:]]|$)'; then
  block "force-pushing main or master is not allowed"
fi

# Block destructive Git cleanup.
if printf '%s\n' "$COMMAND" |
  grep -Eiq 'git[[:space:]]+clean[[:space:]]+[^;&|]*-[a-z]*f[a-z]*d[a-z]*x'; then
  block "git clean -fdx can delete ignored and untracked files"
fi

# Block hard reset of protected branches.
if printf '%s\n' "$COMMAND" |
  grep -Eiq 'git[[:space:]]+reset[[:space:]]+--hard[[:space:]]+(origin/)?(main|master)([[:space:]]|$)'; then
  block "hard reset of main or master is not allowed"
fi

exit 0