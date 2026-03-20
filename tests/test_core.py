"""Tests for src.reicalc_mcp.calculators.core."""

from src.reicalc_mcp.calculators.core import (
    calculate_affordability,
    analyze_brrrr_deal,
    evaluate_house_hack,
    project_portfolio_growth,
    analyze_syndication,
)


# ---------------------------------------------------------------------------
# calculate_affordability
# ---------------------------------------------------------------------------

def test_affordability_basic():
    result = calculate_affordability(
        annual_income=75_000,
        monthly_debts=500,
        down_payment=20_000,
        interest_rate=6.85,
    )
    assert isinstance(result, dict)
    assert result["max_home_price"] > 0
    assert "monthly_payment_breakdown" in result
    assert result["monthly_payment_breakdown"]["total"] > 0


def test_affordability_high_income():
    result = calculate_affordability(
        annual_income=200_000,
        monthly_debts=1_000,
        down_payment=100_000,
        interest_rate=6.5,
        loan_term_years=30,
    )
    assert result["max_home_price"] > 200_000
    assert "debt_to_income" in result
    assert "loan_details" in result


def test_affordability_zero_debts():
    result = calculate_affordability(
        annual_income=80_000,
        monthly_debts=0,
        down_payment=50_000,
        interest_rate=7.0,
    )
    assert result["max_home_price"] > 0
    assert result["down_payment"] == 50_000
    assert "affordability_summary" in result


# ---------------------------------------------------------------------------
# analyze_brrrr_deal
# ---------------------------------------------------------------------------

def test_brrrr_basic():
    result = analyze_brrrr_deal(
        purchase_price=85_000,
        rehab_cost=45_000,
        after_repair_value=175_000,
        monthly_rent=1_400,
    )
    assert isinstance(result, dict)
    assert "overall_rating" in result
    assert "initial_investment" in result
    assert result["initial_investment"]["purchase_price"] == 85_000


def test_brrrr_high_arv():
    result = analyze_brrrr_deal(
        purchase_price=100_000,
        rehab_cost=60_000,
        after_repair_value=250_000,
        monthly_rent=1_800,
        refinance_ltv=0.75,
    )
    assert result["refinance_results"]["after_repair_value"] == 250_000
    assert "cash_flow_analysis" in result
    assert "returns" in result


def test_brrrr_low_rent():
    result = analyze_brrrr_deal(
        purchase_price=120_000,
        rehab_cost=30_000,
        after_repair_value=180_000,
        monthly_rent=900,
    )
    assert "success_indicators" in result
    assert "deal_metrics" in result


# ---------------------------------------------------------------------------
# evaluate_house_hack
# ---------------------------------------------------------------------------

def test_house_hack_basic():
    result = evaluate_house_hack(
        purchase_price=350_000,
        down_payment=70_000,
        monthly_rent_unit2=1_200,
        interest_rate=7.0,
    )
    assert isinstance(result, dict)
    assert result["net_housing_cost"] > 0
    assert result["rental_income"] == 1_200
    assert "mortgage_piti" in result
    assert "mortgage_breakdown" in result


def test_house_hack_covers_expenses():
    result = evaluate_house_hack(
        purchase_price=300_000,
        down_payment=60_000,
        monthly_rent_unit2=2_500,
        interest_rate=7.0,
    )
    assert result["net_housing_cost"] < result["total_housing_cost"]
    assert result["annual_savings"] > 0


# ---------------------------------------------------------------------------
# project_portfolio_growth
# ---------------------------------------------------------------------------

def test_portfolio_growth_basic():
    result = project_portfolio_growth(starting_capital=50_000)
    assert isinstance(result, dict)
    assert result["estimated_portfolio_value"] > 50_000
    assert result["projected_years"] == 20


def test_portfolio_growth_custom_years():
    result = project_portfolio_growth(starting_capital=100_000, years_to_project=10)
    assert result["projected_years"] == 10
    assert result["estimated_portfolio_value"] > 100_000
    assert result["starting_capital"] == 100_000


# ---------------------------------------------------------------------------
# analyze_syndication
# ---------------------------------------------------------------------------

def test_syndication_basic():
    result = analyze_syndication(
        investment_amount=50_000,
        projected_irr=15,
        hold_period=5,
    )
    assert isinstance(result, dict)
    assert result["total_profit"] > 0
    assert result["projected_total_return"] > 50_000


def test_syndication_with_preferred_return():
    result = analyze_syndication(
        investment_amount=100_000,
        projected_irr=12,
        hold_period=7,
        preferred_return=8,
    )
    assert result["average_annual_return"] == 12
    assert result["preferred_return_threshold"] == 8
    assert result["total_profit"] > 0


def test_syndication_short_hold():
    result = analyze_syndication(
        investment_amount=25_000,
        projected_irr=20,
        hold_period=3,
    )
    assert result["investment_amount"] == 25_000
    assert result["total_profit"] > 0


# ---------------------------------------------------------------------------
# House hack PITI verification (Phase 6 requirement)
# ---------------------------------------------------------------------------

