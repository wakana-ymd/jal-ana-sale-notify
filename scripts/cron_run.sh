#!/usr/bin/env bash

set -eu

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [ "${GIT_PULL_BEFORE_RUN:-0}" = "1" ]; then
  git pull --ff-only
fi

python3 run_watch.py --json >> "${WATCH_LOG_PATH:-$REPO_DIR/watch.log}" 2>&1
