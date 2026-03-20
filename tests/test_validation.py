"""Tests for input validation across all public calculator functions."""

import pytest

from src.reicalc_mcp.calculators._validation import (
    validate_positive,
    validate_non_negative,
    validate_range,
    validate_percent,
    validate_non_empty_list,
)
from src.reicalc_mcp.calculators.core import (
    calculate_affordability,
    analyze_brrrr_deal,
    evaluate_house_hack,
    project_portfolio_growth,
    analyze_syndication,
)
from src.reicalc_mcp.calculators.lending import (
    calculate_mortgage_affordability,
    analyze_debt_to_income,
    compare_loans,
)
from src.reicalc_mcp.calculators.financing import (
    analyze_refinance,
    analyze_construction_loan,
    analyze_hard_money_loan,
    analyze_seller_financing,
)
from src.reicalc_mcp.calculators.strategies import (
    analyze_airbnb_str,
    analyze_wholesale_deal,
    analyze_subject_to_deal,
)
from src.reicalc_mcp.calculators.metrics import (
    calculate_irr_tool,
    analyze_fix_flip,
    calculate_npv_tool,
    calculate_cocr,
)
from src.reicalc_mcp.calculators.advanced import (
    analyze_rent_vs_buy,
    calculate_capital_gains_tax,
    analyze_market_comps,
)


# ---------------------------------------------------------------------------
# Validation helpers unit tests
# ---------------------------------------------------------------------------

class TestValidatePositive:
    def test_zero_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive(0, "x")

    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive(-1, "x")

    def test_positive_ok(self):
        validate_positive(1, "x")  # no exception


class TestValidateNonNegative:
    def test_negative_raises(self):
        with pytest.raises(ValueError, match="must be non-negative"):
            validate_non_negative(-0.01, "x")

    def test_zero_ok(self):
        validate_non_negative(0, "x")


