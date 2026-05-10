import { useQuery } from "@tanstack/react-query";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { TrendingUp, TrendingDown, Briefcase, Percent, Gauge } from "lucide-react";
import { fetchAnalytics } from "../api";
import PageHeader from "../components/PageHeader";
import { useTheme } from "../theme";

export default function AnalyticsPage() {
  const { theme } = useTheme();
  const { data, isLoading } = useQuery({ queryKey: ["analytics"], queryFn: fetchAnalytics });

  if (isLoading) {
    return (
      <div className="p-10 max-w-6xl">
        <div className="skeleton h-10 w-72 mb-8" />
        <div className="grid grid-cols-3 gap-6 mb-6">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="skeleton h-28" />
          ))}
        </div>
        <div className="skeleton h-64" />
      </div>
    );
  }
  if (!data) return null;

  const grid = theme === "dark" ? "#1e293b" : "#e2e8f0";
  const axis = theme === "dark" ? "#64748b" : "#94a3b8";
  const tooltipStyle = {
    backgroundColor: theme === "dark" ? "#0f172a" : "#ffffff",
    border: `1px solid ${theme === "dark" ? "#1e293b" : "#e2e8f0"}`,
    borderRadius: 12,
    fontSize: 12,
    color: theme === "dark" ? "#e2e8f0" : "#0f172a",
    boxShadow: "0 10px 15px -3px rgb(15 23 42 / 0.1)",
  };

  return (
    <div className="p-10 max-w-6xl">
      <PageHeader
        eyebrow="Insights"
        title="Portfolio analytics"
        description="Patterns across every score you've generated."
      />

      <div className="grid grid-cols-3 gap-6 mb-6">
        <KpiCard
          icon={<Gauge size={18} />}
          label="Total assessments"
          value={data.total_assessments}
          accent="from-indigo-500 to-violet-500"
        />
        <KpiCard
          icon={<Percent size={18} />}
          label="Approval rate"
          value={`${Math.round(data.approval_rate * 100)}%`}
          trend={data.approval_rate > 0.5 ? "up" : "down"}
          accent="from-emerald-500 to-teal-500"
        />
        <KpiCard
          icon={<Briefcase size={18} />}
          label="Industries covered"
          value={data.average_score_by_industry.length}
          accent="from-fuchsia-500 to-pink-500"
        />
      </div>

      <div className="grid grid-cols-2 gap-6 mb-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold heading tracking-tight">Score distribution</h2>
            <span className="text-xs muted">by score band</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={data.score_distribution} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#6366f1" stopOpacity={1} />
                  <stop offset="100%" stopColor="#8b5cf6" stopOpacity={0.6} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={grid} vertical={false} />
              <XAxis dataKey="range" tick={{ fontSize: 11, fill: axis }} axisLine={false} tickLine={false} />
              <YAxis
                allowDecimals={false}
                tick={{ fontSize: 11, fill: axis }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip cursor={{ fill: theme === "dark" ? "#1e293b66" : "#f1f5f9" }} contentStyle={tooltipStyle} />
              <Bar dataKey="count" fill="url(#barGrad)" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold heading tracking-tight">Approval rate</h2>
            <span className="text-xs muted">over time</span>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <LineChart
              data={data.approval_rate_over_time}
              margin={{ top: 8, right: 10, left: -10, bottom: 0 }}
            >
              <defs>
                <linearGradient id="lineGrad" x1="0" y1="0" x2="1" y2="0">
                  <stop offset="0%" stopColor="#10b981" />
                  <stop offset="100%" stopColor="#059669" />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke={grid} vertical={false} />
              <XAxis dataKey="date" tick={{ fontSize: 11, fill: axis }} axisLine={false} tickLine={false} />
              <YAxis
                domain={[0, 1]}
                tickFormatter={(v) => `${Math.round(v * 100)}%`}
                tick={{ fontSize: 11, fill: axis }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(v: number) => `${Math.round(v * 100)}%`}
                contentStyle={tooltipStyle}
              />
              <Line
                type="monotone"
                dataKey="approval_rate"
                stroke="url(#lineGrad)"
                strokeWidth={2.5}
                dot={{ r: 3, fill: "#10b981", strokeWidth: 0 }}
                activeDot={{ r: 5, fill: "#10b981", stroke: "white", strokeWidth: 2 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold heading tracking-tight">Average score by industry</h2>
            <span className="text-xs muted">top performers</span>
          </div>
          <div className="space-y-3">
            {data.average_score_by_industry.map((i) => {
              const pct = Math.max(0, Math.min(100, i.average_score));
              return (
                <div key={i.industry}>
                  <div className="flex items-center justify-between text-sm mb-1.5">
                    <div className="body-text font-medium">{i.industry}</div>
                    <div className="flex items-center gap-3">
                      <span className="muted text-xs tabular-nums">{i.count} assessed</span>
                      <span className="font-bold heading tabular-nums">{i.average_score.toFixed(1)}</span>
                    </div>
                  </div>
                  <div className="h-2 rounded-full bg-ink-100 dark:bg-ink-800 overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-brand-500 to-accent-500 rounded-full"
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
            {data.average_score_by_industry.length === 0 && (
              <div className="text-sm muted">No data yet.</div>
            )}
          </div>
        </div>

        <div className="card p-6">
          <div className="flex items-center justify-between mb-5">
            <h2 className="font-bold heading tracking-tight">Top decline drivers</h2>
            <span className="text-xs muted">signals behind declines</span>
          </div>
          <div className="space-y-2">
            {data.top_negative_signals.map((s, idx) => (
              <div
                key={s.signal}
                className="flex items-center justify-between p-3 rounded-xl bg-rose-50/50 border border-rose-100
                           dark:bg-rose-500/5 dark:border-rose-500/20"
              >
                <div className="flex items-center gap-3">
                  <div className="w-7 h-7 rounded-lg bg-rose-100 text-rose-700 font-bold text-xs flex items-center justify-center
                                  dark:bg-rose-500/20 dark:text-rose-300">
                    {idx + 1}
                  </div>
                  <div className="text-sm body-text font-medium">{s.signal}</div>
                </div>
                <span className="text-sm font-bold text-rose-700 dark:text-rose-300 tabular-nums">
                  {s.count}×
                </span>
              </div>
            ))}
            {data.top_negative_signals.length === 0 && (
              <div className="text-sm muted">No declines yet.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function KpiCard({
  icon,
  label,
  value,
  trend,
  accent,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  trend?: "up" | "down";
  accent: string;
}) {
  return (
    <div className="card p-6 relative overflow-hidden">
      <div className={`absolute top-0 left-0 right-0 h-1 bg-gradient-to-r ${accent}`} />
      <div className="flex items-start justify-between">
        <div
          className={`w-10 h-10 rounded-xl bg-gradient-to-br ${accent} text-white flex items-center justify-center shadow-card`}
        >
          {icon}
        </div>
        {trend && (
          <div
            className={`flex items-center gap-1 text-xs font-semibold ${
              trend === "up"
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-rose-600 dark:text-rose-400"
            }`}
          >
            {trend === "up" ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
            vs prior
          </div>
        )}
      </div>
      <div className="section-title mt-4">{label}</div>
      <div className="text-3xl font-bold heading mt-1 tabular-nums tracking-tight">{value}</div>
    </div>
  );
}
