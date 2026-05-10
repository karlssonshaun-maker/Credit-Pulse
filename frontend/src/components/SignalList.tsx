import { ArrowDown, ArrowUp, Minus, HelpCircle } from "lucide-react";
import type { Signal } from "../types";

function iconFor(direction: Signal["direction"]) {
  if (direction === "positive")
    return (
      <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/30 flex items-center justify-center">
        <ArrowUp size={14} className="text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />
      </div>
    );
  if (direction === "negative")
    return (
      <div className="w-7 h-7 rounded-lg bg-rose-50 border border-rose-200 dark:bg-rose-500/10 dark:border-rose-500/30 flex items-center justify-center">
        <ArrowDown size={14} className="text-rose-600 dark:text-rose-400" strokeWidth={2.5} />
      </div>
    );
  if (direction === "unknown")
    return (
      <div className="w-7 h-7 rounded-lg bg-ink-100 border border-ink-200 dark:bg-ink-800 dark:border-ink-700 flex items-center justify-center">
        <HelpCircle size={14} className="text-ink-400" />
      </div>
    );
  return (
    <div className="w-7 h-7 rounded-lg bg-ink-100 border border-ink-200 dark:bg-ink-800 dark:border-ink-700 flex items-center justify-center">
      <Minus size={14} className="text-ink-400" />
    </div>
  );
}

const CATEGORY_META: Record<string, { colour: string; tag: string }> = {
  "Business Stability": { colour: "from-indigo-500 to-violet-500", tag: "30%" },
  "Cash Flow Health": { colour: "from-blue-500 to-cyan-500", tag: "35%" },
  "Revenue Quality": { colour: "from-violet-500 to-fuchsia-500", tag: "20%" },
  "Debt & Obligations": { colour: "from-amber-500 to-rose-500", tag: "15%" },
};

export default function SignalList({ signals }: { signals: Signal[] }) {
  const byCategory = signals.reduce<Record<string, Signal[]>>((acc, s) => {
    (acc[s.category] = acc[s.category] || []).push(s);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      {Object.entries(byCategory).map(([category, items]) => {
        const meta = CATEGORY_META[category] ?? { colour: "from-ink-500 to-ink-400", tag: "" };
        return (
          <div key={category}>
            <div className="flex items-center gap-3 mb-3">
              <div className={`h-5 w-1 rounded-full bg-gradient-to-b ${meta.colour}`} />
              <h3 className="text-sm font-semibold heading">{category}</h3>
              {meta.tag && (
                <span className="text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded bg-ink-100 text-ink-600 dark:bg-ink-800 dark:text-ink-300">
                  {meta.tag} weight
                </span>
              )}
            </div>
            <div className="space-y-2">
              {items.map((s) => {
                const pct = s.weight > 0 ? Math.max(0, Math.min(100, (s.score_contribution / s.weight) * 100)) : 0;
                const barColour =
                  s.direction === "positive"
                    ? "bg-emerald-500"
                    : s.direction === "negative"
                    ? "bg-rose-500"
                    : "bg-ink-300 dark:bg-ink-600";
                return (
                  <div
                    key={s.key}
                    className={`flex items-start gap-3 p-3.5 rounded-xl border transition
                                ${s.available
                                  ? "bg-white border-ink-200 hover:border-ink-300 dark:bg-ink-900/40 dark:border-ink-800 dark:hover:border-ink-700"
                                  : "bg-ink-50/60 border-dashed border-ink-200 dark:bg-ink-900/30 dark:border-ink-800"}`}
                  >
                    {iconFor(s.direction)}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2">
                        <div className="font-medium heading truncate">{s.name}</div>
                        <div className="text-xs font-mono font-medium text-ink-500 dark:text-ink-400 whitespace-nowrap">
                          <span className="heading font-semibold">{s.score_contribution.toFixed(1)}</span>
                          <span className="text-ink-400"> / {s.weight}</span>
                        </div>
                      </div>
                      <div className="text-sm body-text mt-1">{s.explanation}</div>
                      {s.available && (
                        <div className="mt-2 h-1 w-full rounded-full bg-ink-100 dark:bg-ink-800 overflow-hidden">
                          <div
                            className={`h-full ${barColour} rounded-full transition-all duration-500`}
                            style={{ width: `${pct}%` }}
                          />
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })}
    </div>
  );
}
