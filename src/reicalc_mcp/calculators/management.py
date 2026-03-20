"""Property management, expense tracking, and deal pipeline calculators."""

from collections import defaultdict
from datetime import datetime

from ._common import round2


# ---------------------------------------------------------------------------
# Stage probabilities for deal pipeline
# ---------------------------------------------------------------------------

STAGE_PROBABILITIES: dict[str, float] = {
    "prospect": 5.0,
    "analyzing": 10.0,
    "offer_made": 20.0,
    "under_contract": 40.0,
    "due_diligence": 60.0,
    "closing": 80.0,
    "closed": 100.0,
    "dead": 0.0,
}

STAGE_ORDER: list[str] = [
    "prospect",
    "analyzing",
    "offer_made",
    "under_contract",
    "due_diligence",
    "closing",
    "closed",
    "dead",
]

# ---------------------------------------------------------------------------
# Expense benchmarks (as percent of property value or rent)
# ---------------------------------------------------------------------------

EXPENSE_BENCHMARKS: dict[str, dict[str, float]] = {
    "maintenance": {"low": 1.0, "high": 2.0, "basis": "property_value"},
    "management": {"low": 8.0, "high": 12.0, "basis": "rent"},
    "insurance": {"low": 0.25, "high": 0.75, "basis": "property_value"},
    "taxes": {"low": 0.5, "high": 2.5, "basis": "property_value"},
    "capex": {"low": 0.5, "high": 1.5, "basis": "property_value"},
}

TAX_DEDUCTIBLE_CATEGORIES: set[str] = {
    "taxes",
    "insurance",
    "maintenance",
    "management",
    "utilities",
}

NON_DEDUCTIBLE_CATEGORIES: set[str] = {
    "mortgage",  # principal portion not deductible (interest is, but simplified here)
    "capex",     # capitalised, depreciated instead
    "other",
}


# ---------------------------------------------------------------------------
# 1. analyze_property_management
# ---------------------------------------------------------------------------

