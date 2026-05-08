export type Driver = {
  type: string;
  description: string;
  weight: number;
};

export type Prediction = {
  id: number;
  ticker: string;
  date: string;             // YYYY-MM-DD
  generated_at: string;     // ISO
  sentiment: "bullish" | "neutral" | "bearish";
  confidence: number;
  horizon_days: number;
  summary: string;
  reasoning: string;
  drivers: Driver[];
  risks: Driver[];
  selling_window_notes: string | null;
  input_hash: string;
  agent_run_ms: number | null;
  cost_usd: number | null;
};

export type PriceRow = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

export type Ticker = {
  symbol: string;
  name: string;
  enabled: boolean;
};
