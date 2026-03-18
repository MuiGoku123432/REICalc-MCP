"""Financial metrics calculators: IRR, fix-and-flip, NPV, COCR, DSCR, break-even."""

from ._common import calculate_mortgage_payment, calculate_irr, calculate_npv, round2


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _performance_rating(irr: float, target: float) -> dict:
    """Rate IRR performance relative to a target rate."""
    diff = irr - target
    if diff >= 10:
        rating = "Exceptional"
        description = "Significantly exceeds target return"
    elif diff >= 5:
        rating = "Excellent"
        description = "Well above target return"
    elif diff >= 0:
        rating = "Good"
        description = "Meets or exceeds target return"
    elif diff >= -5:
        rating = "Marginal"
        description = "Below target return"
    else:
        rating = "Poor"
        description = "Significantly below target return"
    return {
        "rating": rating,
        "description": description,
        "irr": round2(irr),
        "target_irr": target,
        "spread": round2(diff),
    }


def _risk_level(score: float) -> str:
    if score >= 80:
        return "Low"
    if score >= 60:
        return "Moderate"
    if score >= 40:
        return "Elevated"
    return "High"


def _total_expenses(expenses: dict) -> float:
    """Sum all values in an expenses dict."""
    return sum(float(v) for v in expenses.values())


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if denominator else default


# ---------------------------------------------------------------------------
# 1. calculate_irr_tool
# ---------------------------------------------------------------------------


