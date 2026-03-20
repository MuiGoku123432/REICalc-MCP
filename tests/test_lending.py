"""Tests for src.reicalc_mcp.calculators.lending."""

from src.reicalc_mcp.calculators.lending import (
    calculate_mortgage_affordability,
    analyze_debt_to_income,
    compare_loans,
)


# ---------------------------------------------------------------------------
# calculate_mortgage_affordability
# ---------------------------------------------------------------------------

def test_mortgage_affordability_basic():
    result = calculate_mortgage_affordability(
        annual_income=100_000,
        down_payment=40_000,
        interest_rate=7.0,
    )
    assert isinstance(result, dict)
    assert "affordability_results" in result
    assert "debt_to_income_ratios" in result
    assert result["affordability_results"]["max_home_price"] > 0


def test_mortgage_affordability_with_debts():
    result = calculate_mortgage_affordability(
        annual_income=85_000,
        down_payment=30_000,
        interest_rate=6.5,
        car_payment=400,
        student_loans=300,
        credit_cards=150,
    )
    assert "income_analysis" in result
    assert "monthly_payment_breakdown" in result
    assert result["monthly_payment_breakdown"]["total_monthly_payment"] > 0


def test_mortgage_affordability_co_borrower():
    result = calculate_mortgage_affordability(
        annual_income=80_000,
        down_payment=50_000,
        interest_rate=6.75,
        co_borrower_income=60_000,
    )
    assert result["income_analysis"]["co_borrower_annual_income"] == 60_000
    assert result["affordability_results"]["max_home_price"] > 100_000
    assert "loan_details" in result


# ---------------------------------------------------------------------------
# analyze_debt_to_income
# ---------------------------------------------------------------------------

def test_dti_basic():
    result = analyze_debt_to_income(
        monthly_income=8_000,
        proposed_housing_payment=2_200,
    )
    assert isinstance(result, dict)
    assert "dti_ratios" in result
    assert "front_end" in result["dti_ratios"]
    assert "back_end" in result["dti_ratios"]
    assert "qualification" in result
    assert result["qualification"]["overall_status"] in (
        "Excellent Candidate", "Likely Approved", "Manual Underwriting", "Likely Declined"
    )


def test_dti_with_debts():
    result = analyze_debt_to_income(
        monthly_income=7_000,
        proposed_housing_payment=1_800,
        car_payments=500,
        student_loans=300,
        credit_card_minimums=200,
    )
    assert result["debt_breakdown"]["total_non_housing_debts"] == 1_000
    assert "maximum_affordable" in result
    assert "recommendations" in result


def test_dti_fha_loan():
    result = analyze_debt_to_income(
        monthly_income=6_000,
        proposed_housing_payment=1_600,
        loan_type="fha",
    )
    assert result["dti_ratios"]["loan_type"] == "fha"
    assert result["qualification"]["loan_type"] == "fha"
    assert result["qualification"]["loan_type_limits"]["front_end"] == 31


# ---------------------------------------------------------------------------
# compare_loans
# ---------------------------------------------------------------------------

def test_compare_loans_basic():
    loans = [
        {
            "loan_name": "30-Year Fixed",
            "down_payment_percent": 20,
            "interest_rate": 7.0,
            "loan_term_years": 30,
        },
        {
            "loan_name": "15-Year Fixed",
            "down_payment_percent": 20,
            "interest_rate": 6.25,
            "loan_term_years": 15,
        },
    ]
    result = compare_loans(home_price=400_000, loans=loans)
    assert isinstance(result, dict)
    assert "loan_details" in result
    assert len(result["loan_details"]) == 2
    assert "best_options" in result


def test_compare_loans_with_costs():
    loans = [
        {
            "loan_name": "Conventional",
            "down_payment_percent": 20,
            "interest_rate": 7.0,
            "loan_term_years": 30,
        },
        {
            "loan_name": "FHA",
            "down_payment_percent": 3.5,
            "interest_rate": 6.5,
            "loan_term_years": 30,
            "loan_type": "fha",
        },
    ]
    result = compare_loans(
        home_price=350_000,
        loans=loans,
        property_tax_annual=4_200,
        home_insurance_annual=1_500,
    )
    assert "comparison_summary" in result
    assert "side_by_side" in result
    assert result["comparison_summary"]["num_loans_compared"] == 2


def test_dti_computed_housing_payment():
    """Verify DTI can compute PITI from purchase_price/down_payment/interest_rate."""
    result = analyze_debt_to_income(
        monthly_income=8_000,
        purchase_price=350_000,
        down_payment=70_000,
        interest_rate=7.0,
    )
    # proposed_payment should be auto-computed PITI, not 0
    proposed = result["proposed_payment"]["housing_payment"]
    assert proposed > 1_500  # reasonable PITI for $280k loan at 7%
    assert proposed < 3_000
    assert "qualification" in result


def test_compare_loans_with_points():
    loans = [
        {
            "loan_name": "No Points",
            "down_payment_percent": 20,
            "interest_rate": 7.0,
            "loan_term_years": 30,
            "points": 0,
        },
        {
            "loan_name": "1 Point Buydown",
            "down_payment_percent": 20,
            "interest_rate": 6.75,
            "loan_term_years": 30,
            "points": 1,
        },
    ]
    result = compare_loans(home_price=500_000, loans=loans)
    assert "points_analysis" in result
    assert "recommendations" in result
