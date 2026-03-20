"""Mathematically-verified tests for _common.py utilities."""

import pytest

from src.reicalc_mcp.calculators._common import (
    calculate_mortgage_payment,
    calculate_irr,
    calculate_npv,
    safe_irr_pct,
    FHA_UFMIP_RATE,
    calculate_fha_ufmip,
    calculate_fha_loan_amount,
    fha_annual_mip_rate,
)


# ---------------------------------------------------------------------------
# calculate_mortgage_payment — known-value tests
# ---------------------------------------------------------------------------

def test_mortgage_100k_7pct_30yr():
    """$100k at 7%/30yr should be ~$665.30/mo."""
    payment = calculate_mortgage_payment(100_000, 0.07 / 12, 360)
    assert abs(payment - 665.30) < 0.10


def test_mortgage_200k_6pct_15yr():
    """$200k at 6%/15yr should be ~$1,687.71/mo."""
    payment = calculate_mortgage_payment(200_000, 0.06 / 12, 180)
    assert abs(payment - 1687.71) < 0.10


def test_mortgage_zero_rate():
    """At 0% interest, payment = principal / num_payments."""
    payment = calculate_mortgage_payment(120_000, 0, 360)
    assert abs(payment - 333.33) < 0.01


def test_mortgage_small_loan():
    """Small loan: $10k at 5%/10yr."""
    payment = calculate_mortgage_payment(10_000, 0.05 / 12, 120)
    assert abs(payment - 106.07) < 0.10


# ---------------------------------------------------------------------------
# calculate_irr — known-value tests
# ---------------------------------------------------------------------------

def test_irr_simple_10pct():
    """[-100, 110] should give IRR = 10%."""
    result = calculate_irr([-100, 110])
    assert result is not None
    assert abs(result - 0.10) < 0.001


def test_irr_multi_period():
    """[-1000, 200, 200, 200, 200, 200, 200] ~= 5.47%."""
    result = calculate_irr([-1000, 200, 200, 200, 200, 200, 200])
    assert result is not None
    assert abs(result - 0.0547) < 0.005


def test_irr_no_sign_change_returns_none():
    """All positive cash flows should return None."""
    result = calculate_irr([100, 200, 300])
    assert result is None


def test_irr_all_negative_returns_none():
    """All negative cash flows should return None."""
    result = calculate_irr([-100, -200, -300])
    assert result is None


def test_irr_empty_returns_none():
    """Empty cash flows should return None."""
    result = calculate_irr([])
    assert result is None


def test_irr_break_even():
    """[-100, 50, 50] = 0% IRR."""
    result = calculate_irr([-100, 50, 50])
    assert result is not None
    assert abs(result) < 0.001


# ---------------------------------------------------------------------------
# safe_irr_pct
# ---------------------------------------------------------------------------

def test_safe_irr_pct_valid():
    irr, converged = safe_irr_pct([-100, 110])
    assert converged is True
    assert abs(irr - 10.0) < 0.1


def test_safe_irr_pct_no_sign_change():
    irr, converged = safe_irr_pct([100, 200])
    assert converged is False
    assert irr == 0.0


# ---------------------------------------------------------------------------
# calculate_npv — known-value tests
# ---------------------------------------------------------------------------

def test_npv_known_value():
    """NPV of [-1000, 500, 500, 200] at 10%."""
    npv = calculate_npv([-1000, 500, 500, 200], 0.10)
    expected = -1000 + 500 / 1.1 + 500 / 1.21 + 200 / 1.331
    assert abs(npv - expected) < 0.01


def test_npv_zero_rate_is_sum():
    """At rate=0, NPV = sum of cash flows."""
    flows = [-100, 50, 60, 70]
    npv = calculate_npv(flows, 0)
    assert abs(npv - sum(flows)) < 0.001


def test_npv_empty_is_zero():
    assert calculate_npv([], 0.1) == 0.0


def test_npv_negative_one_rate():
    """rate = -1 should return inf (guarded)."""
    import math
    result = calculate_npv([100], -1)
    assert math.isinf(result)


# ---------------------------------------------------------------------------
# Cross-validation: NPV(IRR) ~= 0
# ---------------------------------------------------------------------------

def test_npv_at_irr_is_zero():
    """NPV evaluated at the IRR should be approximately 0."""
    flows = [-1000, 300, 400, 500]
    irr = calculate_irr(flows)
    assert irr is not None
    npv_at_irr = calculate_npv(flows, irr)
    assert abs(npv_at_irr) < 0.01


# ---------------------------------------------------------------------------
# FHA helpers
# ---------------------------------------------------------------------------

def test_fha_ufmip_rate_constant():
    assert FHA_UFMIP_RATE == 0.0175


def test_fha_ufmip_calculation():
    """UFMIP on $350,295 base loan should be $6,130.16."""
    ufmip = calculate_fha_ufmip(350_295)
    assert abs(ufmip - 6130.16) < 0.01


def test_fha_loan_amount_with_ufmip():
    """$363K home, 3.5% down: base $350,295 + UFMIP $6,130.16 = $356,425.16."""
    home_price = 363_000
    down = home_price * 0.035  # $12,705
    loan = calculate_fha_loan_amount(home_price, down, roll_in_ufmip=True)
    base = home_price - down
    expected = base + base * FHA_UFMIP_RATE
    assert abs(loan - round(expected, 2)) < 0.01


def test_fha_loan_amount_without_ufmip():
    loan = calculate_fha_loan_amount(300_000, 10_500, roll_in_ufmip=False)
    assert loan == 289_500.0


def test_fha_mip_rate_30yr_high_ltv():
    """3.5% down → 96.5% LTV → 0.55% MIP for >15yr term."""
    assert fha_annual_mip_rate(96.5, 30) == 0.55


def test_fha_mip_rate_30yr_low_ltv():
    """10% down → 90% LTV → 0.50% MIP for >15yr term."""
    assert fha_annual_mip_rate(90.0, 30) == 0.50


def test_fha_mip_rate_15yr_low_ltv():
    """15yr, LTV ≤ 90% → 0.15%."""
    assert fha_annual_mip_rate(90.0, 15) == 0.15


def test_fha_mip_rate_15yr_high_ltv():
    """15yr, LTV > 90% → 0.40%."""
    assert fha_annual_mip_rate(95.0, 15) == 0.40
