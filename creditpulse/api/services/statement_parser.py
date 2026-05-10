from __future__ import annotations

import csv
import hashlib
import io
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
from typing import Dict, List, Optional, Tuple

from creditpulse.api.services.transaction_categoriser import (
    TransactionCategory,
    categorise,
    extract_counterparty,
    is_bounced_debit,
)


@dataclass
class Transaction:
    date: str
    description: str
    amount: float
    balance: Optional[float]
    category: str
    counterparty: Optional[str]
    bounced: bool = False


@dataclass
class StatementMetrics:
    bank_name: Optional[str]
    period_start: Optional[str]
    period_end: Optional[str]
    transaction_count: int
    monthly_revenue: List[float]
    monthly_expenses: List[float]
    monthly_net_cashflow: List[float]
    average_monthly_revenue: float
    revenue_coefficient_of_variation: float
    positive_cash_flow_months_ratio: float
    months_with_negative_cashflow: int
    average_closing_balance_3m: float
    largest_single_income_source: float
    largest_client_concentration: float
    revenue_source_diversity: int
    repeat_customer_rate: float
    bounced_debit_count: int
    bounce_rate: float
    salary_run_regularity: bool
    detected_salary_amount: Optional[float]
    detected_loan_repayments_monthly: float
    detected_loan_repayments: List[Dict]
    invoice_payment_lag_days: Optional[float]
    category_totals: Dict[str, float]


BANK_DETECTORS: List[Tuple[str, re.Pattern]] = [
    ("FNB", re.compile(r"\b(fnb|first national bank)\b", re.I)),
    ("Nedbank", re.compile(r"\bnedbank\b", re.I)),
    ("Absa", re.compile(r"\babsa\b", re.I)),
    ("Standard Bank", re.compile(r"\b(standard bank|standardbank)\b", re.I)),
    ("Capitec", re.compile(r"\bcapitec\b", re.I)),
]

BANK_COLUMN_PROFILES: Dict[str, Dict[str, List[str]]] = {
    "FNB": {
        "date": ["date", "transaction date"],
        "description": ["description", "details"],
        "amount": ["amount"],
        "balance": ["balance"],
    },
    "Nedbank": {
        "date": ["date", "transaction date"],
        "description": ["description", "narrative"],
        "amount": ["amount"],
        "balance": ["balance", "running balance"],
    },
    "Absa": {
        "date": ["date", "transaction date"],
        "description": ["description", "transaction description"],
        "amount": ["amount"],
        "balance": ["balance"],
    },
    "Standard Bank": {
        "date": ["date", "transaction date"],
        "description": ["description", "reference"],
        "amount": ["amount", "debit", "credit"],
        "balance": ["balance", "running balance"],
    },
}

DEFAULT_PROFILE = {
    "date": ["date", "transaction date", "posting date", "txn date"],
    "description": ["description", "details", "narrative", "reference"],
    "amount": ["amount", "transaction amount"],
    "debit": ["debit", "debits", "money out"],
    "credit": ["credit", "credits", "money in"],
    "balance": ["balance", "running balance", "closing balance"],
}


def compute_file_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def detect_bank(sample_text: str) -> Optional[str]:
    for bank, pattern in BANK_DETECTORS:
        if pattern.search(sample_text):
            return bank
    return None


def _parse_amount(raw: str) -> float:
    if raw is None:
        return 0.0
    cleaned = str(raw).strip().replace(",", "").replace("R", "").replace(" ", "")
    if not cleaned or cleaned in ("-", "--"):
        return 0.0
    negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        negative = True
        cleaned = cleaned[1:-1]
    try:
        val = float(cleaned)
        return -val if negative else val
    except ValueError:
        return 0.0


def _parse_date(raw: str) -> Optional[str]:
    if not raw:
        return None
    raw = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y", "%d %B %Y", "%d/%m/%y", "%Y%m%d"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _find_column(headers: List[str], candidates: List[str]) -> Optional[int]:
    lowered = [h.strip().lower() for h in headers]
    for idx, h in enumerate(lowered):
        for cand in candidates:
            if h == cand or cand in h:
                return idx
    return None