def calculate_irr_tool(
    initial_investment: float,
    annual_cash_flows: list[float],
    projected_sale_price: float,
    selling_costs_percent: float = 7,
    loan_balance_at_sale: float = 0,
    target_irr: float = 15,
    holding_period_years: int | None = None,
) -> dict:
    """Calculate IRR with sensitivity analysis for a real estate investment."""
    holding_period = holding_period_years if holding_period_years is not None else len(annual_cash_flows)

    # Net sale proceeds
    selling_costs = projected_sale_price * (selling_costs_percent / 100)
    net_sale_proceeds = projected_sale_price - selling_costs - loan_balance_at_sale

    # Build cash flow array
    flows = [-abs(initial_investment)]
    for i, cf in enumerate(annual_cash_flows):
        if i == len(annual_cash_flows) - 1:
            flows.append(cf + net_sale_proceeds)
        else:
            flows.append(cf)
    # If holding_period > len(annual_cash_flows), pad with zeros + sale at end
    if holding_period > len(annual_cash_flows):
        # Remove sale proceeds from last cash flow entry and place at holding_period
        if annual_cash_flows:
            flows[-1] = annual_cash_flows[-1]
        for _ in range(holding_period - len(annual_cash_flows) - 1):
            flows.append(0)
        flows.append(net_sale_proceeds)

    # Calculate IRR
    irr = calculate_irr(flows) * 100  # as percentage

    # NPV at target rate
    target_rate = target_irr / 100
    npv_at_target = calculate_npv(flows, target_rate)

    # Cash flow schedule
    total_cash_inflows = sum(cf for cf in flows[1:])
    total_investment = abs(flows[0])

    schedule = []
    for i, cf in enumerate(flows):
        schedule.append({
            "year": i,
            "cash_flow": round2(cf),
            "cumulative": round2(sum(flows[: i + 1])),
            "present_value": round2(cf / (1 + target_rate) ** i),
        })

    # Sensitivity analysis
    # Scenario 1: 10% lower cash flows
    lower_cf_flows = [flows[0]]
    for i in range(1, len(flows)):
        if i < len(flows) - 1:
            lower_cf_flows.append(flows[i] * 0.9)
        else:
            # Last year: reduce cash flow portion but keep sale proceeds
            cf_portion = annual_cash_flows[-1] * 0.9 if annual_cash_flows else 0
            lower_cf_flows.append(cf_portion + net_sale_proceeds)
    irr_lower_cf = calculate_irr(lower_cf_flows) * 100

    # Scenario 2: 10% lower sale price
    lower_sale = projected_sale_price * 0.9
    lower_sale_costs = lower_sale * (selling_costs_percent / 100)
    lower_net_sale = lower_sale - lower_sale_costs - loan_balance_at_sale
    lower_sale_flows = list(flows)
    lower_sale_flows[-1] = (annual_cash_flows[-1] if annual_cash_flows and holding_period <= len(annual_cash_flows) else 0) + lower_net_sale
    irr_lower_sale = calculate_irr(lower_sale_flows) * 100

    # Scenario 3: 20% higher investment
    higher_inv_flows = list(flows)
    higher_inv_flows[0] = flows[0] * 1.2
    irr_higher_inv = calculate_irr(higher_inv_flows) * 100

    sensitivity = {
        "scenarios": [
            {
                "name": "10% Lower Cash Flows",
                "irr": round2(irr_lower_cf),
                "change_from_base": round2(irr_lower_cf - irr),
            },
            {
                "name": "10% Lower Sale Price",
                "irr": round2(irr_lower_sale),
                "change_from_base": round2(irr_lower_sale - irr),
            },
            {
                "name": "20% Higher Investment",
                "irr": round2(irr_higher_inv),
                "change_from_base": round2(irr_higher_inv - irr),
            },
        ],
        "base_case_irr": round2(irr),
    }

    # Performance rating
    perf = _performance_rating(irr, target_irr)

    # Recommendations
    recommendations = []
    if irr >= target_irr:
        recommendations.append("Investment meets or exceeds target IRR")
    else:
        recommendations.append(f"Investment falls short of {target_irr}% target IRR by {round2(target_irr - irr)}%")
    if npv_at_target > 0:
        recommendations.append("Positive NPV indicates value creation at target discount rate")
    else:
        recommendations.append("Negative NPV suggests the investment may not meet return requirements")
    if irr_lower_sale < target_irr:
        recommendations.append("Returns are sensitive to sale price — consider downside protection")
    if irr_lower_cf < target_irr:
        recommendations.append("Returns are sensitive to cash flow variations — stress-test assumptions")

    return {
        "irr_analysis": {
            "irr": round2(irr),
            "target_irr": target_irr,
            "exceeds_target": irr >= target_irr,
            "holding_period_years": holding_period,
        },
        "cash_flow_summary": {
            "initial_investment": round2(total_investment),
            "total_cash_inflows": round2(total_cash_inflows),
            "net_profit": round2(total_cash_inflows - total_investment),
            "multiple_on_invested_capital": round2(_safe_div(total_cash_inflows, total_investment)),
        },
        "cash_flow_schedule": schedule,
        "npv_analysis": {
            "discount_rate": target_irr,
            "npv": round2(npv_at_target),
            "decision": "Accept" if npv_at_target > 0 else "Reject",
        },
        "sale_analysis": {
            "projected_sale_price": round2(projected_sale_price),
            "selling_costs": round2(selling_costs),
            "selling_costs_percent": selling_costs_percent,
            "loan_balance_at_sale": round2(loan_balance_at_sale),
            "net_sale_proceeds": round2(net_sale_proceeds),
        },
        "performance_rating": perf,
        "sensitivity_analysis": sensitivity,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 2. analyze_fix_flip
# ---------------------------------------------------------------------------


def analyze_fix_flip(
    purchase_price: float,
    rehab_budget: float,
    after_repair_value: float,
    purchase_closing_costs: float = 0,
    holding_period_months: int = 6,
    financing_type: str = "hard_money",
    down_payment_percent: float = 20,
    interest_rate: float = 12,
    loan_points: float = 2,
    monthly_holding_costs: float = 0,
    selling_costs_percent: float = 8,
    contingency_percent: float = 10,
) -> dict:
    """Analyze a fix-and-flip real estate deal."""

    # ------ Financing ------
    contingency = rehab_budget * (contingency_percent / 100)
    rehab_total = rehab_budget + contingency

    if financing_type == "cash":
        loan_amount = 0.0
        down_payment = purchase_price + rehab_total
        monthly_payment = 0.0
        total_loan_points = 0.0
        total_interest = 0.0
    else:
        if financing_type == "hard_money":
            # Hard money typically finances purchase + rehab
            loan_basis = purchase_price + rehab_total
        else:
            loan_basis = purchase_price

        down_payment = loan_basis * (down_payment_percent / 100)
        loan_amount = loan_basis - down_payment
        monthly_rate = interest_rate / 100 / 12
        # Interest-only payments for fix-and-flip
        monthly_payment = loan_amount * monthly_rate
        total_loan_points = loan_amount * (loan_points / 100)
        total_interest = monthly_payment * holding_period_months

    total_financing_costs = total_interest + total_loan_points

    financing = {
        "financing_type": financing_type,
        "loan_amount": round2(loan_amount),
        "down_payment": round2(down_payment),
        "down_payment_percent": down_payment_percent,
        "interest_rate": interest_rate,
        "monthly_payment": round2(monthly_payment),
        "loan_points": loan_points,
        "loan_points_cost": round2(total_loan_points),
        "total_interest": round2(total_interest),
        "total_financing_costs": round2(total_financing_costs),
    }

    # ------ Cost breakdown ------
    selling_costs = after_repair_value * (selling_costs_percent / 100)
    total_holding_costs = monthly_holding_costs * holding_period_months
    closing_costs_total = purchase_closing_costs

    total_project_cost = (
        purchase_price
        + closing_costs_total
        + rehab_budget
        + contingency
        + total_financing_costs
        + total_holding_costs
        + selling_costs
    )

    cost_breakdown = {
        "purchase_price": round2(purchase_price),
        "purchase_closing_costs": round2(closing_costs_total),
        "rehab_budget": round2(rehab_budget),
        "contingency": round2(contingency),
        "contingency_percent": contingency_percent,
        "financing_costs": round2(total_financing_costs),
        "holding_costs": round2(total_holding_costs),
        "selling_costs": round2(selling_costs),
        "selling_costs_percent": selling_costs_percent,
        "total_project_cost": round2(total_project_cost),
    }

    # ------ Profit analysis ------
    net_profit = after_repair_value - total_project_cost

    if financing_type == "cash":
        total_cash_invested = purchase_price + closing_costs_total + rehab_total + total_holding_costs
    else:
        total_cash_invested = down_payment + closing_costs_total + total_loan_points + total_holding_costs
        if financing_type != "hard_money":
            total_cash_invested += rehab_total

    roi = _safe_div(net_profit, total_cash_invested) * 100
    annualized_roi = ((1 + roi / 100) ** (12 / max(holding_period_months, 1)) - 1) * 100
    profit_margin = _safe_div(net_profit, after_repair_value) * 100

    profit_analysis = {
        "after_repair_value": round2(after_repair_value),
        "total_project_cost": round2(total_project_cost),
        "net_profit": round2(net_profit),
        "roi": round2(roi),
        "annualized_roi": round2(annualized_roi),
        "profit_margin": round2(profit_margin),
        "profit_per_month": round2(_safe_div(net_profit, holding_period_months)),
    }

    # ------ MAO analysis (70% rule) ------
    mao_70 = after_repair_value * 0.70 - rehab_total
    mao_margin = mao_70 - purchase_price

    mao_analysis = {
        "maximum_allowable_offer": round2(mao_70),
        "purchase_price": round2(purchase_price),
        "difference": round2(mao_margin),
        "meets_70_percent_rule": purchase_price <= mao_70,
        "purchase_as_percent_of_arv": round2(_safe_div(purchase_price, after_repair_value) * 100),
    }

    # ------ Break-even ------
    break_even_sale_price = total_project_cost
    break_even_percent = _safe_div(break_even_sale_price, after_repair_value) * 100

    break_even_analysis = {
        "break_even_sale_price": round2(break_even_sale_price),
        "break_even_as_percent_arv": round2(break_even_percent),
        "margin_of_safety": round2(100 - break_even_percent),
    }

    # ------ Risk assessment ------
    purchase_pct_arv = _safe_div(purchase_price, after_repair_value) * 100
    rehab_pct_arv = _safe_div(rehab_total, after_repair_value) * 100

    risk_factors = []
    risk_score = 100

    if purchase_pct_arv > 75:
        risk_factors.append("Purchase price exceeds 75% of ARV")
        risk_score -= 20
    if rehab_pct_arv > 25:
        risk_factors.append("Rehab costs exceed 25% of ARV")
        risk_score -= 15
    if profit_margin < 10:
        risk_factors.append("Thin profit margin (below 10%)")
        risk_score -= 20
    if holding_period_months > 9:
        risk_factors.append("Extended holding period increases carrying costs")
        risk_score -= 10
    if financing_type == "hard_money" and interest_rate > 14:
        risk_factors.append("High hard money interest rate")
        risk_score -= 10
    if not mao_analysis["meets_70_percent_rule"]:
        risk_factors.append("Does not meet 70% rule")
        risk_score -= 15

    risk_score = max(risk_score, 0)

    risk_assessment = {
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "purchase_percent_of_arv": round2(purchase_pct_arv),
        "rehab_percent_of_arv": round2(rehab_pct_arv),
        "profit_margin": round2(profit_margin),
        "risk_factors": risk_factors,
    }

    # ------ Project timeline ------
    project_timeline = {
        "acquisition_phase": "Month 1",
        "renovation_phase": f"Month 1-{max(holding_period_months - 2, 1)}",
        "listing_phase": f"Month {max(holding_period_months - 1, 2)}",
        "closing_phase": f"Month {holding_period_months}",
        "total_holding_period_months": holding_period_months,
    }

    # ------ Investment requirements ------
    investment_requirements = {
        "total_cash_needed": round2(total_cash_invested),
        "down_payment": round2(down_payment),
        "closing_costs": round2(closing_costs_total),
        "rehab_budget": round2(rehab_budget),
        "contingency": round2(contingency),
        "reserves_recommended": round2(total_cash_invested * 0.1),
    }

    # ------ Deal summary ------
    deal_summary = {
        "purchase_price": round2(purchase_price),
        "after_repair_value": round2(after_repair_value),
        "rehab_budget": round2(rehab_budget),
        "holding_period_months": holding_period_months,
        "financing_type": financing_type,
        "net_profit": round2(net_profit),
        "roi": round2(roi),
    }

    # ------ Recommendations ------
    recommendations = []
    if net_profit > 0 and profit_margin >= 15:
        recommendations.append("Strong profit potential — consider proceeding")
    elif net_profit > 0:
        recommendations.append("Positive but thin margins — ensure accurate rehab estimates")
    else:
        recommendations.append("Deal shows a loss — renegotiate purchase price or reduce costs")

    if mao_analysis["meets_70_percent_rule"]:
        recommendations.append("Meets 70% rule — purchase price is within acceptable range")
    else:
        recommendations.append(f"Negotiate purchase price to ${round2(mao_70):,.2f} or below (70% rule)")

    if risk_score < 60:
        recommendations.append("Elevated risk profile — proceed with caution")

    if holding_period_months > 6:
        recommendations.append("Consider strategies to reduce holding period and carrying costs")

    return {
        "deal_summary": deal_summary,
        "financing": financing,
        "cost_breakdown": cost_breakdown,
        "profit_analysis": profit_analysis,
        "investment_requirements": investment_requirements,
        "mao_analysis": mao_analysis,
        "break_even_analysis": break_even_analysis,
        "risk_assessment": risk_assessment,
        "project_timeline": project_timeline,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 3. calculate_npv_tool
# ---------------------------------------------------------------------------


def calculate_npv_tool(
    initial_investment: float,
    cash_flows: list[dict],
    discount_rate: float,
    terminal_value: float = 0,
    terminal_period: int | None = None,
    inflation_rate: float = 0,
    comparison_investment: dict | None = None,
) -> dict:
    """Calculate Net Present Value with comprehensive analysis."""
    initial = abs(initial_investment)
    rate = discount_rate / 100

    # Sort cash flows by period
    sorted_cfs = sorted(cash_flows, key=lambda x: x["period"])

    # Determine terminal period
    max_period = max(cf["period"] for cf in sorted_cfs) if sorted_cfs else 0
    t_period = terminal_period if terminal_period is not None else max_period

    # Build flat cash flow array for _common helpers
    # Index 0 = initial investment (negative)
    last_period = max(t_period, max_period)
    flow_array = [0.0] * (last_period + 1)
    flow_array[0] = -initial

    for cf in sorted_cfs:
        p = cf["period"]
        flow_array[p] += cf["amount"]

    # Add terminal value
    if terminal_value:
        flow_array[t_period] += terminal_value

    # Calculate nominal NPV
    nominal_npv = calculate_npv(flow_array, rate)

    # Calculate real NPV if inflation
    inf = inflation_rate / 100
    if inf > 0:
        real_rate = (1 + rate) / (1 + inf) - 1
        real_npv = calculate_npv(flow_array, real_rate)
    else:
        real_rate = rate
        real_npv = nominal_npv

    # Profitability index
    pv_inflows = nominal_npv + initial
    profitability_index = _safe_div(pv_inflows, initial)

    # IRR (modified)
    irr_val = calculate_irr(flow_array) * 100

    # Payback period (simple)
    cumulative = -initial
    simple_payback = None
    for i in range(1, len(flow_array)):
        cumulative += flow_array[i]
        if cumulative >= 0:
            # Interpolate
            prev_cum = cumulative - flow_array[i]
            fraction = _safe_div(-prev_cum, flow_array[i])
            simple_payback = round2(i - 1 + fraction)
            break

    # Discounted payback period
    cumulative_pv = -initial
    discounted_payback = None
    for i in range(1, len(flow_array)):
        pv_cf = flow_array[i] / (1 + rate) ** i
        cumulative_pv += pv_cf
        if cumulative_pv >= 0:
            prev_cum = cumulative_pv - pv_cf
            fraction = _safe_div(-prev_cum, pv_cf)
            discounted_payback = round2(i - 1 + fraction)
            break

    payback_analysis = {
        "simple_payback_period": simple_payback,
        "discounted_payback_period": discounted_payback,
        "investment_recovered": simple_payback is not None,
    }

    # Cash flow schedule
    cf_schedule = []
    running_pv = 0.0
    for i, cf in enumerate(flow_array):
        pv_cf = cf / (1 + rate) ** i
        running_pv += pv_cf
        desc = ""
        if i == 0:
            desc = "Initial Investment"
        else:
            # Find matching description from input
            matches = [c for c in sorted_cfs if c["period"] == i]
            if matches and "description" in matches[0]:
                desc = matches[0]["description"]
            if i == t_period and terminal_value:
                desc = (desc + " + Terminal Value").strip(" +")
        cf_schedule.append({
            "period": i,
            "cash_flow": round2(cf),
            "present_value": round2(pv_cf),
            "cumulative_pv": round2(running_pv),
            "description": desc,
        })

    # Decision criteria
    decision_criteria = {
        "npv_positive": nominal_npv > 0,
        "irr_exceeds_discount": irr_val > discount_rate,
        "pi_above_one": profitability_index > 1,
        "payback_acceptable": simple_payback is not None,
        "recommendation": "Accept" if nominal_npv > 0 else "Reject",
    }

    # Sensitivity analysis
    rate_variations = [-2, -1, 0, 1, 2]
    rate_sensitivity = []
    for delta in rate_variations:
        adj_rate = (discount_rate + delta) / 100
        if adj_rate < 0:
            continue
        adj_npv = calculate_npv(flow_array, adj_rate)
        rate_sensitivity.append({
            "discount_rate": round2(discount_rate + delta),
            "npv": round2(adj_npv),
        })

    cf_variations = [-20, -10, 0, 10, 20]
    cf_sensitivity = []
    for pct in cf_variations:
        adj_flows = [flow_array[0]]
        for cf in flow_array[1:]:
            adj_flows.append(cf * (1 + pct / 100))
        adj_npv = calculate_npv(adj_flows, rate)
        cf_sensitivity.append({
            "cash_flow_change_percent": pct,
            "npv": round2(adj_npv),
        })

    sensitivity_analysis = {
        "discount_rate_sensitivity": rate_sensitivity,
        "cash_flow_sensitivity": cf_sensitivity,
    }

    # Opportunity cost
    opportunity_cost: dict = {}
    if comparison_investment is not None:
        comp_return = comparison_investment.get("expected_return", 0)
        comp_rate = comp_return / 100
        comp_fv = initial * (1 + comp_rate) ** last_period
        project_fv = sum(
            flow_array[i] * (1 + rate) ** (last_period - i)
            for i in range(len(flow_array))
        )
        opportunity_cost = {
            "comparison_name": comparison_investment.get("name", "Alternative Investment"),
            "comparison_return": comp_return,
            "comparison_future_value": round2(comp_fv),
            "project_future_value": round2(project_fv),
            "incremental_value": round2(project_fv - comp_fv),
            "preferred_investment": "Project" if project_fv > comp_fv else "Alternative",
        }
    else:
        risk_free = 4.0
        rf_rate = risk_free / 100
        rf_fv = initial * (1 + rf_rate) ** last_period
        opportunity_cost = {
            "comparison_name": "Risk-Free Rate",
            "comparison_return": risk_free,
            "comparison_future_value": round2(rf_fv),
            "project_npv": round2(nominal_npv),
            "npv_exceeds_risk_free": nominal_npv > 0,
        }

    # Investment metrics
    investment_metrics = {
        "npv": round2(nominal_npv),
        "irr": round2(irr_val),
        "profitability_index": round2(profitability_index),
        "modified_irr": round2(irr_val),  # simplified: same as IRR here
        "total_cash_inflows": round2(sum(flow_array[1:])),
        "total_return": round2(sum(flow_array)),
    }

    # Recommendations
    recommendations = []
    if nominal_npv > 0:
        recommendations.append(f"Positive NPV of ${nominal_npv:,.2f} — investment creates value")
    else:
        recommendations.append(f"Negative NPV of ${nominal_npv:,.2f} — investment destroys value")
    if irr_val > discount_rate:
        recommendations.append(f"IRR of {round2(irr_val)}% exceeds {discount_rate}% discount rate")
    else:
        recommendations.append(f"IRR of {round2(irr_val)}% is below {discount_rate}% required return")
    if inf > 0 and real_npv < nominal_npv:
        recommendations.append("Inflation erodes real returns — consider inflation-protected structures")
    if simple_payback is None:
        recommendations.append("Investment does not achieve payback within the analysis period")

    npv_analysis = {
        "nominal_npv": round2(nominal_npv),
        "real_npv": round2(real_npv),
        "discount_rate": discount_rate,
        "inflation_rate": inflation_rate,
        "initial_investment": round2(initial),
        "total_periods": last_period,
        "terminal_value": round2(terminal_value),
    }

    return {
        "npv_analysis": npv_analysis,
        "investment_metrics": investment_metrics,
        "payback_analysis": payback_analysis,
        "decision_criteria": decision_criteria,
        "sensitivity_analysis": sensitivity_analysis,
        "opportunity_cost": opportunity_cost,
        "cash_flow_schedule": cf_schedule,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 4. calculate_cocr
# ---------------------------------------------------------------------------


def calculate_cocr(
    purchase_price: float,
    down_payment: float,
    closing_costs: float = 0,
    renovation_costs: float = 0,
    annual_rental_income: float = 0,
    annual_expenses: dict | None = None,
    vacancy_rate: float = 5,
    loan_details: dict | None = None,
    reserve_fund_percent: float = 5,
) -> dict:
    """Calculate Cash-on-Cash Return and related rental property metrics."""
    if annual_expenses is None:
        annual_expenses = {}
    if loan_details is None:
        loan_details = {}

    # Total cash invested
    total_cash_invested = down_payment + closing_costs + renovation_costs

    # Income analysis
    vacancy_loss = annual_rental_income * (vacancy_rate / 100)
    effective_rental_income = annual_rental_income - vacancy_loss
    reserve_amount = effective_rental_income * (reserve_fund_percent / 100)

    income_analysis = {
        "gross_annual_rental_income": round2(annual_rental_income),
        "vacancy_rate": vacancy_rate,
        "vacancy_loss": round2(vacancy_loss),
        "effective_rental_income": round2(effective_rental_income),
        "monthly_effective_income": round2(effective_rental_income / 12),
    }

    # Expense analysis
    total_annual_expenses = _total_expenses(annual_expenses)
    expense_items = {k: round2(v) for k, v in annual_expenses.items()}

    expense_analysis = {
        "itemized_expenses": expense_items,
        "total_annual_expenses": round2(total_annual_expenses),
        "monthly_expenses": round2(total_annual_expenses / 12),
        "reserve_fund": round2(reserve_amount),
        "reserve_fund_percent": reserve_fund_percent,
        "expense_ratio": round2(_safe_div(total_annual_expenses, effective_rental_income) * 100),
    }

    # NOI
    noi = effective_rental_income - total_annual_expenses - reserve_amount

    # Debt service
    loan_amount = loan_details.get("loan_amount", 0)
    loan_rate = loan_details.get("interest_rate", 0)
    loan_term = loan_details.get("loan_term_years", 30)

    if loan_amount > 0:
        monthly_rate = loan_rate / 100 / 12
        num_payments = loan_term * 12
        monthly_mortgage = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
        annual_debt_service = monthly_mortgage * 12
    else:
        monthly_mortgage = 0.0
        annual_debt_service = 0.0

    # Cash flow
    annual_cash_flow = noi - annual_debt_service
    monthly_cash_flow = annual_cash_flow / 12

    cash_flow_analysis = {
        "net_operating_income": round2(noi),
        "annual_debt_service": round2(annual_debt_service),
        "monthly_mortgage_payment": round2(monthly_mortgage),
        "annual_cash_flow": round2(annual_cash_flow),
        "monthly_cash_flow": round2(monthly_cash_flow),
    }

    # Return metrics
    cocr = _safe_div(annual_cash_flow, total_cash_invested) * 100
    cap_rate = _safe_div(noi, purchase_price) * 100
    grm = _safe_div(purchase_price, annual_rental_income) if annual_rental_income else 0
    dscr = _safe_div(noi, annual_debt_service) if annual_debt_service else float("inf")

    return_metrics = {
        "cash_on_cash_return": round2(cocr),
        "cap_rate": round2(cap_rate),
        "gross_rent_multiplier": round2(grm),
        "debt_service_coverage_ratio": round2(dscr) if dscr != float("inf") else "N/A (no debt)",
        "total_roi_year_1": round2(cocr),  # simplified
    }

    # Performance rating
    if cocr >= 12:
        perf_rating = "Excellent"
        perf_desc = "Exceptional cash-on-cash return"
    elif cocr >= 8:
        perf_rating = "Good"
        perf_desc = "Strong cash-on-cash return"
    elif cocr >= 5:
        perf_rating = "Fair"
        perf_desc = "Moderate cash-on-cash return"
    elif cocr >= 0:
        perf_rating = "Below Average"
        perf_desc = "Low cash-on-cash return"
    else:
        perf_rating = "Poor"
        perf_desc = "Negative cash flow"

    performance_rating = {
        "rating": perf_rating,
        "description": perf_desc,
        "cash_on_cash_return": round2(cocr),
        "cap_rate": round2(cap_rate),
    }

    # Monthly breakdown
    monthly_breakdown = {
        "gross_rent": round2(annual_rental_income / 12),
        "vacancy_loss": round2(vacancy_loss / 12),
        "effective_rent": round2(effective_rental_income / 12),
        "expenses": round2(total_annual_expenses / 12),
        "reserves": round2(reserve_amount / 12),
        "mortgage": round2(monthly_mortgage),
        "net_cash_flow": round2(monthly_cash_flow),
    }

    # Scenario analysis
    scenarios = []
    # Higher vacancy
    for vac in [vacancy_rate, vacancy_rate + 5, vacancy_rate + 10]:
        eff = annual_rental_income * (1 - vac / 100)
        res = eff * (reserve_fund_percent / 100)
        sc_noi = eff - total_annual_expenses - res
        sc_cf = sc_noi - annual_debt_service
        sc_cocr = _safe_div(sc_cf, total_cash_invested) * 100
        scenarios.append({
            "scenario": f"{vac}% Vacancy",
            "annual_cash_flow": round2(sc_cf),
            "cash_on_cash_return": round2(sc_cocr),
        })

    # Rent changes
    for pct in [-10, 10]:
        adj_income = annual_rental_income * (1 + pct / 100)
        eff = adj_income * (1 - vacancy_rate / 100)
        res = eff * (reserve_fund_percent / 100)
        sc_noi = eff - total_annual_expenses - res
        sc_cf = sc_noi - annual_debt_service
        sc_cocr = _safe_div(sc_cf, total_cash_invested) * 100
        scenarios.append({
            "scenario": f"{pct:+d}% Rent Change",
            "annual_cash_flow": round2(sc_cf),
            "cash_on_cash_return": round2(sc_cocr),
        })

    # Interest rate change
    if loan_amount > 0:
        for delta in [1, 2]:
            adj_rate = (loan_rate + delta) / 100 / 12
            adj_payment = calculate_mortgage_payment(loan_amount, adj_rate, loan_term * 12)
            adj_ds = adj_payment * 12
            sc_cf = noi - adj_ds
            sc_cocr = _safe_div(sc_cf, total_cash_invested) * 100
            scenarios.append({
                "scenario": f"+{delta}% Interest Rate",
                "annual_cash_flow": round2(sc_cf),
                "cash_on_cash_return": round2(sc_cocr),
            })

    scenario_analysis = scenarios

    # 5-year projection
    rent_growth = 0.03
    expense_growth = 0.025
    appreciation_rate = 0.04

    projection = []
    proj_income = annual_rental_income
    proj_expenses = total_annual_expenses
    proj_value = purchase_price

    for year in range(1, 6):
        if year > 1:
            proj_income *= (1 + rent_growth)
            proj_expenses *= (1 + expense_growth)
            proj_value *= (1 + appreciation_rate)
        eff = proj_income * (1 - vacancy_rate / 100)
        res = eff * (reserve_fund_percent / 100)
        yr_noi = eff - proj_expenses - res
        yr_cf = yr_noi - annual_debt_service
        yr_cocr = _safe_div(yr_cf, total_cash_invested) * 100
        equity = proj_value - loan_amount  # simplified (no amortization adjustment)
        projection.append({
            "year": year,
            "rental_income": round2(proj_income),
            "expenses": round2(proj_expenses),
            "noi": round2(yr_noi),
            "cash_flow": round2(yr_cf),
            "cash_on_cash_return": round2(yr_cocr),
            "property_value": round2(proj_value),
            "equity": round2(equity),
        })

    # Investment summary
    investment_summary = {
        "purchase_price": round2(purchase_price),
        "down_payment": round2(down_payment),
        "closing_costs": round2(closing_costs),
        "renovation_costs": round2(renovation_costs),
        "total_cash_invested": round2(total_cash_invested),
        "loan_amount": round2(loan_amount),
    }

    # Recommendations
    recommendations = []
    if cocr >= 8:
        recommendations.append("Strong cash-on-cash return — consider proceeding")
    elif cocr >= 5:
        recommendations.append("Moderate return — look for ways to increase income or reduce costs")
    else:
        recommendations.append("Low return — renegotiate price or increase rents before proceeding")

    if cap_rate >= 6:
        recommendations.append(f"Cap rate of {round2(cap_rate)}% is competitive for most markets")
    else:
        recommendations.append(f"Cap rate of {round2(cap_rate)}% may be low — verify market comps")

    if isinstance(dscr, float) and dscr < 1.25:
        recommendations.append("DSCR below 1.25 — tight debt coverage, consider higher down payment")
    if annual_cash_flow < 0:
        recommendations.append("Negative cash flow — this property requires monthly cash infusion")

    return {
        "investment_summary": investment_summary,
        "income_analysis": income_analysis,
        "expense_analysis": expense_analysis,
        "cash_flow_analysis": cash_flow_analysis,
        "return_metrics": return_metrics,
        "performance_rating": performance_rating,
        "monthly_breakdown": monthly_breakdown,
        "scenario_analysis": scenario_analysis,
        "five_year_projection": projection,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 5. calculate_dscr
# ---------------------------------------------------------------------------


def calculate_dscr(
    property_income: dict,
    property_expenses: dict | None = None,
    loan_details: dict | None = None,
    property_details: dict | None = None,
) -> dict:
    """Calculate Debt Service Coverage Ratio for loan qualification."""
    if property_expenses is None:
        property_expenses = {}
    if loan_details is None:
        loan_details = {}
    if property_details is None:
        property_details = {}

    # Income analysis
    monthly_rent = property_income.get("monthly_rent", 0)
    other_monthly_income = property_income.get("other_monthly_income", 0)
    vacancy_rate = property_income.get("vacancy_rate", 5)

    gross_monthly_income = monthly_rent + other_monthly_income
    gross_annual_income = gross_monthly_income * 12
    vacancy_loss = gross_annual_income * (vacancy_rate / 100)
    effective_gross_income = gross_annual_income - vacancy_loss

    income_analysis = {
        "monthly_rent": round2(monthly_rent),
        "other_monthly_income": round2(other_monthly_income),
        "gross_monthly_income": round2(gross_monthly_income),
        "gross_annual_income": round2(gross_annual_income),
        "vacancy_rate": vacancy_rate,
        "vacancy_loss": round2(vacancy_loss),
        "effective_gross_income": round2(effective_gross_income),
    }

    # Expense analysis
    total_annual_expenses = _total_expenses(property_expenses)
    expense_items = {k: round2(v) for k, v in property_expenses.items()}
    expense_ratio = _safe_div(total_annual_expenses, effective_gross_income) * 100

    expense_analysis = {
        "itemized_expenses": expense_items,
        "total_annual_expenses": round2(total_annual_expenses),
        "monthly_expenses": round2(total_annual_expenses / 12),
        "expense_ratio": round2(expense_ratio),
    }

    # NOI
    noi = effective_gross_income - total_annual_expenses
    monthly_noi = noi / 12

    noi_analysis = {
        "net_operating_income": round2(noi),
        "monthly_noi": round2(monthly_noi),
        "noi_margin": round2(_safe_div(noi, effective_gross_income) * 100),
    }

    # Debt service
    loan_amount = loan_details.get("loan_amount", 0)
    interest_rate = loan_details.get("interest_rate", 0)
    loan_term = loan_details.get("loan_term_years", 30)
    loan_type = loan_details.get("loan_type", "dscr")

    if loan_amount > 0:
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term * 12
        monthly_payment = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
        annual_debt_service = monthly_payment * 12
    else:
        monthly_payment = 0.0
        annual_debt_service = 0.0

    debt_service = {
        "loan_amount": round2(loan_amount),
        "interest_rate": interest_rate,
        "loan_term_years": loan_term,
        "monthly_payment": round2(monthly_payment),
        "annual_debt_service": round2(annual_debt_service),
    }

    # DSCR
    dscr_val = _safe_div(noi, annual_debt_service) if annual_debt_service > 0 else float("inf")

    dscr_analysis = {
        "dscr": round2(dscr_val) if dscr_val != float("inf") else "N/A (no debt)",
        "noi": round2(noi),
        "annual_debt_service": round2(annual_debt_service),
        "surplus_deficit": round2(noi - annual_debt_service),
        "monthly_surplus_deficit": round2((noi - annual_debt_service) / 12),
    }

    # Loan qualification
    min_dscr_requirements = {
        "conventional": 1.25,
        "dscr": 1.0,
        "portfolio": 1.2,
        "commercial": 1.25,
    }
    required_dscr = min_dscr_requirements.get(loan_type, 1.25)
    qualifies = dscr_val >= required_dscr if dscr_val != float("inf") else True

    qualification_analysis = {
        "loan_type": loan_type,
        "required_minimum_dscr": required_dscr,
        "actual_dscr": round2(dscr_val) if dscr_val != float("inf") else "N/A",
        "qualifies": qualifies,
        "margin": round2(dscr_val - required_dscr) if dscr_val != float("inf") else "N/A",
        "all_loan_type_requirements": {
            lt: {
                "min_dscr": req,
                "qualifies": (dscr_val >= req) if dscr_val != float("inf") else True,
            }
            for lt, req in min_dscr_requirements.items()
        },
    }

    # Loan metrics
    purchase_price = property_details.get("purchase_price", 0)
    ltv = _safe_div(loan_amount, purchase_price) * 100 if purchase_price else 0
    cap_rate = _safe_div(noi, purchase_price) * 100 if purchase_price else 0

    loan_metrics = {
        "loan_to_value": round2(ltv),
        "cap_rate": round2(cap_rate),
        "debt_yield": round2(_safe_div(noi, loan_amount) * 100) if loan_amount else "N/A",
    }

    # Maximum loan analysis
    if annual_debt_service > 0 and dscr_val != float("inf"):
        max_annual_ds = noi / required_dscr
        max_monthly_ds = max_annual_ds / 12
        # Back-calculate max loan from max monthly payment
        monthly_rate = interest_rate / 100 / 12
        if monthly_rate > 0:
            max_loan = max_monthly_ds * ((1 - (1 + monthly_rate) ** -(loan_term * 12)) / monthly_rate)
        else:
            max_loan = max_monthly_ds * loan_term * 12
        additional_capacity = max(max_loan - loan_amount, 0)
    else:
        max_loan = 0
        max_annual_ds = noi
        additional_capacity = 0

    maximum_loan_analysis = {
        "maximum_loan_at_required_dscr": round2(max_loan),
        "current_loan_amount": round2(loan_amount),
        "additional_borrowing_capacity": round2(additional_capacity),
        "maximum_annual_debt_service": round2(max_annual_ds),
    }

    # Stress tests
    stress_tests = []

    # Vacancy stress
    for extra_vac in [5, 10, 15]:
        adj_vac = vacancy_rate + extra_vac
        adj_egi = gross_annual_income * (1 - adj_vac / 100)
        adj_noi = adj_egi - total_annual_expenses
        adj_dscr = _safe_div(adj_noi, annual_debt_service) if annual_debt_service else 0
        stress_tests.append({
            "scenario": f"+{extra_vac}% Vacancy (total {adj_vac}%)",
            "noi": round2(adj_noi),
            "dscr": round2(adj_dscr),
            "passes_minimum": adj_dscr >= required_dscr,
        })

    # Expense stress
    for pct in [10, 20]:
        adj_exp = total_annual_expenses * (1 + pct / 100)
        adj_noi = effective_gross_income - adj_exp
        adj_dscr = _safe_div(adj_noi, annual_debt_service) if annual_debt_service else 0
        stress_tests.append({
            "scenario": f"+{pct}% Expenses",
            "noi": round2(adj_noi),
            "dscr": round2(adj_dscr),
            "passes_minimum": adj_dscr >= required_dscr,
        })

    # Combined stress
    adj_vac = vacancy_rate + 5
    adj_egi = gross_annual_income * (1 - adj_vac / 100)
    adj_exp = total_annual_expenses * 1.1
    adj_noi = adj_egi - adj_exp
    adj_dscr = _safe_div(adj_noi, annual_debt_service) if annual_debt_service else 0
    stress_tests.append({
        "scenario": "Combined: +5% Vacancy + 10% Expenses",
        "noi": round2(adj_noi),
        "dscr": round2(adj_dscr),
        "passes_minimum": adj_dscr >= required_dscr,
    })

    stress_test_results = {
        "scenarios": stress_tests,
        "passes_all": all(s["passes_minimum"] for s in stress_tests),
    }

    # Break-even analysis
    if annual_debt_service > 0:
        be_occupancy = _safe_div(
            (total_annual_expenses + annual_debt_service),
            gross_annual_income,
        ) * 100
    else:
        be_occupancy = _safe_div(total_annual_expenses, gross_annual_income) * 100

    break_even_analysis = {
        "break_even_occupancy": round2(be_occupancy),
        "current_occupancy": round2(100 - vacancy_rate),
        "occupancy_cushion": round2(100 - vacancy_rate - be_occupancy),
        "break_even_rent": round2(
            _safe_div((total_annual_expenses + annual_debt_service), 12 * (1 - vacancy_rate / 100))
        ),
    }

    # Performance metrics
    units = property_details.get("units", 1)
    performance_metrics = {
        "per_unit_noi": round2(noi / units) if units else round2(noi),
        "per_unit_rent": round2(monthly_rent / units) if units else round2(monthly_rent),
        "per_unit_expenses": round2(total_annual_expenses / units) if units else round2(total_annual_expenses),
        "operating_expense_ratio": round2(expense_ratio),
        "property_type": property_details.get("property_type", "Not specified"),
        "total_units": units,
    }

    # Recommendations
    recommendations = []
    if dscr_val != float("inf"):
        if dscr_val >= 1.5:
            recommendations.append(f"Strong DSCR of {round2(dscr_val)} — comfortable debt coverage")
        elif dscr_val >= required_dscr:
            recommendations.append(f"DSCR of {round2(dscr_val)} meets {loan_type} requirements")
        else:
            recommendations.append(
                f"DSCR of {round2(dscr_val)} is below {required_dscr} minimum for {loan_type} loans"
            )
            recommendations.append("Consider increasing down payment, raising rents, or reducing expenses")

    if not stress_test_results["passes_all"]:
        recommendations.append("Property fails some stress tests — limited margin of safety")

    if be_occupancy > 85:
        recommendations.append("High break-even occupancy — limited vacancy tolerance")

    if expense_ratio > 50:
        recommendations.append("Expense ratio above 50% — review for cost reduction opportunities")

    return {
        "income_analysis": income_analysis,
        "expense_analysis": expense_analysis,
        "noi_analysis": noi_analysis,
        "debt_service": debt_service,
        "dscr_analysis": dscr_analysis,
        "loan_metrics": loan_metrics,
        "qualification_analysis": qualification_analysis,
        "maximum_loan_analysis": maximum_loan_analysis,
        "stress_test_results": stress_test_results,
        "break_even_analysis": break_even_analysis,
        "performance_metrics": performance_metrics,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 6. analyze_breakeven
# ---------------------------------------------------------------------------


def analyze_breakeven(
    property_costs: dict,
    fixed_costs: dict | None = None,
    variable_costs: dict | None = None,
    revenue_streams: dict | None = None,
    analysis_parameters: dict | None = None,
) -> dict:
    """Analyze break-even points for a rental property investment."""
    if fixed_costs is None:
        fixed_costs = {}
    if variable_costs is None:
        variable_costs = {}
    if revenue_streams is None:
        revenue_streams = {}
    if analysis_parameters is None:
        analysis_parameters = {}

    # Property costs
    purchase_price = property_costs.get("purchase_price", 0)
    down_payment = property_costs.get("down_payment", 0)
    renovation_costs = property_costs.get("renovation_costs", 0)
    closing_costs = property_costs.get("closing_costs", 0)
    total_initial = down_payment + renovation_costs + closing_costs

    initial_investment = {
        "purchase_price": round2(purchase_price),
        "down_payment": round2(down_payment),
        "renovation_costs": round2(renovation_costs),
        "closing_costs": round2(closing_costs),
        "total_initial_investment": round2(total_initial),
    }

    # Fixed costs (monthly)
    mortgage_payment = fixed_costs.get("mortgage_payment", 0)
    property_tax = fixed_costs.get("property_tax", 0)
    insurance = fixed_costs.get("insurance", 0)
    hoa = fixed_costs.get("hoa", 0)
    other_fixed = sum(v for k, v in fixed_costs.items()
                      if k not in ("mortgage_payment", "property_tax", "insurance", "hoa"))
    total_fixed_monthly = mortgage_payment + property_tax + insurance + hoa + other_fixed
    total_fixed_annual = total_fixed_monthly * 12

    # Variable costs
    utilities_per_unit = variable_costs.get("utilities_per_unit", 0)
    maintenance_percent = variable_costs.get("maintenance_percent", 5)
    vacancy_rate = variable_costs.get("vacancy_rate", 5)
    management_percent = variable_costs.get("management_percent", 0)

    # Revenue
    monthly_rent_per_unit = revenue_streams.get("monthly_rent_per_unit", 0)
    total_units = revenue_streams.get("total_units", 1)
    other_monthly_income = revenue_streams.get("other_monthly_income", 0)
    annual_rent_increase = revenue_streams.get("annual_rent_increase", 3)

    gross_monthly_rent = monthly_rent_per_unit * total_units + other_monthly_income
    gross_annual_rent = gross_monthly_rent * 12

    # Variable costs calculation
    vacancy_loss = gross_annual_rent * (vacancy_rate / 100)
    maintenance_cost = gross_annual_rent * (maintenance_percent / 100)
    management_cost = gross_annual_rent * (management_percent / 100)
    utilities_annual = utilities_per_unit * total_units * 12
    total_variable_annual = vacancy_loss + maintenance_cost + management_cost + utilities_annual
    total_variable_monthly = total_variable_annual / 12

    effective_income = gross_annual_rent - vacancy_loss
    total_annual_costs = total_fixed_annual + total_variable_annual
    total_monthly_costs = total_annual_costs / 12

    cost_analysis = {
        "fixed_costs": {
            "mortgage_payment": round2(mortgage_payment),
            "property_tax": round2(property_tax),
            "insurance": round2(insurance),
            "hoa": round2(hoa),
            "other": round2(other_fixed),
            "total_monthly": round2(total_fixed_monthly),
            "total_annual": round2(total_fixed_annual),
        },
        "variable_costs": {
            "vacancy_loss": round2(vacancy_loss),
            "maintenance": round2(maintenance_cost),
            "management": round2(management_cost),
            "utilities": round2(utilities_annual),
            "total_monthly": round2(total_variable_monthly),
            "total_annual": round2(total_variable_annual),
        },
        "total_monthly_costs": round2(total_monthly_costs),
        "total_annual_costs": round2(total_annual_costs),
    }

    # Break-even analysis

    # 1. Break-even occupancy rate
    # At what occupancy do revenues cover all costs?
    if gross_annual_rent > 0:
        # Revenue at occupancy X = gross_annual_rent * (X/100) - variable costs that scale
        # Fixed costs + non-vacancy variable costs must be covered
        non_vacancy_variable = maintenance_cost + management_cost + utilities_annual
        # Revenue at occupancy x = gross_annual_rent * (x/100)
        # Costs = total_fixed_annual + non_vacancy_variable
        # Breakeven: gross_annual_rent * x/100 = total_fixed_annual + non_vacancy_variable
        breakeven_occupancy = _safe_div(
            (total_fixed_annual + non_vacancy_variable), gross_annual_rent
        ) * 100
    else:
        breakeven_occupancy = 100.0

    # 2. Break-even rent per unit
    if total_units > 0:
        # What rent makes annual income = annual costs?
        # rent * units * 12 * (1 - vacancy/100) = total_fixed_annual + variable costs
        # Solve for rent
        occupancy_factor = (1 - vacancy_rate / 100)
        if occupancy_factor > 0:
            # Approximate: ignore percentage-based variable costs scaling with rent
            be_annual_need = total_fixed_annual + utilities_annual
            # maintenance and management scale with rent, so:
            # rent * U * 12 * occ * (1 - maint% - mgmt%) = be_annual_need
            scale = 1 - (maintenance_percent + management_percent) / 100
            denominator = total_units * 12 * occupancy_factor * scale
            breakeven_rent = _safe_div(be_annual_need, denominator)
        else:
            breakeven_rent = 0
    else:
        breakeven_rent = 0

    # 3. Time to positive cash flow (months from start)
    annual_cash_flow = effective_income - total_annual_costs + vacancy_loss  # add back vacancy since it's in variable
    # Recalculate properly
    net_annual = effective_income - maintenance_cost - management_cost - utilities_annual - total_fixed_annual
    monthly_net = net_annual / 12

    if monthly_net > 0:
        time_to_positive = 0  # Already positive
    else:
        # With annual rent increases, when does it become positive?
        time_to_positive = None
        proj_rent = gross_monthly_rent
        proj_costs = total_monthly_costs
        for month in range(1, 361):  # 30 years max
            if month % 12 == 0:
                proj_rent *= (1 + annual_rent_increase / 100)
            proj_eff = proj_rent * (1 - vacancy_rate / 100)
            proj_var = (proj_rent * 12 * (maintenance_percent + management_percent) / 100) / 12 + utilities_per_unit * total_units
            proj_net = proj_eff - total_fixed_monthly - proj_var
            if proj_net > 0:
                time_to_positive = month
                break

    # 4. ROI break-even (when cumulative cash flow = initial investment)
    if monthly_net > 0:
        roi_breakeven_months = total_initial / monthly_net
        roi_breakeven_years = roi_breakeven_months / 12
    elif monthly_net == 0:
        roi_breakeven_months = None
        roi_breakeven_years = None
    else:
        roi_breakeven_months = None
        roi_breakeven_years = None

    breakeven_analysis = {
        "breakeven_occupancy": {
            "rate": round2(breakeven_occupancy),
            "current_occupancy": round2(100 - vacancy_rate),
            "margin": round2(100 - vacancy_rate - breakeven_occupancy),
        },
        "breakeven_rent": {
            "per_unit_monthly": round2(breakeven_rent),
            "current_rent_per_unit": round2(monthly_rent_per_unit),
            "margin": round2(monthly_rent_per_unit - breakeven_rent),
            "margin_percent": round2(_safe_div(monthly_rent_per_unit - breakeven_rent, monthly_rent_per_unit) * 100),
        },
        "time_to_positive_cash_flow": {
            "months": time_to_positive if time_to_positive is not None else "N/A",
            "already_positive": monthly_net > 0,
        },
        "roi_breakeven": {
            "months": round2(roi_breakeven_months) if roi_breakeven_months is not None else "N/A",
            "years": round2(roi_breakeven_years) if roi_breakeven_years is not None else "N/A",
        },
    }

    # Current performance
    cocr = _safe_div(net_annual, total_initial) * 100 if total_initial else 0
    current_performance = {
        "gross_monthly_income": round2(gross_monthly_rent),
        "effective_monthly_income": round2(effective_income / 12),
        "total_monthly_costs": round2(total_monthly_costs),
        "net_monthly_cash_flow": round2(monthly_net),
        "net_annual_cash_flow": round2(net_annual),
        "cash_on_cash_return": round2(cocr),
    }

    # Sensitivity analysis
    sensitivity_scenarios = []
    for rent_delta in [-10, -5, 0, 5, 10]:
        for vac_delta in [0, 5, 10]:
            adj_rent = monthly_rent_per_unit * (1 + rent_delta / 100)
            adj_gross = adj_rent * total_units * 12 + other_monthly_income * 12
            adj_vac = vacancy_rate + vac_delta
            adj_eff = adj_gross * (1 - adj_vac / 100)
            adj_var = adj_gross * (maintenance_percent + management_percent) / 100 + utilities_annual
            adj_net = adj_eff - adj_var - total_fixed_annual
            sensitivity_scenarios.append({
                "rent_change_percent": rent_delta,
                "vacancy_rate": adj_vac,
                "annual_cash_flow": round2(adj_net),
                "positive": adj_net > 0,
            })

    sensitivity_analysis = {
        "scenarios": sensitivity_scenarios,
    }

    # Analysis parameters
    target_cf = analysis_parameters.get("target_cash_flow", 0)
    analysis_years = analysis_parameters.get("analysis_period_years", 10)
    include_appreciation = analysis_parameters.get("include_appreciation", False)
    appreciation_rate = analysis_parameters.get("appreciation_rate", 3)

    # Target analysis
    if target_cf > 0:
        # What rent needed for target cash flow?
        target_annual = target_cf * 12
        needed_net = target_annual + total_fixed_annual + utilities_annual
        scale = 1 - (maintenance_percent + management_percent) / 100
        occ_factor = 1 - vacancy_rate / 100
        denom = total_units * 12 * occ_factor * scale
        target_rent = _safe_div(needed_net, denom) if denom else 0
        target_gap = target_cf - monthly_net
    else:
        target_rent = breakeven_rent
        target_gap = 0

    target_analysis = {
        "target_monthly_cash_flow": round2(target_cf),
        "current_monthly_cash_flow": round2(monthly_net),
        "gap": round2(target_gap),
        "required_rent_per_unit": round2(target_rent),
        "rent_increase_needed": round2(target_rent - monthly_rent_per_unit),
        "achievable": monthly_net >= target_cf,
    }

    # Multi-year projection
    expense_growth_rate = 0.025
    multi_year = []
    proj_rent_annual = gross_annual_rent
    proj_fixed = total_fixed_annual
    proj_value = purchase_price

    for year in range(1, analysis_years + 1):
        if year > 1:
            proj_rent_annual *= (1 + annual_rent_increase / 100)
            proj_fixed *= (1 + expense_growth_rate)  # approximate
        proj_eff = proj_rent_annual * (1 - vacancy_rate / 100)
        proj_var = proj_rent_annual * (maintenance_percent + management_percent) / 100 + utilities_annual
        proj_net = proj_eff - proj_var - proj_fixed
        cumulative = sum(
            entry["net_cash_flow"] for entry in multi_year
        ) + proj_net

        entry: dict = {
            "year": year,
            "gross_income": round2(proj_rent_annual),
            "total_costs": round2(proj_fixed + proj_var),
            "net_cash_flow": round2(proj_net),
            "cumulative_cash_flow": round2(cumulative),
        }
        if include_appreciation:
            proj_value *= (1 + appreciation_rate / 100)
            entry["property_value"] = round2(proj_value)
            entry["total_equity_gain"] = round2(proj_value - purchase_price)
        multi_year.append(entry)

    multi_year_projection = {
        "assumptions": {
            "annual_rent_increase": annual_rent_increase,
            "expense_growth_rate": expense_growth_rate * 100,
            "include_appreciation": include_appreciation,
            "appreciation_rate": appreciation_rate if include_appreciation else "N/A",
        },
        "projections": multi_year,
    }

    # Risk assessment
    risk_factors = []
    risk_score = 100

    if breakeven_occupancy > 85:
        risk_factors.append("High break-even occupancy — limited vacancy tolerance")
        risk_score -= 20
    if monthly_net < 0:
        risk_factors.append("Negative cash flow from day one")
        risk_score -= 25
    if cocr < 5:
        risk_factors.append("Cash-on-cash return below 5%")
        risk_score -= 15
    if monthly_rent_per_unit - breakeven_rent < monthly_rent_per_unit * 0.1:
        risk_factors.append("Break-even rent is very close to current rent — thin margin")
        risk_score -= 15
    if total_units == 1:
        risk_factors.append("Single-unit property — no income diversification")
        risk_score -= 10

    risk_score = max(risk_score, 0)

    risk_assessment = {
        "risk_score": risk_score,
        "risk_level": _risk_level(risk_score),
        "risk_factors": risk_factors,
    }

    # Recommendations
    recommendations = []
    if monthly_net > 0:
        recommendations.append(f"Property generates ${round2(monthly_net)}/month positive cash flow")
    else:
        recommendations.append(f"Property has ${round2(monthly_net)}/month negative cash flow — needs improvement")

    if breakeven_occupancy < 75:
        recommendations.append(f"Low break-even occupancy ({round2(breakeven_occupancy)}%) provides safety margin")
    elif breakeven_occupancy < 90:
        recommendations.append(f"Moderate break-even occupancy ({round2(breakeven_occupancy)}%) — manageable risk")
    else:
        recommendations.append(f"High break-even occupancy ({round2(breakeven_occupancy)}%) — consider risk mitigation")

    if roi_breakeven_years is not None and roi_breakeven_years <= 5:
        recommendations.append(f"Investment pays back in {round2(roi_breakeven_years)} years — attractive timeline")
    elif roi_breakeven_years is not None:
        recommendations.append(f"Long payback period of {round2(roi_breakeven_years)} years — evaluate alternatives")

    if monthly_rent_per_unit < breakeven_rent:
        rent_gap = breakeven_rent - monthly_rent_per_unit
        recommendations.append(f"Increase rent by ${round2(rent_gap)}/unit to reach break-even")

    return {
        "initial_investment": initial_investment,
        "cost_analysis": cost_analysis,
        "breakeven_analysis": breakeven_analysis,
        "current_performance": current_performance,
        "sensitivity_analysis": sensitivity_analysis,
        "target_analysis": target_analysis,
        "multi_year_projection": multi_year_projection,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
    }
