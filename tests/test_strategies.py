"""Tests for src.reicalc_mcp.calculators.strategies."""

from src.reicalc_mcp.calculators.strategies import (
    analyze_airbnb_str,
    analyze_1031_exchange,
    analyze_wholesale_deal,
    analyze_subject_to_deal,
)


# ---------------------------------------------------------------------------
# analyze_airbnb_str
# ---------------------------------------------------------------------------

def test_airbnb_basic():
    result = analyze_airbnb_str(
        purchase_price=350_000,
        average_daily_rate=200,
        occupancy_rate=70,
    )
    assert isinstance(result, dict)
    assert "revenue_analysis" in result
    assert "cash_flow_comparison" in result
    assert result["revenue_analysis"]["annual_gross_revenue"] > 0


def test_airbnb_with_expenses():
    result = analyze_airbnb_str(
        purchase_price=400_000,
        average_daily_rate=250,
        occupancy_rate=65,
        monthly_expenses=800,
        furnishing_cost=15_000,
        management_fee_percent=25,
    )
    assert "expense_analysis" in result
    assert "risk_assessment" in result
    assert "break_even_occupancy" in result
    assert result["break_even_occupancy"] > 0


def test_airbnb_financing():
    result = analyze_airbnb_str(
        purchase_price=300_000,
        average_daily_rate=180,
        down_payment_percent=25,
        interest_rate=7.5,
    )
    assert "financing" in result
    assert result["financing"]["purchase_price"] == 300_000
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_1031_exchange
# ---------------------------------------------------------------------------

def test_1031_exchange_basic():
    result = analyze_1031_exchange(
        relinquished_property={
            "sale_price": 500_000,
            "adjusted_basis": 300_000,
        },
        replacement_property={
            "purchase_price": 600_000,
        },
        holding_period_years=5,
    )
    assert isinstance(result, dict)
    assert "tax_deferral_benefit" in result
    assert result["tax_deferral_benefit"]["total_taxes_deferred"] > 0


def test_1031_exchange_with_depreciation():
    result = analyze_1031_exchange(
        relinquished_property={
            "sale_price": 700_000,
            "adjusted_basis": 400_000,
            "depreciation_taken": 80_000,
            "original_purchase_price": 450_000,
        },
        replacement_property={
            "purchase_price": 800_000,
            "closing_costs": 15_000,
        },
        capital_gains_rate=15,
        state_tax_rate=5,
        holding_period_years=8,
    )
    assert "tax_liability_without_exchange" in result
    assert "relinquished_property_analysis" in result
    assert "comparison" in result


def test_1031_exchange_timeline():
    result = analyze_1031_exchange(
        relinquished_property={
            "sale_price": 400_000,
            "adjusted_basis": 250_000,
        },
        replacement_property={
            "purchase_price": 450_000,
        },
    )
    assert "timeline" in result
    assert "qualification_checklist" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_wholesale_deal
# ---------------------------------------------------------------------------

def test_wholesale_basic():
    result = analyze_wholesale_deal(
        contract_price=120_000,
        after_repair_value=220_000,
        estimated_rehab_cost=40_000,
        assignment_fee=10_000,
    )
    assert isinstance(result, dict)
    assert "deal_summary" in result
    assert "wholesaler_profit" in result
    assert result["wholesaler_profit"]["assignment_fee"] == 10_000


def test_wholesale_with_holding_costs():
    result = analyze_wholesale_deal(
        contract_price=150_000,
        after_repair_value=280_000,
        estimated_rehab_cost=50_000,
        assignment_fee=15_000,
        holding_costs_monthly=1_200,
        estimated_closing_costs=5_000,
    )
    assert "end_buyer_analysis" in result
    assert "mao_analysis" in result
    assert "exit_strategies" in result


def test_wholesale_deal_viability():
    result = analyze_wholesale_deal(
        contract_price=100_000,
        after_repair_value=200_000,
        estimated_rehab_cost=35_000,
        assignment_fee=8_000,
        target_buyer_type="flipper",
    )
    assert "deal_viability" in result
    assert result["deal_viability"] in ("Strong", "Moderate", "Marginal", "Not viable")
    assert "risk_assessment" in result


# ---------------------------------------------------------------------------
# analyze_subject_to_deal
# ---------------------------------------------------------------------------

def test_subject_to_basic():
    result = analyze_subject_to_deal(
        purchase_price=200_000,
        existing_loan_balance=160_000,
        existing_interest_rate=4.5,
        existing_loan_remaining_years=22,
        monthly_rent=1_500,
    )
    assert isinstance(result, dict)
    assert "deal_structure" in result
    assert "cash_flow_analysis" in result
    assert result["cash_flow_analysis"]["monthly_cash_flow"] > 0


