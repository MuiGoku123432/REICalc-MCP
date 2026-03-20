"""Tests for src.reicalc_mcp.calculators.lending."""

from src.reicalc_mcp.calculators.lending import (
    calculate_mortgage_affordability,
    analyze_debt_to_income,
    compare_loans,
    calculate_piti,
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


def test_dti_fha_computed_piti():
    """FHA DTI with computed PITI should use UFMIP-inflated loan and correct MIP rate."""
    result = analyze_debt_to_income(
        monthly_income=8_000,
        purchase_price=363_000,
        down_payment=12_705,
        interest_rate=7.0,
        loan_type="fha",
        property_tax_rate=2.2,
        insurance_rate=0.5,
    )
    proposed = result["proposed_payment"]["housing_payment"]
    # With UFMIP rolled in: base $350,295 + UFMIP → ~$356,425 loan
    # P&I on $356,425 at 7% ≈ $2,371, tax ≈ $665, ins ≈ $151, MIP(0.55%) ≈ $163
    # Total ≈ $3,350
    assert proposed > 3_100, f"FHA PITI too low: {proposed}"
    assert proposed < 3_600, f"FHA PITI too high: {proposed}"


def test_fha_35pct_down_mip_never_drops():
    """FHA 3.5% down (96.5% LTV) → MIP for life of loan, pmi_drop_month is None."""
    loans = [
        {
            "loan_name": "FHA 3.5%",
            "down_payment_percent": 3.5,
            "interest_rate": 7.0,
            "loan_term_years": 30,
            "loan_type": "fha",
        },
    ]
    result = compare_loans(home_price=300_000, loans=loans, comparison_period_years=30)
    fha = result["loan_details"][0]
    assert fha["pmi_details"]["pmi_drop_month"] is None


def test_fha_10pct_down_mip_drops_at_133():
    """FHA 10% down (90% LTV) → MIP drops after 11 years (month 133)."""
    loans = [
        {
            "loan_name": "FHA 10%",
            "down_payment_percent": 10,
            "interest_rate": 7.0,
            "loan_term_years": 30,
            "loan_type": "fha",
        },
    ]
    result = compare_loans(home_price=300_000, loans=loans, comparison_period_years=15)
    fha = result["loan_details"][0]
    assert fha["pmi_details"]["pmi_drop_month"] == 133


def test_conventional_pmi_drops_at_78_ltv():
    """Conventional PMI should drop when LTV reaches 78%."""
    loans = [
        {
            "loan_name": "Conv 10%",
            "down_payment_percent": 10,
            "interest_rate": 7.0,
            "loan_term_years": 30,
            "loan_type": "conventional",
        },
    ]
    result = compare_loans(home_price=300_000, loans=loans, comparison_period_years=15)
    conv = result["loan_details"][0]
    # PMI should drop somewhere between month 60 and 180
    assert conv["pmi_details"]["pmi_drop_month"] is not None
    assert 60 < conv["pmi_details"]["pmi_drop_month"] < 180


def test_compare_loans_fha_ufmip_in_loan_amount():
    """FHA loan in compare_loans should include UFMIP in loan_amount."""
    loans = [
        {
            "loan_name": "FHA 3.5%",
            "down_payment_percent": 3.5,
            "interest_rate": 7.0,
            "loan_term_years": 30,
            "loan_type": "fha",
        },
    ]
    result = compare_loans(home_price=363_000, loans=loans)
    fha = result["loan_details"][0]
    base_loan = 363_000 * 0.965  # $350,295
    # Loan amount should include UFMIP
    assert fha["loan_amount"] > base_loan
    assert fha["upfront_costs"]["ufmip"] > 6_000


# ---------------------------------------------------------------------------
# calculate_piti
# ---------------------------------------------------------------------------

def test_piti_conventional_basic():
    result = calculate_piti(home_price=400_000, down_payment_percent=20, interest_rate=7.0)
    assert "monthly_payment" in result
    assert result["monthly_payment"]["total_piti"] > 0
    assert result["pmi_details"]["pmi_required"] is False
    assert result["loan_details"]["loan_type"] == "conventional"


def test_piti_fha_35_down():
    """FHA 3.5% down on $363K: verify UFMIP, MIP rate, and total PITI."""
    result = calculate_piti(
        home_price=363_000,
        down_payment_percent=3.5,
        interest_rate=7.0,
        property_tax_rate=2.2,
        insurance_rate=0.5,
        loan_type="fha",
    )
    assert "fha_details" in result
    fha = result["fha_details"]
    # UFMIP should be ~$6,130
    assert abs(fha["ufmip"] - 6130.16) < 1
    assert fha["annual_mip_rate"] == 0.55
    # Total PITI should be ~$3,232
    total = result["monthly_payment"]["total_piti"]
    assert 3_100 < total < 3_400, f"Expected ~$3,232, got {total}"


def test_piti_custom_pmi_override():
    """Custom pmi_rate should override defaults."""
    result = calculate_piti(
        home_price=300_000,
        down_payment_percent=10,
        interest_rate=7.0,
        pmi_rate=1.0,
    )
    assert result["pmi_details"]["pmi_rate"] == 1.0
    assert result["pmi_details"]["pmi_required"] is True


def test_piti_fha_details_present():
    """FHA loans should include fha_details."""
    result = calculate_piti(home_price=200_000, down_payment_percent=3.5, loan_type="fha")
    assert "fha_details" in result
    assert result["fha_details"]["ufmip_rate"] == 1.75


def test_piti_conventional_no_fha_details():
    """Conventional loans should not include fha_details."""
    result = calculate_piti(home_price=200_000, down_payment_percent=20)
    assert "fha_details" not in result


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
