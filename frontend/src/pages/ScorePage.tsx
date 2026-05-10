import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { Loader2, Building2, Receipt, Landmark, AlertCircle, Zap, ShieldCheck, Database } from "lucide-react";
import { requestScore } from "../api";
import type { ScoreRequestPayload, ScoreResponse } from "../types";
import PageHeader from "../components/PageHeader";

const SAMPLES = [
  { reg: "2015/001234/07", label: "Retail SME" },
  { reg: "2019/556789/07", label: "Logistics" },
  { reg: "2012/998877/07", label: "Manufacturing" },
];

export default function ScorePage() {
  const navigate = useNavigate();
  const [form, setForm] = useState<ScoreRequestPayload>({
    registration_number: "2015/001234/07",
    tax_number: "9012345678",
    statement_months: 6,
    loan_amount_requested: 150000,
    loan_term_months: 12,
    use_mock_bank_api: true,
  });

  const mutation = useMutation({
    mutationFn: requestScore,
    onSuccess: (data: ScoreResponse) => {
      navigate(`/score/${data.scoring_request_id}`, { state: data });
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    mutation.mutate(form);
  };

  return (
    <div className="p-10 max-w-5xl">
      <PageHeader
        eyebrow="New Assessment"
        title="Score a business"
        description="Enter a CIPC registration number. We pull alternative data across CIPC, SARS, bureau and bank signals — typically in under 3 seconds."
      />

      <div className="grid grid-cols-3 gap-6 mb-6">
        <FeatureTile
          icon={<Zap size={18} />}
          label="Sub-3s response"
          detail="Parallel enrichment across 4 sources"
        />
        <FeatureTile
          icon={<ShieldCheck size={18} />}
          label="Explainable"
          detail="19 signals, fully traceable"
        />
        <FeatureTile
          icon={<Database size={18} />}
          label="POPIA aligned"
          detail="All access is logged and auditable"
        />
      </div>

      <form onSubmit={handleSubmit} className="card p-8 space-y-6">
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label className="label mb-0 flex items-center gap-2">
              <Building2 size={13} /> CIPC registration number
            </label>
            <div className="flex gap-1.5">
              {SAMPLES.map((s) => (
                <button
                  key={s.reg}
                  type="button"
                  onClick={() => setForm({ ...form, registration_number: s.reg })}
                  className="text-[11px] px-2 py-1 rounded-md border border-ink-200 text-ink-600 hover:border-brand-400 hover:text-brand-600
                             dark:border-ink-700 dark:text-ink-300 dark:hover:border-brand-400 dark:hover:text-brand-300 transition"
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <input
            type="text"
            required
            value={form.registration_number}
            onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
            placeholder="2019/123456/07"
            className="input font-mono"
          />
        </div>

        <div>
          <label className="label flex items-center gap-2">
            <Receipt size={13} /> Tax number
            <span className="text-[10px] font-normal normal-case text-ink-400">optional</span>
          </label>
          <input
            type="text"
            value={form.tax_number || ""}
            onChange={(e) => setForm({ ...form, tax_number: e.target.value })}
            placeholder="9876543210"
            className="input font-mono"
          />
        </div>

        <div className="pt-2 border-t divider">
          <div className="section-title mb-4 flex items-center gap-2">
            <Landmark size={13} /> Loan parameters
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Loan amount (ZAR)</label>
              <div className="relative">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-ink-400 text-sm font-medium">R</span>
                <input
                  type="number"
                  value={form.loan_amount_requested ?? ""}
                  onChange={(e) =>
                    setForm({ ...form, loan_amount_requested: Number(e.target.value) || undefined })
                  }
                  className="input pl-8 tabular-nums"
                />
              </div>
            </div>
            <div>
              <label className="label">Term (months)</label>
              <input
                type="number"
                value={form.loan_term_months ?? ""}
                onChange={(e) =>
                  setForm({ ...form, loan_term_months: Number(e.target.value) || undefined })
                }
                className="input tabular-nums"
              />
            </div>
          </div>
        </div>

        {mutation.isError && (
          <div className="p-3.5 bg-rose-50 border border-rose-200 rounded-xl text-sm text-rose-800
                          dark:bg-rose-500/10 dark:border-rose-500/30 dark:text-rose-300
                          flex items-start gap-2.5">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <div>
              {(mutation.error as any)?.response?.data?.detail ||
                "Request failed — check your API key in Settings."}
            </div>
          </div>
        )}

        <button type="submit" disabled={mutation.isPending} className="btn-primary w-full py-3">
          {mutation.isPending ? (
            <>
              <Loader2 className="animate-spin" size={18} /> Scoring business…
            </>
          ) : (
            <>
              <Zap size={17} strokeWidth={2.4} /> Generate credit score
            </>
          )}
        </button>
      </form>
    </div>
  );
}

function FeatureTile({
  icon,
  label,
  detail,
}: {
  icon: React.ReactNode;
  label: string;
  detail: string;
}) {
  return (
    <div className="card p-4 flex items-start gap-3">
      <div className="w-9 h-9 rounded-lg bg-brand-gradient-soft dark:bg-brand-500/10 border border-brand-100 dark:border-brand-500/20 flex items-center justify-center text-brand-600 dark:text-brand-300">
        {icon}
      </div>
      <div>
        <div className="text-sm font-semibold heading">{label}</div>
        <div className="text-xs muted mt-0.5">{detail}</div>
      </div>
    </div>
  );
}
