"""Tests for src.reicalc_mcp.calculators.advanced."""

from src.reicalc_mcp.calculators.advanced import (
    analyze_rent_vs_buy,
    calculate_capital_gains_tax,
    analyze_joint_venture,
    analyze_market_comps,
)


# ---------------------------------------------------------------------------
# analyze_rent_vs_buy
# ---------------------------------------------------------------------------

def test_rent_vs_buy_basic():
    result = analyze_rent_vs_buy(
        monthly_rent=2_000,
        home_price=400_000,
    )
    assert isinstance(result, dict)
    assert "annual_comparison" in result
    assert "net_wealth_analysis" in result
    assert len(result["annual_comparison"]) == 10  # default 10 years


def test_rent_vs_buy_custom_period():
    result = analyze_rent_vs_buy(
        monthly_rent=1_800,
        home_price=350_000,
        down_payment_percent=25,
        interest_rate=6.5,
        analysis_period_years=7,
    )
    assert len(result["annual_comparison"]) == 7
    assert "crossover_analysis" in result
    assert "tax_benefit_analysis" in result


def test_rent_vs_buy_wealth_comparison():
    result = analyze_rent_vs_buy(
        monthly_rent=2_500,
        home_price=500_000,
        annual_appreciation=4.0,
        investment_return_rate=8.0,
    )
    assert "total_cost_summary" in result
    assert "cumulative_comparison" in result
    assert "recommendations" in result
    assert isinstance(result["net_wealth_analysis"]["buying_is_better"], bool)


# ---------------------------------------------------------------------------
# calculate_capital_gains_tax
# ---------------------------------------------------------------------------

def test_capital_gains_basic():
    result = calculate_capital_gains_tax(
        sale_price=500_000,
        purchase_price=300_000,
        holding_period_years=5,
        other_income=85_000,
    )
    assert isinstance(result, dict)
    assert "gain_calculation" in result
    assert "tax_liability" in result
    assert result["gain_calculation"]["total_gain"] > 0
    assert result["tax_liability"]["total"] > 0


def test_capital_gains_primary_residence():
    result = calculate_capital_gains_tax(
        sale_price=600_000,
        purchase_price=350_000,
        holding_period_years=7,
        is_primary_residence=True,
        years_lived_in=5,
        filing_status="married",
        other_income=120_000,
    )
    assert result["primary_residence_exclusion"]["eligible"] is True
    assert result["primary_residence_exclusion"]["exclusion_amount"] > 0
    assert result["gain_calculation"]["taxable_gain"] < result["gain_calculation"]["total_gain"]


def test_capital_gains_with_depreciation():
    result = calculate_capital_gains_tax(
        sale_price=450_000,
        purchase_price=280_000,
        depreciation_taken=50_000,
        improvements_cost=30_000,
        holding_period_years=10,
        state="TX",
        other_income=100_000,
    )
    assert result["tax_liability"]["depreciation_recapture"] > 0
    assert "effective_tax_rate" in result
    assert "net_proceeds" in result
    assert "optimization_strategies" in result


# ---------------------------------------------------------------------------
# analyze_joint_venture
# ---------------------------------------------------------------------------

def test_joint_venture_pro_rata():
    result = analyze_joint_venture(
        total_project_cost=500_000,
        projected_profit=100_000,
        project_duration_months=18,
        partners=[
            {"name": "Alice", "capital_contribution": 300_000, "role": "capital"},
            {"name": "Bob", "capital_contribution": 200_000, "role": "operating"},
        ],
    )
    assert isinstance(result, dict)
    assert "partnership_summary" in result
    assert "capital_structure" in result
    assert "profit_distribution" in result
    assert len(result["profit_distribution"]) == 2


def test_joint_venture_preferred_return():
    result = analyze_joint_venture(
        total_project_cost=1_000_000,
        projected_profit=250_000,
        project_duration_months=24,
        partners=[
            {"name": "LP1", "capital_contribution": 600_000, "role": "capital"},
            {"name": "GP1", "capital_contribution": 400_000, "role": "operating"},
        ],
        profit_split_method="preferred_return",
        preferred_return_rate=8,
    )
    assert "return_analysis" in result
    assert "fairness_analysis" in result
    assert result["return_analysis"][0]["roi_percent"] > 0