def parse_csv(content: bytes, bank_hint: Optional[str] = None) -> Tuple[List[Transaction], Optional[str]]:
    text = content.decode("utf-8-sig", errors="ignore")
    sample = text[:2000]
    bank = bank_hint or detect_bank(sample)
    profile = BANK_COLUMN_PROFILES.get(bank or "", DEFAULT_PROFILE) if bank else DEFAULT_PROFILE

    reader = csv.reader(io.StringIO(text))
    rows = [row for row in reader if row]
    if not rows:
        return [], bank

    header_idx = 0
    for i, row in enumerate(rows[:10]):
        joined = " ".join(row).lower()
        if any(cand in joined for cand in ("date", "description", "amount", "balance")):
            header_idx = i
            break

    headers = rows[header_idx]
    data_rows = rows[header_idx + 1:]

    date_col = _find_column(headers, profile.get("date", DEFAULT_PROFILE["date"]))
    desc_col = _find_column(headers, profile.get("description", DEFAULT_PROFILE["description"]))
    amount_col = _find_column(headers, profile.get("amount", DEFAULT_PROFILE["amount"]))
    debit_col = _find_column(headers, DEFAULT_PROFILE["debit"])
    credit_col = _find_column(headers, DEFAULT_PROFILE["credit"])
    balance_col = _find_column(headers, profile.get("balance", DEFAULT_PROFILE["balance"]))

    transactions: List[Transaction] = []
    for row in data_rows:
        if not row or len(row) < 2:
            continue
        date_val = _parse_date(row[date_col]) if date_col is not None and date_col < len(row) else None
        description = row[desc_col].strip() if desc_col is not None and desc_col < len(row) else ""
        if not date_val:
            continue

        amount = 0.0
        if amount_col is not None and amount_col < len(row):
            amount = _parse_amount(row[amount_col])
        elif debit_col is not None or credit_col is not None:
            debit_val = _parse_amount(row[debit_col]) if debit_col is not None and debit_col < len(row) else 0.0
            credit_val = _parse_amount(row[credit_col]) if credit_col is not None and credit_col < len(row) else 0.0
            amount = credit_val - abs(debit_val)

        balance = None
        if balance_col is not None and balance_col < len(row):
            balance = _parse_amount(row[balance_col])

        bounced = is_bounced_debit(description)
        category = categorise(description, amount)
        if bounced:
            category = TransactionCategory.FEES

        transactions.append(
            Transaction(
                date=date_val,
                description=description,
                amount=round(amount, 2),
                balance=balance,
                category=category.value,
                counterparty=extract_counterparty(description),
                bounced=bounced,
            )
        )

    return transactions, bank


def parse_pdf(content: bytes, bank_hint: Optional[str] = None) -> Tuple[List[Transaction], Optional[str]]:
    try:
        import pdfplumber
    except ImportError:
        return [], bank_hint

    transactions: List[Transaction] = []
    bank = bank_hint
    with pdfplumber.open(io.BytesIO(content)) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text() or ""
            full_text += text + "\n"
            if bank is None:
                bank = detect_bank(text)
            for table in page.extract_tables() or []:
                if not table or len(table) < 2:
                    continue
                headers = [str(c or "").strip() for c in table[0]]
                date_col = _find_column(headers, DEFAULT_PROFILE["date"])
                desc_col = _find_column(headers, DEFAULT_PROFILE["description"])
                amount_col = _find_column(headers, DEFAULT_PROFILE["amount"])
                balance_col = _find_column(headers, DEFAULT_PROFILE["balance"])
                if date_col is None or desc_col is None:
                    continue
                for row in table[1:]:
                    if not row:
                        continue
                    row = [str(c or "").strip() for c in row]
                    date_val = _parse_date(row[date_col]) if date_col < len(row) else None
                    description = row[desc_col] if desc_col < len(row) else ""
                    if not date_val:
                        continue
                    amount = _parse_amount(row[amount_col]) if amount_col is not None and amount_col < len(row) else 0.0
                    balance = _parse_amount(row[balance_col]) if balance_col is not None and balance_col < len(row) else None
                    bounced = is_bounced_debit(description)
                    category = categorise(description, amount)
                    if bounced:
                        category = TransactionCategory.FEES
                    transactions.append(
                        Transaction(
                            date=date_val,
                            description=description,
                            amount=round(amount, 2),
                            balance=balance,
                            category=category.value,
                            counterparty=extract_counterparty(description),
                            bounced=bounced,
                        )
                    )

    return transactions, bank


def _month_key(iso_date: str) -> str:
    return iso_date[:7]


