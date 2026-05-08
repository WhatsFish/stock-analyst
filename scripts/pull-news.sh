#!/usr/bin/env bash
# Cron entry: pull SEC filings + NewsAPI articles into news_item / event.
set -euo pipefail

PROJECT_DIR="/home/liharr/src/stock-analyst"
ENV_FILE="${STOCK_ENV_FILE:-/home/liharr/.config/stock-analyst.env}"
VENV="$PROJECT_DIR/.venv"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

exec "$VENV/bin/python" "$PROJECT_DIR/scripts/pull-news.py"
