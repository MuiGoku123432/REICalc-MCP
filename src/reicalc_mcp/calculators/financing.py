"""Financing calculators: refinance, construction loan, hard money, seller financing."""

from typing import Any

from ._common import calculate_mortgage_payment, calculate_irr, calculate_npv, round2


# ---------------------------------------------------------------------------
# 1. Refinance Analysis
# ---------------------------------------------------------------------------

def analyze_refinance(
    current_loan_balance: float,
    current_interest_rate: float,
    current_monthly_payment: float,
    current_remaining_years: float,
    new_interest_rate: float,
    new_loan_term_years: int = 30,
    new_closing_costs: float = 0,
    cash_out_amount: float = 0,
    property_value: float = 0,
) -> dict:
    """Analyze whether refinancing a mortgage makes financial sense."""

    # --- Current loan ---
    current_monthly_rate = current_interest_rate / 100 / 12
    current_remaining_months = int(current_remaining_years * 12)
    current_total_remaining = current_monthly_payment * current_remaining_months
    current_total_interest = current_total_remaining - current_loan_balance

    current_loan = {
        "balance": round2(current_loan_balance),
        "interest_rate": current_interest_rate,
        "monthly_payment": round2(current_monthly_payment),
        "remaining_years": current_remaining_years,
        "remaining_months": current_remaining_months,
        "total_remaining_payments": round2(current_total_remaining),
        "total_remaining_interest": round2(current_total_interest),
    }

    # --- New loan ---
    new_loan_amount = current_loan_balance + cash_out_amount + new_closing_costs
    new_monthly_rate = new_interest_rate / 100 / 12
    new_num_payments = new_loan_term_years * 12
    new_monthly_payment = calculate_mortgage_payment(
        new_loan_amount, new_monthly_rate, new_num_payments,
    )
    new_total_payments = new_monthly_payment * new_num_payments
    new_total_interest = new_total_payments - new_loan_amount

    new_ltv = (new_loan_amount / property_value * 100) if property_value > 0 else 0

    new_loan = {
        "loan_amount": round2(new_loan_amount),
        "interest_rate": new_interest_rate,
        "loan_term_years": new_loan_term_years,
        "monthly_payment": round2(new_monthly_payment),
        "total_payments": round2(new_total_payments),
        "total_interest": round2(new_total_interest),
        "closing_costs": round2(new_closing_costs),
        "cash_out_amount": round2(cash_out_amount),
        "ltv": round2(new_ltv),
    }

    # --- Monthly comparison ---
    monthly_savings = current_monthly_payment - new_monthly_payment

    monthly_comparison = {
        "current_payment": round2(current_monthly_payment),
        "new_payment": round2(new_monthly_payment),
        "monthly_savings": round2(monthly_savings),
        "annual_savings": round2(monthly_savings * 12),
    }

    # --- Break-even analysis ---
    if monthly_savings > 0:
        break_even_months = new_closing_costs / monthly_savings
        break_even_years = break_even_months / 12
    else:
        break_even_months = float("inf")
        break_even_years = float("inf")

    break_even_analysis = {
        "closing_costs": round2(new_closing_costs),
        "monthly_savings": round2(monthly_savings),
        "break_even_months": round2(break_even_months) if break_even_months != float("inf") else None,
        "break_even_years": round2(break_even_years) if break_even_years != float("inf") else None,
        "recoverable": monthly_savings > 0,
    }

    # --- Total cost comparison ---
    # Compare over the shorter of the two remaining terms
    comparison_months = min(current_remaining_months, new_num_payments)

    current_total_cost_over_period = current_monthly_payment * comparison_months
    new_total_cost_over_period = new_monthly_payment * comparison_months + new_closing_costs

    # Full lifetime comparison
    total_cost_comparison = {
        "comparison_period_months": comparison_months,
        "current_total_cost": round2(current_total_remaining),
        "new_total_cost": round2(new_total_payments + new_closing_costs),
        "total_savings": round2(current_total_remaining - (new_total_payments + new_closing_costs)),
        "current_total_interest": round2(current_total_interest),
        "new_total_interest": round2(new_total_interest),
        "interest_savings": round2(current_total_interest - new_total_interest),
    }

    # --- NPV of savings ---
    discount_rate = new_interest_rate / 100 / 12  # use new rate as discount
    savings_cash_flows = [-new_closing_costs]
    for _ in range(comparison_months):
        savings_cash_flows.append(monthly_savings)
    npv_savings = calculate_npv(savings_cash_flows, discount_rate)

    npv_analysis = {
        "discount_rate_annual": new_interest_rate,
        "npv_of_savings": round2(npv_savings),
        "npv_positive": npv_savings > 0,
    }

    # --- Cash-out analysis ---
    cash_out_analysis: dict[str, Any] | None = None
    if cash_out_amount > 0:
        # Cost of cash-out: additional interest over the life of the loan
        base_loan_amount = current_loan_balance + new_closing_costs
        base_payment = calculate_mortgage_payment(
            base_loan_amount, new_monthly_rate, new_num_payments,
        )
        additional_payment = new_monthly_payment - base_payment
        cost_of_cash_out = additional_payment * new_num_payments

        # ROI scenarios for cash-out usage
        roi_scenarios = []
        for roi_label, annual_roi in [
            ("Home improvement (15% ROI)", 0.15),
            ("Debt consolidation (8% savings)", 0.08),
            ("Investment (10% return)", 0.10),
            ("Emergency fund (3% return)", 0.03),
        ]:
            net_gain = cash_out_amount * annual_roi * new_loan_term_years - cost_of_cash_out
            roi_scenarios.append({
                "scenario": roi_label,
                "estimated_return": round2(cash_out_amount * annual_roi * new_loan_term_years),
                "cost_of_borrowing": round2(cost_of_cash_out),
                "net_gain_loss": round2(net_gain),
                "profitable": net_gain > 0,
            })

        cash_out_analysis = {
            "cash_out_amount": round2(cash_out_amount),
            "additional_monthly_cost": round2(additional_payment),
            "total_cost_of_cash_out": round2(cost_of_cash_out),
            "effective_cash_out_rate": round2(
                (cost_of_cash_out / cash_out_amount * 100) if cash_out_amount > 0 else 0
            ),
            "roi_scenarios": roi_scenarios,
        }

    # --- Recommendations ---
    recommendations = _refinance_recommendations(
        monthly_savings, break_even_months, break_even_years,
        current_interest_rate, new_interest_rate, current_remaining_years,
        new_loan_term_years, cash_out_amount, new_ltv,
    )

    result: dict[str, Any] = {
        "current_loan": current_loan,
        "new_loan": new_loan,
        "monthly_comparison": monthly_comparison,
        "break_even_analysis": break_even_analysis,
        "total_cost_comparison": total_cost_comparison,
        "npv_analysis": npv_analysis,
        "recommendations": recommendations,
    }
    if cash_out_analysis is not None:
        result["cash_out_analysis"] = cash_out_analysis

    return result


