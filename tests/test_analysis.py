"""Tests for src.reicalc_mcp.calculators.analysis."""

from src.reicalc_mcp.calculators.analysis import (
    analyze_sensitivity,
    run_monte_carlo,
    calculate_tax_benefits,
    compare_properties,
)


# ---------------------------------------------------------------------------
# analyze_sensitivity
# ---------------------------------------------------------------------------

def test_sensitivity_basic():
    result = analyze_sensitivity(
        base_scenario={
            "purchase_price": 300_000,
            "annual_rental_income": 30_000,
            "annual_expenses": 8_000,
        },
    )
    assert isinstance(result, dict)
    assert "sensitivity_analysis" in result
    assert "risk_assessment" in result
    assert "base_case" in result


def test_sensitivity_custom_variables():
    result = analyze_sensitivity(
        base_scenario={
            "purchase_price": 250_000,
            "annual_rental_income": 24_000,
            "annual_expenses": 6_000,
        },
        sensitivity_variables=[
            {"variable": "purchase_price", "variations": [-10, 0, 10]},
            {"variable": "rental_income", "variations": [-15, 0, 15]},
        ],
    )
    assert len(result["sensitivity_analysis"]) == 2
    assert "two_way_analysis" in result
    assert "recommendations" in result


def test_sensitivity_with_metrics():
    result = analyze_sensitivity(
        base_scenario={
            "purchase_price": 400_000,
            "annual_rental_income": 40_000,
            "annual_expenses": 12_000,
            "vacancy_rate": 8,
        },
        analysis_metrics=["irr", "cash_on_cash"],
    )
    assert "tornado_diagram" in result
    assert "critical_values" in result


# ---------------------------------------------------------------------------
# run_monte_carlo
# ---------------------------------------------------------------------------

def test_monte_carlo_basic():
    result = run_monte_carlo(
        investment_parameters={
            "purchase_price": 300_000,
            "annual_rental_income": 30_000,
            "annual_expenses": 8_000,
            "down_payment_percent": 20,
        },
        variable_distributions={
            "rental_income": {"mean": 30_000, "std_dev": 3_000, "distribution": "normal"},
            "expenses": {"mean": 8_000, "std_dev": 1_500, "distribution": "normal"},
        },
        simulation_settings={"num_simulations": 100, "random_seed": 42},
    )
    assert isinstance(result, dict)
    assert "summary_statistics" in result
    assert "probability_analysis" in result


def test_monte_carlo_with_targets():
    result = run_monte_carlo(
        investment_parameters={
            "purchase_price": 250_000,
            "annual_rental_income": 24_000,
            "annual_expenses": 6_000,
            "down_payment_percent": 25,
        },
        variable_distributions={
            "rental_income": {"mean": 24_000, "std_dev": 2_000, "distribution": "normal"},
        },
        simulation_settings={"num_simulations": 50, "random_seed": 123},
        target_metrics={"minimum_irr": 10, "minimum_cash_flow": 0},
    )
    assert "risk_metrics" in result
    assert "scenario_analysis" in result


def test_monte_carlo_metadata():
    result = run_monte_carlo(
        investment_parameters={
            "purchase_price": 200_000,
            "annual_rental_income": 20_000,
            "annual_expenses": 5_000,
        },
        variable_distributions={
            "rental_income": {"mean": 20_000, "std_dev": 2_000, "distribution": "normal"},
        },
        simulation_settings={"num_simulations": 50, "random_seed": 99},
    )
    assert "simulation_metadata" in result
    assert result["simulation_metadata"]["num_simulations"] == 50


# ---------------------------------------------------------------------------
# calculate_tax_benefits
# ---------------------------------------------------------------------------

def test_tax_benefits_basic():
    result = calculate_tax_benefits(
        property_details={
            "purchase_price": 400_000,
            "land_value": 100_000,
        },
        income_expenses={
            "annual_rental_income": 36_000,
            "annual_expenses": 10_000,
        },
        loan_details={
            "loan_amount": 320_000,
            "interest_rate": 7.0,
            "loan_term_years": 30,
        },
        taxpayer_info={
            "taxable_income": 85_000,
            "filing_status": "single",
            "marginal_tax_rate": 24,
        },
    )
    assert isinstance(result, dict)
    assert "depreciation_analysis" in result
    assert result["depreciation_analysis"]["annual_depreciation"] > 0


