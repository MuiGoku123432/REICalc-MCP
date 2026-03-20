"""Tests for src.reicalc_mcp.calculators.management."""

from src.reicalc_mcp.calculators.management import (
    analyze_property_management,
    track_property_expenses,
    track_deal_pipeline,
)


# ---------------------------------------------------------------------------
# analyze_property_management
# ---------------------------------------------------------------------------

def test_property_management_basic():
    result = analyze_property_management(
        monthly_rent=1_500,
        num_units=1,
        property_value=250_000,
    )
    assert isinstance(result, dict)
    assert "self_management_analysis" in result
    assert "professional_management_analysis" in result
    assert "cost_comparison" in result


def test_property_management_multi_unit():
    result = analyze_property_management(
        monthly_rent=1_200,
        num_units=4,
        property_value=500_000,
        annual_maintenance_cost=5_000,
    )
    assert "break_even_analysis" in result
    assert "time_value_analysis" in result
    assert "efficiency_metrics" in result


def test_property_management_custom_fees():
    result = analyze_property_management(
        monthly_rent=2_000,
        num_units=2,
        self_management={"hours_per_week": 8, "hourly_value": 60},
        professional_management={
            "management_fee_percent": 10,
            "leasing_fee_percent": 75,
            "maintenance_markup_percent": 15,
        },
    )
    assert "risk_comparison" in result
    assert "recommendations" in result
    assert result["cost_comparison"]["cheaper_option"] in (
        "self_management", "professional_management"
    )


# ---------------------------------------------------------------------------
# track_property_expenses
# ---------------------------------------------------------------------------

def test_expenses_basic():
    expenses = [
        {"category": "maintenance", "amount": 500, "date": "2025-01"},
        {"category": "insurance", "amount": 100, "date": "2025-01"},
        {"category": "taxes", "amount": 250, "date": "2025-01"},
        {"category": "maintenance", "amount": 300, "date": "2025-02"},
        {"category": "insurance", "amount": 100, "date": "2025-02"},
        {"category": "taxes", "amount": 250, "date": "2025-02"},
    ]
    result = track_property_expenses(expenses=expenses)
    assert isinstance(result, dict)
    assert "expense_summary" in result
    assert result["expense_summary"]["total"] > 0


def test_expenses_with_benchmarks():
    expenses = [
        {"category": "maintenance", "amount": 400, "date": "2025-01"},
        {"category": "maintenance", "amount": 350, "date": "2025-02"},
        {"category": "maintenance", "amount": 600, "date": "2025-03"},
        {"category": "insurance", "amount": 150, "date": "2025-01"},
        {"category": "insurance", "amount": 150, "date": "2025-02"},
        {"category": "insurance", "amount": 150, "date": "2025-03"},
    ]
    result = track_property_expenses(
        expenses=expenses,
        property_value=300_000,
        monthly_rent=2_000,
    )
    assert "benchmarking" in result
    assert "expense_ratios" in result
    assert "tax_classification" in result


def test_expenses_with_budget():
    expenses = [
        {"category": "maintenance", "amount": 500, "date": "2025-01"},
        {"category": "taxes", "amount": 300, "date": "2025-01"},
    ]
    result = track_property_expenses(
        expenses=expenses,
        annual_budget={"maintenance": 5_000, "taxes": 3_600},
    )
    assert "budget_analysis" in result
    assert result["budget_analysis"] is not None
    assert "recommendations" in result


def test_expenses_budget_type_is_dict():
    """Bug J: annual_budget must accept dict (not float) matching management.py signature."""
    expenses = [
        {"category": "maintenance", "amount": 200, "date": "2025-03"},
        {"category": "utilities", "amount": 150, "date": "2025-03"},
    ]
    result = track_property_expenses(
        expenses=expenses,
        annual_budget={"maintenance": 3_000, "utilities": 2_000},
    )
    budget = result["budget_analysis"]
    assert budget is not None
    # Budget analysis should contain per-category breakdowns from the dict keys
    assert any("maintenance" in str(budget).lower() for _ in [1])


# ---------------------------------------------------------------------------
# track_deal_pipeline
# ---------------------------------------------------------------------------

def test_pipeline_basic():
    deals = [
        {
            "name": "123 Main St",
            "stage": "analyzing",
            "property_type": "sfh",
            "purchase_price": 200_000,
            "estimated_profit": 30_000,
            "date_added": "2025-12-01",
        },
        {
            "name": "456 Oak Ave",
            "stage": "offer_made",
            "property_type": "sfh",
            "purchase_price": 250_000,
            "estimated_profit": 40_000,
            "date_added": "2026-01-15",
        },
        {
            "name": "789 Pine Rd",
            "stage": "closed",
            "property_type": "duplex",
            "purchase_price": 350_000,
            "estimated_profit": 55_000,
            "date_added": "2025-06-01",
        },
    ]
    result = track_deal_pipeline(deals=deals)
    assert isinstance(result, dict)
    assert "pipeline_summary" in result
    assert result["pipeline_summary"]["total_deals"] == 3


def test_pipeline_health():
    deals = [
        {
            "name": "Deal A",
            "stage": "prospect",
            "purchase_price": 150_000,
            "estimated_profit": 20_000,
            "date_added": "2026-02-01",
        },
        {
            "name": "Deal B",
            "stage": "under_contract",
            "purchase_price": 300_000,
            "estimated_profit": 45_000,
            "date_added": "2026-01-10",
        },
    ]
    result = track_deal_pipeline(deals=deals)
    assert "pipeline_health" in result
    assert result["pipeline_health"]["score"] >= 0
    assert result["pipeline_health"]["status"] in ("healthy", "needs_attention", "critical")


def test_pipeline_empty():
    result = track_deal_pipeline(deals=[])
    assert result["pipeline_summary"]["total_deals"] == 0
    assert "recommendations" in result


# ---------------------------------------------------------------------------
# Bug B: or True removal — monthly_time_saved should be 0 when self is cheaper
# ---------------------------------------------------------------------------

def test_time_saved_zero_when_self_cheaper():
    """When self-management wins, monthly_time_saved should be 0, not hours_per_month."""
    result = analyze_property_management(
        monthly_rent=800,
        num_units=1,
        self_management={"hours_per_week": 2, "hourly_value": 15},
        professional_management={"management_fee_percent": 12},
    )
    if result["cost_comparison"]["cheaper_option"] == "self_management":
        assert result["time_value_analysis"]["monthly_time_saved_with_professional"] == 0


# ---------------------------------------------------------------------------
# Bug H: avg_tenant_stay_months parameter
# ---------------------------------------------------------------------------

def test_custom_tenant_stay_months():
    """Custom avg_tenant_stay_months should change leasing fee amortisation."""
    result_24 = analyze_property_management(
        monthly_rent=1_500,
        num_units=1,
        avg_tenant_stay_months=24,
    )
    result_12 = analyze_property_management(
        monthly_rent=1_500,
        num_units=1,
        avg_tenant_stay_months=12,
    )
    # Shorter stay → higher amortized leasing fee
    fee_24 = result_24["professional_management_analysis"]["costs"]["annual_leasing_fee_amortized"]
    fee_12 = result_12["professional_management_analysis"]["costs"]["annual_leasing_fee_amortized"]
    assert fee_12 > fee_24
