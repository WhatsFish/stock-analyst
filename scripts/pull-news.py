#!/usr/bin/env python3
"""Pull recent SEC filings and (optionally) NewsAPI articles for enabled tickers.

Idempotent: news_item has UNIQUE (ticker, source, url); re-runs are no-ops.
NewsAPI is skipped silently if NEWSAPI_KEY is empty — useful while we
wait to provision a key.
"""
import os
import sys
import time
from datetime import datetime, timezone, timedelta

import psycopg2
import requests

PG_HOST = os.environ.get("STOCK_PG_HOST", "127.0.0.1")
PG_PORT = int(os.environ.get("STOCK_PG_PORT", "5432"))
PG_USER = os.environ["STOCK_PG_USER"]
PG_PASSWORD = os.environ["STOCK_PG_PASSWORD"]
PG_DB = os.environ["STOCK_PG_DB"]

NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", "").strip()
# SEC asks every API client to identify themselves with a contact email.
EDGAR_UA = os.environ.get("EDGAR_UA", "stock-analyst contact@example.com")

# Ticker -> 10-digit SEC CIK (zero-padded).
CIK = {
    "MSFT": "0000789019",
}

# Filing types worth surfacing to the timeline as discrete events.
EVENT_FILING_TYPES = {"10-K", "10-Q", "8-K"}

# Per-ticker NewsAPI query string (English-language search).
NEWSAPI_QUERIES = {
    "MSFT": "Microsoft Corporation",
}


def fetch_sec_filings(symbol):
    cik = CIK.get(symbol)
    if not cik:
        return [], []
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(
        url,
        headers={"User-Agent": EDGAR_UA, "Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    recent = data.get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accessions = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    items, events = [], []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).date()
    for form, date_str, accession, primary in zip(forms, dates, accessions, primary_docs):
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d < cutoff:
            continue
        clean_acc = accession.replace("-", "")
        url_link = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{clean_acc}/{primary}"
        items.append({
            "ticker": symbol,
            "ts": datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc),
            "source": "sec",
            "url": url_link,
            "headline": f"SEC filing: {form}",
            "summary": f"{symbol} {form} filed {d.isoformat()}",
            "relevance": 0.9 if form in EVENT_FILING_TYPES else 0.5,
        })
        if form in EVENT_FILING_TYPES:
            events.append({
                "ticker": symbol,
                "date": d,
                "type": "sec_filing",
                "description": f"{form} filed",
                "url": url_link,
                "source": "sec",
            })
    return items, events


def fetch_newsapi(symbol):
    if not NEWSAPI_KEY:
        return []
    q = NEWSAPI_QUERIES.get(symbol, symbol)
    # Keep the request volume low — free tier is 100/day, we run every 4h.
    from_date = (datetime.now(timezone.utc) - timedelta(days=3)).date().isoformat()
    r = requests.get(
        "https://newsapi.org/v2/everything",
        params={
            "q": q,
            "from": from_date,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": 50,
        },
        headers={"X-Api-Key": NEWSAPI_KEY},
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    out = []
    for art in data.get("articles", []):
        published = art.get("publishedAt")
        if not published:
            continue
        try:
            ts = datetime.fromisoformat(published.replace("Z", "+00:00"))
        except ValueError:
            continue
        title = (art.get("title") or "").strip()
        if not title:
            continue
        out.append({
            "ticker": symbol,
            "ts": ts,
            "source": "newsapi",
            "url": art.get("url"),
            "headline": title[:500],
            "summary": (art.get("description") or "").strip(),
            "relevance": None,
        })
    return out


def insert_items(conn, items):
    if not items:
        return 0
    cur = conn.cursor()
    inserted = 0
    for i in items:
        cur.execute(
            """
            INSERT INTO news_item
              (ticker, ts, source, url, headline, summary, relevance)
            VALUES
              (%(ticker)s, %(ts)s, %(source)s, %(url)s, %(headline)s, %(summary)s, %(relevance)s)
            ON CONFLICT (ticker, source, url) DO NOTHING
            """,
            i,
        )
        inserted += cur.rowcount
    return inserted


def insert_events(conn, events):
    if not events:
        return 0
    cur = conn.cursor()
    inserted = 0
    for e in events:
        cur.execute(
            """
            INSERT INTO event
              (ticker, date, type, description, url, source)
            VALUES
              (%(ticker)s, %(date)s, %(type)s, %(description)s, %(url)s, %(source)s)
            ON CONFLICT (ticker, date, type, description) DO NOTHING
            """,
            e,
        )
        inserted += cur.rowcount
    return inserted


def main():
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, user=PG_USER,
        password=PG_PASSWORD, dbname=PG_DB,
    )
    try:
        cur = conn.cursor()
        cur.execute("SELECT symbol FROM ticker WHERE enabled = TRUE ORDER BY symbol")
        tickers = [r[0] for r in cur.fetchall()]
        for symbol in tickers:
            print(f"=== {symbol} ===")
            try:
                items, events = fetch_sec_filings(symbol)
                ni = insert_items(conn, items)
                ne = insert_events(conn, events)
                print(f"  SEC: {ni} new items, {ne} new events (saw {len(items)} filings)")
            except Exception as e:
                print(f"  SEC failed: {e}", file=sys.stderr)
            try:
                items = fetch_newsapi(symbol)
                ni = insert_items(conn, items)
                if NEWSAPI_KEY:
                    print(f"  NewsAPI: {ni} new items (saw {len(items)})")
                else:
                    print("  NewsAPI: skipped (no key)")
            except Exception as e:
                print(f"  NewsAPI failed: {e}", file=sys.stderr)
            conn.commit()
            time.sleep(0.5)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
