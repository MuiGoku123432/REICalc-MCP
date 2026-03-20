"""Tests for src.reicalc_mcp.calculators.financing."""

from src.reicalc_mcp.calculators.financing import (
    analyze_refinance,
    analyze_construction_loan,
    analyze_hard_money_loan,
    analyze_seller_financing,
)


# ---------------------------------------------------------------------------
# analyze_refinance
# ---------------------------------------------------------------------------

def test_refinance_rate_drop():
    result = analyze_refinance(
        current_loan_balance=280_000,
        current_interest_rate=7.5,
        current_remaining_years=27,
        new_interest_rate=6.0,
        new_closing_costs=4_000,
    )
    assert isinstance(result, dict)
    assert "current_loan" in result
    assert "new_loan" in result
    assert "monthly_comparison" in result
    assert result["monthly_comparison"]["monthly_savings"] > 0


def test_refinance_cash_out():
    result = analyze_refinance(
        current_loan_balance=200_000,
        current_interest_rate=7.0,
        current_remaining_years=25,
        new_interest_rate=6.75,
        new_closing_costs=5_000,
        cash_out_amount=50_000,
        property_value=400_000,
    )
    assert "cash_out_analysis" in result
    assert result["cash_out_analysis"]["cash_out_amount"] == 50_000
    assert "break_even_analysis" in result


def test_refinance_break_even():
    result = analyze_refinance(
        current_loan_balance=300_000,
        current_interest_rate=8.0,
        current_remaining_years=28,
        new_interest_rate=6.5,
        new_closing_costs=6_000,
    )
    assert "total_cost_comparison" in result
    assert "npv_analysis" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_construction_loan
# ---------------------------------------------------------------------------

def test_construction_loan_basic():
    result = analyze_construction_loan(
        land_cost=80_000,
        construction_budget=250_000,
    )
    assert isinstance(result, dict)
    assert "project_summary" in result
    assert "construction_loan" in result
    assert "permanent_loan_conversion" in result


def test_construction_loan_custom_rates():
    result = analyze_construction_loan(
        land_cost=100_000,
        construction_budget=350_000,
        interest_rate=9.0,
        permanent_loan_rate=7.0,
        construction_period_months=18,
        contingency_percent=15,
    )
    assert "interest_analysis" in result
    assert "total_project_costs" in result
    assert "risk_assessment" in result


def test_construction_loan_with_draw_schedule():
    result = analyze_construction_loan(
        land_cost=60_000,
        construction_budget=200_000,
        draw_schedule=[
            {"phase": "Foundation", "percent": 20},
            {"phase": "Framing", "percent": 25},
            {"phase": "Mechanical", "percent": 25},
            {"phase": "Finish", "percent": 30},
        ],
    )
    assert "draw_schedule" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_hard_money_loan
# ---------------------------------------------------------------------------

def test_hard_money_basic():
    result = analyze_hard_money_loan(
        property_value=200_000,
        purchase_price=160_000,
        rehab_budget=40_000,
    )
    assert isinstance(result, dict)
    assert "loan_summary" in result
    assert "cost_analysis" in result
    assert "exit_strategy_analysis" in result


def test_hard_money_sell_exit():
    result = analyze_hard_money_loan(
        property_value=250_000,
        purchase_price=180_000,
        rehab_budget=50_000,
        interest_rate=14,
        loan_term_months=9,
        exit_strategy="sell",
        after_repair_value=300_000,
    )
    assert "comparison_to_conventional" in result
    assert "risk_assessment" in result
    assert "total_cost_of_capital" in result


def test_hard_money_hold_exit():
    result = analyze_hard_money_loan(
        property_value=180_000,
        purchase_price=140_000,
        rehab_budget=30_000,
        exit_strategy="hold",
        after_repair_value=220_000,
    )
    assert "monthly_payments" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_seller_financing
# ---------------------------------------------------------------------------

def test_seller_financing_basic():
    result = analyze_seller_financing(
        purchase_price=300_000,
        down_payment=30_000,
        interest_rate=5.0,
        loan_term_years=20,
    )
    assert isinstance(result, dict)
    assert "loan_terms" in result
    assert "comparison_to_conventional" in result
    assert "buyer_benefits" in result
    assert "seller_benefits" in result


def test_seller_financing_with_balloon():
    result = analyze_seller_financing(
        purchase_price=250_000,
        down_payment=25_000,
        interest_rate=6.0,
        loan_term_years=30,
        balloon_payment_years=5,
    )
    assert "balloon_analysis" in result
    assert "risk_assessment" in result


def test_seller_financing_below_market():
    result = analyze_seller_financing(
        purchase_price=350_000,
        down_payment=50_000,
        interest_rate=4.5,
        loan_term_years=15,
        market_interest_rate=7.0,
        buyer_credit_score=580,
    )
    assert "payment_schedule" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# Refinance: verify computed payment matches manual calculation
# ---------------------------------------------------------------------------

def test_refinance_computed_payment():
    """Verify that removing current_monthly_payment and computing it gives correct results."""
    from src.reicalc_mcp.calculators._common import calculate_mortgage_payment

    balance = 250_000
    rate = 7.0
    years = 25

    result = analyze_refinance(
        current_loan_balance=balance,
        current_interest_rate=rate,
        current_remaining_years=years,
        new_interest_rate=6.0,
    )

    # The computed current monthly payment should match manual calculation
    expected = calculate_mortgage_payment(balance, rate / 100 / 12, int(years * 12))
    actual = result["current_loan"]["monthly_payment"]
    assert abs(actual - round(expected, 2)) < 0.01

    # Monthly savings should be positive (dropping from 7% to 6%)
    assert result["monthly_comparison"]["monthly_savings"] > 0