def test_joint_venture_legal_considerations():
    result = analyze_joint_venture(
        total_project_cost=750_000,
        projected_profit=150_000,
        project_duration_months=12,
        partners=[
            {"name": "Partner A", "capital_contribution": 500_000, "role": "capital"},
            {"name": "Partner B", "capital_contribution": 250_000, "role": "both"},
        ],
    )
    assert "legal_considerations" in result
    assert len(result["legal_considerations"]) > 0
    assert "risk_allocation" in result
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# analyze_market_comps
# ---------------------------------------------------------------------------

def test_market_comps_basic():
    result = analyze_market_comps(
        subject_property={
            "address": "100 Test St",
            "square_feet": 1_800,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2005,
            "condition": "good",
            "lot_size": 7_000,
        },
        comparable_properties=[
            {
                "address": "101 Test St",
                "sale_price": 350_000,
                "square_feet": 1_750,
                "bedrooms": 3,
                "bathrooms": 2,
                "year_built": 2003,
                "condition": "good",
                "distance_miles": 0.5,
                "sale_date": "2026-01-15",
                "lot_size": 6_800,
            },
            {
                "address": "102 Test St",
                "sale_price": 375_000,
                "square_feet": 1_900,
                "bedrooms": 3,
                "bathrooms": 2.5,
                "year_built": 2008,
                "condition": "excellent",
                "distance_miles": 0.8,
                "sale_date": "2025-11-20",
                "lot_size": 7_200,
            },
            {
                "address": "103 Test St",
                "sale_price": 340_000,
                "square_feet": 1_700,
                "bedrooms": 3,
                "bathrooms": 2,
                "year_built": 2002,
                "condition": "average",
                "distance_miles": 1.2,
                "sale_date": "2025-09-10",
                "lot_size": 6_500,
            },
        ],
    )
    assert isinstance(result, dict)
    assert "valuation_summary" in result
    assert result["valuation_summary"]["estimated_value"] > 0
    assert "comparable_analyses" in result
    assert len(result["comparable_analyses"]) == 3


def test_market_comps_confidence():
    result = analyze_market_comps(
        subject_property={
            "square_feet": 2_000,
            "bedrooms": 4,
            "bathrooms": 2.5,
            "year_built": 2010,
            "condition": "good",
            "lot_size": 8_000,
        },
        comparable_properties=[
            {
                "address": "Comp 1",
                "sale_price": 420_000,
                "square_feet": 2_050,
                "bedrooms": 4,
                "bathrooms": 2.5,
                "year_built": 2011,
                "distance_miles": 0.3,
                "sale_date": "2026-02-01",
                "lot_size": 8_200,
            },
            {
                "address": "Comp 2",
                "sale_price": 410_000,
                "square_feet": 1_950,
                "bedrooms": 4,
                "bathrooms": 2,
                "year_built": 2009,
                "distance_miles": 0.5,
                "sale_date": "2026-01-10",
                "lot_size": 7_800,
            },
        ],
    )
    assert "confidence_score" in result["valuation_summary"]
    assert result["valuation_summary"]["confidence_label"] in ("High", "Medium", "Low")
    assert "statistical_analysis" in result


def test_market_comps_cma_report():
    result = analyze_market_comps(
        subject_property={
            "square_feet": 1_500,
            "bedrooms": 3,
            "bathrooms": 2,
            "year_built": 2000,
            "condition": "average",
            "lot_size": 6_000,
        },
        comparable_properties=[
            {
                "address": "Near Comp",
                "sale_price": 300_000,
                "square_feet": 1_550,
                "bedrooms": 3,
                "bathrooms": 2,
                "year_built": 2001,
                "distance_miles": 0.2,
                "sale_date": "2026-02-15",
                "lot_size": 6_200,
            },
        ],
    )
    assert "cma_report" in result
    assert "adjustment_summary" in result
    assert "recommendations" in result
