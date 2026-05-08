import type { PriceRow } from "@/lib/types";

export function PriceSummary({ prices }: { prices: PriceRow[] }) {
  if (prices.length === 0) {
    return (
      <div className="border border-neutral-200 dark:border-neutral-800 rounded-md bg-white dark:bg-neutral-900 p-5">
        <p className="text-sm text-neutral-500">no price data yet</p>
      </div>
    );
  }
  const last = prices[prices.length - 1];
  const prev = prices.length >= 2 ? prices[prices.length - 2] : null;
  const change = prev ? last.close - prev.close : 0;
  const pct = prev && prev.close ? (change / prev.close) * 100 : 0;
  const isUp = change >= 0;
  const high = Math.max(...prices.map((p) => p.high));
  const low = Math.min(...prices.map((p) => p.low));

  return (
    <div className="border border-neutral-200 dark:border-neutral-800 rounded-md bg-white dark:bg-neutral-900 p-5">
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-semibold tabular-nums">
          ${last.close.toFixed(2)}
        </span>
        <span
          className={`text-sm font-mono ${
            isUp
              ? "text-emerald-600 dark:text-emerald-400"
              : "text-red-600 dark:text-red-400"
          }`}
        >
          {isUp ? "+" : ""}
          {change.toFixed(2)} ({isUp ? "+" : ""}
          {pct.toFixed(2)}%)
        </span>
        <span className="text-xs text-neutral-500 font-mono ml-auto">
          close · {last.date}
        </span>
      </div>
      <div className="mt-3 grid grid-cols-3 gap-4 text-xs text-neutral-600 dark:text-neutral-400">
        <div>
          <span className="block text-neutral-500 uppercase tracking-wider text-[10px] mb-0.5">
            open
          </span>
          <span className="tabular-nums">${last.open.toFixed(2)}</span>
        </div>
        <div>
          <span className="block text-neutral-500 uppercase tracking-wider text-[10px] mb-0.5">
            range ({prices.length}d)
          </span>
          <span className="tabular-nums">
            ${low.toFixed(2)} – ${high.toFixed(2)}
          </span>
        </div>
        <div>
          <span className="block text-neutral-500 uppercase tracking-wider text-[10px] mb-0.5">
            volume
          </span>
          <span className="tabular-nums">{last.volume.toLocaleString()}</span>
        </div>
      </div>
    </div>
  );
}
