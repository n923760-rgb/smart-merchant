"""Category VAT fixtures, rounding boundaries and integer precision guarantees."""

from dataclasses import FrozenInstanceError
from decimal import ROUND_DOWN, localcontext

import pytest

from app.domains.billing.tax_calculation import calculate_standard_vat


@pytest.mark.parametrize("lines,net,tax,gross", [
    (["14.99", "20.00"], "34.99", "5.25", "40.24"),
    (["0.10", "0.10"], "0.20", "0.03", "0.23"),
    (["0.03"], "0.03", "0.00", "0.03"),
    (["0.10"], "0.10", "0.02", "0.12"),
    (["1.50"], "1.50", "0.23", "1.73"),
    (["100"], "100.00", "15.00", "115.00"),
    (["0", "0.0", "0.00"], "0.00", "0.00", "0.00"),
    (["90071992547409.93"], "90071992547409.93", "13510798882111.49", "103582791429521.42"),
    (["0.01"] * 100, "1.00", "0.15", "1.15"),
    (["8695652173913043.47"], "8695652173913043.47", "1304347826086956.52", "9999999999999999.99"),
])
def test_category_totals_and_rounding(lines, net, tax, gross):
    result = calculate_standard_vat(lines)
    assert (result.taxable_amount, result.tax_amount, result.gross_amount) == (net, tax, gross)


def test_category_tax_is_not_sum_of_individually_rounded_line_tax():
    single = calculate_standard_vat(["0.10"])
    combined = calculate_standard_vat(["0.10", "0.10"])
    assert single.tax_amount == "0.02"
    assert combined.tax_amount == "0.03"  # Not the incorrect 0.04 sum.


@pytest.mark.parametrize("bad", [
    1, 0.1, True, None, "-1", "NaN", "Infinity", "1e2", "1.001", "01.00",
    " 1.00", "1.00 ", "+1", ".5", "1.", "١.٠٠", "10000000000000000.00",
])
def test_invalid_or_ambiguous_money_cannot_enter_tax_calculation(bad):
    with pytest.raises(ValueError):
        calculate_standard_vat([bad])


@pytest.mark.parametrize("bad", [[], ["1"] * 101, "1.00", None, {"1.00"}])
def test_line_collection_is_bounded_and_explicit(bad):
    with pytest.raises(ValueError):
        calculate_standard_vat(bad)


@pytest.mark.parametrize("lines", [
    ["9999999999999999.99"],  # Net fits, but tax-inclusive gross does not.
    ["8695652173913043.48"],  # One halala above the greatest qualified net.
    ["5000000000000000.00", "5000000000000000.00"],  # Net sum overflows too.
])
def test_tax_inclusive_storage_overflow_is_rejected(lines):
    with pytest.raises(ValueError, match="storage range"):
        calculate_standard_vat(lines)


def test_result_is_immutable_and_decimal_context_cannot_change_money():
    lines = ("90071992547409.93", "0.07")
    normal = calculate_standard_vat(lines)
    with localcontext() as context:
        context.prec = 2
        context.rounding = ROUND_DOWN
        assert calculate_standard_vat(lines) == normal
    assert lines == ("90071992547409.93", "0.07")
    with pytest.raises(FrozenInstanceError):
        normal.tax_amount = "0.00"
