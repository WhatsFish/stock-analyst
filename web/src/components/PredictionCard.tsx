import { format } from "date-fns";
import type { Prediction } from "@/lib/types";

const SENTIMENT_TONE: Record<string, { dot: string; text: string; label: string }> = {
  bullish: {
    dot: "bg-emerald-500",
    text: "text-emerald-700 dark:text-emerald-400",
    label: "Bullish",
  },
  neutral: {
    dot: "bg-neutral-400",
    text: "text-neutral-700 dark:text-neutral-300",
    label: "Neutral",
  },
  bearish: {
    dot: "bg-red-500",
    text: "text-red-700 dark:text-red-400",
    label: "Bearish",
  },
};

function fmtConfidence(v: number): string {
  return `${(v * 100).toFixed(0)}%`;
}

export function PredictionCard({ p }: { p: Prediction }) {
  const tone = SENTIMENT_TONE[p.sentiment] ?? SENTIMENT_TONE.neutral;
  const generated = new Date(p.generated_at);
  return (
    <section className="border border-neutral-200 dark:border-neutral-800 rounded-md bg-white dark:bg-neutral-900 p-5">
      <header className="flex items-center gap-3 mb-3">
        <span className={`inline-block w-2.5 h-2.5 rounded-full ${tone.dot}`} />
        <span className={`text-base font-medium ${tone.text}`}>{tone.label}</span>
        <span className="text-sm text-neutral-500">
          confidence {fmtConfidence(Number(p.confidence))} · horizon {p.horizon_days}d
        </span>
        <span className="ml-auto text-xs text-neutral-500 font-mono">
          {format(generated, "yyyy-MM-dd HH:mm")} UTC
        </span>
      </header>

      <p className="text-sm text-neutral-800 dark:text-neutral-200 leading-relaxed mb-4">
        {p.summary}
      </p>

      <div className="grid md:grid-cols-2 gap-4 text-sm">
        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
            Drivers
          </h3>
          {p.drivers.length === 0 && (
            <p className="text-neutral-500 italic text-xs">none recorded</p>
          )}
          <ul className="space-y-1.5">
            {p.drivers.map((d, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-neutral-500 font-mono text-xs shrink-0 w-12 text-right">
                  {(d.weight * 100).toFixed(0)}%
                </span>
                <span>
                  <span className="text-neutral-500 text-xs">{d.type}</span>{" "}
                  {d.description}
                </span>
              </li>
            ))}
          </ul>
        </div>

        <div>
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
            Risks
          </h3>
          {p.risks.length === 0 && (
            <p className="text-neutral-500 italic text-xs">none recorded</p>
          )}
          <ul className="space-y-1.5">
            {p.risks.map((r, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-neutral-500 font-mono text-xs shrink-0 w-12 text-right">
                  {(r.weight * 100).toFixed(0)}%
                </span>
                <span>
                  <span className="text-neutral-500 text-xs">{r.type}</span>{" "}
                  {r.description}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {p.selling_window_notes && (
        <div className="mt-5 pt-4 border-t border-neutral-200 dark:border-neutral-800">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-neutral-500 mb-2">
            Selling-window notes
          </h3>
          <p className="text-sm text-neutral-700 dark:text-neutral-300 leading-relaxed">
            {p.selling_window_notes}
          </p>
        </div>
      )}

      <details className="mt-5 pt-4 border-t border-neutral-200 dark:border-neutral-800">
        <summary className="cursor-pointer text-xs font-semibold uppercase tracking-wider text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300">
          Reasoning ({p.reasoning.length} chars)
        </summary>
        <div className="mt-3 prose prose-sm prose-neutral dark:prose-invert text-sm text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
          {p.reasoning}
        </div>
      </details>
    </section>
  );
}
