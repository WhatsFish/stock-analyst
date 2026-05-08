#!/usr/bin/env bash
# Cron entry: prepare input bundles, run claude -p, parse output, INSERT
# prediction rows, log to cost-tracker.
#
# Mirrors ai-feed/scripts/run-agent.sh. Cost logging is best-effort and
# never masks the agent's exit code.
set -euo pipefail

PROJECT_DIR="/home/liharr/src/stock-analyst"
ENV_FILE="${STOCK_ENV_FILE:-/home/liharr/.config/stock-analyst.env}"
COST_ENV="/home/liharr/.config/cost-tracker.env"
CLAUDE_BIN="/home/liharr/.nvm/versions/node/v24.15.0/bin/claude"
VENV="$PROJECT_DIR/.venv"
AGENT_COST_USD_ESTIMATE="${AGENT_COST_USD_ESTIMATE:-0.50}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
fi

cd "$PROJECT_DIR"
mkdir -p output

# 1. Prepare per-ticker input bundles from the DB.
"$VENV/bin/python" "$PROJECT_DIR/scripts/prepare-input.py"

# 2. Run the headless agent.
START_TS=$(date -u +%s)
START_ISO=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

set +e
"$CLAUDE_BIN" -p "$(cat agent-task.md)" \
  --dangerously-skip-permissions \
  --max-budget-usd 2 \
  --add-dir "$PROJECT_DIR"
EXIT=$?
set -e

END_TS=$(date -u +%s)
DURATION_MS=$(( (END_TS - START_TS) * 1000 ))

# 3. Parse output JSON files and INSERT prediction rows. Best-effort —
# never let a parse failure mask the agent's exit.
set +e
"$VENV/bin/python" "$PROJECT_DIR/scripts/insert-prediction.py" \
  --duration-ms "$DURATION_MS" \
  --cost-usd "$AGENT_COST_USD_ESTIMATE"
set -e

# 4. Log to cost-tracker (separate DB).
if [ -f "$COST_ENV" ]; then
  set +e
  # shellcheck disable=SC1090
  source "$COST_ENV"
  METADATA="{\"started_at\":\"$START_ISO\",\"exit_code\":$EXIT,\"script\":\"stock-analyst run-agent.sh\"}"
  docker exec -e PGPASSWORD="$COST_PG_PASSWORD" "$COST_DB_CONTAINER" \
    psql -h "$COST_PG_HOST" -p "$COST_PG_PORT" -U "$COST_PG_USER" -d "$COST_PG_DB" \
    -c "INSERT INTO cost_event (service, provider, cost_usd, duration_ms, metadata) \
        VALUES ('stock-analyst-agent', 'anthropic', $AGENT_COST_USD_ESTIMATE, $DURATION_MS, '$METADATA'::jsonb);" \
    > /dev/null 2>&1 || true
  set -e
fi

exit $EXIT