def analyze_property_management(
    monthly_rent: float,
    num_units: int = 1,
    property_value: float = 0,
    self_management: dict | None = None,
    professional_management: dict | None = None,
    annual_maintenance_cost: float = 0,
    current_vacancy_rate: float = 5,
    avg_tenant_stay_months: int = 24,
) -> dict:
    """Compare self-management vs professional property management.

    Returns cost analysis, break-even unit count, time-value analysis,
    efficiency metrics, risk comparison, and recommendations.
    """
    self_mgmt = self_management or {}
    prof_mgmt = professional_management or {}

    # --- Self-management inputs ---
    hours_per_week: float = self_mgmt.get("hours_per_week", 10)
    hourly_value: float = self_mgmt.get("hourly_value", 50)
    self_vacancy_rate: float = self_mgmt.get("vacancy_rate", 5)

    # --- Professional management inputs ---
    mgmt_fee_pct: float = prof_mgmt.get("management_fee_percent", 10)
    leasing_fee_pct: float = prof_mgmt.get("leasing_fee_percent", 50)
    maint_markup_pct: float = prof_mgmt.get("maintenance_markup_percent", 10)
    prof_vacancy_rate: float = prof_mgmt.get("vacancy_rate", 3)

    total_monthly_rent = monthly_rent * num_units
    total_annual_rent = total_monthly_rent * 12

    # ---- Self-management costs ----
    monthly_opportunity_cost = round2(hours_per_week * hourly_value * 52 / 12)
    annual_opportunity_cost = round2(monthly_opportunity_cost * 12)
    self_vacancy_loss = round2(total_annual_rent * (self_vacancy_rate / 100))
    self_total_cost = round2(annual_opportunity_cost + self_vacancy_loss)

    hours_per_month = round2(hours_per_week * 52 / 12)
    hours_per_year = round2(hours_per_week * 52)

    # Effective hourly rate: what you "earn" by self-managing
    # (savings from not paying professional fees) / hours spent
    prof_annual_fee = total_annual_rent * (mgmt_fee_pct / 100)
    effective_hourly_rate = round2(prof_annual_fee / hours_per_year) if hours_per_year > 0 else 0

    # ---- Professional management costs ----
    monthly_mgmt_fee = round2(total_monthly_rent * (mgmt_fee_pct / 100))
    annual_mgmt_fee = round2(monthly_mgmt_fee * 12)

    # Leasing fee: amortize over average tenant stay
    leasing_fee_per_unit = monthly_rent * (leasing_fee_pct / 100)
    monthly_leasing_amortized = round2(leasing_fee_per_unit * num_units / avg_tenant_stay_months)
    annual_leasing_amortized = round2(monthly_leasing_amortized * 12)

    # Maintenance markup
    annual_maint_markup = round2(annual_maintenance_cost * (maint_markup_pct / 100))
    monthly_maint_markup = round2(annual_maint_markup / 12)

    prof_vacancy_loss = round2(total_annual_rent * (prof_vacancy_rate / 100))

    prof_total_fees = round2(annual_mgmt_fee + annual_leasing_amortized + annual_maint_markup)
    prof_total_cost = round2(prof_total_fees + prof_vacancy_loss)

    # ---- Cost comparison ----
    annual_difference = round2(prof_total_cost - self_total_cost)
    monthly_difference = round2(annual_difference / 12)
    cheaper_option = "self_management" if annual_difference > 0 else "professional_management"
    annual_savings = round2(abs(annual_difference))

    # ---- Break-even analysis ----
    # Find unit count where professional mgmt cost == self-mgmt cost
    # Self cost scales linearly with vacancy but opportunity cost stays similar per unit
    # Prof cost scales linearly with rent
    # Per-unit self cost = (hours_per_week * hourly_value * 52 / 12 * 12) / num_units + annual_rent_per_unit * self_vacancy / 100
    # Actually, more hours needed per unit, assume linear scaling
    per_unit_self_hours_year = hours_per_year / num_units if num_units > 0 else hours_per_year
    per_unit_self_cost = per_unit_self_hours_year * hourly_value + monthly_rent * 12 * (self_vacancy_rate / 100)
    per_unit_prof_cost = monthly_rent * 12 * (mgmt_fee_pct / 100) + (
        leasing_fee_per_unit * 12 / avg_tenant_stay_months
    ) + (annual_maintenance_cost / num_units if num_units > 0 else 0) * (maint_markup_pct / 100) + (
        monthly_rent * 12 * (prof_vacancy_rate / 100)
    )

    # Break-even: n * per_unit_prof_cost = hours_per_week * hourly_value * 52 + n * monthly_rent * 12 * self_vacancy / 100
    # Rearranging with assumption that self-mgmt hours scale ~sqrt(n) or linearly
    # Simplified: total_self = base_hours_cost + n * vacancy_cost_self
    #             total_prof = n * per_unit_prof_cost
    # base_hours_cost = hours_per_week * hourly_value * 52 (fixed time commitment)
    # n * per_unit_prof_cost = base_hours_cost + n * per_unit_vacancy_self
    # n = base_hours_cost / (per_unit_prof_cost - per_unit_vacancy_self)
    base_hours_cost = hours_per_week * hourly_value * 52
    per_unit_vacancy_self = monthly_rent * 12 * (self_vacancy_rate / 100)
    denominator = per_unit_prof_cost - per_unit_vacancy_self
    break_even_units = round2(base_hours_cost / denominator) if denominator > 0 else 0
    break_even_units_rounded = max(1, int(round(break_even_units))) if break_even_units > 0 else 0

    # ---- Time value analysis ----
    monthly_time_saved = round2(hours_per_month) if cheaper_option == "professional_management" else 0
    annual_time_saved = round2(hours_per_year)
    time_value_of_savings = round2(annual_time_saved * hourly_value)
    cost_per_hour_saved = round2(prof_total_fees / hours_per_year) if hours_per_year > 0 else 0

    # ---- Efficiency metrics ----
    self_cost_per_unit = round2(self_total_cost / num_units) if num_units > 0 else 0
    prof_cost_per_unit = round2(prof_total_cost / num_units) if num_units > 0 else 0
    self_cost_pct_of_rent = round2(self_total_cost / total_annual_rent * 100) if total_annual_rent > 0 else 0
    prof_cost_pct_of_rent = round2(prof_total_cost / total_annual_rent * 100) if total_annual_rent > 0 else 0

    # ---- Risk comparison ----
    vacancy_difference = round2(self_vacancy_rate - prof_vacancy_rate)
    vacancy_cost_impact = round2(total_annual_rent * (vacancy_difference / 100))

    # ---- Recommendations ----
    recommendations: list[str] = []
    if num_units >= break_even_units_rounded and break_even_units_rounded > 0:
        recommendations.append(
            f"With {num_units} units, professional management is cost-effective "
            f"(break-even is {break_even_units_rounded} units)."
        )
    else:
        recommendations.append(
            f"Self-management is more cost-effective at {num_units} units. "
            f"Consider professional management at {break_even_units_rounded}+ units."
        )

    if effective_hourly_rate < hourly_value:
        recommendations.append(
            "Your time is worth more than the effective savings from self-managing. "
            "Consider professional management."
        )
    else:
        recommendations.append(
            "Self-management yields a good effective hourly rate for your time."
        )

    if prof_vacancy_rate < self_vacancy_rate:
        recommendations.append(
            f"Professional managers may reduce vacancy by {vacancy_difference}%, "
            f"saving ~${abs(vacancy_cost_impact):,.2f}/year."
        )

    if annual_maintenance_cost > 0 and maint_markup_pct > 0:
        recommendations.append(
            f"Maintenance markup adds ${annual_maint_markup:,.2f}/year. "
            "Consider negotiating this rate or handling maintenance directly."
        )

    return {
        "self_management_analysis": {
            "costs": {
                "monthly_opportunity_cost": monthly_opportunity_cost,
                "annual_opportunity_cost": annual_opportunity_cost,
                "annual_vacancy_loss": self_vacancy_loss,
                "total_annual_cost": self_total_cost,
            },
            "time_commitment": {
                "hours_per_week": hours_per_week,
                "hours_per_month": hours_per_month,
                "hours_per_year": hours_per_year,
            },
            "effective_hourly_rate": effective_hourly_rate,
        },
        "professional_management_analysis": {
            "costs": {
                "monthly_management_fee": monthly_mgmt_fee,
                "annual_management_fee": annual_mgmt_fee,
                "annual_leasing_fee_amortized": annual_leasing_amortized,
                "annual_maintenance_markup": annual_maint_markup,
                "annual_vacancy_loss": prof_vacancy_loss,
                "total_annual_fees": prof_total_fees,
                "total_annual_cost": prof_total_cost,
            },
            "fees_breakdown": {
                "management_fee_percent": mgmt_fee_pct,
                "leasing_fee_percent": leasing_fee_pct,
                "maintenance_markup_percent": maint_markup_pct,
                "monthly_management_fee": monthly_mgmt_fee,
                "monthly_leasing_amortized": monthly_leasing_amortized,
                "monthly_maintenance_markup": monthly_maint_markup,
            },
        },
        "cost_comparison": {
            "annual_difference": annual_difference,
            "monthly_difference": monthly_difference,
            "cheaper_option": cheaper_option,
            "annual_savings": annual_savings,
        },
        "break_even_analysis": {
            "break_even_units": break_even_units,
            "break_even_units_rounded": break_even_units_rounded,
            "current_units": num_units,
            "above_break_even": num_units >= break_even_units_rounded > 0,
        },
        "time_value_analysis": {
            "monthly_time_saved_with_professional": monthly_time_saved,
            "annual_time_saved_with_professional": annual_time_saved,
            "time_value_of_savings": time_value_of_savings,
            "cost_per_hour_saved": cost_per_hour_saved,
            "hourly_value": hourly_value,
        },
        "efficiency_metrics": {
            "self_cost_per_unit": self_cost_per_unit,
            "professional_cost_per_unit": prof_cost_per_unit,
            "self_cost_percent_of_rent": self_cost_pct_of_rent,
            "professional_cost_percent_of_rent": prof_cost_pct_of_rent,
        },
        "risk_comparison": {
            "self_vacancy_rate": self_vacancy_rate,
            "professional_vacancy_rate": prof_vacancy_rate,
            "vacancy_rate_difference": vacancy_difference,
            "annual_vacancy_cost_impact": vacancy_cost_impact,
            "self_management_risks": [
                "Higher vacancy rates without professional marketing",
                "Tenant screening may be less rigorous",
                "Legal compliance responsibility falls on owner",
                "Maintenance response times may be slower",
            ],
            "professional_management_risks": [
                "Less direct control over property",
                "Maintenance markup increases costs",
                "Manager priorities may not align with owner",
                "Communication delays possible",
            ],
        },
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 2. track_property_expenses
# ---------------------------------------------------------------------------

def track_property_expenses(
    expenses: list[dict],
    property_value: float = 0,
    monthly_rent: float = 0,
    annual_budget: dict | None = None,
) -> dict:
    """Aggregate, benchmark, and analyse property expenses.

    Each expense dict: category, amount, date (YYYY-MM), description.

    Returns expense summary, benchmarking, budget analysis, tax classification,
    expense ratios, trends, and recommendations.
    """
    # ---- Aggregate by category and month ----
    by_category: dict[str, float] = defaultdict(float)
    by_month: dict[str, float] = defaultdict(float)
    by_category_month: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    category_counts: dict[str, int] = defaultdict(int)

    for exp in expenses:
        cat = exp.get("category", "other")
        amt = float(exp.get("amount", 0))
        date = exp.get("date", "unknown")
        by_category[cat] += amt
        by_month[date] += amt
        by_category_month[cat][date] += amt
        category_counts[cat] += 1

    total_expenses = round2(sum(by_category.values()))
    sorted_months = sorted(by_month.keys())
    num_months = len(sorted_months) if sorted_months else 1

    monthly_average = round2(total_expenses / num_months)

    by_category_rounded = {k: round2(v) for k, v in sorted(by_category.items(), key=lambda x: -x[1])}
    by_month_rounded = {k: round2(by_month[k]) for k in sorted_months}

    # Category details
    category_details: dict[str, dict] = {}
    for cat, total in by_category.items():
        months_with_expense = len(by_category_month[cat])
        category_details[cat] = {
            "total": round2(total),
            "count": category_counts[cat],
            "monthly_average": round2(total / num_months),
            "percent_of_total": round2(total / total_expenses * 100) if total_expenses > 0 else 0,
        }

    # ---- Benchmarking ----
    benchmarking: dict[str, dict] = {}
    annual_rent = monthly_rent * 12

    for cat, bench in EXPENSE_BENCHMARKS.items():
        if cat not in by_category:
            continue
        actual_annual = by_category[cat] * (12 / num_months)  # annualize
        if bench["basis"] == "property_value" and property_value > 0:
            actual_pct = actual_annual / property_value * 100
            expected_low = property_value * (bench["low"] / 100)
            expected_high = property_value * (bench["high"] / 100)
        elif bench["basis"] == "rent" and annual_rent > 0:
            actual_pct = actual_annual / annual_rent * 100
            expected_low = annual_rent * (bench["low"] / 100)
            expected_high = annual_rent * (bench["high"] / 100)
        else:
            continue

        if actual_annual < expected_low:
            status = "below_average"
        elif actual_annual > expected_high:
            status = "above_average"
        else:
            status = "within_range"

        benchmarking[cat] = {
            "actual_annual": round2(actual_annual),
            "actual_percent": round2(actual_pct),
            "benchmark_low_percent": bench["low"],
            "benchmark_high_percent": bench["high"],
            "benchmark_low_amount": round2(expected_low),
            "benchmark_high_amount": round2(expected_high),
            "status": status,
            "basis": bench["basis"],
        }

    # ---- Budget analysis ----
    budget_analysis: dict | None = None
    if annual_budget is not None:
        total_budget = sum(annual_budget.values()) if annual_budget else 0
        # Annualise actual expenses
        annualised_total = total_expenses * (12 / num_months)
        budget_variance = round2(total_budget - annualised_total)
        budget_utilization = round2(annualised_total / total_budget * 100) if total_budget > 0 else 0

        category_variances: dict[str, dict] = {}
        for cat, budgeted in annual_budget.items():
            actual_annual = by_category.get(cat, 0) * (12 / num_months)
            variance = round2(budgeted - actual_annual)
            utilization = round2(actual_annual / budgeted * 100) if budgeted > 0 else 0
            status = "under_budget" if variance > 0 else "over_budget" if variance < 0 else "on_budget"
            category_variances[cat] = {
                "budgeted": round2(budgeted),
                "actual_annualised": round2(actual_annual),
                "variance": variance,
                "utilization_percent": utilization,
                "status": status,
            }

        budget_analysis = {
            "total_budget": round2(total_budget),
            "total_annualised_expenses": round2(annualised_total),
            "total_variance": budget_variance,
            "budget_utilization_percent": budget_utilization,
            "overall_status": "under_budget" if budget_variance > 0 else "over_budget" if budget_variance < 0 else "on_budget",
            "category_variances": category_variances,
        }

    # ---- Tax classification ----
    deductible_total = 0.0
    non_deductible_total = 0.0
    deductible_items: dict[str, float] = {}
    non_deductible_items: dict[str, float] = {}

    for cat, total in by_category.items():
        if cat in TAX_DEDUCTIBLE_CATEGORIES:
            deductible_total += total
            deductible_items[cat] = round2(total)
        else:
            non_deductible_total += total
            non_deductible_items[cat] = round2(total)

    tax_classification = {
        "deductible": {
            "total": round2(deductible_total),
            "categories": deductible_items,
        },
        "non_deductible": {
            "total": round2(non_deductible_total),
            "categories": non_deductible_items,
            "note": "Mortgage principal and CapEx are capitalised/depreciated, not directly deducted.",
        },
        "deductible_percent": round2(deductible_total / total_expenses * 100) if total_expenses > 0 else 0,
    }

    # ---- Expense ratios ----
    expense_ratios: dict[str, float] = {}
    if property_value > 0:
        annualised = total_expenses * (12 / num_months)
        expense_ratios["expense_to_value_percent"] = round2(annualised / property_value * 100)
    if annual_rent > 0:
        annualised = total_expenses * (12 / num_months)
        expense_ratios["expense_to_rent_percent"] = round2(annualised / annual_rent * 100)
        expense_ratios["operating_expense_ratio"] = round2(
            (annualised - by_category.get("mortgage", 0) * (12 / num_months)) / annual_rent * 100
        )
    expense_ratios["average_monthly_expense"] = monthly_average

    # ---- Trends ----
    trends: dict = {}
    if len(sorted_months) >= 2:
        monthly_values = [by_month[m] for m in sorted_months]
        first_half = monthly_values[: len(monthly_values) // 2]
        second_half = monthly_values[len(monthly_values) // 2 :]
        avg_first = sum(first_half) / len(first_half) if first_half else 0
        avg_second = sum(second_half) / len(second_half) if second_half else 0
        trend_direction = "increasing" if avg_second > avg_first * 1.05 else (
            "decreasing" if avg_second < avg_first * 0.95 else "stable"
        )
        month_over_month_changes: list[dict] = []
        for i in range(1, len(sorted_months)):
            prev = by_month[sorted_months[i - 1]]
            curr = by_month[sorted_months[i]]
            change = round2(curr - prev)
            change_pct = round2((curr - prev) / prev * 100) if prev > 0 else 0
            month_over_month_changes.append({
                "month": sorted_months[i],
                "change": change,
                "change_percent": change_pct,
            })

        trends = {
            "direction": trend_direction,
            "average_first_half": round2(avg_first),
            "average_second_half": round2(avg_second),
            "month_over_month": month_over_month_changes,
            "highest_month": max(sorted_months, key=lambda m: by_month[m]),
            "lowest_month": min(sorted_months, key=lambda m: by_month[m]),
        }

    # ---- Recommendations ----
    recommendations: list[str] = []
    for cat, bench_info in benchmarking.items():
        if bench_info["status"] == "above_average":
            recommendations.append(
                f"{cat.capitalize()} expenses are above industry averages "
                f"({bench_info['actual_percent']:.1f}% vs {bench_info['benchmark_low_percent']}-"
                f"{bench_info['benchmark_high_percent']}%). Review for savings opportunities."
            )
        elif bench_info["status"] == "below_average":
            recommendations.append(
                f"{cat.capitalize()} expenses are below average. "
                "Ensure adequate spending to maintain property condition."
            )

    if budget_analysis and budget_analysis["overall_status"] == "over_budget":
        recommendations.append(
            f"Overall spending is ${abs(budget_analysis['total_variance']):,.2f} over budget. "
            "Review discretionary expenses."
        )

    if trends.get("direction") == "increasing":
        recommendations.append(
            "Expenses are trending upward. Investigate the cause and consider cost controls."
        )

    if not recommendations:
        recommendations.append("Expenses appear to be within normal ranges.")

    return {
        "expense_summary": {
            "by_category": by_category_rounded,
            "by_month": by_month_rounded,
            "category_details": category_details,
            "total": total_expenses,
            "monthly_average": monthly_average,
            "num_months": num_months,
        },
        "benchmarking": benchmarking,
        "budget_analysis": budget_analysis,
        "tax_classification": tax_classification,
        "expense_ratios": expense_ratios,
        "trends": trends,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 3. track_deal_pipeline
# ---------------------------------------------------------------------------

def track_deal_pipeline(
    deals: list[dict],
    stage_probabilities: dict[str, float] | None = None,
) -> dict:
    """Analyse a real-estate deal pipeline.

    Each deal dict: name, stage, property_type, purchase_price,
    estimated_profit, offer_amount (optional), date_added, notes (optional).

    Returns pipeline summary, performance metrics, expected value analysis,
    pipeline health, stage analysis, and recommendations.
    """
    probs = stage_probabilities if stage_probabilities is not None else STAGE_PROBABILITIES
    total_deals = len(deals)
    if total_deals == 0:
        return {
            "pipeline_summary": {
                "total_deals": 0,
                "by_stage": {},
                "total_value": 0,
            },
            "performance_metrics": {
                "conversion_rates": {},
                "avg_deal_size": 0,
            },
            "expected_value_analysis": {
                "total_expected_value": 0,
                "by_stage": {},
            },
            "pipeline_health": {
                "score": 0,
                "status": "empty",
                "issues": ["No deals in pipeline."],
            },
            "stage_analysis": {},
            "recommendations": ["Start adding deals to your pipeline."],
        }

    # ---- Aggregate by stage ----
    by_stage: dict[str, list[dict]] = defaultdict(list)
    by_type: dict[str, int] = defaultdict(int)

    for deal in deals:
        stage = deal.get("stage", "prospect")
        by_stage[stage].append(deal)
        ptype = deal.get("property_type", "unknown")
        by_type[ptype] += 1

    stage_summary: dict[str, dict] = {}
    for stage in STAGE_ORDER:
        stage_deals = by_stage.get(stage, [])
        if not stage_deals:
            continue
        total_value = sum(d.get("purchase_price", 0) for d in stage_deals)
        total_profit = sum(d.get("estimated_profit", 0) for d in stage_deals)
        stage_summary[stage] = {
            "count": len(stage_deals),
            "total_value": round2(total_value),
            "total_estimated_profit": round2(total_profit),
            "avg_deal_size": round2(total_value / len(stage_deals)),
            "probability": probs.get(stage, 0),
        }

    total_pipeline_value = round2(sum(
        d.get("purchase_price", 0) for d in deals if d.get("stage") != "dead"
    ))

    # ---- Performance metrics ----
    active_deals = [d for d in deals if d.get("stage") not in ("dead", "closed")]
    closed_deals = [d for d in deals if d.get("stage") == "closed"]
    dead_deals = [d for d in deals if d.get("stage") == "dead"]

    avg_deal_size = round2(
        sum(d.get("purchase_price", 0) for d in deals) / total_deals
    ) if total_deals > 0 else 0

    avg_profit = round2(
        sum(d.get("estimated_profit", 0) for d in deals) / total_deals
    ) if total_deals > 0 else 0

    # Conversion rates by stage (deals that passed through each stage)
    # Approximated: count of deals in this stage or later / total non-dead deals
    non_dead = [d for d in deals if d.get("stage") != "dead"]
    total_non_dead = len(non_dead) if non_dead else 1

    conversion_rates: dict[str, float] = {}
    for i, stage in enumerate(STAGE_ORDER):
        if stage in ("dead",):
            continue
        # Deals at this stage or later
        later_stages = set(STAGE_ORDER[i:]) - {"dead"}
        count_at_or_past = sum(1 for d in non_dead if d.get("stage") in later_stages)
        conversion_rates[stage] = round2(count_at_or_past / total_non_dead * 100) if total_non_dead > 0 else 0

    overall_conversion = round2(
        len(closed_deals) / total_deals * 100
    ) if total_deals > 0 else 0

    # ---- Expected value analysis ----
    total_expected_value = 0.0
    ev_by_stage: dict[str, dict] = {}

    for stage in STAGE_ORDER:
        stage_deals = by_stage.get(stage, [])
        if not stage_deals:
            continue
        prob = probs.get(stage, 0) / 100
        stage_profit = sum(d.get("estimated_profit", 0) for d in stage_deals)
        stage_ev = round2(stage_profit * prob)
        total_expected_value += stage_ev
        ev_by_stage[stage] = {
            "total_estimated_profit": round2(stage_profit),
            "probability": probs.get(stage, 0),
            "expected_value": stage_ev,
            "deal_count": len(stage_deals),
        }

    total_expected_value = round2(total_expected_value)

    # ---- Pipeline velocity (time between date_added and now) ----
    today = datetime.now()
    stage_ages: dict[str, list[float]] = defaultdict(list)
    for deal in deals:
        date_str = deal.get("date_added", "")
        if not date_str:
            continue
        try:
            added = datetime.strptime(date_str, "%Y-%m-%d")
            days_in_pipeline = (today - added).days
            stage = deal.get("stage", "prospect")
            stage_ages[stage].append(days_in_pipeline)
        except (ValueError, TypeError):
            continue

    velocity: dict[str, dict] = {}
    for stage, ages in stage_ages.items():
        velocity[stage] = {
            "avg_days_in_pipeline": round2(sum(ages) / len(ages)) if ages else 0,
            "min_days": min(ages) if ages else 0,
            "max_days": max(ages) if ages else 0,
            "deal_count": len(ages),
        }

    # ---- Pipeline health ----
    health_score = 100.0
    issues: list[str] = []

    # Check for pipeline balance
    prospect_count = len(by_stage.get("prospect", []))
    closing_count = len(by_stage.get("closing", []) + by_stage.get("under_contract", []) + by_stage.get("due_diligence", []))

    if prospect_count == 0 and active_deals:
        health_score -= 20
        issues.append("No prospects in pipeline. Add new leads to maintain deal flow.")

    if len(active_deals) == 0:
        health_score -= 30
        issues.append("No active deals. Pipeline needs new opportunities.")

    dead_ratio = len(dead_deals) / total_deals if total_deals > 0 else 0
    if dead_ratio > 0.5:
        health_score -= 20
        issues.append(
            f"High dead-deal ratio ({dead_ratio:.0%}). Review deal qualification criteria."
        )

    # Check concentration
    if total_deals > 3:
        stage_counts = [len(by_stage.get(s, [])) for s in STAGE_ORDER if s not in ("dead", "closed")]
        max_in_stage = max(stage_counts) if stage_counts else 0
        if max_in_stage / total_deals > 0.6:
            health_score -= 15
            issues.append("Pipeline is concentrated in one stage. Aim for better distribution.")

    # Age check
    for stage, vel in velocity.items():
        if stage not in ("closed", "dead") and vel["avg_days_in_pipeline"] > 90:
            health_score -= 10
            issues.append(
                f"Deals in '{stage}' stage averaging {vel['avg_days_in_pipeline']:.0f} days. "
                "Consider following up or closing stale deals."
            )
            break  # Only penalise once

    health_score = max(0, min(100, health_score))
    if health_score >= 80:
        health_status = "healthy"
    elif health_score >= 50:
        health_status = "needs_attention"
    else:
        health_status = "critical"

    if not issues:
        issues.append("Pipeline appears healthy.")

    # ---- Stage analysis (detailed) ----
    stage_analysis: dict[str, dict] = {}
    for stage in STAGE_ORDER:
        stage_deals = by_stage.get(stage, [])
        if not stage_deals:
            continue
        deal_names = [d.get("name", "unnamed") for d in stage_deals]
        types = defaultdict(int)
        for d in stage_deals:
            types[d.get("property_type", "unknown")] += 1

        total_value = sum(d.get("purchase_price", 0) for d in stage_deals)
        total_profit = sum(d.get("estimated_profit", 0) for d in stage_deals)
        offer_amounts = [d.get("offer_amount", 0) for d in stage_deals if d.get("offer_amount")]

        stage_analysis[stage] = {
            "deal_count": len(stage_deals),
            "deals": deal_names,
            "property_types": dict(types),
            "total_purchase_price": round2(total_value),
            "total_estimated_profit": round2(total_profit),
            "avg_purchase_price": round2(total_value / len(stage_deals)),
            "avg_estimated_profit": round2(total_profit / len(stage_deals)),
            "probability": probs.get(stage, 0),
            "velocity": velocity.get(stage, {}),
        }
        if offer_amounts:
            stage_analysis[stage]["avg_offer_amount"] = round2(sum(offer_amounts) / len(offer_amounts))

    # ---- Recommendations ----
    recommendations: list[str] = []

    if prospect_count < 3 and total_deals > 0:
        recommendations.append(
            "Maintain at least 3 prospects in the pipeline for consistent deal flow."
        )

    if overall_conversion > 0 and overall_conversion < 10:
        recommendations.append(
            f"Overall conversion rate is {overall_conversion}%. "
            "Improve deal qualification to increase close rates."
        )
    elif overall_conversion >= 30:
        recommendations.append(
            f"Strong conversion rate of {overall_conversion}%. "
            "Consider increasing deal volume to grow portfolio."
        )

    if dead_ratio > 0.3:
        recommendations.append(
            "Significant portion of deals are dead. Analyse common failure points."
        )

    # Value concentration
    if closed_deals:
        avg_closed_profit = sum(d.get("estimated_profit", 0) for d in closed_deals) / len(closed_deals)
        if avg_closed_profit > 0:
            recommendations.append(
                f"Average closed deal profit: ${avg_closed_profit:,.2f}. "
                "Use this as a benchmark for evaluating new opportunities."
            )

    if total_expected_value > 0:
        recommendations.append(
            f"Pipeline expected value is ${total_expected_value:,.2f}. "
            "Focus on advancing high-probability deals to maximise returns."
        )

    if not recommendations:
        recommendations.append("Pipeline metrics look good. Keep up the momentum.")

    return {
        "pipeline_summary": {
            "total_deals": total_deals,
            "active_deals": len(active_deals),
            "closed_deals": len(closed_deals),
            "dead_deals": len(dead_deals),
            "by_stage": stage_summary,
            "by_property_type": dict(by_type),
            "total_value": total_pipeline_value,
        },
        "performance_metrics": {
            "avg_deal_size": avg_deal_size,
            "avg_estimated_profit": avg_profit,
            "overall_conversion_rate": overall_conversion,
            "conversion_rates": conversion_rates,
        },
        "expected_value_analysis": {
            "total_expected_value": total_expected_value,
            "by_stage": ev_by_stage,
        },
        "pipeline_health": {
            "score": round2(health_score),
            "status": health_status,
            "issues": issues,
        },
        "stage_analysis": stage_analysis,
        "recommendations": recommendations,
    }