def _refinance_recommendations(
    monthly_savings: float,
    break_even_months: float,
    break_even_years: float,
    current_rate: float,
    new_rate: float,
    current_remaining_years: float,
    new_term_years: int,
    cash_out_amount: float,
    new_ltv: float,
) -> list[str]:
    recs: list[str] = []
    rate_diff = current_rate - new_rate

    if rate_diff >= 1.0:
        recs.append(
            f"Rate reduction of {rate_diff:.2f}% is significant. "
            "Refinancing is generally recommended with a rate drop of 1% or more."
        )
    elif rate_diff >= 0.5:
        recs.append(
            f"Rate reduction of {rate_diff:.2f}% is moderate. "
            "Evaluate break-even period carefully before proceeding."
        )
    elif rate_diff > 0:
        recs.append(
            f"Rate reduction of {rate_diff:.2f}% is small. "
            "The break-even period may be too long to justify refinancing."
        )
    else:
        recs.append(
            "The new rate is not lower than your current rate. "
            "Refinancing for rate reduction is not recommended."
        )

    if monthly_savings > 0 and break_even_months != float("inf"):
        if break_even_months <= 24:
            recs.append(
                f"Break-even in {break_even_months:.0f} months ({break_even_years:.1f} years) is excellent. "
                "You will recover closing costs quickly."
            )
        elif break_even_months <= 48:
            recs.append(
                f"Break-even in {break_even_months:.0f} months ({break_even_years:.1f} years) is reasonable "
                "if you plan to stay in the home long-term."
            )
        else:
            recs.append(
                f"Break-even of {break_even_months:.0f} months ({break_even_years:.1f} years) is lengthy. "
                "Only refinance if you plan to remain in the property for many years."
            )

    if new_term_years > current_remaining_years:
        recs.append(
            f"The new loan extends your term from {current_remaining_years:.1f} to {new_term_years} years. "
            "Consider whether the lower payment justifies the extended timeline."
        )

    if cash_out_amount > 0:
        recs.append(
            "Cash-out refinancing increases your loan balance. "
            "Ensure the funds are used for value-adding purposes such as home improvements or debt consolidation."
        )
        if new_ltv > 80:
            recs.append(
                f"Cash-out brings your LTV to {new_ltv:.1f}%, which may require PMI. "
                "Consider reducing the cash-out amount."
            )

    if not recs:
        recs.append("Review the numbers carefully and consult a mortgage professional before proceeding.")

    return recs


# ---------------------------------------------------------------------------
# 2. Construction Loan Analysis
# ---------------------------------------------------------------------------

_DEFAULT_DRAW_SCHEDULE = [
    {"phase": "Foundation", "percent": 10, "description": "Site prep, excavation, foundation pour"},
    {"phase": "Framing", "percent": 20, "description": "Structural framing, roof, windows"},
    {"phase": "MEP Rough-In", "percent": 20, "description": "Mechanical, electrical, plumbing rough-in"},
    {"phase": "Interior", "percent": 20, "description": "Insulation, drywall, interior finishes"},
    {"phase": "Finish", "percent": 15, "description": "Cabinets, counters, flooring, fixtures"},
    {"phase": "Landscaping & Final", "percent": 15, "description": "Landscaping, driveway, final touches"},
]


