"""Arithmetic only: caller must independently qualify the standard VAT category.

No tax-policy selection, invoice issuance or application activation occurs here.
Inputs are already-rounded, tax-exclusive SAR line net amounts in one category.
"""

import re
from dataclasses import dataclass

MAX_MINOR = 10**18 - 1  # NUMERIC(18,2), including tax-inclusive totals.
NET_PATTERN = re.compile(r"(?:0|[1-9][0-9]{0,15})(?:\.[0-9]{1,2})?", re.ASCII)


@dataclass(frozen=True)
class StandardVatBreakdown:
    taxable_amount: str
    tax_amount: str
    gross_amount: str


def _minor(value: str) -> int:
    if not isinstance(value, str) or NET_PATTERN.fullmatch(value) is None:
        raise ValueError("Expected a nonnegative SAR decimal string with up to two places.")
    whole, _, fraction = value.partition(".")
    return int(whole) * 100 + int(fraction.ljust(2, "0"))


def _money(minor: int) -> str:
    return f"{minor // 100}.{minor % 100:02d}"


def calculate_standard_vat(line_net_amounts: list[str] | tuple[str, ...]) -> StandardVatBreakdown:
    """Calculate only a single standard 15% category, without discounts/charges.

    Round the category tax once (nonnegative HALF_UP), never sum rounded line VAT.
    Reject overflow for every final stored amount. No floats or Decimal context.
    This function does not determine tax applicability or produce an amount due.
    """
    if not isinstance(line_net_amounts, (list, tuple)) or not 1 <= len(line_net_amounts) <= 100:
        raise ValueError("Expected between one and 100 already-rounded net line amounts.")
    taxable = sum(_minor(value) for value in line_net_amounts)
    tax = (taxable * 15 + 50) // 100
    gross = taxable + tax
    if any(value > MAX_MINOR for value in (taxable, tax, gross)):
        raise ValueError("Calculated amounts exceed the qualified SAR storage range.")
    return StandardVatBreakdown(_money(taxable), _money(tax), _money(gross))
