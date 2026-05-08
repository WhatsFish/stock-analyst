#!/usr/bin/env bash
# Bootstrap the stock_analyst Postgres role + DB inside the shared
# traffic-monitor-db-1 container, then apply schema.sql.
#
# Idempotent: safe to re-run. Reads STOCK_PG_PASSWORD from the env file
# at /home/liharr/.config/stock-analyst.env (mode 600).
#
# Run from the repo root.
set -euo pipefail

ENV_FILE="${STOCK_ENV_FILE:-/home/liharr/.config/stock-analyst.env}"
DB_CONTAINER="${STOCK_DB_CONTAINER:-traffic-monitor-db-1}"
SCHEMA_FILE="$(dirname "$0")/schema.sql"

if [ ! -f "$ENV_FILE" ]; then
  echo "ERROR: $ENV_FILE not found. Create it with STOCK_PG_PASSWORD=..." >&2
  exit 1
fi
# shellcheck disable=SC1090
source "$ENV_FILE"

if [ -z "${STOCK_PG_PASSWORD:-}" ]; then
  echo "ERROR: STOCK_PG_PASSWORD not set in $ENV_FILE" >&2
  exit 1
fi

# Step 1: create role + database. The shared db container's superuser is
# `umami` (the role created when umami was first installed); reuse it.
docker exec -i "$DB_CONTAINER" psql -U umami -d umami <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'stock_analyst') THEN
    CREATE ROLE stock_analyst WITH LOGIN PASSWORD '${STOCK_PG_PASSWORD}';
  END IF;
END
\$\$;

SELECT 'CREATE DATABASE stock_analyst OWNER stock_analyst'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'stock_analyst')\gexec

GRANT ALL PRIVILEGES ON DATABASE stock_analyst TO stock_analyst;
SQL

# Step 2: apply schema as the owner role.
docker exec -i -e PGPASSWORD="$STOCK_PG_PASSWORD" "$DB_CONTAINER" \
  psql -h localhost -U stock_analyst -d stock_analyst < "$SCHEMA_FILE"

echo "stock_analyst bootstrap complete."