def _coefficient_of_variation(values: List[float]) -> float:
    if not values:
        return 0.0
    mean = statistics.mean(values)
    if mean == 0:
        return 0.0
    stdev = statistics.pstdev(values) if len(values) > 1 else 0.0
    return stdev / abs(mean)


def _detect_salary_runs(transactions: List[Transaction]) -> Tuple[bool, Optional[float]]:
    salary_by_month: Dict[str, float] = defaultdict(float)
    for tx in transactions:
        if tx.category == TransactionCategory.SALARY.value and tx.amount < 0:
            salary_by_month[_month_key(tx.date)] += abs(tx.amount)

    if len(salary_by_month) < 3:
        return False, None

    values = list(salary_by_month.values())
    avg = statistics.mean(values)
    cv = _coefficient_of_variation(values)
    regular = cv < 0.3 and avg > 1000
    return regular, round(avg, 2) if regular else None


def _detect_loan_repayments(transactions: List[Transaction]) -> Tuple[float, List[Dict]]:
    by_counterparty: Dict[str, List[Transaction]] = defaultdict(list)
    for tx in transactions:
        if tx.category == TransactionCategory.DEBT_SERVICE.value and tx.amount < 0 and tx.counterparty:
            by_counterparty[tx.counterparty.lower()].append(tx)

    detected: List[Dict] = []
    for counterparty, txs in by_counterparty.items():
        months_hit = {_month_key(t.date) for t in txs}
        if len(months_hit) >= 3:
            avg = statistics.mean([abs(t.amount) for t in txs])
            detected.append({
                "counterparty": counterparty,
                "monthly_amount": round(avg, 2),
                "months_observed": len(months_hit),
            })

    monthly_total = sum(d["monthly_amount"] for d in detected)
    return round(monthly_total, 2), detected


def _invoice_payment_lag(transactions: List[Transaction]) -> Optional[float]:
    invoice_dates: List[date] = []
    payment_dates: List[date] = []
    for tx in transactions:
        d = datetime.fromisoformat(tx.date).date()
        desc = tx.description.lower()
        if "invoice" in desc and tx.amount < 0:
            invoice_dates.append(d)
        elif tx.category == TransactionCategory.INCOME.value and ("inv" in desc or "invoice" in desc):
            payment_dates.append(d)
    if not invoice_dates or not payment_dates:
        return None
    lags = []
    for pay_d in payment_dates:
        candidates = [inv for inv in invoice_dates if inv <= pay_d]
        if candidates:
            nearest = max(candidates)
            lags.append((pay_d - nearest).days)
    if not lags:
        return None
    return round(statistics.mean(lags), 1)