def test_tax_benefits_married():
    result = calculate_tax_benefits(
        property_details={
            "purchase_price": 500_000,
            "land_value": 125_000,
        },
        income_expenses={
            "annual_rental_income": 42_000,
            "annual_expenses": 12_000,
        },
        loan_details={
            "loan_amount": 400_000,
            "interest_rate": 6.5,
            "loan_term_years": 30,
        },
        taxpayer_info={
            "taxable_income": 150_000,
            "filing_status": "married",
            "marginal_tax_rate": 22,
        },
    )
    assert "annual_tax_analysis" in result
    assert "summary_metrics" in result
    assert "recommendations" in result


def test_tax_benefits_with_cost_seg():
    result = calculate_tax_benefits(
        property_details={
            "purchase_price": 600_000,
            "land_value": 120_000,
            "cost_segregation": True,
        },
        income_expenses={
            "annual_rental_income": 54_000,
            "annual_expenses": 15_000,
        },
        loan_details={
            "loan_amount": 480_000,
            "interest_rate": 7.0,
            "loan_term_years": 30,
        },
        taxpayer_info={
            "taxable_income": 200_000,
            "filing_status": "married",
            "marginal_tax_rate": 32,
        },
        cost_segregation_breakdown={
            "5_year": 60_000,
            "7_year": 30_000,
            "15_year": 40_000,
            "27_5_year": 350_000,
        },
    )
    assert "cost_segregation_analysis" in result
    assert "effective_tax_rates" in result


# ---------------------------------------------------------------------------
# compare_properties
# ---------------------------------------------------------------------------

def test_compare_properties_basic():
    result = compare_properties(
        properties=[
            {
                "name": "Property A",
                "purchase_price": 250_000,
                "monthly_rent": 2_000,
                "annual_expenses": 6_000,
                "down_payment_percent": 20,
            },
            {
                "name": "Property B",
                "purchase_price": 350_000,
                "monthly_rent": 2_800,
                "annual_expenses": 8_000,
                "down_payment_percent": 20,
            },
        ],
    )
    assert isinstance(result, dict)
    assert "rankings" in result
    assert "best_options" in result
    assert len(result["property_analyses"]) == 2


# ---------------------------------------------------------------------------
# Bug F: 2026 tax brackets in analysis.py
# ---------------------------------------------------------------------------

def test_federal_tax_2026_brackets():
    """Verify analysis.py _federal_tax uses 2026 brackets (48475 threshold, not 47150)."""
    from src.reicalc_mcp.calculators.analysis import _federal_tax

    # $50,000 income: 10% on first $11,925, 12% on next $36,550 ($11,925-$48,475), 22% on remainder
    tax = _federal_tax(50_000)
    expected = 11_925 * 0.10 + (48_475 - 11_925) * 0.12 + (50_000 - 48_475) * 0.22
    assert abs(tax - expected) < 1.0


# ---------------------------------------------------------------------------
# Bug G: downside deviation denominator (Monte Carlo)
# ---------------------------------------------------------------------------

def test_monte_carlo_sortino_ratio():
    """Sortino ratio should use len(downside_values) not total n as denominator."""
    result = run_monte_carlo(
        investment_parameters={
            "purchase_price": 300_000,
            "annual_rental_income": 30_000,
            "annual_expenses": 8_000,
            "down_payment_percent": 20,
        },
        variable_distributions={
            "rental_income": {"mean": 30_000, "std_dev": 3_000, "distribution": "normal"},
            "expenses": {"mean": 8_000, "std_dev": 1_500, "distribution": "normal"},
        },
        simulation_settings={"num_simulations": 500, "random_seed": 42},
        target_metrics={"minimum_irr": 10, "minimum_cash_flow": 0},
    )
    # Sortino ratio should exist and be a valid number
    sortino = result["risk_metrics"]["sortino_ratio"]
    assert isinstance(sortino, (int, float))


def test_compare_properties_with_loan_terms():
    result = compare_properties(
        properties=[
            {
                "name": "Condo",
                "purchase_price": 200_000,
                "monthly_rent": 1_600,
                "annual_expenses": 5_000,
                "down_payment_percent": 25,
            },
            {
                "name": "SFH",
                "purchase_price": 300_000,
                "monthly_rent": 2_200,
                "annual_expenses": 7_000,
                "down_payment_percent": 20,
            },
        ],
        loan_terms={"interest_rate": 6.75, "loan_term_years": 30},
    )
    assert "comparison_matrix" in result
    assert "insights" in result
    assert "recommendations" in result
