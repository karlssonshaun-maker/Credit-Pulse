# CreditPulse SA — Scoring Methodology

*Written for credit committees, not developers. A plain-English walk-through of every signal the score is built from, why we weighted each one the way we did, and how the final number is assembled.*

---

## 1. What the score means

A CreditPulse score is a number from **0 to 100** indicating the estimated creditworthiness of a South African SME. Higher is better. The score is always accompanied by:

- a **risk tier**: Very Low / Low / Medium / High / Very High
- a **recommendation**: Approve / Review / Decline
- a **confidence** level: Low / Medium / High (based on how many data sources were reachable)

The score is **rule-based**, not a machine-learning model. This is a deliberate choice for this stage of the product — every contribution to the number can be traced to a specific signal with a plain-English explanation a credit analyst can read.

---

## 2. The four signal categories and their weights

| Category              | Weight | What it measures                                        |
|-----------------------|--------|---------------------------------------------------------|
| Business Stability    | 30%    | How real, how old, and how compliant the business is    |
| Cash Flow Health      | 35%    | Revenue, consistency, bank behaviour                    |
| Revenue Quality       | 20%    | Customer base, concentration risk, payment speed        |
| Debt & Obligations    | 15%    | Existing credit obligations and adverse history         |

Cash flow is the single largest category because — especially for SMEs that are too young or too small to have a meaningful bureau footprint — how money actually moves through the business is the most predictive signal we have.

---

## 3. Every signal explained

### Business Stability (30% / 30 pts)

**Trading age (10 pts)** — Businesses under 1 year old get 0; 1–2 years get ~10; 2–5 years get ~20; 5+ years get full 30. Sourced from CIPC registration date. Why weighted heavily: survival rates climb sharply after year two.

**CIPC status (8 pts)** — Active gets full weight. Deregistered or in-liquidation scores zero AND triggers a hard penalty multiplier (see §5) — we will not score these as even "medium risk" regardless of everything else.

**VAT registration (2 pts)** — If the business is VAT-registered with SARS, it passed the R1m turnover threshold — a structural indicator of scale. Small weight because plenty of legitimate SMEs operate below that threshold.

**SARS tax compliance (8 pts)** — Compliant gets full 8. Non-compliant gets 0 and a 25% penalty multiplier applied to the final score. Why weighted heavily: tax non-compliance is one of the strongest leading indicators of cash-flow distress in SA SMEs.

**Director history (2 pts)** — Checks for prior liquidations, sequestrations, or adverse findings against directors. Small weight because each individual flag is worth investigating but not decisive.

### Cash Flow Health (35% / 35 pts)

**Average monthly revenue (8 pts)** — Bucketed: <R20k scores 15%, R20k–R100k scores 45%, R100k–R500k scores 75%, R500k+ scores full. Why: repayment capacity is a direct function of revenue volume.

**Revenue consistency (8 pts)** — Coefficient of variation of monthly revenue over the period. CV < 0.3 is excellent (full weight), 0.3–0.6 good, 0.6–1.0 variable, above 1.0 erratic. Why: seasonal businesses can still pay — but chaotic revenue makes debt service unpredictable.

**Positive cash-flow months (7 pts)** — What percentage of the last 12 months had net positive cash flow. Scored linearly. Why: tells you whether the business is self-sustaining or burning reserves.

**Average bank balance (5 pts)** — 3-month average closing balance as a ratio of monthly revenue. <5% of turnover is very thin, >50% is strong reserves. Why: a shock-absorber metric.

**Debit-order bounce rate (4 pts)** — Percentage of debit orders that bounced in the last 6 months. <1% is clean; >15% is severe. Why: the most direct early-warning signal of payment distress we can observe.

**Salary-run regularity (3 pts)** — Did the business pay staff on a recurring monthly pattern? Signals a real operating business with staff obligations.

### Revenue Quality (20% / 20 pts)