def compute_metrics(transactions: List[Transaction], bank: Optional[str] = None) -> StatementMetrics:
    if not transactions:
        return StatementMetrics(
            bank_name=bank, period_start=None, period_end=None, transaction_count=0,
            monthly_revenue=[], monthly_expenses=[], monthly_net_cashflow=[],
            average_monthly_revenue=0.0, revenue_coefficient_of_variation=0.0,
            positive_cash_flow_months_ratio=0.0, months_with_negative_cashflow=0,
            average_closing_balance_3m=0.0, largest_single_income_source=0.0,
            largest_client_concentration=0.0, revenue_source_diversity=0,
            repeat_customer_rate=0.0, bounced_debit_count=0, bounce_rate=0.0,
            salary_run_regularity=False, detected_salary_amount=None,
            detected_loan_repayments_monthly=0.0, detected_loan_repayments=[],
            invoice_payment_lag_days=None, category_totals={},
        )

    sorted_txs = sorted(transactions, key=lambda t: t.date)
    period_start = sorted_txs[0].date
    period_end = sorted_txs[-1].date

    revenue_by_month: Dict[str, float] = defaultdict(float)
    expense_by_month: Dict[str, float] = defaultdict(float)
    net_by_month: Dict[str, float] = defaultdict(float)

    bounced = 0
    debit_orders = 0
    category_totals: Dict[str, float] = defaultdict(float)
    revenue_by_counterparty: Dict[str, float] = defaultdict(float)
    counterparty_months: Dict[str, set] = defaultdict(set)
    all_months: set = set()

    for tx in sorted_txs:
        month = _month_key(tx.date)
        all_months.add(month)
        category_totals[tx.category] += tx.amount
        if tx.bounced:
            bounced += 1
        if tx.amount < 0 and tx.category in (
            TransactionCategory.FIXED_COSTS.value,
            TransactionCategory.DEBT_SERVICE.value,
        ):
            debit_orders += 1
        if tx.category == TransactionCategory.INCOME.value and tx.amount > 0:
            revenue_by_month[month] += tx.amount
            if tx.counterparty:
                cp = tx.counterparty.lower()
                revenue_by_counterparty[cp] += tx.amount
                counterparty_months[cp].add(month)
        if tx.category == TransactionCategory.TRANSFERS.value:
            continue
        if tx.amount < 0:
            expense_by_month[month] += abs(tx.amount)
        net_by_month[month] += tx.amount

    months_sorted = sorted(all_months)
    monthly_revenue = [round(revenue_by_month.get(m, 0.0), 2) for m in months_sorted]
    monthly_expenses = [round(expense_by_month.get(m, 0.0), 2) for m in months_sorted]
    monthly_net = [round(net_by_month.get(m, 0.0), 2) for m in months_sorted]

    avg_revenue = statistics.mean(monthly_revenue) if monthly_revenue else 0.0
    cv = _coefficient_of_variation(monthly_revenue)
    positive_months = sum(1 for v in monthly_net if v > 0)
    negative_months = sum(1 for v in monthly_net if v < 0)
    pos_ratio = positive_months / len(monthly_net) if monthly_net else 0.0

    last_three = months_sorted[-3:] if len(months_sorted) >= 3 else months_sorted
    closing_balances: List[float] = []
    for month in last_three:
        txs_in_month = [t for t in sorted_txs if _month_key(t.date) == month and t.balance is not None]
        if txs_in_month:
            closing_balances.append(txs_in_month[-1].balance or 0.0)
    avg_closing = statistics.mean(closing_balances) if closing_balances else 0.0

    total_revenue = sum(revenue_by_counterparty.values())
    largest_concentration = 0.0
    largest_single_amount = 0.0
    if revenue_by_counterparty and total_revenue > 0:
        largest_single_amount = max(revenue_by_counterparty.values())
        largest_concentration = largest_single_amount / total_revenue

    bounce_rate = bounced / debit_orders if debit_orders else 0.0
    salary_regular, salary_amount = _detect_salary_runs(sorted_txs)
    loan_monthly, loan_details = _detect_loan_repayments(sorted_txs)
    payment_lag = _invoice_payment_lag(sorted_txs)

    repeat_count = sum(1 for cp, months in counterparty_months.items() if len(months) >= 2)
    repeat_rate = repeat_count / len(counterparty_months) if counterparty_months else 0.0

    return StatementMetrics(
        bank_name=bank,
        period_start=period_start,
        period_end=period_end,
        transaction_count=len(sorted_txs),
        monthly_revenue=monthly_revenue,
        monthly_expenses=monthly_expenses,
        monthly_net_cashflow=monthly_net,
        average_monthly_revenue=round(avg_revenue, 2),
        revenue_coefficient_of_variation=round(cv, 3),
        positive_cash_flow_months_ratio=round(pos_ratio, 3),
        months_with_negative_cashflow=negative_months,
        average_closing_balance_3m=round(avg_closing, 2),
        largest_single_income_source=round(largest_single_amount, 2),
        largest_client_concentration=round(largest_concentration, 3),
        revenue_source_diversity=len(revenue_by_counterparty),
        repeat_customer_rate=round(repeat_rate, 3),
        bounced_debit_count=bounced,
        bounce_rate=round(bounce_rate, 3),
        salary_run_regularity=salary_regular,
        detected_salary_amount=salary_amount,
        detected_loan_repayments_monthly=loan_monthly,
        detected_loan_repayments=loan_details,
        invoice_payment_lag_days=payment_lag,
        category_totals={k: round(v, 2) for k, v in category_totals.items()},
    )


def parse_statement(content: bytes, filename: str, bank_hint: Optional[str] = None) -> Tuple[List[Transaction], StatementMetrics]:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        transactions, bank = parse_pdf(content, bank_hint)
    else:
        transactions, bank = parse_csv(content, bank_hint)
    metrics = compute_metrics(transactions, bank)
    return transactions, metrics


def metrics_to_dict(metrics: StatementMetrics) -> Dict:
    return asdict(metrics)


def transactions_to_dicts(transactions: List[Transaction]) -> List[Dict]:
    return [asdict(t) for t in transactions]
