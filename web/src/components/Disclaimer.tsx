export function Disclaimer() {
  return (
    <div className="mt-12 text-xs text-neutral-500 dark:text-neutral-500 leading-relaxed border-t border-neutral-200 dark:border-neutral-800 pt-4">
      <strong className="text-neutral-700 dark:text-neutral-400">
        Informational only. Not investment advice.
      </strong>
      {" "}
      This dashboard renders the output of an LLM-driven analysis pipeline run
      once per US trading day. Predictions are qualitative outlooks; they are
      not guaranteed and have no track record until enough have accumulated for
      calibration. Make your own decisions; this is one input, not a
      recommendation.
    </div>
  );
}
