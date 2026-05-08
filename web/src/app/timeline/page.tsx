import Link from "next/link";
import {
  getEnabledTickers,
  getRecentPrices,
  getPredictionsInRange,
} from "@/lib/queries";
import { Disclaimer } from "@/components/Disclaimer";

export const dynamic = "force-dynamic";
export const revalidate = 300;

const DAYS = 90;
const SVG_W = 880;
const SVG_H = 280;
const PAD_L = 56;
const PAD_R = 12;
const PAD_T = 16;
const PAD_B = 32;

const SENTIMENT_FILL: Record<string, string> = {
  bullish: "#10b981",
  neutral: "#a3a3a3",
  bearish: "#ef4444",
};

export default async function TimelinePage() {
  const tickers = await getEnabledTickers();
  if (tickers.length === 0) {
    return (
      <main className="max-w-5xl mx-auto px-5 py-12">
        <p className="text-sm text-neutral-500">No enabled tickers.</p>
      </main>
    );
  }
  const t = tickers[0];
  const [prices, predictions] = await Promise.all([
    getRecentPrices(t.symbol, DAYS),
    getPredictionsInRange(t.symbol, DAYS),
  ]);

  const innerW = SVG_W - PAD_L - PAD_R;
  const innerH = SVG_H - PAD_T - PAD_B;

  const closes = prices.map((p) => p.close);
  const minP = closes.length ? Math.min(...closes) : 0;
  const maxP = closes.length ? Math.max(...closes) : 1;
  // Pad y-range slightly so the line doesn't hug the edges.
  const yPad = (maxP - minP) * 0.08 || 1;
  const yMin = minP - yPad;
  const yMax = maxP + yPad;

  const xFor = (i: number) =>
    PAD_L + (prices.length <= 1 ? innerW / 2 : (i / (prices.length - 1)) * innerW);
  const yFor = (close: number) =>
    PAD_T + innerH - ((close - yMin) / (yMax - yMin)) * innerH;

  const linePath = prices
    .map((p, i) => `${i === 0 ? "M" : "L"} ${xFor(i).toFixed(1)} ${yFor(p.close).toFixed(1)}`)
    .join(" ");

  // Prediction dots: anchor each to the price on its date, if available.
  const priceByDate = new Map(prices.map((p, i) => [p.date, i]));
  const predDots = predictions
    .map((pr) => {
      const idx = priceByDate.get(pr.date);
      if (idx === undefined) return null;
      return {
        x: xFor(idx),
        y: yFor(prices[idx].close),
        sentiment: pr.sentiment,
        confidence: pr.confidence,
        date: pr.date,
      };
    })
    .filter((d): d is NonNullable<typeof d> => d !== null);

  // Y-axis tick labels — just min, mid, max.
  const yTicks = [yMax, (yMax + yMin) / 2, yMin];

  // X-axis: first, middle, last date labels.
  const xTickIdx = prices.length === 0 ? [] : prices.length === 1 ? [0] : [0, Math.floor((prices.length - 1) / 2), prices.length - 1];

  return (
    <main className="max-w-5xl mx-auto px-5 py-12">
      <header className="mb-6">
        <div className="flex items-baseline gap-3 mb-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t.symbol}</h1>
          <span className="text-sm text-neutral-500">{t.name} · {DAYS}-day timeline</span>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/stock" className="text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200">
            today
          </Link>
          <Link href="/stock/timeline" className="font-medium underline">
            timeline
          </Link>
        </nav>
      </header>

      {prices.length === 0 ? (
        <p className="text-sm text-neutral-500">No price data in window.</p>
      ) : (
        <div className="border border-neutral-200 dark:border-neutral-800 rounded-md bg-white dark:bg-neutral-900 p-4 overflow-x-auto">
          <svg
            viewBox={`0 0 ${SVG_W} ${SVG_H}`}
            className="w-full h-auto"
            preserveAspectRatio="xMidYMid meet"
          >
            {yTicks.map((v, i) => (
              <g key={`y${i}`}>
                <line
                  x1={PAD_L}
                  x2={SVG_W - PAD_R}
                  y1={yFor(v)}
                  y2={yFor(v)}
                  stroke="currentColor"
                  strokeOpacity={0.08}
                  strokeDasharray="2 4"
                />
                <text
                  x={PAD_L - 6}
                  y={yFor(v) + 4}
                  textAnchor="end"
                  className="fill-current text-[10px] font-mono"
                  opacity={0.6}
                >
                  ${v.toFixed(2)}
                </text>
              </g>
            ))}
            {xTickIdx.map((i) => (
              <text
                key={`x${i}`}
                x={xFor(i)}
                y={SVG_H - 8}
                textAnchor="middle"
                className="fill-current text-[10px] font-mono"
                opacity={0.6}
              >
                {prices[i].date}
              </text>
            ))}
            <path
              d={linePath}
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              opacity={0.85}
            />
            {predDots.map((d, i) => (
              <g key={`p${i}`}>
                <circle
                  cx={d.x}
                  cy={d.y}
                  r={4 + d.confidence * 3}
                  fill={SENTIMENT_FILL[d.sentiment] ?? SENTIMENT_FILL.neutral}
                  fillOpacity={0.8}
                  stroke="white"
                  strokeWidth={1}
                >
                  <title>
                    {d.date} · {d.sentiment} · conf {(d.confidence * 100).toFixed(0)}%
                  </title>
                </circle>
              </g>
            ))}
          </svg>
          <div className="flex gap-4 mt-3 text-xs text-neutral-500">
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: SENTIMENT_FILL.bullish }} />
              bullish
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: SENTIMENT_FILL.neutral }} />
              neutral
            </span>
            <span className="flex items-center gap-1.5">
              <span className="inline-block w-2.5 h-2.5 rounded-full" style={{ background: SENTIMENT_FILL.bearish }} />
              bearish
            </span>
            <span className="ml-auto">
              {predictions.length} prediction{predictions.length === 1 ? "" : "s"} in window
            </span>
          </div>
        </div>
      )}

      <Disclaimer />
    </main>
  );
}
