import Link from "next/link";
import { getEnabledTickers, getLatestPrediction, getRecentPrices } from "@/lib/queries";
import { Disclaimer } from "@/components/Disclaimer";
import { PredictionCard } from "@/components/PredictionCard";
import { PriceSummary } from "@/components/PriceSummary";

export const dynamic = "force-dynamic";
export const revalidate = 300;

export default async function StockHome() {
  const tickers = await getEnabledTickers();
  if (tickers.length === 0) {
    return (
      <main className="max-w-3xl mx-auto px-5 py-12">
        <h1 className="text-2xl font-semibold mb-2">stock</h1>
        <p className="text-sm text-neutral-500">No enabled tickers in the database.</p>
      </main>
    );
  }

  // For now we always render the first enabled ticker. Selector UI will
  // come once there's more than one symbol in the table.
  const t = tickers[0];
  const [prediction, prices] = await Promise.all([
    getLatestPrediction(t.symbol),
    getRecentPrices(t.symbol, 60),
  ]);

  return (
    <main className="max-w-3xl mx-auto px-5 py-12">
      <header className="mb-8">
        <div className="flex items-baseline gap-3 mb-2">
          <h1 className="text-2xl font-semibold tracking-tight">{t.symbol}</h1>
          <span className="text-sm text-neutral-500">{t.name}</span>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/stock" className="font-medium underline">today</Link>
          <Link href="/stock/timeline" className="text-neutral-500 hover:text-neutral-800 dark:hover:text-neutral-200">
            timeline
          </Link>
        </nav>
      </header>

      <section className="mb-6">
        <PriceSummary prices={prices} />
      </section>

      <section className="mb-6">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
          Latest analysis
        </h2>
        {prediction ? (
          <PredictionCard p={prediction} />
        ) : (
          <div className="border border-dashed border-neutral-300 dark:border-neutral-700 rounded-md p-6 text-sm text-neutral-500">
            <p className="mb-1">No prediction yet.</p>
            <p>
              The agent runs once per US trading day after market close (≈ 22:30 UTC).
              The first run will populate this card.
            </p>
          </div>
        )}
      </section>

      <Disclaimer />
    </main>
  );
}