class TestValidateRange:
    def test_below_raises(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_range(-1, "x", 0, 100)

    def test_above_raises(self):
        with pytest.raises(ValueError, match="must be between"):
            validate_range(101, "x", 0, 100)

    def test_in_range_ok(self):
        validate_range(50, "x", 0, 100)


class TestValidatePercent:
    def test_negative_raises(self):
        with pytest.raises(ValueError):
            validate_percent(-1, "x")

    def test_over_100_raises(self):
        with pytest.raises(ValueError):
            validate_percent(100.1, "x")


class TestValidateNonEmptyList:
    def test_empty_raises(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_non_empty_list([], "x")

    def test_non_empty_ok(self):
        validate_non_empty_list([1], "x")


# ---------------------------------------------------------------------------
# Core module validation
# ---------------------------------------------------------------------------

def test_affordability_negative_income():
    with pytest.raises(ValueError):
        calculate_affordability(annual_income=-50000, monthly_debts=0, down_payment=10000, interest_rate=7)


def test_affordability_rate_over_100():
    with pytest.raises(ValueError):
        calculate_affordability(annual_income=50000, monthly_debts=0, down_payment=10000, interest_rate=101)


def test_brrrr_negative_price():
    with pytest.raises(ValueError):
        analyze_brrrr_deal(purchase_price=-100, rehab_cost=0, after_repair_value=100, monthly_rent=100)


def test_brrrr_vacancy_over_100():
    with pytest.raises(ValueError):
        analyze_brrrr_deal(
            purchase_price=100000, rehab_cost=0, after_repair_value=200000,
            monthly_rent=1000, vacancy_rate=110,
        )


def test_house_hack_negative_price():
    with pytest.raises(ValueError):
        evaluate_house_hack(purchase_price=-1, down_payment=0, monthly_rent_unit2=0, interest_rate=7)


def test_portfolio_growth_zero_capital():
    with pytest.raises(ValueError):
        project_portfolio_growth(starting_capital=0)


def test_syndication_zero_investment():
    with pytest.raises(ValueError):
        analyze_syndication(investment_amount=0, projected_irr=10, hold_period=5)


# ---------------------------------------------------------------------------
# Lending module validation
# ---------------------------------------------------------------------------

def test_mortgage_affordability_negative_income():
    with pytest.raises(ValueError):
        calculate_mortgage_affordability(annual_income=-1, down_payment=10000, interest_rate=7)


def test_dti_negative_income():
    with pytest.raises(ValueError):
        analyze_debt_to_income(monthly_income=-1, proposed_housing_payment=1000)


def test_compare_loans_zero_price():
    with pytest.raises(ValueError):
        compare_loans(home_price=0, loans=[])


# ---------------------------------------------------------------------------
# Financing module validation
# ---------------------------------------------------------------------------

def test_refinance_negative_balance():
    with pytest.raises(ValueError):
        analyze_refinance(current_loan_balance=-1, current_interest_rate=7, current_remaining_years=25, new_interest_rate=6)


def test_refinance_rate_over_100():
    with pytest.raises(ValueError):
        analyze_refinance(current_loan_balance=100000, current_interest_rate=101, current_remaining_years=25, new_interest_rate=6)


def test_construction_loan_negative_land():
    with pytest.raises(ValueError):
        analyze_construction_loan(land_cost=-1, construction_budget=100000)


def test_hard_money_zero_value():
    with pytest.raises(ValueError):
        analyze_hard_money_loan(property_value=0, purchase_price=100000)


def test_seller_financing_negative_price():
    with pytest.raises(ValueError):
        analyze_seller_financing(purchase_price=-1, down_payment=10000, interest_rate=5, loan_term_years=20)


# ---------------------------------------------------------------------------
# Strategies module validation
# ---------------------------------------------------------------------------

def test_airbnb_zero_price():
    with pytest.raises(ValueError):
        analyze_airbnb_str(purchase_price=0, average_daily_rate=200)


def test_airbnb_occupancy_over_100():
    with pytest.raises(ValueError):
        analyze_airbnb_str(purchase_price=100000, average_daily_rate=200, occupancy_rate=110)


def test_wholesale_negative_contract():
    with pytest.raises(ValueError):
        analyze_wholesale_deal(contract_price=-1, after_repair_value=200000, estimated_rehab_cost=0, assignment_fee=0)


def test_subject_to_zero_balance():
    with pytest.raises(ValueError):
        analyze_subject_to_deal(
            purchase_price=200000, existing_loan_balance=0, existing_interest_rate=4,
            existing_loan_remaining_years=20, monthly_rent=1500,
        )


# ---------------------------------------------------------------------------
# Metrics module validation
# ---------------------------------------------------------------------------

def test_irr_tool_zero_investment():
    with pytest.raises(ValueError):
        calculate_irr_tool(initial_investment=0, annual_cash_flows=[1000], projected_sale_price=100000)


def test_irr_tool_empty_cash_flows():
    with pytest.raises(ValueError):
        calculate_irr_tool(initial_investment=100000, annual_cash_flows=[], projected_sale_price=100000)


def test_fix_flip_negative_price():
    with pytest.raises(ValueError):
        analyze_fix_flip(purchase_price=-1, rehab_budget=0, after_repair_value=100000)


def test_npv_tool_empty_cash_flows():
    with pytest.raises(ValueError):
        calculate_npv_tool(initial_investment=100000, cash_flows=[], discount_rate=10)


def test_cocr_zero_down_payment():
    with pytest.raises(ValueError):
        calculate_cocr(purchase_price=100000, down_payment=0, annual_rental_income=10000)


# ---------------------------------------------------------------------------
# Advanced module validation
# ---------------------------------------------------------------------------

def test_rent_vs_buy_zero_price():
    with pytest.raises(ValueError):
        analyze_rent_vs_buy(monthly_rent=2000, home_price=0)


def test_capital_gains_negative_sale():
    with pytest.raises(ValueError):
        calculate_capital_gains_tax(sale_price=-1, purchase_price=100000, holding_period_years=5)


def test_market_comps_empty_comps():
    with pytest.raises(ValueError):
        analyze_market_comps(
            subject_property={"square_feet": 1500},
            comparable_properties=[],
        )
