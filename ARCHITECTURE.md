# CreditPulse SA — Architecture

## Goals

- **Infrastructure positioning** — we score, lenders lend. No capital at risk on our side.
- **Explainable** — every score includes a human-readable signal-level breakdown. No black-box ML in MVP.
- **Fast** — sub-3s per score, even with 4 external enrichments.
- **POPIA-aware** — every scoring request writes to an immutable audit log.
- **Swap-in-ready** — stubbed integrations share the same async client shape as real API clients would.

## Data flow

```
  Lender ─────────▶  POST /v1/score         (X-API-Key)
                          │
                          ▼
           ┌──────────────────────────────────┐
           │ auth middleware verifies key     │
           │ rate-limit check                 │
           └─────────────┬────────────────────┘
                         │
                         ▼
         ┌─────────────────────────────────────┐
         │ scoring service: orchestrator       │
         │                                     │
         │  ┌──────── asyncio.gather ────────┐ │
         │  │                                │ │
         │  ▼     ▼        ▼         ▼       │ │
         │ CIPC  SARS  TransUnion  Bank API  │ │
         │  │    │       │           │       │ │
         │  └───▶ Redis cache check ◀┘       │ │
         │                                    │
         │ Each: 5s timeout, graceful fail    │
         └────────────────┬───────────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │ statement metrics (cached   │
            │ from prior upload, or       │
            │ computed from bank_api)     │
            └─────────────┬───────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │ assemble_features() →       │
            │ FeatureBundle               │
            └─────────────┬───────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │ 19 signal calculators       │
            │ → weight × normalised value │
            │ → score contribution        │
            └─────────────┬───────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │ penalty multipliers         │
            │ (deregistered, liquidation, │
            │  tax non-compliance, etc.)  │
            └─────────────┬───────────────┘
                          │
                          ▼
            ┌─────────────────────────────┐
            │ persist scoring_request,    │
            │ enrichment_results (×N),    │
            │ audit_log, increment quota  │
            │ — single transaction        │
            └─────────────┬───────────────┘
                          │
                          ▼
                    ScoreResponse (JSON)
```

## Components

### API (FastAPI, async)
- **Routes**: `/v1/score`, `/v1/score/{id}`, `/v1/businesses`, `/v1/statements/upload`, `/v1/lenders`, `/v1/lenders/me`, `/v1/history`, `/v1/analytics/overview`, `/health`
- **Middleware**: API-key auth, audit logging, rate limiting (per-minute sliding window)

### Scoring engine
- **Rule-based** — deliberately chosen for MVP because:
  1. Explainable to a credit committee on day one.
  2. Doesn't need a training set — we haven't got enough labelled SA SME data yet.
  3. Easy to swap to gradient-boosted model later (feature pipeline is already isolated in `ml/features.py`).
- **Signals** live in `api/services/signals.py` — each is a pure function `FeatureBundle → SignalResult` returning a normalised value, weight, contribution, direction (positive/neutral/negative), and a plain-English explanation. This is the surface the lender dashboard consumes directly.
- **Penalty multipliers** stack multiplicatively (tax non-compliance × director adverse × severe listings can compound). Capped 0–100 at the end.
- **SHAP readiness**: explainer module returns top 3 drivers in each direction; when we move to an ML model the same `ScoringResult` surface will carry SHAP values instead of rule contributions.

### Enrichment
- `asyncio.gather` runs all sources in parallel.
- Redis is the cache. TTLs: CIPC 24h, SARS 7 days, TransUnion 1h, Bank API 1h.
- Timeout 5s per source. If a source fails, `data_sources_unavailable` tells the lender which signals are missing and downgrades the `confidence` field on the response.
- Every call — cache hit or miss — writes one row into `enrichment_results`.

### Statement parser
- Handles CSV (FNB, Nedbank, Absa, Standard Bank — each has subtly different column shapes) and PDF (via `pdfplumber`).
- Categoriser is regex-based keyword rules — fast, explainable, easy to extend.
- Computes 14 metrics including coefficient of variation of monthly revenue, salary-run regularity, largest-client concentration, detected recurring loan repayments.

### Database (Postgres)
- Tables: `businesses`, `lender_accounts`, `scoring_requests`, `bank_statements`, `enrichment_results`, `audit_log`.
- Heavy use of `JSONB` for `signals`, `raw_transactions`, `computed_metrics`, `enrichment_summary` — lets us evolve the signal shape without migrations.
- Indexes on all foreign keys, lender × time composites for history queries.
- Every scoring write is one DB transaction — either the whole record (score + enrichment rows + audit log + quota increment) persists or nothing does.

### Worker
- Optional `enrichment_worker.py` — reads from `creditpulse:enrichment:queue`, runs enrichment, writes results to `creditpulse:enrichment:result:<job_id>`. Intended for an async / webhook-triggered path in production.

### Frontend
- React 18 + TypeScript + Vite + Tailwind + TanStack Query + Recharts.
- No global state manager beyond Query — all server state is cached and invalidated by key.
- API key lives in `localStorage` (demo simplicity). In prod this would be replaced with OAuth / SAML.

## Tech decisions

| Decision                           | Why                                                                |
|------------------------------------|--------------------------------------------------------------------|
| FastAPI + async                    | Enrichment is I/O-bound; async gets parallelism for free           |
| Rule-based scorer (not ML)         | Explainable + works without training data                          |
| Pydantic v2                        | ~5–10× faster than v1, strict types                                |
| SQLAlchemy 2.0 async               | Future-proof ORM API; works with asyncpg                           |
| JSONB for signals                  | Signal shape will change frequently as we learn                    |
| Redis for cache + queue            | Single dependency covers both; workers need both anyway            |
| pdfplumber                         | Best free tabular PDF parser; SA bank statements are all tables    |
| Single-transaction persistence     | No partial state — audit trail matches what the lender saw         |
| No hardcoded secrets               | Config via env vars; `.env.example` documents required keys        |
| CORS whitelist (dev localhost)     | Configurable for prod via `CORS_ORIGINS`                           |

## Production hardening checklist (post-MVP)

- Replace stubbed integrations with real CIPC / TransUnion / SARS eFiling / Stitch (open banking) clients. The client signatures already match.
- Move API-key hashing to Argon2id.
- Split rate-limit store from in-memory dict to Redis (so it works across multiple API replicas).
- Move seed/migration runner out of the `api` container entrypoint — one-shot init container.
- Add webhook delivery for async scoring.
- Add structured monitoring — Prometheus metrics (request count, latency, source availability), Grafana dashboard.
- WAF + mTLS for the bank-facing endpoints.
