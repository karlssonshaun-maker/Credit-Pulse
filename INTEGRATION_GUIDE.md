# CreditPulse SA — Integration Guide

For banks and alternative lenders integrating the scoring API.

---

## 1. Getting credentials

Your CreditPulse account manager provisions a **lender account**. You receive:

- **Account name** (e.g. `FNB Business`)
- **API key** — shown once on creation. Format: `cp_<32 chars>`. Store it in your secrets manager.
- **Monthly request quota** — governed by your tier (`trial`, `standard`, `enterprise`).

You can also create a lender account directly for testing:

```bash
curl -X POST http://localhost:8000/v1/lenders \
  -H "Content-Type: application/json" \
  -d '{"name": "Acme Lending", "tier": "standard", "monthly_limit": 1000}'
```

Response includes the raw `api_key` — the only time you will ever see it. We only store a SHA-256 hash of it.

---

## 2. Authentication

Every request must include the key in the `X-API-Key` header:

```
X-API-Key: cp_AbCdEf...
```

No header, or an unknown / deactivated key → **401 Unauthorized**.
Monthly quota exhausted → **429 Too Many Requests**.
Rate-limit exceeded (default 120/min) → **429** with `Retry-After` header.

---

## 3. Scoring a business

### Endpoint

```
POST /v1/score
```

### Request

```json
{
  "registration_number": "2019/123456/07",
  "tax_number": "9876543210",
  "statement_months": 6,
  "loan_amount_requested": 150000,
  "loan_term_months": 12
}
```

| Field                    | Required | Notes                                                            |
|--------------------------|----------|------------------------------------------------------------------|
| `registration_number`    | yes      | CIPC registration in `YYYY/NNNNNN/NN` format                     |
| `tax_number`             | no       | Enables SARS compliance signals (+~8 pts if compliant)           |
| `statement_months`       | no       | How many months of statements to analyse (default 6)             |
| `loan_amount_requested`  | no       | Used for debt-service coverage calculation                       |
| `loan_term_months`       | no       | Paired with `loan_amount_requested`                              |
| `use_mock_bank_api`      | no       | Dev only — generates synthetic bank data when no statement on file |

### Response (200 OK)

```json
{
  "scoring_request_id": "a3b0c5f2-...",
  "score": 74,
  "risk_tier": "medium",
  "recommendation": "review",
  "confidence": "high",
  "business": {
    "name": "Thabo's Electronics CC",
    "registration_number": "2019/123456/07",
    "trading_age_months": 52,
    "industry": "Retail - Electronics",
    "province": "gauteng"
  },
  "signals": [ /* 19 signal objects */ ],
  "top_strengths": [ ... ],
  "top_concerns": [ ... ],
  "penalty_notes": [],
  "data_sources_used": ["cipc", "sars", "transunion", "bank_statement"],
  "data_sources_unavailable": [],
  "processing_ms": 847,
  "score_generated_at": "2026-04-21T10:23:11Z"
}
```

### Retrieving a past score

```
GET /v1/score/{scoring_request_id}
```

Only works if the request was made by **your** lender account.

---

## 4. Uploading bank statements

The scoring engine improves dramatically when real statements are on file. Upload before scoring.

```
POST /v1/statements/upload
Content-Type: multipart/form-data

registration_number: 2019/123456/07
bank_hint: FNB                    (optional — auto-detected if omitted)
file: @statement.csv              (or .pdf)
```

CSV formats supported: **FNB**, **Nedbank**, **Absa**, **Standard Bank**, **Capitec** (best-effort).
PDF: any bank, parsed via `pdfplumber`.

Response contains the computed metrics (revenue array, CV, bounce rate, etc.).

---

## 5. Error codes

| Status | Meaning                                                  |
|--------|----------------------------------------------------------|
| 200    | OK                                                       |
| 201    | Resource created (e.g. lender, business)                 |
| 400    | Bad request — malformed body, empty file, unparseable    |
| 401    | Missing or invalid API key                               |
| 404    | Resource not found                                       |
| 409    | Conflict (e.g. business already exists)                  |
| 422    | Pydantic validation failed (see `detail[]`)              |
| 429    | Rate limit or monthly quota exceeded (honour `Retry-After`) |
| 500    | Unexpected server error — retry with exponential backoff |

---

## 6. Data sources & availability

The API is designed to **degrade gracefully**. If a source times out or errors, the score is still produced with remaining signals — the missing source appears in `data_sources_unavailable` and `confidence` may drop from `high` to `medium` or `low`.

| Source     | TTL cache | What it contributes                                   |
|------------|-----------|-------------------------------------------------------|
| CIPC       | 24h       | Registration status, trading age, director history    |
| SARS       | 7 days    | Tax compliance, VAT status                            |
| TransUnion | 1h        | Commercial score, adverse listings                    |
| Bank statement / open banking | n/a | All cash-flow and revenue-quality signals |

---

## 7. Async scoring (webhooks)

For batch workloads, submit jobs to the enrichment queue. The worker service processes asynchronously and writes results to Redis (production would deliver via webhook to your URL).

*Webhook delivery is wired up but not exposed in the HTTP API yet — contact us for early access.*

---

## 8. History & analytics

```
GET /v1/history?page=1&page_size=25&min_score=50&recommendation=approve
GET /v1/analytics/overview
```

History is scoped to your lender account. Analytics returns distribution, approval-rate time series, industry breakdown, and top decline-driver signals — useful for monitoring model drift and portfolio composition.

---

## 9. Best practices

- **Cache the score on your side** for the duration of a loan application — don't re-score on every page load.
- **Re-score monthly** for performing loans in your book. Consistency and bureau data move.
- **Upload fresh statements** before rescoring — bank data is the most predictive signal category.
- **Don't make approve/decline decisions on score alone** — always combine with your own policy rules. The `recommendation` field is guidance, not a credit mandate.
- **Log the `scoring_request_id`** on your side — it's your audit reference for any downstream POPIA or NCR query.

---

## 10. Support

- Docs: `http://localhost:8000/docs` (OpenAPI / Swagger UI)
- Status: `GET /health`
- Account: `GET /v1/lenders/me`
