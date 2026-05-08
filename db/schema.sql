-- stock_analyst schema. One DB, five tables. Multi-ticker from day one
-- even though only MSFT is enabled at startup — keeps `ticker` columns
-- present so we never have to do a backfill migration if we add another.
--
-- Apply by running ./db/bootstrap.sh (which handles role + DB creation
-- via the umami superuser, then pipes this file through psql).

CREATE TABLE IF NOT EXISTS ticker (
  symbol      TEXT        PRIMARY KEY,
  name        TEXT        NOT NULL,
  enabled     BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Daily OHLCV. Pulled by scripts/pull-prices.sh after US market close.
CREATE TABLE IF NOT EXISTS price_observation (
  ticker       TEXT        NOT NULL REFERENCES ticker(symbol),
  date         DATE        NOT NULL,
  open         NUMERIC(12,4),
  high         NUMERIC(12,4),
  low          NUMERIC(12,4),
  close        NUMERIC(12,4),
  volume       BIGINT,
  source       TEXT        NOT NULL,
  ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (ticker, date)
);

-- Raw news / filings / IR posts. Filtered/scored later by the agent.
CREATE TABLE IF NOT EXISTS news_item (
  id           BIGSERIAL    PRIMARY KEY,
  ticker       TEXT         NOT NULL REFERENCES ticker(symbol),
  ts           TIMESTAMPTZ  NOT NULL,
  source       TEXT         NOT NULL,    -- 'sec' | 'ir' | 'newsapi' | ...
  url          TEXT,
  headline     TEXT         NOT NULL,
  summary      TEXT,
  relevance    NUMERIC(3,2),              -- 0..1, optional pre-filter score
  ingested_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  -- Idempotent ingest: don't double-insert the same article on re-run.
  UNIQUE (ticker, source, url)
);
CREATE INDEX IF NOT EXISTS news_item_ticker_ts ON news_item (ticker, ts DESC);

-- Known events with a date (could be future, e.g. upcoming earnings).
CREATE TABLE IF NOT EXISTS event (
  id           BIGSERIAL    PRIMARY KEY,
  ticker       TEXT         NOT NULL REFERENCES ticker(symbol),
  date         DATE         NOT NULL,
  type         TEXT         NOT NULL,    -- 'earnings' | 'sec_filing' | 'fed' | 'product' | 'other'
  description  TEXT         NOT NULL,
  url          TEXT,
  source       TEXT         NOT NULL,
  ingested_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  UNIQUE (ticker, date, type, description)
);
CREATE INDEX IF NOT EXISTS event_ticker_date ON event (ticker, date);

-- Agent output. One row per agent run = one prediction-for-date.
CREATE TABLE IF NOT EXISTS prediction (
  id             BIGSERIAL    PRIMARY KEY,
  ticker         TEXT         NOT NULL REFERENCES ticker(symbol),
  date           DATE         NOT NULL,                -- US trading day this is "for"
  generated_at   TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
  sentiment      TEXT         NOT NULL CHECK (sentiment IN ('bullish','neutral','bearish')),
  confidence     NUMERIC(3,2) NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
  horizon_days   INT          NOT NULL,                -- e.g. 5, 30
  summary        TEXT         NOT NULL,                -- one paragraph
  reasoning      TEXT         NOT NULL,                -- markdown body
  drivers        JSONB        NOT NULL DEFAULT '[]'::jsonb,
  risks          JSONB        NOT NULL DEFAULT '[]'::jsonb,
  selling_window_notes TEXT,
  -- sha256 of the input bundle hashed into the agent — lets us detect
  -- whether the same data would yield the same call (and dedup re-runs).
  input_hash     TEXT         NOT NULL,
  agent_run_ms   INT,
  cost_usd       NUMERIC(12,6)
);
CREATE INDEX IF NOT EXISTS prediction_ticker_date ON prediction (ticker, date DESC);
CREATE INDEX IF NOT EXISTS prediction_generated  ON prediction (generated_at DESC);

-- Seed the only enabled ticker for now. INSERT-only — will not stomp the
-- name field on re-apply.
INSERT INTO ticker (symbol, name, enabled)
VALUES ('MSFT', 'Microsoft Corporation', TRUE)
ON CONFLICT (symbol) DO NOTHING;
