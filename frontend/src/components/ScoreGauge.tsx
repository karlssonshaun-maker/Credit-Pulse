interface Props {
  score: number;
  size?: number;
}

function scoreTheme(score: number): { solid: string; from: string; to: string; label: string } {
  if (score >= 80) return { solid: "#059669", from: "#10b981", to: "#059669", label: "Very Low Risk" };
  if (score >= 65) return { solid: "#16a34a", from: "#22c55e", to: "#16a34a", label: "Low Risk" };
  if (score >= 50) return { solid: "#d97706", from: "#f59e0b", to: "#d97706", label: "Medium Risk" };
  if (score >= 35) return { solid: "#ea580c", from: "#fb923c", to: "#ea580c", label: "High Risk" };
  return { solid: "#dc2626", from: "#f87171", to: "#dc2626", label: "Very High Risk" };
}

export default function ScoreGauge({ score, size = 220 }: Props) {
  const stroke = 14;
  const radius = (size - stroke * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - clamped / 100);
  const theme = scoreTheme(score);
  const gid = `grad-${theme.solid.replace("#", "")}`;

  return (
    <div
      className="inline-flex items-center justify-center relative"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} className="-rotate-90">
        <defs>
          <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={theme.from} />
            <stop offset="100%" stopColor={theme.to} />
          </linearGradient>
          <filter id={`glow-${gid}`} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          className="stroke-ink-200 dark:stroke-ink-800"
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={`url(#${gid})`}
          strokeWidth={stroke}
          strokeLinecap="round"
          fill="none"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          filter={`url(#glow-${gid})`}
          style={{ transition: "stroke-dashoffset 800ms cubic-bezier(0.2, 0.8, 0.2, 1)" }}
        />
      </svg>
      <div className="absolute text-center">
        <div
          className="text-6xl font-bold tabular-nums tracking-tight"
          style={{ color: theme.solid }}
        >
          {clamped}
        </div>
        <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-ink-500 dark:text-ink-400 mt-1">
          out of 100
        </div>
        <div
          className="text-[11px] font-semibold mt-1"
          style={{ color: theme.solid }}
        >
          {theme.label}
        </div>
      </div>
    </div>
  );
}
