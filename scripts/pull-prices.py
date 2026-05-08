#!/usr/bin/env python3
"""Pull daily OHLCV for every enabled ticker; upsert into price_observation.

Run via scripts/pull-prices.sh (which sources the env file and activates the
venv). On every fire we re-fetch the last LOOKBACK_DAYS so missed cron runs
self-heal.
"""
import os
import sys
from datetime import date, timedelta

import psycopg2
import yfinance as yf

PG_HOST = os.environ.get("STOCK_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("STOCK_PG_PORT", "5432"))
PG_USER = os.environ["STOCK_PG_USER"]
PG_PASSWORD = os.environ["STOCK_PG_PASSWORD"]
PG_DB = os.environ["STOCK_PG_DB"]

LOOKBACK_DAYS = int(os.environ.get("PRICE_LOOKBACK_DAYS", "120"))
SOURCE = "yfinance"


def main() -> int:
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER,
        password=PG_PASSWORD, dbname=PG_DB,
    )
    try:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM ticker WHERE enabled = TRUE ORDER BY symbol")
        tickers = [r[0] for r in cur.fetchall()]
        if not tickers:
            print("no enabled tickers", file=sys.stderr)
            return 0

        end = date.today() + timedelta(days=1)
        start = end - timedelta(days=LOOKBACK_DAYS)

        for symbol in tickers:
            print(f"fetching {symbol} {start}..{end}")
            df = yf.Ticker(symbol).history(
                start=start.isoformat(), end=end.isoformat(), auto_adjust=False,
            )
            if df.empty:
                print(f"  {symbol}: no rows returned")
                continue
            rows = 0
            for ts, r in df.iterrows():
                d = ts.date() if hasattr(ts, "date") else ts
                cur.execute(
                    """
                    INSERT INTO price_observation
                      (ticker, date, open, high, low, close, volume, source)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                      open = EXCLUDED.open,
                      high = EXCLUDED.high,
                      low = EXCLUDED.low,
                      close = EXCLUDED.close,
                      volume = EXCLUDED.volume,
                      source = EXCLUDED.source,
                      ingested_at = NOW()
                    """,
                    (
                        symbol, d,
                        float(r["Open"]), float(r["High"]),
                        float(r["Low"]), float(r["Close"]),
                        int(r["Volume"]), SOURCE,
                    ),
                )
                rows += 1
            conn.commit()
            print(f"  {symbol}: upserted {rows} rows")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
