"""Tests for src.reicalc_mcp.calculators.metrics."""

from src.reicalc_mcp.calculators.metrics import (
    calculate_irr_tool,
    analyze_fix_flip,
    calculate_npv_tool,
    calculate_cocr,
    calculate_dscr,
    analyze_breakeven,
)


# ---------------------------------------------------------------------------
# calculate_irr_tool
# ---------------------------------------------------------------------------

def test_irr_basic():
    result = calculate_irr_tool(
        initial_investment=100_000,
        annual_cash_flows=[8_000, 8_500, 9_000, 9_500, 10_000],
        projected_sale_price=250_000,
    )
    assert isinstance(result, dict)
    assert "irr_analysis" in result
    assert result["irr_analysis"]["irr"] > 0


def test_irr_with_loan_balance():
    result = calculate_irr_tool(
        initial_investment=60_000,
        annual_cash_flows=[5_000, 5_200, 5_400],
        projected_sale_price=200_000,
        loan_balance_at_sale=120_000,
        target_irr=12,
    )
    assert result["irr_analysis"]["holding_period_years"] == 3
    assert "cash_flow_summary" in result
    assert "sensitivity_analysis" in result


def test_irr_cash_flow_schedule():
    result = calculate_irr_tool(
        initial_investment=80_000,
        annual_cash_flows=[6_000, 6_500, 7_000, 7_500],
        projected_sale_price=180_000,
        selling_costs_percent=6,
    )
    assert "cash_flow_schedule" in result
    assert len(result["cash_flow_schedule"]) == 5  # year 0 + 4 years
    assert "npv_analysis" in result


# ---------------------------------------------------------------------------
# analyze_fix_flip
# ---------------------------------------------------------------------------

def test_fix_flip_basic():
    result = analyze_fix_flip(
        purchase_price=150_000,
        rehab_budget=50_000,
        after_repair_value=280_000,
    )
    assert isinstance(result, dict)
    assert "profit_analysis" in result
    assert result["profit_analysis"]["net_profit"] > 0


def test_fix_flip_cash_purchase():
    result = analyze_fix_flip(
        purchase_price=120_000,
        rehab_budget=40_000,
        after_repair_value=220_000,
        financing_type="cash",
        holding_period_months=4,
    )
    assert "cost_breakdown" in result
    assert "deal_summary" in result


def test_fix_flip_with_holding_costs():
    result = analyze_fix_flip(
        purchase_price=180_000,
        rehab_budget=60_000,
        after_repair_value=320_000,
        monthly_holding_costs=1_500,
        holding_period_months=8,
    )
    assert "investment_requirements" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# calculate_npv_tool
# ---------------------------------------------------------------------------

def test_npv_basic():
    result = calculate_npv_tool(
        initial_investment=100_000,
        cash_flows=[
            {"period": 1, "amount": 15_000},
            {"period": 2, "amount": 18_000},
            {"period": 3, "amount": 20_000},
            {"period": 4, "amount": 22_000},
            {"period": 5, "amount": 25_000},
        ],
        discount_rate=10,
    )
    assert isinstance(result, dict)
    assert "npv_analysis" in result


def test_npv_with_terminal_value():
    result = calculate_npv_tool(
        initial_investment=200_000,
        cash_flows=[
            {"period": 1, "amount": 25_000},
            {"period": 2, "amount": 28_000},
            {"period": 3, "amount": 30_000},
        ],
        discount_rate=8,
        terminal_value=300_000,
    )
    assert "investment_metrics" in result
    assert "cash_flow_schedule" in result


def test_npv_decision_criteria():
    result = calculate_npv_tool(
        initial_investment=50_000,
        cash_flows=[
            {"period": 1, "amount": 20_000},
            {"period": 2, "amount": 20_000},
            {"period": 3, "amount": 20_000},
        ],
        discount_rate=10,
    )
    assert "decision_criteria" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# calculate_cocr
# ---------------------------------------------------------------------------

def test_cocr_basic():
    result = calculate_cocr(
        purchase_price=300_000,
        down_payment=60_000,
        closing_costs=5_000,
        annual_rental_income=24_000,
        annual_expenses={"insurance": 1_200, "taxes": 3_000, "maintenance": 2_400},
        loan_details={"interest_rate": 7.0, "loan_term_years": 30},
    )
    assert isinstance(result, dict)
    assert "return_metrics" in result
    assert result["return_metrics"]["cash_on_cash_return"] is not None


def test_cocr_with_renovation():
    result = calculate_cocr(
        purchase_price=250_000,
        down_payment=50_000,
        closing_costs=4_000,
        renovation_costs=20_000,
        annual_rental_income=30_000,
        vacancy_rate=8,
    )
    assert "income_analysis" in result
    assert "investment_summary" in result


