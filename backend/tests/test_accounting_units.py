from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.domains.accounting.schemas import JournalIn, LineIn
from app.domains.accounting.service import journal_digest


def payload(amount="100.00"):
    return {
        "request_id": str(uuid4()),
        "booking_date": "2026-10-03",
        "description": "Service revenue, no POS required",
        "lines": [
            {"account_id": str(uuid4()), "debit": amount},
            {"account_id": str(uuid4()), "credit": amount},
        ],
    }


@pytest.mark.parametrize("amount", ["0", "-1", "1.001", "NaN", "Infinity", "1e20", 0.1, True])
def test_invalid_money_is_rejected(amount):
    with pytest.raises(ValidationError):
        JournalIn.model_validate(payload(amount))


def test_unbalanced_or_double_sided_line_is_rejected():
    data = payload()
    data["lines"][1]["credit"] = "99.99"
    with pytest.raises(ValidationError):
        JournalIn.model_validate(data)
    with pytest.raises(ValidationError):
        LineIn(account_id=uuid4(), debit="1", credit="1")


def test_decimal_balance_is_exact_and_digest_normalizes_amount_strings():
    data = payload("0.30")
    data["lines"] = [
        {"account_id": str(uuid4()), "debit": "0.10"},
        {"account_id": str(uuid4()), "debit": "0.20"},
        {"account_id": str(uuid4()), "credit": "0.30"},
    ]
    first = JournalIn.model_validate(data)
    data["lines"][0]["debit"] = "0.1"
    second = JournalIn.model_validate(data)
    assert journal_digest(first) == journal_digest(second)
    data["description"] = "Changed request content"
    assert journal_digest(first) != journal_digest(JournalIn.model_validate(data))


def test_accounting_payload_rejects_pos_context_and_empty_description():
    data = payload()
    data["terminal_id"] = str(uuid4())
    with pytest.raises(ValidationError):
        JournalIn.model_validate(data)
    data.pop("terminal_id")
    data["description"] = "   "
    with pytest.raises(ValidationError):
        JournalIn.model_validate(data)