**Revenue source diversity (6 pts)** — Count of distinct payers in the last 6 months. 1 payer = concentration risk (scored 10%), 10+ = well diversified (full weight).

**Largest client concentration (5 pts)** — What percentage of revenue comes from a single customer. <20% is well distributed, >60% is severe concentration — if they lose that client the business fails.

**Repeat customer rate (5 pts)** — Percentage of payers who appear in multiple months. High stickiness indicates recurring revenue. Low means project- or one-off-based revenue, which is harder to lend against.

**Invoice payment lag (4 pts)** — Average days between invoice and payment. ≤15 days is excellent; >60 days indicates working-capital stress on the business.

### Debt & Obligations (15% / 15 pts)

**Credit bureau score (6 pts)** — Normalised from TransUnion commercial score (0–1000 scale). We do not over-weight this because many SA SMEs have thin bureau files — alternative signals carry more information for us than bureau score does.

**Existing loan obligations (3 pts)** — Detected from recurring debit-order patterns in the bank statement. Higher ratio to revenue = less headroom for new debt.

**Debt service coverage (3 pts)** — Monthly revenue divided by monthly debt service. ≥10× is very strong, <2× is stressed.

**Judgements & adverse listings (3 pts)** — Any judgements, defaults, or administration orders on record. Zero = full weight; 3+ triggers a hard penalty multiplier.

---

## 4. Signal behaviour when data is missing

Every signal returns `available: false` and zero points when its underlying data can't be fetched. The **confidence** field on the response drops accordingly:

- 4/4 sources reachable → `high` confidence
- 3/4 including bank statement → `high`
- 2 sources → `medium`
- Only 1 source → `low`

A lender should treat a `low` confidence score as directional rather than dispositive.

---

## 5. Hard-penalty multipliers

After signals sum, the following multipliers apply if triggered (they compound):

| Trigger                               | Multiplier |
|---------------------------------------|------------|
| CIPC deregistered                     | 0.30       |
| CIPC in liquidation                   | 0.20       |
| SARS tax non-compliant                | 0.75       |
| Director adverse history              | 0.85       |
| 3+ adverse credit listings            | 0.70       |

These exist because some findings are categorically disqualifying regardless of other signals. A deregistered business cannot pay you back irrespective of cash flow.

---

## 6. Risk tiers and recommendations

After multipliers, the final 0–100 score maps as:

| Score   | Risk Tier   | Default Recommendation |
|---------|-------------|------------------------|
| 80–100  | Very Low    | Approve                |
| 65–79   | Low         | Approve                |
| 50–64   | Medium      | Review                 |
| 35–49   | High        | Decline                |
| 0–34    | Very High   | Decline                |

If a **loan amount** is provided, the recommendation is additionally stressed:
- If the monthly payment exceeds 50% of revenue, a Low-tier score is downgraded to Medium (Review).
- If it exceeds 75% of revenue, the tier drops to High (Decline) regardless of the raw score.

This prevents a strong business from being approved for a loan it structurally cannot service.

---

## 7. What the score does **not** do

- **It does not decide your credit policy.** The recommendation is guidance. Your own affordability rules, exposure limits, and relationship factors come first.
- **It does not replace a human analyst for complex cases.** For large or unusual applications, use the signal breakdown as a checklist, not a verdict.
- **It is not a prediction of default probability.** It is an ordinal ranking — higher scores are likelier to repay than lower scores — not a calibrated PD. We will introduce a calibrated ML-based PD once we have sufficient labelled repayment outcomes from partner lenders.

---

## 8. Change management

When we change signal weights, add new signals, or adjust penalty multipliers:

- We version the scoring model (`score_model_version` will appear on responses in a future release).
- Existing scores in your history remain unchanged — they were the score at the time.
- Major changes (>5% shift in average score across our portfolio) are pre-announced with 30 days' notice to partner lenders.

Transparency on the scoring logic is the product. If you ever want to understand why any specific score came out as it did, the signal breakdown in the response is the full story.
