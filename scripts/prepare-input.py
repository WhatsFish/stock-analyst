#!/usr/bin/env python3
"""Render input/<today>-<TICKER>.md for each enabled ticker.

The agent reads these bundles and produces output/<today>-<TICKER>.json.
Pre-rendering keeps the agent's job scoped: read text in, write JSON out.
"""
import hashlib
import os
import sys
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import psycopg2

PG_HOST = os.environ.get("STOCK_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("STOCK_PG_PORT", "5432"))
PG_USER = os.environ["STOCK_PG_USER"]
PG_PASSWORD = os.environ["STOCK_PG_PASSWORD"]
PG_DB = os.environ["STOCK_PG_DB"]

PROJECT_DIR = Path(os.environ.get(
    "STOCK_PROJECT_DIR", "/home/liharr/src/stock-analyst"))
INPUT_DIR = PROJECT_DIR / "input"
TODAY = date.today()


def fetch_prices(cur, symbol, lookback=60):
    cur.execute(
        """SELECT date, open, high, low, close, volume
           FROM price_observation
           WHERE ticker = %s AND date >= %s
           ORDER BY date""",
        (symbol, TODAY - timedelta(days=lookback)),
    )
    return cur.fetchall()


def fetch_news(cur, symbol, lookback=30, limit=80):
    cur.execute(
        """SELECT ts, source, headline, url, summary
           FROM news_item
           WHERE ticker = %s AND ts >= %s
           ORDER BY ts DESC
           LIMIT %s""",
        (symbol, datetime.now(timezone.utc) - timedelta(days=lookback), limit),
    )
    return cur.fetchall()


def fetch_events(cur, symbol, past=14, future=60):
    cur.execute(
        """SELECT date, type, description, url
           FROM event
           WHERE ticker = %s AND date >= %s AND date <= %s
           ORDER BY date""",
        (symbol, TODAY - timedelta(days=past), TODAY + timedelta(days=future)),
    )
    return cur.fetchall()


def fetch_last_prediction(cur, symbol):
    cur.execute(
        """SELECT date, generated_at, sentiment, confidence, horizon_days, summary
           FROM prediction WHERE ticker = %s
           ORDER BY generated_at DESC LIMIT 1""",
        (symbol,),
    )
    return cur.fetchone()


def render(symbol, prices, news, events, last):
    out = []
    out.append(f"# Stock analysis input — {symbol} — {TODAY.isoformat()}")
    out.append("")
    out.append(f"Generated UTC: {datetime.now(timezone.utc).isoformat()}")
    out.append("")

    out.append(f"## Recent prices ({symbol})")
    out.append("")
    if prices:
        first_close = float(prices[0][4])
        last_close = float(prices[-1][4])
        pct = (last_close - first_close) / first_close * 100 if first_close else 0
        high_p = max(float(p[2]) for p in prices)
        low_p = min(float(p[3]) for p in prices)
        out.append(f"- Last close: ${last_close:.2f} on {prices[-1][0]}")
        out.append(f"- Period range: ${low_p:.2f} – ${high_p:.2f}")
        out.append(f"- Period start close: ${first_close:.2f} on {prices[0][0]}")
        out.append(f"- Total return over period: {pct:+.2f}%")
        out.append("")
        out.append("Most recent 20 sessions:")
        out.append("")
        out.append("| date | open | high | low | close | volume |")
        out.append("|------|------|------|-----|-------|--------|")
        for p in prices[-20:]:
            out.append(
                f"| {p[0]} | {float(p[1]):.2f} | {float(p[2]):.2f} | "
                f"{float(p[3]):.2f} | {float(p[4]):.2f} | {p[5]:,} |"
            )
    else:
        out.append("(no price data — agent should note this and lower confidence)")
    out.append("")

    out.append(f"## Recent news ({symbol}, last 30 days)")
    out.append("")
    if news:
        for ts, source, headline, url, summary in news:
            out.append(f"- {ts.strftime('%Y-%m-%d')} **[{source}]** {headline}")
            if url:
                out.append(f"  - {url}")
            if summary and summary != headline and len(summary) > 0:
                out.append(f"  - {summary[:240]}")
    else:
        out.append("(no news in window)")
    out.append("")

    out.append("## Events near today (recent + upcoming 60d)")
    out.append("")
    if events:
        for d, type_, desc, url in events:
            marker = "PAST" if d < TODAY else ("TODAY" if d == TODAY else "UPCOMING")
            line = f"- {d} [{marker}] [{type_}] {desc}"
            if url:
                line += f" — {url}"
            out.append(line)
    else:
        out.append("(no events known in window)")
    out.append("")

    out.append("## Most recent previous prediction (for self-comparison)")
    out.append("")
    if last:
        out.append(f"- For date: {last[0]}")
        out.append(f"- Generated: {last[1].isoformat()}")
        out.append(f"- Sentiment: {last[2]} (confidence {float(last[3]):.2f})")
        out.append(f"- Horizon: {last[4]} days")
        out.append(f"- Summary: {last[5]}")
    else:
        out.append("(no previous predictions — first run)")
    out.append("")

    return "\n".join(out)


def main():
    INPUT_DIR.mkdir(exist_ok=True)
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
            return 1
        for symbol in tickers:
            content = render(
                symbol,
                fetch_prices(cur, symbol),
                fetch_news(cur, symbol),
                fetch_events(cur, symbol),
                fetch_last_prediction(cur, symbol),
            )
            path = INPUT_DIR / f"{TODAY.isoformat()}-{symbol}.md"
            path.write_text(content)
            digest = hashlib.sha256(content.encode()).hexdigest()
            print(f"wrote {path} ({len(content)} bytes, sha256 {digest[:12]})")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
