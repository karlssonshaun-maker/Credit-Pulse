# CreditPulse SA

Alternative credit scoring infrastructure for South African SMEs. Banks and alternative lenders call the CreditPulse API to get a 0–100 credit score, risk tier, and recommendation in under 3 seconds — based on CIPC, SARS, credit bureau, and bank-statement-derived cash flow signals.

**We score. The bank lends.**

---

## Quick start

```bash
cp .env.example .env
docker compose up --build
```

This starts:

| Service    | Port | URL                                 |
|------------|------|-------------------------------------|
| API        | 8000 | http://localhost:8000/docs          |
| Dashboard  | 3000 | http://localhost:3000               |
| Adminer    | 8080 | http://localhost:8080 (DB UI)       |
| Postgres   | 5432 | creditpulse / creditpulse_dev_only  |
| Redis      | 6379 |                                     |

On first boot the API runs Alembic migrations and seeds 10 sample SA SMEs, 2 demo lender accounts, and 5 pre-computed score results.

### Demo API keys (seeded)

```
cp_demo_fnb_business_key_do_not_use_in_prod
cp_demo_test_bank_key_do_not_use_in_prod
```

### Try the API

```bash
curl -X POST http://localhost:8000/v1/score \
  -H "X-API-Key: cp_demo_fnb_business_key_do_not_use_in_prod" \
  -H "Content-Type: application/json" \
  -d '{
    "registration_number": "2015/001234/07",
    "tax_number": "9012345678",
    "loan_amount_requested": 150000,
    "loan_term_months": 12
  }'
```

---

## Architecture at a glance

```
┌────────────────┐        ┌─────────────────┐       ┌─────────────────┐
│  React/TS      │◀──────▶│  FastAPI        │──────▶│  PostgreSQL     │
│  Dashboard     │  REST  │  (async)        │       │  (businesses,   │
│  (port 3000)   │        │  (port 8000)    │       │   scores, audit)│
└────────────────┘        └────────┬────────┘       └─────────────────┘
                                   │
                                   │ asyncio.gather
                                   ▼
                          ┌───────────────────┐    ┌────────────────┐
                          │ Enrichment layer  │───▶│ Redis cache    │
                          │ CIPC · SARS ·     │    │ (24h / 7d / 1h)│
                          │ TransUnion · Bank │    └────────────────┘
                          └─────────┬─────────┘
                                    │
                                    ▼
                          ┌───────────────────┐
                          │ Rule-based scorer │
                          │ 19 signals,       │
                          │ 4 categories,     │
                          │ penalty mults     │
                          └───────────────────┘
```

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for details.

---

## How scoring works

Each scoring request:

1. **Parallel enrichment** — CIPC business register, SARS compliance, TransUnion bureau, and optionally bank API (all stubbed with realistic synthetic data in MVP) fetch in parallel via `asyncio.gather`. Each has a 5s timeout; if a source fails the score is still returned, flagged with `data_sources_unavailable`.
2. **Statement metrics** — If bank statements are available, compute 12-month revenue arrays, coefficient of variation, positive cash-flow months, bounce rate, largest-client concentration, salary-run regularity, detected loan repayments.
3. **19 rule-based signals** across 4 weighted categories:
   - Business Stability (30%)
   - Cash Flow Health (35%)
   - Revenue Quality (20%)
   - Debt & Obligations (15%)
4. **Hard-penalty multipliers** for CIPC deregistration, liquidation, tax non-compliance, adverse director history, severe bureau listings.
5. **Risk tier + recommendation** derived from final 0–100 score, adjusted for loan amount vs. revenue.

Full methodology in **[SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md)**.

---

## Project structure

```
creditpulse/
├── api/
│   ├── main.py
│   ├── routes/               # score, businesses, statements, lenders, history, analytics
│   ├── models/schemas.py     # Pydantic v2 request/response models
│   ├── services/             # enrichment, scoring, statement_parser, signals, categoriser
│   └── middleware/           # auth, audit, ratelimit
├── db/
│   ├── models.py             # SQLAlchemy 2.0 ORM
│   ├── enums.py              # RiskTier, Recommendation, etc.
│   ├── session.py
│   ├── redis_client.py
│   ├── seed.py
│   └── migrations/           # Alembic
├── workers/enrichment_worker.py
├── integrations/             # cipc, transunion, sars, bank_apis (stubbed)
├── ml/
│   ├── features.py           # FeatureBundle & feature assembly
│   ├── rule_engine.py        # Score calculation + penalty multipliers
│   └── explainer.py          # Top strengths/concerns
└── tests/

frontend/
├── src/
│   ├── pages/                # ScorePage, ResultPage, HistoryPage, AnalyticsPage, SettingsPage
│   ├── components/           # ScoreGauge, RiskBadge, SignalList
│   ├── api.ts
│   └── types.ts
└── ...
```

---

## Local development (without Docker)

```bash
# Backend
python -m venv .venv && source .venv/bin/activate  # (or .venv\Scripts\activate on Windows)
pip install -r requirements.txt

# Start Postgres + Redis yourself, or:
docker compose up -d postgres redis adminer

alembic upgrade head
python -m creditpulse.db.seed
uvicorn creditpulse.api.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

---

## Tests

```bash
pytest
```

Covers:
- Signal calculators (all 19 signals, edge cases, missing-data behaviour)
- Score assembly (penalty application, risk tier boundaries, loan-adjustment logic)
- Bank statement parser (FNB, Nedbank, Absa formats + bounce detection)
- Integration layer (cache hits/misses, timeout degradation)
- Auth (key generation, hashing)

Target: >80% coverage.

---

## Further reading

- **[ARCHITECTURE.md](ARCHITECTURE.md)** — components, data flow, tech decisions
- **[INTEGRATION_GUIDE.md](INTEGRATION_GUIDE.md)** — how a bank integrates the API
- **[SCORING_METHODOLOGY.md](SCORING_METHODOLOGY.md)** — plain-English signal-by-signal explanation for credit committees

---

## License

Proprietary — internal build.
