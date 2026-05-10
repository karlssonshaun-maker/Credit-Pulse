import { useLocation, useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useRef } from "react";
import {
  Download,
  Check,
  X,
  ArrowLeft,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  Clock,
  Calendar,
  Building2,
} from "lucide-react";
import { fetchScore } from "../api";
import type { ScoreResponse } from "../types";
import ScoreGauge from "../components/ScoreGauge";
import SignalList from "../components/SignalList";
import { RecommendationBadge, RiskTierBadge } from "../components/RiskBadge";

export default function ResultPage() {
  const { id } = useParams<{ id: string }>();
  const location = useLocation();
  const cached = location.state as ScoreResponse | undefined;

  const { data, isLoading, error } = useQuery({
    queryKey: ["score", id],
    queryFn: () => fetchScore(id!),
    enabled: !!id,
    initialData: cached && cached.scoring_request_id === id ? cached : undefined,
  });

  const printRef = useRef<HTMLDivElement>(null);

  if (isLoading && !data) {
    return (
      <div className="p-10 max-w-6xl">
        <div className="skeleton h-10 w-80 mb-6" />
        <div className="grid grid-cols-3 gap-6">
          <div className="skeleton h-64" />
          <div className="skeleton h-64 col-span-2" />
        </div>
      </div>
    );
  }
  if (error) {
    return <div className="p-10 text-rose-600">Failed to load result.</div>;
  }
  if (!data) return null;

  const exportPdf = () => window.print();

  return (
    <div className="p-10 max-w-6xl" ref={printRef}>
      <Link
        to="/history"
        className="inline-flex items-center gap-1.5 text-xs font-medium muted hover:heading mb-4 transition print:hidden"
      >
        <ArrowLeft size={14} /> Back to history
      </Link>

      <header className="flex items-start justify-between mb-8 gap-6">
        <div className="flex items-start gap-4">
          <div className="w-12 h-12 rounded-xl bg-brand-gradient-soft dark:bg-brand-500/10 border border-brand-100 dark:border-brand-500/20 flex items-center justify-center text-brand-600 dark:text-brand-300 shrink-0">
            <Building2 size={22} strokeWidth={2} />
          </div>
          <div>
            <h1 className="text-3xl font-bold tracking-tight heading">{data.business.name}</h1>
            <div className="muted mt-1 flex items-center flex-wrap gap-x-3 gap-y-1 text-sm">
              <span className="font-mono">{data.business.registration_number}</span>
              {data.business.industry && (
                <>
                  <span className="text-ink-300 dark:text-ink-700">·</span>
                  <span>{data.business.industry}</span>
                </>
              )}
              {data.business.province && (
                <>
                  <span className="text-ink-300 dark:text-ink-700">·</span>
                  <span>{data.business.province.replace("_", " ")}</span>
                </>
              )}
            </div>
          </div>
        </div>
        <button onClick={exportPdf} className="btn-ghost print:hidden">
          <Download size={15} /> Export PDF
        </button>
      </header>

      <div className="grid grid-cols-3 gap-6 mb-6">
        <div className="card p-8 col-span-1 flex flex-col items-center justify-center text-center">
          <ScoreGauge score={data.score} />
          <div className="mt-5 flex flex-col items-center gap-2.5">
            <RiskTierBadge tier={data.risk_tier} />
            <RecommendationBadge recommendation={data.recommendation} />
          </div>
          <div className="mt-5 pt-4 border-t divider w-full">
            <div className="text-[10px] section-title">Confidence</div>
            <div className="text-sm font-semibold heading uppercase mt-0.5">{data.confidence}</div>
          </div>
        </div>

        <div className="card p-6 col-span-2 flex flex-col">
          <div className="section-title mb-4">Assessment summary</div>

          <div className="grid grid-cols-2 gap-x-6 gap-y-4 mb-5">
            <SummaryStat
              icon={<Calendar size={14} />}
              label="Trading age"
              value={
                data.business.trading_age_months
                  ? `${Math.round((data.business.trading_age_months / 12) * 10) / 10} yrs`
                  : "—"
              }
            />
            <SummaryStat
              icon={<Clock size={14} />}
              label="Processing time"
              value={`${data.processing_ms} ms`}
            />
            <SummaryStat
              icon={<Check size={14} />}
              label="Sources queried"
              value={`${data.data_sources_used.length} of ${
                data.data_sources_used.length + data.data_sources_unavailable.length
              }`}
            />
            <SummaryStat
              icon={<Calendar size={14} />}
              label="Generated"
              value={new Date(data.score_generated_at).toLocaleString()}
            />
          </div>

          <div className="mb-3">
            <div className="section-title mb-2">Data sources</div>
            <div className="flex flex-wrap gap-1.5">
              {data.data_sources_used.map((s) => (
                <span
                  key={s}
                  className="chip bg-emerald-50 text-emerald-700 border-emerald-200
                             dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30"
                >
                  <Check size={11} strokeWidth={3} /> {s}
                </span>
              ))}
              {data.data_sources_unavailable.map((s) => (
                <span
                  key={s}
                  className="chip bg-ink-50 text-ink-500 border-ink-200
                             dark:bg-ink-800/40 dark:text-ink-400 dark:border-ink-700"
                >
                  <X size={11} strokeWidth={3} /> {s}
                </span>
              ))}
            </div>
          </div>

          {data.penalty_notes.length > 0 && (
            <div className="mt-auto p-3.5 bg-amber-50 border border-amber-200 rounded-xl text-sm text-amber-800
                            dark:bg-amber-500/10 dark:border-amber-500/30 dark:text-amber-200
                            flex items-start gap-2.5">
              <AlertTriangle size={16} className="shrink-0 mt-0.5" />
              <div>
                <div className="font-semibold mb-1">Penalty multipliers applied</div>
                {data.penalty_notes.map((n, i) => (
                  <div key={i} className="text-xs">• {n}</div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {(data.top_strengths.length > 0 || data.top_concerns.length > 0) && (
        <div className="grid grid-cols-2 gap-6 mb-6">
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 border border-emerald-200 dark:bg-emerald-500/10 dark:border-emerald-500/30 flex items-center justify-center">
                <TrendingUp size={14} className="text-emerald-600 dark:text-emerald-400" strokeWidth={2.5} />
              </div>
              <h2 className="text-sm font-semibold heading">Top strengths</h2>
            </div>
            <ul className="space-y-3">
              {data.top_strengths.map((s, i) => (
                <li key={i} className="text-sm">
                  <div className="font-semibold heading">{s.name}</div>
                  <div className="body-text mt-0.5">{s.explanation}</div>
                </li>
              ))}
              {data.top_strengths.length === 0 && (
                <li className="text-sm muted">No material strengths detected.</li>
              )}
            </ul>
          </div>
          <div className="card p-6">
            <div className="flex items-center gap-2 mb-4">
              <div className="w-7 h-7 rounded-lg bg-rose-50 border border-rose-200 dark:bg-rose-500/10 dark:border-rose-500/30 flex items-center justify-center">
                <TrendingDown size={14} className="text-rose-600 dark:text-rose-400" strokeWidth={2.5} />
              </div>
              <h2 className="text-sm font-semibold heading">Top concerns</h2>
            </div>
            <ul className="space-y-3">
              {data.top_concerns.length === 0 && (
                <li className="text-sm muted">No material concerns flagged.</li>
              )}
              {data.top_concerns.map((c, i) => (
                <li key={i} className="text-sm">
                  <div className="font-semibold heading">{c.name}</div>
                  <div className="body-text mt-0.5">{c.explanation}</div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      <div className="card p-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-bold heading tracking-tight">Signal breakdown</h2>
          <div className="text-xs muted">19 signals · 4 categories</div>
        </div>
        <SignalList signals={data.signals} />
      </div>
    </div>
  );
}

function SummaryStat({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div>
      <div className="flex items-center gap-1.5 section-title">
        {icon}
        {label}
      </div>
      <div className="text-base font-semibold heading mt-1 tabular-nums">{value}</div>
    </div>
  );
}