def test_cocr_no_loan():
    result = calculate_cocr(
        purchase_price=200_000,
        down_payment=200_000,
        annual_rental_income=20_000,
    )
    assert "cash_flow_analysis" in result
    assert "expense_analysis" in result


# ---------------------------------------------------------------------------
# calculate_dscr
# ---------------------------------------------------------------------------

def test_dscr_basic():
    result = calculate_dscr(
        property_income={"monthly_rent": 3_000, "vacancy_rate": 5},
        loan_details={
            "loan_amount": 200_000,
            "interest_rate": 7.0,
            "loan_term_years": 30,
        },
    )
    assert isinstance(result, dict)
    assert "dscr_analysis" in result
    assert result["dscr_analysis"]["dscr"] not in (None, "N/A (no debt)")


def test_dscr_with_expenses():
    result = calculate_dscr(
        property_income={"monthly_rent": 4_000, "vacancy_rate": 5},
        property_expenses={
            "insurance": 100,
            "taxes": 250,
            "maintenance": 200,
        },
        loan_details={
            "loan_amount": 300_000,
            "interest_rate": 6.5,
            "loan_term_years": 30,
        },
    )
    assert "income_analysis" in result
    assert "qualification_analysis" in result
    assert "stress_test_results" in result


def test_dscr_high_rent():
    result = calculate_dscr(
        property_income={"monthly_rent": 6_000, "other_monthly_income": 500},
        loan_details={
            "loan_amount": 250_000,
            "interest_rate": 7.0,
            "loan_term_years": 30,
        },
    )
    assert result["dscr_analysis"]["dscr"] > 1.0
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_breakeven
# ---------------------------------------------------------------------------

def test_breakeven_basic():
    result = analyze_breakeven(
        property_costs={
            "purchase_price": 250_000,
            "down_payment": 50_000,
            "renovation_costs": 10_000,
            "closing_costs": 5_000,
        },
        revenue_streams={"monthly_rent": 2_000},
    )
    assert isinstance(result, dict)
    assert "breakeven_analysis" in result


def test_breakeven_with_fixed_costs():
    result = analyze_breakeven(
        property_costs={
            "purchase_price": 300_000,
            "down_payment": 60_000,
            "closing_costs": 6_000,
        },
        fixed_costs={
            "mortgage": 1_500,
            "insurance": 100,
            "taxes": 250,
        },
        revenue_streams={"monthly_rent": 2_500},
    )
    assert "cost_analysis" in result
    assert "initial_investment" in result
    assert "recommendations" in result


def test_breakeven_with_variable_costs():
    result = analyze_breakeven(
        property_costs={
            "purchase_price": 350_000,
            "down_payment": 70_000,
            "renovation_costs": 15_000,
            "closing_costs": 7_000,
        },
        fixed_costs={"mortgage": 1_800, "insurance": 120},
        variable_costs={"maintenance": 200, "management": 250},
        revenue_streams={"monthly_rent": 2_800},
    )
    assert "sensitivity_analysis" in result
    assert "risk_assessment" in result


# ---------------------------------------------------------------------------
# IRR known-value assertion
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Bug A3: COCR wrapper param order + Bug I: growth rate params
# ---------------------------------------------------------------------------

def test_cocr_param_order():
    """Verify annual_rental_income is used as income, not closing_costs."""
    result = calculate_cocr(
        purchase_price=300_000,
        down_payment=60_000,
        closing_costs=5_000,
        annual_rental_income=24_000,
    )
    assert result["income_analysis"]["gross_annual_rental_income"] == 24_000


def test_cocr_custom_growth_rates():
    """Custom rent_growth should change 5-year projection."""
    result_default = calculate_cocr(
        purchase_price=300_000,
        down_payment=60_000,
        annual_rental_income=24_000,
    )
    result_high = calculate_cocr(
        purchase_price=300_000,
        down_payment=60_000,
        annual_rental_income=24_000,
        rent_growth=0.10,
    )
    # Higher growth → higher year 5 projected rental income
    default_y5 = result_default["five_year_projection"][-1]["rental_income"]
    high_y5 = result_high["five_year_projection"][-1]["rental_income"]
    assert high_y5 > default_y5


def test_irr_tool_known_value():
    """Test IRR tool with a known investment returning ~18.6%."""
    result = calculate_irr_tool(
        initial_investment=100_000,
        annual_cash_flows=[10_000, 10_000, 10_000, 10_000, 10_000],
        projected_sale_price=150_000,
        selling_costs_percent=0,
        loan_balance_at_sale=0,
    )
    irr = result["irr_analysis"]["irr"]
    assert irr > 10, f"IRR too low: {irr}"
    assert irr < 30, f"IRR too high: {irr}"
