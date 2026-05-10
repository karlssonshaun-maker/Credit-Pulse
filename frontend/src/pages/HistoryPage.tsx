import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { format } from "date-fns";
import { Filter, Search, ChevronLeft, ChevronRight, Inbox } from "lucide-react";
import { fetchHistory } from "../api";
import { RecommendationBadge, RiskTierBadge } from "../components/RiskBadge";
import PageHeader from "../components/PageHeader";

const REC_OPTIONS = [
  { value: "", label: "All" },
  { value: "approve", label: "Approve" },
  { value: "review", label: "Review" },
  { value: "decline", label: "Decline" },
];

export default function HistoryPage() {
  const [filters, setFilters] = useState<{
    min_score?: number;
    max_score?: number;
    recommendation?: string;
  }>({});
  const [page, setPage] = useState(1);

  const { data, isLoading } = useQuery({
    queryKey: ["history", filters, page],
    queryFn: () => fetchHistory({ ...filters, page, page_size: 25 }),
  });

  const scoreColour = (s: number) => {
    if (s >= 80) return "text-emerald-600 dark:text-emerald-400";
    if (s >= 65) return "text-green-600 dark:text-green-400";
    if (s >= 50) return "text-amber-600 dark:text-amber-400";
    if (s >= 35) return "text-orange-600 dark:text-orange-400";
    return "text-rose-600 dark:text-rose-400";
  };

  return (
    <div className="p-10 max-w-6xl">
      <PageHeader
        eyebrow="Portfolio"
        title="Assessment history"
        description="Every credit score generated for your lender account."
      />

      <div className="card p-4 mb-5">
        <div className="flex flex-wrap items-end gap-4">
          <div className="flex items-center gap-2 muted text-xs font-semibold tracking-wider uppercase">
            <Filter size={13} /> Filter
          </div>

          <div>
            <label className="label">Min score</label>
            <input
              type="number"
              className="input w-24 tabular-nums"
              value={filters.min_score ?? ""}
              onChange={(e) =>
                setFilters({ ...filters, min_score: Number(e.target.value) || undefined })
              }
            />
          </div>
          <div>
            <label className="label">Max score</label>
            <input
              type="number"
              className="input w-24 tabular-nums"
              value={filters.max_score ?? ""}
              onChange={(e) =>
                setFilters({ ...filters, max_score: Number(e.target.value) || undefined })
              }
            />
          </div>

          <div>
            <label className="label">Recommendation</label>
            <div className="flex gap-1">
              {REC_OPTIONS.map((o) => (
                <button
                  key={o.value}
                  onClick={() => setFilters({ ...filters, recommendation: o.value || undefined })}
                  className={`text-xs font-medium px-3 py-1.5 rounded-lg border transition ${
                    (filters.recommendation ?? "") === o.value
                      ? "bg-brand-gradient text-white border-transparent shadow-card"
                      : "border-ink-200 text-ink-600 hover:border-ink-300 dark:border-ink-700 dark:text-ink-300 dark:hover:border-ink-600"
                  }`}
                >
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          <div className="ml-auto">
            <label className="label flex items-center gap-1.5">
              <Search size={12} /> Search
            </label>
            <input
              type="text"
              placeholder="Business name or reg. no."
              className="input w-56"
              disabled
            />
          </div>
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-ink-50/50 dark:bg-ink-900/40 border-b divider">
              {["Business", "Registration", "Score", "Risk", "Decision", "Assessed"].map((h) => (
                <th
                  key={h}
                  className="text-left px-5 py-3 section-title"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {isLoading &&
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i} className="border-b divider">
                  <td colSpan={6} className="p-3"><div className="skeleton h-8" /></td>
                </tr>
              ))}
            {data?.items.map((item) => (
              <tr
                key={item.id}
                className="border-b divider last:border-0 hover:bg-ink-50/60 dark:hover:bg-ink-900/40 transition"
              >
                <td className="px-5 py-3.5">
                  <Link
                    to={`/score/${item.id}`}
                    className="font-semibold heading hover:text-brand-600 dark:hover:text-brand-400 transition"
                  >
                    {item.business_name}
                  </Link>
                </td>
                <td className="px-5 py-3.5 font-mono text-xs muted">{item.registration_number}</td>
                <td className="px-5 py-3.5">
                  <span className={`text-base font-bold tabular-nums ${scoreColour(item.score)}`}>
                    {item.score}
                  </span>
                </td>
                <td className="px-5 py-3.5">
                  <RiskTierBadge tier={item.risk_tier} />
                </td>
                <td className="px-5 py-3.5">
                  <RecommendationBadge recommendation={item.recommendation} />
                </td>
                <td className="px-5 py-3.5 text-xs muted">
                  {format(new Date(item.requested_at), "dd MMM yyyy · HH:mm")}
                </td>
              </tr>
            ))}
            {data?.items.length === 0 && (
              <tr>
                <td colSpan={6} className="p-16 text-center">
                  <div className="inline-flex flex-col items-center gap-2 muted">
                    <Inbox size={28} />
                    <div className="text-sm">No assessments match your filters.</div>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {data && data.total > data.page_size && (
        <div className="flex justify-between items-center mt-4 text-sm">
          <span className="muted">
            Showing{" "}
            <span className="font-semibold heading">
              {(data.page - 1) * data.page_size + 1}–
              {Math.min(data.page * data.page_size, data.total)}
            </span>{" "}
            of <span className="font-semibold heading">{data.total}</span>
          </span>
          <div className="flex gap-2">
            <button
              disabled={page === 1}
              onClick={() => setPage(page - 1)}
              className="btn-ghost px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft size={15} /> Previous
            </button>
            <button
              disabled={page * data.page_size >= data.total}
              onClick={() => setPage(page + 1)}
              className="btn-ghost px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              Next <ChevronRight size={15} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
