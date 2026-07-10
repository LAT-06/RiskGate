#!/usr/bin/env bash

set -euo pipefail

INPUT="$(cat)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Formatter skipped: python3 is unavailable." >&2
  exit 0
fi

FILE_PATH="$(
  printf '%s' "$INPUT" |
    python3 -c '
import json
import sys

payload = json.load(sys.stdin)
print(payload.get("tool_input", {}).get("file_path", ""))
'
)"

if [[ -z "$FILE_PATH" || ! -f "$FILE_PATH" ]]; then
  exit 0
fi

PROJECT_DIR="${CLAUDE_PROJECT_DIR:?CLAUDE_PROJECT_DIR is not set}"

# Refuse to process files outside the repository.
if ! python3 - "$PROJECT_DIR" "$FILE_PATH" <<'PY'
from pathlib import Path
import sys

project = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()

try:
    target.relative_to(project)
except ValueError:
    raise SystemExit(1)
PY
then
  echo "Formatter skipped: file is outside the project directory." >&2
  exit 0
fi

cd "$PROJECT_DIR"

BASENAME="$(basename "$FILE_PATH")"

# Lockfiles should only be modified by their package manager.
case "$BASENAME" in
  pnpm-lock.yaml | package-lock.json | yarn.lock)
    exit 0
    ;;
esac

format_failed() {
  echo "Formatter failed for: $FILE_PATH" >&2
  exit 2
}

case "$FILE_PATH" in
  *.py)
    if command -v ruff >/dev/null 2>&1; then
      ruff format "$FILE_PATH" || format_failed
    elif python3 -m ruff --version >/dev/null 2>&1; then
      python3 -m ruff format "$FILE_PATH" || format_failed
    fi
    ;;

  *.ts | *.tsx | *.js | *.jsx | *.vue | *.json | *.jsonc | *.css | *.scss | *.md | *.yml | *.yaml)
    if command -v pnpm >/dev/null 2>&1 &&
      [[ -f "$PROJECT_DIR/package.json" ]]; then
      pnpm exec prettier --write "$FILE_PATH" || format_failed
    fi
    ;;

  *.tf | *.tfvars)
    if command -v terraform >/dev/null 2>&1; then
      terraform fmt "$FILE_PATH" || format_failed
    fi
    ;;

  *.sh)
    if command -v shfmt >/dev/null 2>&1; then
      shfmt -w "$FILE_PATH" || format_failed
    fi
    ;;
esac

exit 0