def test_subject_to_with_expenses():
    result = analyze_subject_to_deal(
        purchase_price=250_000,
        existing_loan_balance=200_000,
        existing_interest_rate=3.75,
        existing_loan_remaining_years=25,
        monthly_rent=1_800,
        monthly_expenses=400,
        down_payment_to_seller=5_000,
    )
    assert "equity_analysis" in result
    assert "investment_returns" in result
    assert "comparison_to_traditional" in result


def test_subject_to_projection():
    result = analyze_subject_to_deal(
        purchase_price=180_000,
        existing_loan_balance=150_000,
        existing_interest_rate=5.0,
        existing_loan_remaining_years=24,
        monthly_rent=1_400,
        property_value=195_000,
    )
    assert "5_year_projection" in result
    assert len(result["5_year_projection"]) == 5
    assert "risk_assessment" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# Subject-to: verify computed payment matches manual calculation
# ---------------------------------------------------------------------------

def test_subject_to_computed_payment():
    """Verify that removing existing_monthly_payment and computing it gives correct results."""
    from src.reicalc_mcp.calculators._common import calculate_mortgage_payment

    balance = 160_000
    rate = 4.5
    years = 22

    result = analyze_subject_to_deal(
        purchase_price=200_000,
        existing_loan_balance=balance,
        existing_interest_rate=rate,
        existing_loan_remaining_years=years,
        monthly_rent=1_500,
    )

    # The computed monthly payment should match manual calculation
    expected = calculate_mortgage_payment(balance, rate / 100 / 12, int(years * 12))
    actual = result["deal_structure"]["existing_monthly_payment"]
    assert abs(actual - round(expected, 2)) < 0.01

    # Should have positive cash flow (1500 rent > ~900 payment)
    assert result["cash_flow_analysis"]["monthly_cash_flow"] > 0


def test_wholesale_custom_rehab_months():
    """Verify parameterized rehab months are used."""
    result = analyze_wholesale_deal(
        contract_price=120_000,
        after_repair_value=220_000,
        estimated_rehab_cost=40_000,
        assignment_fee=10_000,
        holding_costs_monthly=1_000,
        estimated_rehab_months=3,
    )
    # 3 months * $1000 = $3000 holding costs
    # vs default 6 months * $1000 = $6000
    all_in = result["end_buyer_analysis"]["all_in_cost"]
    # Verify holding costs are based on 3 months not 6
    expected_all_in = (120_000 + 10_000) + 40_000 + 0 + 3_000  # contract+fee + rehab + closing + holding
    assert abs(all_in - expected_all_in) < 0.01


# ---------------------------------------------------------------------------
# Bug fix: Subject-to custom appreciation and rent growth
# ---------------------------------------------------------------------------

def test_subject_to_custom_appreciation():
    """5% appreciation should produce higher 5-year values than default 3%."""
    result_default = analyze_subject_to_deal(
        purchase_price=200_000,
        existing_loan_balance=160_000,
        existing_interest_rate=4.5,
        existing_loan_remaining_years=22,
        monthly_rent=1_500,
    )
    result_5pct = analyze_subject_to_deal(
        purchase_price=200_000,
        existing_loan_balance=160_000,
        existing_interest_rate=4.5,
        existing_loan_remaining_years=22,
        monthly_rent=1_500,
        appreciation_rate=5.0,
    )
    val_default = result_default["5_year_projection"][-1]["property_value"]
    val_5pct = result_5pct["5_year_projection"][-1]["property_value"]
    assert val_5pct > val_default, "5% appreciation should exceed 3% default"


def test_subject_to_custom_rent_growth():
    """4% rent growth should produce higher year-5 rent than default 2%."""
    result_default = analyze_subject_to_deal(
        purchase_price=200_000,
        existing_loan_balance=160_000,
        existing_interest_rate=4.5,
        existing_loan_remaining_years=22,
        monthly_rent=1_500,
    )
    result_4pct = analyze_subject_to_deal(
        purchase_price=200_000,
        existing_loan_balance=160_000,
        existing_interest_rate=4.5,
        existing_loan_remaining_years=22,
        monthly_rent=1_500,
        rent_growth_rate=4.0,
    )
    rent_default = result_default["5_year_projection"][-1]["monthly_rent"]
    rent_4pct = result_4pct["5_year_projection"][-1]["monthly_rent"]
    assert rent_4pct > rent_default, "4% rent growth should exceed 2% default"
