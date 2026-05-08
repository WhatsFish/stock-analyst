import { query } from "./db";
import type { Prediction, PriceRow, Ticker } from "./types";

export async function getEnabledTickers(): Promise<Ticker[]> {
  return query<Ticker>(
    "SELECT symbol, name, enabled FROM ticker WHERE enabled = TRUE ORDER BY symbol",
  );
}

export async function getLatestPrediction(symbol: string): Promise<Prediction | null> {
  const rows = await query<Prediction>(
    `SELECT id, ticker, to_char(date,'YYYY-MM-DD') AS date,
            generated_at, sentiment, confidence, horizon_days,
            summary, reasoning, drivers, risks, selling_window_notes,
            input_hash, agent_run_ms, cost_usd
     FROM prediction
     WHERE ticker = $1
     ORDER BY generated_at DESC
     LIMIT 1`,
    [symbol],
  );
  return rows[0] ?? null;
}

export async function getRecentPrices(symbol: string, days: number): Promise<PriceRow[]> {
  return query<PriceRow>(
    `SELECT to_char(date,'YYYY-MM-DD') AS date,
            open::float AS open, high::float AS high,
            low::float AS low, close::float AS close,
            volume
     FROM price_observation
     WHERE ticker = $1 AND date >= CURRENT_DATE - $2::int
     ORDER BY date`,
    [symbol, days],
  );
}

export async function getPredictionsInRange(
  symbol: string,
  days: number,
): Promise<{ date: string; sentiment: string; confidence: number }[]> {
  return query<{ date: string; sentiment: string; confidence: number }>(
    `SELECT to_char(date,'YYYY-MM-DD') AS date,
            sentiment, confidence::float AS confidence
     FROM prediction
     WHERE ticker = $1 AND date >= CURRENT_DATE - $2::int
     ORDER BY date`,
    [symbol, days],
  );
}
