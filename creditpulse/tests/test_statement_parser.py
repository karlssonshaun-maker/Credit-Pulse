from pathlib import Path

from creditpulse.api.services.statement_parser import compute_metrics, parse_csv, parse_statement
from creditpulse.api.services.transaction_categoriser import TransactionCategory, categorise, is_bounced_debit

FIXTURES = Path(__file__).parent / "fixtures"


def _read(name: str) -> bytes:
    return (FIXTURES / name).read_bytes()


def test_categoriser_detects_salary():
    assert categorise("STAFF SALARY PAYROLL", -10000).value == "SALARY"


def test_categoriser_detects_debt_service():
    assert categorise("LOAN REPAYMENT ABC FINANCE", -5000).value == "DEBT_SERVICE"


def test_categoriser_detects_tax():
    assert categorise("SARS EFILING VAT PAYMENT", -3000).value == "TAX"


def test_categoriser_detects_transfers():
    assert categorise("TRANSFER TO OWN ACCOUNT", -1000).value == "TRANSFERS"


def test_bounced_detection():
    assert is_bounced_debit("UNPAID DEBIT ORDER RETURNED")
    assert is_bounced_debit("R/D RETURNED")
    assert not is_bounced_debit("EFT CREDIT CUSTOMER")


def test_parse_fnb_csv():
    content = _read("fnb_statement.csv")
    txs, bank = parse_csv(content)
    assert len(txs) > 0
    assert any(t.category == "INCOME" and t.amount > 0 for t in txs)
    assert any(t.category == "SALARY" for t in txs)


def test_parse_nedbank_csv():
    content = _read("nedbank_statement.csv")
    txs, bank = parse_csv(content, bank_hint="Nedbank")
    assert len(txs) > 0
    incomes = [t for t in txs if t.category == "INCOME"]
    assert len(incomes) >= 1


def test_parse_absa_debit_credit_format():
    content = _read("absa_statement.csv")
    txs, bank = parse_csv(content, bank_hint="Absa")
    assert len(txs) > 0
    incomes = [t for t in txs if t.amount > 0]
    outgoing = [t for t in txs if t.amount < 0]
    assert len(incomes) >= 1
    assert len(outgoing) >= 1


def test_compute_metrics_produces_sensible_output():
    content = _read("fnb_statement.csv")
    txs, metrics = parse_statement(content, "fnb.csv")
    assert metrics.transaction_count > 0
    assert metrics.average_monthly_revenue > 0
    assert len(metrics.monthly_revenue) >= 2
    assert metrics.bounced_debit_count >= 1


def test_empty_statement_metrics():
    metrics = compute_metrics([])
    assert metrics.transaction_count == 0
    assert metrics.average_monthly_revenue == 0.0