def test_house_hack_piti_370k():
    """$370k house, 5% down, 7% rate should produce PITI ~$3,380/mo, not $350."""
    from src.reicalc_mcp.calculators._common import calculate_mortgage_payment

    purchase_price = 370_000
    down_payment = purchase_price * 0.05  # 5% down = $18,500
    result = evaluate_house_hack(
        purchase_price=purchase_price,
        down_payment=down_payment,
        monthly_rent_unit2=1_500,
        interest_rate=7.0,
    )
    # PITI should be in the $3,000-$4,000 range for a $370k house, NOT ~$350
    piti = result["mortgage_piti"]
    assert piti > 2_500, f"PITI too low: {piti}. Should compute mortgage, not use flat input."
    assert piti < 4_500, f"PITI unexpectedly high: {piti}"

    # Verify P&I component matches calculate_mortgage_payment
    loan_amount = purchase_price - down_payment
    expected_pi = calculate_mortgage_payment(loan_amount, 0.07 / 12, 360)
    actual_pi = result["mortgage_breakdown"]["principal_interest"]
    assert abs(actual_pi - round(expected_pi)) <= 1

    # Verify net cost makes sense
    assert result["net_housing_cost"] > 0  # $3,380 PITI - $1,500 rent > 0
    assert result["effective_housing_cost_reduction_pct"] > 0


def test_house_hack_with_additional_expenses():
    """Test that additional_expenses are included in total housing cost."""
    result = evaluate_house_hack(
        purchase_price=300_000,
        down_payment=60_000,
        monthly_rent_unit2=1_200,
        interest_rate=7.0,
        additional_expenses=200,
    )
    assert result["additional_expenses"] == 200
    assert result["total_housing_cost"] == result["mortgage_piti"] + 200


def test_syndication_preferred_return_analysis():
    """Verify preferred return is actually computed and compared."""
    result = analyze_syndication(
        investment_amount=100_000,
        projected_irr=12,
        hold_period=5,
        preferred_return=8,
    )
    pref = result["preferred_return_analysis"]
    assert pref["annual_preferred_amount"] == round(100_000 * 0.08)
    assert pref["total_preferred_over_hold"] == round(100_000 * 0.08 * 5)
    assert "projected_profit_exceeds_preferred" in pref


def test_portfolio_growth_custom_rate():
    """Verify custom growth rate is used."""
    result = project_portfolio_growth(starting_capital=100_000, years_to_project=10, annual_growth_rate=5.0)
    expected = 100_000 * (1.05 ** 10)
    assert abs(result["estimated_portfolio_value"] - expected) < 1


def test_brrrr_returns_include_equity_split():
    """Verify BRRRR returns split into cash flow + equity created."""
    result = analyze_brrrr_deal(
        purchase_price=100_000,
        rehab_cost=50_000,
        after_repair_value=200_000,
        monthly_rent=1_500,
    )
    returns = result["returns"]
    assert "annual_cash_flow_return" in returns
    assert "equity_created" in returns
    assert "total_return_year_1" in returns


# ---------------------------------------------------------------------------
# Bug fix: PMI should be monthly (/12), not annual
# ---------------------------------------------------------------------------

def test_affordability_pmi_monthly_not_annual():
    """PMI should be ~$30/mo for a $71k loan at 0.5%, not $355 (annual amount)."""
    result = calculate_affordability(
        annual_income=100_000,
        monthly_debts=0,
        down_payment=10_000,
        interest_rate=7.0,
    )
    pmi = result["monthly_payment_breakdown"]["pmi"]
    # At 0.5% annual on a loan of ~$200k-$300k, monthly PMI should be < $200
    assert pmi < 200, f"PMI {pmi} looks like annual amount, not monthly"
    assert result["loan_details"]["pmi_required"] is True


# ---------------------------------------------------------------------------
# Bug fix: BRRRR custom loan terms
# ---------------------------------------------------------------------------

def test_brrrr_custom_loan_terms():
    """15-year refi should produce a higher monthly payment than 30-year default."""
    result_30 = analyze_brrrr_deal(
        purchase_price=100_000,
        rehab_cost=50_000,
        after_repair_value=200_000,
        monthly_rent=1_500,
    )
    result_15 = analyze_brrrr_deal(
        purchase_price=100_000,
        rehab_cost=50_000,
        after_repair_value=200_000,
        monthly_rent=1_500,
        refinance_loan_term_years=15,
    )
    payment_30 = result_30["refinance_results"]["new_monthly_payment"]
    payment_15 = result_15["refinance_results"]["new_monthly_payment"]
    assert payment_15 > payment_30, "15yr refi payment should exceed 30yr"


# ---------------------------------------------------------------------------
# Bug fix: leverage_multiplier param
# ---------------------------------------------------------------------------

def test_portfolio_growth_leverage_multiplier():
    """Custom leverage multiplier should change estimated properties."""
    result_default = project_portfolio_growth(starting_capital=100_000)
    result_2x = project_portfolio_growth(starting_capital=100_000, leverage_multiplier=2.0)
    assert result_default["estimated_properties"] == 6  # 100k // 50k * 3
    assert result_2x["estimated_properties"] == 4  # 100k // 50k * 2


# ---------------------------------------------------------------------------
# Bug C: portfolio growth wrapper should expose all params
# ---------------------------------------------------------------------------

def test_portfolio_growth_custom_avg_property_cost():
    """Custom avg_property_cost should change estimated property count."""
    result = project_portfolio_growth(
        starting_capital=100_000,
        avg_property_cost=100_000,
        leverage_multiplier=3.0,
    )
    # 100k // 100k * 3 = 3 properties
    assert result["estimated_properties"] == 3
