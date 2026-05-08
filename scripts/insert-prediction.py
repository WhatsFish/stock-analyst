#!/usr/bin/env python3
"""Read output/<today>-<TICKER>.json files and INSERT into prediction.

Called from run-agent.sh after the headless agent exits. Best-effort: a
malformed file is logged and skipped, but doesn't sink the whole run.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import date
from pathlib import Path

import psycopg2

PROJECT_DIR = Path(os.environ.get(
    "STOCK_PROJECT_DIR", "/home/liharr/src/stock-analyst"))
OUTPUT_DIR = PROJECT_DIR / "output"
INPUT_DIR = PROJECT_DIR / "input"
TODAY = date.today()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--duration-ms", type=int, default=None)
    ap.add_argument("--cost-usd", type=float, default=None)
    args = ap.parse_args()

    pg_kwargs = {
        "host": os.environ.get("STOCK_PG_HOST", "127.0.0.1"),
        "port": int(os.environ.get("STOCK_PG_PORT", "5432")),
        "user": os.environ["STOCK_PG_USER"],
        "password": os.environ["STOCK_PG_PASSWORD"],
        "dbname": os.environ["STOCK_PG_DB"],
    }

    pattern = f"{TODAY.isoformat()}-*.json"
    files = sorted(OUTPUT_DIR.glob(pattern))
    if not files:
        print(f"no output files matching {pattern}", file=sys.stderr)
        return 1

    conn = psycopg2.connect(**pg_kwargs)
    inserted = 0
    try:
        cur = conn.cursor()
        for f in files:
            try:
                data = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                print(f"  skipping {f.name}: invalid JSON ({e})", file=sys.stderr)
                continue
            ticker = data["ticker"]
            input_md = INPUT_DIR / f"{TODAY.isoformat()}-{ticker}.md"
            input_hash = (
                hashlib.sha256(input_md.read_bytes()).hexdigest()
                if input_md.exists() else "unknown"
            )

            cur.execute(
                """
                INSERT INTO prediction
                  (ticker, date, sentiment, confidence, horizon_days,
                   summary, reasoning, drivers, risks, selling_window_notes,
                   input_hash, agent_run_ms, cost_usd)
                VALUES
                  (%s, %s, %s, %s, %s,
                   %s, %s, %s::jsonb, %s::jsonb, %s,
                   %s, %s, %s)
                """,
                (
                    ticker, data["date"],
                    data["sentiment"], data["confidence"], data["horizon_days"],
                    data["summary"], data["reasoning"],
                    json.dumps(data.get("drivers", [])),
                    json.dumps(data.get("risks", [])),
                    data.get("selling_window_notes"),
                    input_hash, args.duration_ms, args.cost_usd,
                ),
            )
            inserted += 1
            print(f"  inserted prediction for {ticker} "
                  f"({data['sentiment']}, conf {data['confidence']})")
        conn.commit()
    finally:
        conn.close()
    return 0 if inserted else 1


if __name__ == "__main__":
    sys.exit(main())
