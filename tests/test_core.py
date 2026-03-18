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
        owner_expenses=2_000,
    )
    assert isinstance(result, dict)
    assert result["net_housing_cost"] < result["gross_housing_cost"]
    assert result["rental_income"] == 1_200


def test_house_hack_covers_expenses():
    result = evaluate_house_hack(
        purchase_price=300_000,
        down_payment=60_000,
        monthly_rent_unit2=2_500,
        owner_expenses=2_000,
    )
    assert result["net_housing_cost"] < 0  # rent covers more than expenses
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
