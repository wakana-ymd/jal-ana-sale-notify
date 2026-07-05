#!/usr/bin/env bash

set -eu

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

PYTHON_BIN="${PYTHON_BIN:-$REPO_DIR/.venv/bin/python}"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="${PYTHON_BIN_FALLBACK:-python3}"
fi

if [ "${GIT_PULL_BEFORE_RUN:-0}" = "1" ]; then
  git pull --ff-only
fi

"$PYTHON_BIN" run_watch.py --json >> "${WATCH_LOG_PATH:-$REPO_DIR/watch.log}" 2>&1
