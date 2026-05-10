from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Tuple


class TransactionCategory(str, Enum):
    INCOME = "INCOME"
    FIXED_COSTS = "FIXED_COSTS"
    VARIABLE_COSTS = "VARIABLE_COSTS"
    DEBT_SERVICE = "DEBT_SERVICE"
    TAX = "TAX"
    TRANSFERS = "TRANSFERS"
    FEES = "FEES"
    SALARY = "SALARY"
    UNCATEGORISED = "UNCATEGORISED"


KEYWORD_RULES: list[Tuple[TransactionCategory, re.Pattern]] = [
    (TransactionCategory.TAX, re.compile(r"\b(sars|vat payment|paye|uif|sdl|income tax|efiling)\b", re.I)),
    (TransactionCategory.DEBT_SERVICE, re.compile(
        r"\b(loan repayment|instalment|installment|hp\s|hire purchase|credit card|"
        r"visa payment|mastercard payment|overdraft|bond repayment|vehicle finance|bank loan)\b", re.I
    )),
    (TransactionCategory.FIXED_COSTS, re.compile(
        r"\b(rent|lease|insurance|assurance|subscription|medical aid|"
        r"dstv|telkom|vodacom|mtn|cell ?c|rain|afrihost|office 365|microsoft|google workspace)\b", re.I
    )),
    (TransactionCategory.SALARY, re.compile(r"\b(salary|wages|payroll|staff pay|sal\.?|remuneration)\b", re.I)),
    (TransactionCategory.VARIABLE_COSTS, re.compile(
        r"\b(supplier|makro|builders warehouse|stock|inventory|eskom|municipal|"
        r"fuel|petrol|shell|bp|caltex|engen|uber|bolt|courier|fedex|aramex)\b", re.I
    )),
    (TransactionCategory.TRANSFERS, re.compile(
        r"\b(transfer to|transfer from|internal transfer|inter[- ]?account|own account)\b", re.I
    )),
    (TransactionCategory.FEES, re.compile(
        r"\b(bank charge|monthly fee|service fee|admin fee|transaction fee|atm withdrawal fee|"
        r"sms notification|cash handling)\b", re.I
    )),
    (TransactionCategory.INCOME, re.compile(
        r"\b(invoice|inv[.\s]|payment received|eft credit|card settlement|yoco|snapscan|"
        r"zapper|pos settlement|merchant settlement|customer payment|paid by)\b", re.I
    )),
]


def is_bounced_debit(description: str) -> bool:
    return bool(re.search(r"\b(unpaid|returned|rd\s*dr|reversed|debit order reversal|r/d|nsf)\b", description, re.I))


def categorise(description: str, amount: float) -> TransactionCategory:
    desc = description or ""
    for category, pattern in KEYWORD_RULES:
        if pattern.search(desc):
            return category
    if amount > 0:
        return TransactionCategory.INCOME
    if amount < 0:
        return TransactionCategory.VARIABLE_COSTS
    return TransactionCategory.UNCATEGORISED


def extract_counterparty(description: str) -> Optional[str]:
    if not description:
        return None
    cleaned = re.sub(r"\b(ref|reference|inv|invoice|payment|eft|credit|debit|pos|atm)\b[:\s-]*", "", description, flags=re.I)
    cleaned = re.sub(r"\b\d{6,}\b", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -:,.")
    return cleaned[:64] if cleaned else None
