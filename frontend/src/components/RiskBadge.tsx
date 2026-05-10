import type { Recommendation, RiskTier } from "../types";

const TIER_STYLES: Record<RiskTier, { bg: string; dot: string; label: string }> = {
  very_low: {
    bg:
      "bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30",
    dot: "bg-emerald-500",
    label: "Very Low Risk",
  },
  low: {
    bg:
      "bg-green-50 text-green-700 border-green-200 dark:bg-green-500/10 dark:text-green-300 dark:border-green-500/30",
    dot: "bg-green-500",
    label: "Low Risk",
  },
  medium: {
    bg:
      "bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30",
    dot: "bg-amber-500",
    label: "Medium Risk",
  },
  high: {
    bg:
      "bg-orange-50 text-orange-700 border-orange-200 dark:bg-orange-500/10 dark:text-orange-300 dark:border-orange-500/30",
    dot: "bg-orange-500",
    label: "High Risk",
  },
  very_high: {
    bg:
      "bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:border-rose-500/30",
    dot: "bg-rose-500",
    label: "Very High Risk",
  },
};

const REC_STYLES: Record<Recommendation, string> = {
  approve:
    "bg-emerald-600 text-white shadow-[0_4px_12px_-2px_rgb(5_150_105_/_0.4)]",
  review:
    "bg-amber-500 text-white shadow-[0_4px_12px_-2px_rgb(217_119_6_/_0.4)]",
  decline:
    "bg-rose-600 text-white shadow-[0_4px_12px_-2px_rgb(225_29_72_/_0.4)]",
};

export function RiskTierBadge({ tier }: { tier: RiskTier }) {
  const s = TIER_STYLES[tier];
  return (
    <span className={`chip ${s.bg}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {s.label}
    </span>
  );
}

export function RecommendationBadge({
  recommendation,
}: {
  recommendation: Recommendation;
}) {
  return (
    <span
      className={`inline-flex items-center text-xs font-bold tracking-wider uppercase px-3 py-1.5 rounded-lg ${REC_STYLES[recommendation]}`}
    >
      {recommendation}
    </span>
  );
}