def analyze_construction_loan(
    land_cost: float,
    construction_budget: float,
    total_project_cost: float | None = None,
    construction_period_months: int = 12,
    interest_rate: float = 8,
    down_payment_percent: float = 20,
    permanent_loan_rate: float = 7,
    permanent_loan_term: int = 30,
    contingency_percent: float = 10,
    draw_schedule: list[dict[str, Any]] | None = None,
) -> dict:
    """Analyze a construction-to-permanent loan scenario."""

    # --- Project summary ---
    contingency = construction_budget * contingency_percent / 100
    calc_total_project_cost = total_project_cost if total_project_cost else (land_cost + construction_budget + contingency)

    project_summary = {
        "land_cost": round2(land_cost),
        "construction_budget": round2(construction_budget),
        "contingency": round2(contingency),
        "contingency_percent": contingency_percent,
        "total_project_cost": round2(calc_total_project_cost),
    }

    # --- Construction loan ---
    down_payment = calc_total_project_cost * down_payment_percent / 100
    construction_loan_amount = calc_total_project_cost - down_payment
    monthly_rate = interest_rate / 100 / 12

    construction_loan = {
        "loan_amount": round2(construction_loan_amount),
        "interest_rate": interest_rate,
        "down_payment": round2(down_payment),
        "down_payment_percent": down_payment_percent,
        "construction_period_months": construction_period_months,
    }

    # --- Draw schedule ---
    phases = draw_schedule if draw_schedule else _DEFAULT_DRAW_SCHEDULE
    built_draw_schedule: list[dict[str, Any]] = []
    cumulative_drawn = 0.0
    months_per_phase = max(1, construction_period_months // len(phases))
    current_month = 1

    for i, phase in enumerate(phases):
        pct = phase.get("percent", 0)
        draw_amount = construction_loan_amount * pct / 100
        cumulative_drawn += draw_amount

        built_draw_schedule.append({
            "phase": phase.get("phase", f"Phase {i + 1}"),
            "description": phase.get("description", ""),
            "percent_of_total": pct,
            "draw_amount": round2(draw_amount),
            "cumulative_drawn": round2(cumulative_drawn),
            "month": current_month,
        })
        current_month += months_per_phase

    # --- Interest analysis (monthly interest on drawn balance) ---
    interest_analysis: list[dict[str, Any]] = []
    total_construction_interest = 0.0
    drawn_balance = 0.0
    phase_idx = 0

    for month in range(1, construction_period_months + 1):
        # Check if a draw happens this month
        while phase_idx < len(built_draw_schedule) and built_draw_schedule[phase_idx]["month"] <= month:
            if built_draw_schedule[phase_idx]["month"] == month:
                drawn_balance += built_draw_schedule[phase_idx]["draw_amount"]
            phase_idx += 1

        month_interest = drawn_balance * monthly_rate
        total_construction_interest += month_interest

        interest_analysis.append({
            "month": month,
            "drawn_balance": round2(drawn_balance),
            "monthly_interest": round2(month_interest),
            "cumulative_interest": round2(total_construction_interest),
        })

    # --- Permanent loan conversion ---
    permanent_loan_amount = construction_loan_amount + total_construction_interest
    perm_monthly_rate = permanent_loan_rate / 100 / 12
    perm_num_payments = permanent_loan_term * 12
    perm_monthly_payment = calculate_mortgage_payment(
        permanent_loan_amount, perm_monthly_rate, perm_num_payments,
    )
    perm_total_payments = perm_monthly_payment * perm_num_payments
    perm_total_interest = perm_total_payments - permanent_loan_amount

    permanent_loan_conversion = {
        "permanent_loan_amount": round2(permanent_loan_amount),
        "interest_rate": permanent_loan_rate,
        "loan_term_years": permanent_loan_term,
        "monthly_payment": round2(perm_monthly_payment),
        "total_payments": round2(perm_total_payments),
        "total_interest": round2(perm_total_interest),
    }

    # --- Total project costs ---
    total_out_of_pocket = down_payment + total_construction_interest
    total_with_financing = down_payment + perm_total_payments

    total_project_costs = {
        "down_payment": round2(down_payment),
        "construction_interest": round2(total_construction_interest),
        "total_out_of_pocket_during_construction": round2(total_out_of_pocket),
        "permanent_loan_total_payments": round2(perm_total_payments),
        "total_cost_with_financing": round2(total_with_financing),
    }

    # --- Comparison to buying existing ---
    # Assume buying existing at project cost with a conventional loan
    existing_loan_amount = calc_total_project_cost - down_payment
    existing_monthly_payment = calculate_mortgage_payment(
        existing_loan_amount, perm_monthly_rate, perm_num_payments,
    )
    existing_total_payments = existing_monthly_payment * perm_num_payments

    payment_difference = perm_monthly_payment - existing_monthly_payment
    total_cost_difference = (perm_total_payments + total_construction_interest) - existing_total_payments

    comparison_to_existing = {
        "existing_home_price": round2(calc_total_project_cost),
        "existing_loan_amount": round2(existing_loan_amount),
        "existing_monthly_payment": round2(existing_monthly_payment),
        "existing_total_payments": round2(existing_total_payments),
        "construction_monthly_payment": round2(perm_monthly_payment),
        "monthly_payment_difference": round2(payment_difference),
        "total_cost_premium_for_construction": round2(total_cost_difference),
        "premium_explanation": "Construction interest during build phase increases total loan amount.",
    }

    # --- Risk assessment ---
    risk_assessment = _construction_risk_assessment(
        contingency_percent, construction_period_months, construction_loan_amount,
        calc_total_project_cost, interest_rate,
    )

    # --- Recommendations ---
    recommendations = _construction_recommendations(
        contingency_percent, construction_period_months, total_construction_interest,
        construction_loan_amount, payment_difference,
    )

    return {
        "project_summary": project_summary,
        "construction_loan": construction_loan,
        "draw_schedule": built_draw_schedule,
        "interest_analysis": interest_analysis,
        "permanent_loan_conversion": permanent_loan_conversion,
        "total_project_costs": total_project_costs,
        "comparison_to_existing": comparison_to_existing,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
    }


def _construction_risk_assessment(
    contingency_pct: float,
    period_months: int,
    loan_amount: float,
    total_cost: float,
    interest_rate: float,
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []

    if contingency_pct < 10:
        risks.append({
            "risk": "Low contingency reserve",
            "severity": "High",
            "detail": (
                f"Contingency of {contingency_pct}% is below the recommended 10-15%. "
                "Cost overruns are common in construction projects."
            ),
        })
    elif contingency_pct < 15:
        risks.append({
            "risk": "Moderate contingency reserve",
            "severity": "Medium",
            "detail": f"Contingency of {contingency_pct}% is adequate but consider 15% for complex projects.",
        })
    else:
        risks.append({
            "risk": "Adequate contingency reserve",
            "severity": "Low",
            "detail": f"Contingency of {contingency_pct}% provides a good buffer for unexpected costs.",
        })

    if period_months > 12:
        risks.append({
            "risk": "Extended construction timeline",
            "severity": "Medium",
            "detail": (
                f"A {period_months}-month build exposes you to more interest accumulation "
                "and potential material cost increases."
            ),
        })

    if interest_rate > 9:
        risks.append({
            "risk": "High construction loan rate",
            "severity": "Medium",
            "detail": (
                f"Construction loan rate of {interest_rate}% is elevated. "
                "Shop multiple lenders for better terms."
            ),
        })

    risks.append({
        "risk": "Construction delays",
        "severity": "Medium",
        "detail": (
            "Weather, permits, and supply chain issues commonly cause delays. "
            "Budget for 2-3 extra months of interest payments."
        ),
    })

    return risks


def _construction_recommendations(
    contingency_pct: float,
    period_months: int,
    total_interest: float,
    loan_amount: float,
    payment_diff: float,
) -> list[str]:
    recs: list[str] = []

    if contingency_pct < 10:
        recs.append(
            "Increase your contingency reserve to at least 10-15% of the construction budget "
            "to protect against cost overruns."
        )

    interest_pct = (total_interest / loan_amount * 100) if loan_amount > 0 else 0
    recs.append(
        f"Construction interest adds {interest_pct:.1f}% to your loan amount. "
        "Minimize draws early and accelerate the build to reduce carrying costs."
    )

    if period_months > 12:
        recs.append(
            "Consider ways to shorten the construction timeline to reduce interest accumulation."
        )

    if payment_diff > 0:
        recs.append(
            f"Your permanent mortgage will be ${payment_diff:,.0f}/month higher than buying an equivalent "
            "existing home due to construction interest rolled into the loan."
        )

    recs.append(
        "Get multiple contractor bids, lock in material costs where possible, "
        "and ensure your builder provides a detailed scope of work."
    )

    return recs


# ---------------------------------------------------------------------------
# 3. Hard Money Loan Analysis
# ---------------------------------------------------------------------------

def analyze_hard_money_loan(
    property_value: float,
    purchase_price: float,
    rehab_budget: float = 0,
    loan_to_value: float = 70,
    interest_rate: float = 12,
    loan_term_months: int = 12,
    origination_points: float = 2,
    exit_strategy: str = "refinance",
    after_repair_value: float | None = None,
) -> dict:
    """Analyze a hard money loan for fix-and-flip or bridge financing."""

    if exit_strategy not in ("refinance", "sell", "hold"):
        raise ValueError(f"Invalid exit_strategy '{exit_strategy}'. Must be refinance, sell, or hold.")

    arv = after_repair_value if after_repair_value else property_value + rehab_budget

    # --- Loan summary ---
    ltv_based_max = property_value * loan_to_value / 100
    purchase_plus_rehab = purchase_price + rehab_budget
    loan_amount = min(ltv_based_max, purchase_plus_rehab)

    cash_needed = purchase_plus_rehab - loan_amount

    loan_summary = {
        "property_value": round2(property_value),
        "purchase_price": round2(purchase_price),
        "rehab_budget": round2(rehab_budget),
        "after_repair_value": round2(arv),
        "loan_to_value": loan_to_value,
        "ltv_based_max_loan": round2(ltv_based_max),
        "loan_amount": round2(loan_amount),
        "cash_needed_at_closing": round2(cash_needed),
        "loan_term_months": loan_term_months,
    }

    # --- Cost analysis ---
    monthly_rate = interest_rate / 100 / 12
    origination_fee = loan_amount * origination_points / 100
    # Interest-only payments
    monthly_interest_payment = loan_amount * monthly_rate
    total_interest = monthly_interest_payment * loan_term_months
    total_loan_cost = total_interest + origination_fee

    cost_analysis = {
        "origination_points": origination_points,
        "origination_fee": round2(origination_fee),
        "interest_rate": interest_rate,
        "monthly_interest_payment": round2(monthly_interest_payment),
        "total_interest": round2(total_interest),
        "total_loan_cost": round2(total_loan_cost),
    }

    # --- Monthly payments ---
    monthly_payments: list[dict[str, Any]] = []
    for month in range(1, loan_term_months + 1):
        payment: dict[str, Any] = {
            "month": month,
            "interest_payment": round2(monthly_interest_payment),
            "principal_payment": 0.0,
            "total_payment": round2(monthly_interest_payment),
            "remaining_balance": round2(loan_amount),
        }
        if month == loan_term_months:
            payment["principal_payment"] = round2(loan_amount)
            payment["total_payment"] = round2(monthly_interest_payment + loan_amount)
            payment["remaining_balance"] = 0.0
            payment["note"] = "Balloon payment - full principal due"
        monthly_payments.append(payment)

    # --- Exit strategy analysis ---
    exit_strategy_analysis = _analyze_exit_strategy(
        exit_strategy, loan_amount, arv, total_loan_cost, cash_needed,
        origination_fee, purchase_price, rehab_budget, loan_term_months,
        interest_rate,
    )

    # --- Comparison to conventional ---
    conv_rate = 7.0
    conv_term = 30
    conv_monthly_rate = conv_rate / 100 / 12
    conv_num_payments = conv_term * 12
    conv_down_pct = 20
    conv_down = purchase_price * conv_down_pct / 100
    conv_loan_amount = purchase_price - conv_down
    conv_monthly_payment = calculate_mortgage_payment(
        conv_loan_amount, conv_monthly_rate, conv_num_payments,
    )
    conv_closing_costs = conv_loan_amount * 0.03

    # Compare over the hard money loan term
    hm_total_cost_over_term = total_loan_cost + cash_needed
    conv_total_cost_over_term = conv_down + conv_closing_costs + (conv_monthly_payment * loan_term_months)

    comparison_to_conventional = {
        "conventional_assumptions": {
            "interest_rate": conv_rate,
            "loan_term_years": conv_term,
            "down_payment_percent": conv_down_pct,
            "down_payment": round2(conv_down),
            "loan_amount": round2(conv_loan_amount),
            "monthly_payment": round2(conv_monthly_payment),
            "closing_costs": round2(conv_closing_costs),
        },
        "hard_money_total_cost": round2(hm_total_cost_over_term),
        "conventional_total_cost": round2(conv_total_cost_over_term),
        "cost_premium": round2(hm_total_cost_over_term - conv_total_cost_over_term),
        "hard_money_monthly_cost": round2(monthly_interest_payment),
        "conventional_monthly_cost": round2(conv_monthly_payment),
        "monthly_cost_difference": round2(monthly_interest_payment - conv_monthly_payment),
        "note": (
            "Hard money loans are significantly more expensive but offer speed, "
            "flexibility, and access for borrowers who may not qualify for conventional financing."
        ),
    }

    # --- Risk assessment ---
    risk_assessment = _hard_money_risk_assessment(
        loan_amount, arv, interest_rate, loan_term_months,
        exit_strategy, rehab_budget,
    )

    # --- Total cost of capital ---
    total_capital_invested = cash_needed + origination_fee
    total_cost_of_capital = {
        "cash_invested": round2(cash_needed),
        "origination_fee": round2(origination_fee),
        "total_interest_paid": round2(total_interest),
        "total_capital_invested": round2(total_capital_invested),
        "total_cost_of_borrowing": round2(total_loan_cost),
        "effective_annual_cost": round2(
            (total_loan_cost / loan_amount * 12 / loan_term_months * 100) if loan_amount > 0 else 0
        ),
    }

    # --- Recommendations ---
    recommendations = _hard_money_recommendations(
        interest_rate, loan_term_months, exit_strategy, arv,
        purchase_price, rehab_budget, total_loan_cost,
    )

    return {
        "loan_summary": loan_summary,
        "cost_analysis": cost_analysis,
        "monthly_payments": monthly_payments,
        "exit_strategy_analysis": exit_strategy_analysis,
        "comparison_to_conventional": comparison_to_conventional,
        "risk_assessment": risk_assessment,
        "total_cost_of_capital": total_cost_of_capital,
        "recommendations": recommendations,
    }


def _analyze_exit_strategy(
    strategy: str,
    loan_amount: float,
    arv: float,
    total_loan_cost: float,
    cash_needed: float,
    origination_fee: float,
    purchase_price: float,
    rehab_budget: float,
    loan_term_months: int,
    interest_rate: float,
) -> dict[str, Any]:
    total_investment = purchase_price + rehab_budget + total_loan_cost

    if strategy == "refinance":
        # Refinance into a permanent loan at 75% LTV of ARV
        refi_ltv = 75
        refi_loan_amount = arv * refi_ltv / 100
        can_pay_off = refi_loan_amount >= loan_amount
        cash_back = refi_loan_amount - loan_amount if can_pay_off else 0

        refi_rate = 7.0
        refi_term = 30
        refi_monthly_rate = refi_rate / 100 / 12
        refi_payments = refi_term * 12
        refi_monthly_payment = calculate_mortgage_payment(
            refi_loan_amount, refi_monthly_rate, refi_payments,
        )

        return {
            "strategy": "refinance",
            "refinance_ltv": refi_ltv,
            "refinance_loan_amount": round2(refi_loan_amount),
            "can_pay_off_hard_money": can_pay_off,
            "cash_back_at_refinance": round2(cash_back),
            "new_monthly_payment": round2(refi_monthly_payment),
            "new_interest_rate": refi_rate,
            "new_loan_term_years": refi_term,
            "total_cost_through_refinance": round2(total_loan_cost),
        }

    elif strategy == "sell":
        # Calculate needed sale price to break even and to profit
        selling_costs_pct = 6  # agent commissions + closing
        # Break even: sale_price - selling_costs = total_investment
        # sale_price - sale_price * 0.06 = total_investment
        # sale_price * 0.94 = total_investment
        break_even_price = total_investment / 0.94
        profit_at_arv = arv - (arv * selling_costs_pct / 100) - total_investment
        profit_margin = (profit_at_arv / total_investment * 100) if total_investment > 0 else 0

        # Cash-on-cash return
        total_cash_invested = cash_needed + origination_fee
        cash_on_cash = (profit_at_arv / total_cash_invested * 100) if total_cash_invested > 0 else 0

        # Annualized return
        annualized = (cash_on_cash * 12 / loan_term_months) if loan_term_months > 0 else 0

        return {
            "strategy": "sell",
            "after_repair_value": round2(arv),
            "selling_costs_percent": selling_costs_pct,
            "selling_costs": round2(arv * selling_costs_pct / 100),
            "break_even_sale_price": round2(break_even_price),
            "total_investment": round2(total_investment),
            "projected_profit_at_arv": round2(profit_at_arv),
            "profit_margin": round2(profit_margin),
            "cash_on_cash_return": round2(cash_on_cash),
            "annualized_return": round2(annualized),
        }

    else:  # hold
        # Calculate as rental property
        estimated_monthly_rent = arv * 0.008  # 0.8% rule of thumb
        refi_loan = arv * 0.75
        refi_rate = 7.0
        refi_monthly_rate = refi_rate / 100 / 12
        refi_payments = 30 * 12
        refi_monthly_payment = calculate_mortgage_payment(
            refi_loan, refi_monthly_rate, refi_payments,
        )
        monthly_cash_flow = estimated_monthly_rent - refi_monthly_payment

        return {
            "strategy": "hold",
            "estimated_monthly_rent": round2(estimated_monthly_rent),
            "refinance_loan_amount": round2(refi_loan),
            "refinance_monthly_payment": round2(refi_monthly_payment),
            "estimated_monthly_cash_flow": round2(monthly_cash_flow),
            "annual_cash_flow": round2(monthly_cash_flow * 12),
            "total_cost_through_hold": round2(total_loan_cost),
            "note": "Rental estimate uses 0.8% of ARV rule of thumb. Actual rents may vary.",
        }


def _hard_money_risk_assessment(
    loan_amount: float,
    arv: float,
    interest_rate: float,
    term_months: int,
    exit_strategy: str,
    rehab_budget: float,
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []

    loan_to_arv = (loan_amount / arv * 100) if arv > 0 else 0
    if loan_to_arv > 70:
        risks.append({
            "risk": "High loan-to-ARV ratio",
            "severity": "High",
            "detail": (
                f"Loan-to-ARV of {loan_to_arv:.1f}% leaves little margin for error. "
                "If ARV estimates are off, you may not be able to exit profitably."
            ),
        })

    if interest_rate > 14:
        risks.append({
            "risk": "Very high interest rate",
            "severity": "High",
            "detail": f"Interest rate of {interest_rate}% significantly increases holding costs.",
        })
    elif interest_rate > 10:
        risks.append({
            "risk": "Elevated interest rate",
            "severity": "Medium",
            "detail": f"Interest rate of {interest_rate}% is standard for hard money but costly.",
        })

    if term_months <= 6:
        risks.append({
            "risk": "Short loan term",
            "severity": "High",
            "detail": (
                f"A {term_months}-month term leaves little room for construction delays or market changes."
            ),
        })

    if rehab_budget > 0:
        risks.append({
            "risk": "Rehab cost overruns",
            "severity": "Medium",
            "detail": "Rehab projects frequently exceed budget by 10-20%. Ensure adequate reserves.",
        })

    if exit_strategy == "sell":
        risks.append({
            "risk": "Market timing risk",
            "severity": "Medium",
            "detail": "Selling depends on market conditions at time of completion. A downturn could reduce profits.",
        })
    elif exit_strategy == "refinance":
        risks.append({
            "risk": "Refinance qualification risk",
            "severity": "Medium",
            "detail": (
                "Permanent financing depends on property appraisal and borrower qualification. "
                "Changes in lending standards could affect your ability to refinance."
            ),
        })

    risks.append({
        "risk": "Balloon payment default",
        "severity": "High",
        "detail": (
            "Failure to repay or refinance by term end could result in foreclosure. "
            "Have a backup exit strategy."
        ),
    })

    return risks


def _hard_money_recommendations(
    interest_rate: float,
    term_months: int,
    exit_strategy: str,
    arv: float,
    purchase_price: float,
    rehab_budget: float,
    total_loan_cost: float,
) -> list[str]:
    recs: list[str] = []
    total_investment = purchase_price + rehab_budget + total_loan_cost
    potential_profit = arv - total_investment

    if potential_profit > 0:
        margin = potential_profit / arv * 100
        if margin > 20:
            recs.append(
                f"Projected profit margin of {margin:.1f}% provides a good buffer. "
                "This deal appears viable for hard money financing."
            )
        elif margin > 10:
            recs.append(
                f"Projected profit margin of {margin:.1f}% is moderate. "
                "Ensure your ARV and rehab estimates are accurate."
            )
        else:
            recs.append(
                f"Projected profit margin of {margin:.1f}% is thin. "
                "Small cost overruns or market shifts could eliminate profits."
            )
    else:
        recs.append(
            "At current estimates, this deal may not be profitable. "
            "Re-evaluate purchase price, rehab budget, or ARV assumptions."
        )

    if exit_strategy == "sell":
        recs.append(
            "For a flip, complete rehab as quickly as possible to minimize holding costs. "
            f"Each month of delay costs approximately ${arv * interest_rate / 100 / 12:,.0f} in interest."
        )
    elif exit_strategy == "refinance":
        recs.append(
            "Begin the refinance process 60-90 days before the hard money loan matures "
            "to ensure a smooth transition."
        )
    else:
        recs.append(
            "For a buy-and-hold strategy, confirm rental income projections support "
            "the permanent financing payment before committing."
        )

    if interest_rate > 12:
        recs.append(
            "Shop multiple hard money lenders. Rates vary significantly "
            "and a lower rate can save thousands in holding costs."
        )

    recs.append(
        "Always have a backup exit strategy. If your primary plan falls through, "
        "know your alternatives before closing on the loan."
    )

    return recs


# ---------------------------------------------------------------------------
# 4. Seller Financing Analysis
# ---------------------------------------------------------------------------

def analyze_seller_financing(
    purchase_price: float,
    down_payment: float,
    interest_rate: float,
    loan_term_years: int,
    balloon_payment_years: int | None = None,
    monthly_payment_override: float | None = None,
    market_interest_rate: float = 7,
    buyer_credit_score: int | None = None,
) -> dict:
    """Analyze a seller-financed real estate transaction."""

    loan_amount = purchase_price - down_payment
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term_years * 12

    # --- Loan terms ---
    if monthly_payment_override and monthly_payment_override > 0:
        monthly_payment = monthly_payment_override
    else:
        monthly_payment = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)

    total_payments = monthly_payment * num_payments
    total_interest = total_payments - loan_amount
    dp_percent = (down_payment / purchase_price * 100) if purchase_price > 0 else 0

    loan_terms = {
        "purchase_price": round2(purchase_price),
        "down_payment": round2(down_payment),
        "down_payment_percent": round2(dp_percent),
        "loan_amount": round2(loan_amount),
        "interest_rate": interest_rate,
        "loan_term_years": loan_term_years,
        "monthly_payment": round2(monthly_payment),
        "total_payments": round2(total_payments),
        "total_interest": round2(total_interest),
        "has_balloon": balloon_payment_years is not None,
        "payment_override": monthly_payment_override is not None,
    }

    # --- Payment schedule (first 5 years + balloon year) ---
    payment_schedule: list[dict[str, Any]] = []
    balance = loan_amount
    balloon_balance: float | None = None

    years_to_show: set[int] = {1, 2, 3, 4, 5}
    if balloon_payment_years is not None:
        years_to_show.add(balloon_payment_years)

    yearly_data: dict[int, dict[str, float]] = {}

    for month in range(1, num_payments + 1):
        interest_portion = balance * monthly_rate
        principal_portion = monthly_payment - interest_portion

        if principal_portion > balance:
            principal_portion = balance
        balance -= principal_portion

        if balance < 0:
            balance = 0.0

        year = (month - 1) // 12 + 1
        if year not in yearly_data:
            yearly_data[year] = {
                "interest_paid": 0.0,
                "principal_paid": 0.0,
                "end_balance": 0.0,
            }
        yearly_data[year]["interest_paid"] += interest_portion
        yearly_data[year]["principal_paid"] += principal_portion
        yearly_data[year]["end_balance"] = balance

        if balloon_payment_years is not None and month == balloon_payment_years * 12:
            balloon_balance = balance

    for year in sorted(years_to_show):
        if year in yearly_data:
            yd = yearly_data[year]
            entry: dict[str, Any] = {
                "year": year,
                "annual_payment": round2(monthly_payment * 12),
                "interest_paid": round2(yd["interest_paid"]),
                "principal_paid": round2(yd["principal_paid"]),
                "ending_balance": round2(yd["end_balance"]),
            }
            if balloon_payment_years is not None and year == balloon_payment_years:
                entry["balloon_payment_due"] = True
                entry["balloon_amount"] = round2(yd["end_balance"])
            payment_schedule.append(entry)

    # --- Comparison to conventional ---
    market_monthly_rate = market_interest_rate / 100 / 12
    conv_monthly_payment = calculate_mortgage_payment(loan_amount, market_monthly_rate, num_payments)
    conv_total_payments = conv_monthly_payment * num_payments
    conv_total_interest = conv_total_payments - loan_amount
    conv_closing_costs = loan_amount * 0.03

    monthly_diff = monthly_payment - conv_monthly_payment
    interest_diff = total_interest - conv_total_interest

    comparison_to_conventional = {
        "market_interest_rate": market_interest_rate,
        "conventional_monthly_payment": round2(conv_monthly_payment),
        "seller_finance_monthly_payment": round2(monthly_payment),
        "monthly_difference": round2(monthly_diff),
        "conventional_total_interest": round2(conv_total_interest),
        "seller_finance_total_interest": round2(total_interest),
        "interest_difference": round2(interest_diff),
        "conventional_closing_costs": round2(conv_closing_costs),
        "seller_finance_closing_costs": round2(0),
        "closing_cost_savings": round2(conv_closing_costs),
        "net_cost_difference": round2(interest_diff - conv_closing_costs),
    }

    # --- Buyer benefits ---
    buyer_benefits: list[str] = []
    buyer_benefits.append("No bank qualification required - faster, more flexible approval process.")
    buyer_benefits.append(f"Potential closing cost savings of ${conv_closing_costs:,.0f} vs conventional financing.")

    if interest_rate < market_interest_rate:
        buyer_benefits.append(
            f"Below-market interest rate saves ${abs(monthly_diff):,.0f}/month "
            f"and ${abs(interest_diff):,.0f} in total interest."
        )
    elif interest_rate == market_interest_rate:
        buyer_benefits.append("Interest rate matches market rate with simpler closing process.")

    if buyer_credit_score is not None and buyer_credit_score < 620:
        buyer_benefits.append(
            "Seller financing provides access to homeownership despite credit challenges."
        )

    buyer_benefits.append("Negotiable terms - down payment, rate, and schedule can all be customized.")

    # --- Seller benefits ---
    seller_benefits: list[str] = []
    seller_benefits.append(f"Earn ${total_interest:,.0f} in interest income over the life of the loan.")

    if interest_rate > 0:
        seller_benefits.append(
            f"Interest rate of {interest_rate}% provides steady income stream of ${monthly_payment:,.0f}/month."
        )

    seller_benefits.append("Installment sale may provide tax benefits by spreading capital gains over time.")
    seller_benefits.append("Property serves as collateral - can foreclose if buyer defaults.")
    seller_benefits.append("May command a higher sale price due to favorable financing terms offered.")

    # --- Balloon analysis ---
    balloon_analysis: dict[str, Any] | None = None
    if balloon_payment_years is not None and balloon_balance is not None:
        # Can buyer refinance the balloon?
        remaining_term_after_balloon = loan_term_years - balloon_payment_years
        refi_rate = market_interest_rate
        refi_monthly_rate = refi_rate / 100 / 12
        refi_payments = remaining_term_after_balloon * 12 if remaining_term_after_balloon > 0 else 30 * 12
        refi_monthly_payment = calculate_mortgage_payment(
            balloon_balance, refi_monthly_rate, refi_payments,
        ) if balloon_balance > 0 else 0

        balloon_analysis = {
            "balloon_due_year": balloon_payment_years,
            "balloon_amount": round2(balloon_balance),
            "original_loan_amount": round2(loan_amount),
            "principal_paid_before_balloon": round2(loan_amount - balloon_balance),
            "percent_paid_down": round2(
                ((loan_amount - balloon_balance) / loan_amount * 100) if loan_amount > 0 else 0
            ),
            "refinance_estimate": {
                "loan_amount": round2(balloon_balance),
                "estimated_rate": refi_rate,
                "estimated_monthly_payment": round2(refi_monthly_payment),
                "remaining_term_years": remaining_term_after_balloon if remaining_term_after_balloon > 0 else 30,
            },
            "refinance_feasible": balloon_balance <= purchase_price * 0.80,
        }

    # --- Risk assessment ---
    risk_assessment = _seller_financing_risk_assessment(
        interest_rate, market_interest_rate, balloon_payment_years,
        balloon_balance, loan_amount, dp_percent, buyer_credit_score,
    )

    # --- Recommendations ---
    recommendations = _seller_financing_recommendations(
        interest_rate, market_interest_rate, balloon_payment_years,
        balloon_balance, monthly_diff, dp_percent, buyer_credit_score,
    )

    result: dict[str, Any] = {
        "loan_terms": loan_terms,
        "payment_schedule": payment_schedule,
        "comparison_to_conventional": comparison_to_conventional,
        "buyer_benefits": buyer_benefits,
        "seller_benefits": seller_benefits,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
    }
    if balloon_analysis is not None:
        result["balloon_analysis"] = balloon_analysis

    return result


def _seller_financing_risk_assessment(
    interest_rate: float,
    market_rate: float,
    balloon_years: int | None,
    balloon_balance: float | None,
    loan_amount: float,
    dp_percent: float,
    credit_score: int | None,
) -> list[dict[str, str]]:
    risks: list[dict[str, str]] = []

    if balloon_years is not None and balloon_balance is not None:
        severity = "High" if balloon_balance > loan_amount * 0.8 else "Medium"
        risks.append({
            "risk": "Balloon payment risk",
            "severity": severity,
            "detail": (
                f"A balloon payment of ${balloon_balance:,.0f} is due in year {balloon_years}. "
                "Buyer must refinance or have funds available, which depends on future market conditions."
            ),
        })

    if interest_rate > market_rate + 2:
        risks.append({
            "risk": "Above-market interest rate",
            "severity": "Medium",
            "detail": (
                f"The seller financing rate of {interest_rate}% is significantly above "
                f"the market rate of {market_rate}%. Buyer may be overpaying."
            ),
        })

    if dp_percent < 10:
        risks.append({
            "risk": "Low down payment",
            "severity": "Medium",
            "detail": (
                f"Down payment of {dp_percent:.1f}% provides limited equity protection for the seller "
                "and increases buyer default risk."
            ),
        })

    if credit_score is not None and credit_score < 580:
        risks.append({
            "risk": "Low buyer credit score",
            "severity": "High",
            "detail": (
                f"Buyer credit score of {credit_score} indicates elevated default risk. "
                "Seller should ensure adequate down payment and legal protections."
            ),
        })
    elif credit_score is not None and credit_score < 660:
        risks.append({
            "risk": "Below-average buyer credit",
            "severity": "Medium",
            "detail": (
                f"Buyer credit score of {credit_score} is below average. "
                "Consider requiring a larger down payment for seller protection."
            ),
        })

    risks.append({
        "risk": "Due-on-sale clause",
        "severity": "Medium",
        "detail": (
            "If the seller has an existing mortgage, the due-on-sale clause could be triggered. "
            "Verify the property is owned free and clear or obtain lender approval."
        ),
    })

    risks.append({
        "risk": "Legal and documentation risk",
        "severity": "Low",
        "detail": (
            "Seller financing requires proper legal documentation including promissory note, "
            "deed of trust, and potentially a land contract. Use a real estate attorney."
        ),
    })

    return risks


def _seller_financing_recommendations(
    interest_rate: float,
    market_rate: float,
    balloon_years: int | None,
    balloon_balance: float | None,
    monthly_diff: float,
    dp_percent: float,
    credit_score: int | None,
) -> list[str]:
    recs: list[str] = []

    if interest_rate <= market_rate:
        recs.append(
            f"The seller financing rate of {interest_rate}% is at or below market rate ({market_rate}%). "
            "This is a favorable deal for the buyer."
        )
    elif interest_rate <= market_rate + 1:
        recs.append(
            f"The rate premium of {interest_rate - market_rate:.2f}% over market "
            "is reasonable given the flexibility of seller financing."
        )
    else:
        recs.append(
            f"The rate of {interest_rate}% is {interest_rate - market_rate:.2f}% above market. "
            "Negotiate a lower rate or plan to refinance into conventional financing when possible."
        )

    if balloon_years is not None:
        recs.append(
            f"Begin preparing for the balloon payment at least 12-18 months before year {balloon_years}. "
            "Improve credit score and build savings to ensure refinancing options."
        )
        if balloon_balance is not None and balloon_balance > 0:
            recs.append(
                "Consider making extra principal payments to reduce the balloon amount and ease the refinance."
            )

    if dp_percent < 20:
        recs.append(
            "A larger down payment reduces risk for both parties and may help negotiate better terms."
        )

    if credit_score is not None and credit_score < 660:
        recs.append(
            "Use the seller financing period to rebuild credit. Make all payments on time "
            "and reduce other debts to position for conventional refinancing."
        )

    recs.append(
        "Both parties should hire a real estate attorney to draft proper documentation "
        "including a promissory note, deed of trust, and escrow arrangement for payments."
    )

    recs.append(
        "Consider using a loan servicing company to handle payment processing, record-keeping, "
        "and year-end tax reporting for both buyer and seller."
    )

    return recs
