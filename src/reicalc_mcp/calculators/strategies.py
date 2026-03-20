"""Investment strategy calculators: Airbnb/STR, 1031 Exchange, Wholesale, Subject-To."""

from ._common import calculate_mortgage_payment, calculate_irr, safe_irr_pct, round2
from ._validation import validate_positive, validate_non_negative, validate_percent


# ---------------------------------------------------------------------------
# 1. Airbnb / Short-Term Rental Analysis
# ---------------------------------------------------------------------------

def analyze_airbnb_str(
    purchase_price: float,
    average_daily_rate: float,
    down_payment_percent: float = 20,
    interest_rate: float = 7,
    occupancy_rate: float = 65,
    monthly_expenses: float = 0,
    management_fee_percent: float = 20,
    cleaning_fee_per_turnover: float = 100,
    average_stay_nights: float = 3,
    seasonal_adjustment: dict[str, float] | None = None,
    furnishing_cost: float = 0,
    platform_fee_percent: float = 3,
    ltr_rent_estimate: float | None = None,
) -> dict:
    """Analyze an Airbnb / short-term rental deal and compare to long-term rental."""

    validate_positive(purchase_price, "purchase_price")
    validate_positive(average_daily_rate, "average_daily_rate")
    validate_percent(occupancy_rate, "occupancy_rate")

    # --- Financing ---
    down_payment = purchase_price * down_payment_percent / 100
    loan_amount = purchase_price - down_payment
    monthly_rate = interest_rate / 100 / 12
    num_payments = 30 * 12
    monthly_mortgage = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)

    # --- Revenue ---
    occupied_nights_year = 365 * (occupancy_rate / 100)
    annual_gross_revenue = average_daily_rate * occupied_nights_year

    # Turnovers
    turnovers_per_year = occupied_nights_year / average_stay_nights if average_stay_nights > 0 else 0
    annual_cleaning_cost = turnovers_per_year * cleaning_fee_per_turnover

    # Fees
    annual_management_fee = annual_gross_revenue * management_fee_percent / 100
    annual_platform_fee = annual_gross_revenue * platform_fee_percent / 100
    annual_operating_expenses = monthly_expenses * 12

    total_annual_expenses = (
        annual_cleaning_cost
        + annual_management_fee
        + annual_platform_fee
        + annual_operating_expenses
    )

    annual_net_revenue = annual_gross_revenue - total_annual_expenses
    monthly_net_revenue = annual_net_revenue / 12

    # --- Cash flow ---
    monthly_cash_flow_str = monthly_net_revenue - monthly_mortgage
    annual_cash_flow_str = monthly_cash_flow_str * 12

    # --- Long-term rental estimate (0.7 % of purchase price per month, or user-supplied) ---
    monthly_ltr_rent = ltr_rent_estimate if ltr_rent_estimate is not None else purchase_price * 0.007
    annual_ltr_gross = monthly_ltr_rent * 12
    # Assume 8 % vacancy, 10 % management for LTR
    annual_ltr_net = annual_ltr_gross * (1 - 0.08) * (1 - 0.10) - annual_operating_expenses
    monthly_cash_flow_ltr = annual_ltr_net / 12 - monthly_mortgage
    annual_cash_flow_ltr = monthly_cash_flow_ltr * 12

    # --- Total cash invested ---
    total_cash_invested = down_payment + furnishing_cost

    # --- Cash-on-cash ---
    coc_str = (annual_cash_flow_str / total_cash_invested * 100) if total_cash_invested > 0 else 0
    coc_ltr = (annual_cash_flow_ltr / total_cash_invested * 100) if total_cash_invested > 0 else 0

    # --- Break-even occupancy ---
    # Find occupancy where monthly net revenue == monthly mortgage
    # net = ADR * occ * 365/12 - fees(occ) - expenses/12 = mortgage
    # revenue_per_occ_point = ADR * 365 / 12  (per 1.0 occupancy)
    # fees are proportional to revenue: (management + platform) %
    # cleaning per month = (occ * 365 / avg_stay) / 12 * cleaning_fee
    fee_pct = (management_fee_percent + platform_fee_percent) / 100
    rev_per_unit_occ = average_daily_rate * 365  # annual revenue at 100 % occupancy
    cleaning_per_unit_occ = (365 / average_stay_nights * cleaning_fee_per_turnover) if average_stay_nights > 0 else 0

    net_per_unit_occ = rev_per_unit_occ * (1 - fee_pct) - cleaning_per_unit_occ
    annual_fixed = annual_operating_expenses + monthly_mortgage * 12
    break_even_occ = (annual_fixed / net_per_unit_occ * 100) if net_per_unit_occ > 0 else 0

    # --- Seasonal breakdown ---
    seasonal_breakdown: list[dict] | None = None
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    ]

    if seasonal_adjustment is not None:
        seasonal_breakdown = []
        for month in month_names:
            multiplier = seasonal_adjustment.get(month, 1.0)
            adj_occ = min(occupancy_rate * multiplier, 100)
            days_in_month = 30  # simplified
            occupied_nights = days_in_month * adj_occ / 100
            gross = average_daily_rate * occupied_nights
            turnovers = occupied_nights / average_stay_nights if average_stay_nights > 0 else 0
            cleaning = turnovers * cleaning_fee_per_turnover
            mgmt = gross * management_fee_percent / 100
            platform = gross * platform_fee_percent / 100
            net = gross - cleaning - mgmt - platform - monthly_expenses
            cash_flow = net - monthly_mortgage
            seasonal_breakdown.append({
                "month": month,
                "occupancy_rate": round2(adj_occ),
                "occupied_nights": round2(occupied_nights),
                "gross_revenue": round2(gross),
                "net_revenue": round2(net),
                "cash_flow": round2(cash_flow),
            })

    # --- Risk assessment ---
    risk_assessment = _str_risk_assessment(occupancy_rate, break_even_occ, annual_cash_flow_str, coc_str)

    # --- Recommendations ---
    recommendations = _str_recommendations(
        coc_str, coc_ltr, break_even_occ, occupancy_rate, annual_cash_flow_str, annual_cash_flow_ltr,
    )

    return {
        "revenue_analysis": {
            "annual_gross_revenue": round2(annual_gross_revenue),
            "annual_net_after_fees": round2(annual_net_revenue),
            "monthly_gross_revenue": round2(annual_gross_revenue / 12),
            "monthly_net_after_fees": round2(monthly_net_revenue),
            "occupied_nights_per_year": round2(occupied_nights_year),
            "turnovers_per_year": round(turnovers_per_year),
        },
        "expense_analysis": {
            "annual_management_fees": round2(annual_management_fee),
            "annual_cleaning_costs": round2(annual_cleaning_cost),
            "annual_platform_fees": round2(annual_platform_fee),
            "annual_operating_expenses": round2(annual_operating_expenses),
            "total_annual_expenses": round2(total_annual_expenses),
            "furnishing_cost": round2(furnishing_cost),
        },
        "cash_flow_comparison": {
            "str_monthly_cash_flow": round2(monthly_cash_flow_str),
            "str_annual_cash_flow": round2(annual_cash_flow_str),
            "str_cash_on_cash_return": round2(coc_str),
            "ltr_estimated_monthly_rent": round2(monthly_ltr_rent),
            "ltr_monthly_cash_flow": round2(monthly_cash_flow_ltr),
            "ltr_annual_cash_flow": round2(annual_cash_flow_ltr),
            "ltr_cash_on_cash_return": round2(coc_ltr),
            "str_premium_over_ltr": round2(annual_cash_flow_str - annual_cash_flow_ltr),
        },
        "financing": {
            "purchase_price": round2(purchase_price),
            "down_payment": round2(down_payment),
            "loan_amount": round2(loan_amount),
            "monthly_mortgage_payment": round2(monthly_mortgage),
            "interest_rate": interest_rate,
            "total_cash_invested": round2(total_cash_invested),
        },
        "seasonal_breakdown": seasonal_breakdown,
        "risk_assessment": risk_assessment,
        "break_even_occupancy": round2(break_even_occ),
        "recommendations": recommendations,
    }


def _str_risk_assessment(
    occupancy_rate: float,
    break_even_occ: float,
    annual_cash_flow: float,
    coc: float,
) -> dict:
    """Build risk assessment dict for STR analysis."""
    occupancy_buffer = occupancy_rate - break_even_occ

    if occupancy_buffer >= 20:
        occupancy_risk = "Low"
    elif occupancy_buffer >= 10:
        occupancy_risk = "Moderate"
    else:
        occupancy_risk = "High"

    return {
        "occupancy_sensitivity": {
            "current_occupancy": occupancy_rate,
            "break_even_occupancy": round2(break_even_occ),
            "buffer": round2(occupancy_buffer),
            "risk_level": occupancy_risk,
        },
        "regulation_risk": (
            "Short-term rental regulations are changing rapidly in many markets. "
            "Verify local zoning, licensing, and HOA restrictions before purchasing."
        ),
        "competition_risk": (
            "STR markets can become saturated quickly. Research comparable listings, "
            "average occupancy trends, and new supply in the target area."
        ),
        "overall_risk": (
            "Low" if annual_cash_flow > 0 and coc > 8 and occupancy_buffer >= 15
            else "Moderate" if annual_cash_flow > 0
            else "High"
        ),
    }


def _str_recommendations(
    coc_str: float,
    coc_ltr: float,
    break_even_occ: float,
    occupancy_rate: float,
    annual_cf_str: float,
    annual_cf_ltr: float,
) -> list[str]:
    recs: list[str] = []

    if annual_cf_str > annual_cf_ltr:
        recs.append(
            f"STR strategy produces ${round2(annual_cf_str - annual_cf_ltr):,.2f} more "
            f"annual cash flow than LTR. Consider STR if regulations allow."
        )
    else:
        recs.append(
            "Long-term rental produces equal or better cash flow. STR may not "
            "justify the additional effort and risk."
        )

    if break_even_occ > occupancy_rate * 0.85:
        recs.append(
            "Break-even occupancy is close to projected occupancy. "
            "Small dips in demand could eliminate cash flow."
        )
    elif break_even_occ < 40:
        recs.append("Strong break-even buffer provides downside protection.")

    if coc_str < 5:
        recs.append("Cash-on-cash return below 5 %. Evaluate whether the effort is worthwhile.")
    elif coc_str >= 12:
        recs.append("Excellent cash-on-cash return. This looks like a strong STR opportunity.")

    recs.append("Verify local STR regulations, insurance requirements, and tax implications.")
    return recs


# ---------------------------------------------------------------------------
# 2. 1031 Exchange Analysis
# ---------------------------------------------------------------------------

def analyze_1031_exchange(
    relinquished_property: dict,
    replacement_property: dict,
    holding_period_years: float = 0,
    filing_status: str = "single",
    capital_gains_rate: float = 15,
    state_tax_rate: float = 5,
) -> dict:
    """Analyze a 1031 tax-deferred exchange scenario."""

    # --- Unpack relinquished property ---
    sale_price: float = relinquished_property["sale_price"]
    adjusted_basis: float = relinquished_property["adjusted_basis"]
    selling_costs_pct: float = relinquished_property.get("selling_costs_percent", 6)
    depreciation_taken: float = relinquished_property.get("depreciation_taken", 0)
    original_purchase_price: float = relinquished_property.get("original_purchase_price", adjusted_basis)

    # --- Unpack replacement property ---
    replacement_price: float = replacement_property["purchase_price"]
    replacement_closing: float = replacement_property.get("closing_costs", 0)

    # --- Relinquished property analysis ---
    selling_costs = sale_price * selling_costs_pct / 100
    net_sale_price = sale_price - selling_costs

    capital_gain = net_sale_price - adjusted_basis
    appreciation_gain = capital_gain - depreciation_taken

    # --- Tax liability without exchange ---
    depreciation_recapture_rate = 25.0
    depreciation_recapture_tax = depreciation_taken * depreciation_recapture_rate / 100
    federal_capital_gains_tax = max(appreciation_gain, 0) * capital_gains_rate / 100
    state_tax = max(capital_gain, 0) * state_tax_rate / 100

    # Net Investment Income Tax (3.8 % for high earners — include as informational)
    niit = max(capital_gain, 0) * 3.8 / 100

    total_tax_without_exchange = (
        depreciation_recapture_tax + federal_capital_gains_tax + state_tax + niit
    )

    # --- Boot calculation ---
    # Boot = cash or non-like-kind property received
    # If replacement < net sale price, the difference is boot (taxable)
    total_replacement_cost = replacement_price + replacement_closing
    boot = max(net_sale_price - total_replacement_cost, 0)
    boot_tax = 0.0
    if boot > 0:
        boot_tax = boot * (capital_gains_rate + state_tax_rate + 3.8) / 100

    taxes_deferred = total_tax_without_exchange - boot_tax

    # --- Reinvest comparison (no exchange) ---
    proceeds_after_tax = net_sale_price - total_tax_without_exchange
    # Assume reinvestment at same cap rate — compare equity positions
    equity_with_exchange = total_replacement_cost  # full equity rolled
    equity_without_exchange = proceeds_after_tax + replacement_closing  # what you could buy

    # --- Timeline ---
    timeline = {
        "day_0": "Close on relinquished property sale",
        "day_45": "Deadline to identify up to 3 replacement properties (or use 200% / 95% rule)",
        "day_180": "Deadline to close on replacement property",
        "notes": [
            "Use a Qualified Intermediary (QI) — never touch the funds directly.",
            "Both properties must be held for investment or business use.",
            "Calendar days, not business days.",
        ],
    }

    # --- Qualification checklist ---
    qualifications: list[dict[str, object]] = []

    qualifications.append({
        "requirement": "Like-kind property",
        "description": "Both properties must be real property held for investment or business use",
        "met": True,  # assumed for real estate to real estate
    })
    qualifications.append({
        "requirement": "Qualified Intermediary",
        "description": "Must use a QI to hold proceeds — cannot take constructive receipt",
        "met": None,  # user must confirm
    })
    qualifications.append({
        "requirement": "Equal or greater value",
        "description": f"Replacement (${replacement_price:,.0f}) should >= net sale (${net_sale_price:,.0f})",
        "met": replacement_price >= net_sale_price,
    })
    qualifications.append({
        "requirement": "Equal or greater debt",
        "description": "New mortgage should be >= old mortgage to avoid mortgage boot",
        "met": None,  # unknown without mortgage info
    })
    qualifications.append({
        "requirement": "Holding period",
        "description": "IRS safe harbor: hold each property >= 2 years",
        "met": holding_period_years >= 2,
    })
    qualifications.append({
        "requirement": "45-day identification",
        "description": "Replacement property must be identified within 45 days",
        "met": None,
    })
    qualifications.append({
        "requirement": "180-day closing",
        "description": "Replacement must close within 180 days of relinquished sale",
        "met": None,
    })

    # --- Comparison ---
    comparison = {
        "with_exchange": {
            "taxes_paid": round2(boot_tax),
            "total_equity_deployed": round2(total_replacement_cost),
            "tax_savings": round2(taxes_deferred),
        },
        "without_exchange": {
            "taxes_paid": round2(total_tax_without_exchange),
            "proceeds_available": round2(proceeds_after_tax),
            "purchasing_power_lost": round2(total_tax_without_exchange),
        },
        "advantage": round2(taxes_deferred),
    }

    # --- Recommendations ---
    recommendations = _1031_recommendations(
        taxes_deferred, boot, holding_period_years, replacement_price, net_sale_price,
    )

    return {
        "relinquished_property_analysis": {
            "sale_price": round2(sale_price),
            "selling_costs": round2(selling_costs),
            "net_sale_price": round2(net_sale_price),
            "original_purchase_price": round2(original_purchase_price),
            "adjusted_basis": round2(adjusted_basis),
            "depreciation_taken": round2(depreciation_taken),
            "total_capital_gain": round2(capital_gain),
            "appreciation_gain": round2(appreciation_gain),
        },
        "tax_liability_without_exchange": {
            "depreciation_recapture_tax": round2(depreciation_recapture_tax),
            "federal_capital_gains_tax": round2(federal_capital_gains_tax),
            "state_tax": round2(state_tax),
            "net_investment_income_tax": round2(niit),
            "total_tax": round2(total_tax_without_exchange),
            "effective_tax_rate": round2(
                total_tax_without_exchange / capital_gain * 100 if capital_gain > 0 else 0
            ),
        },
        "tax_deferral_benefit": {
            "total_taxes_deferred": round2(taxes_deferred),
            "present_value_note": (
                "Deferred taxes can be invested for additional returns. "
                "At a 7% return, deferred taxes double in ~10 years."
            ),
        },
        "replacement_property_requirements": {
            "minimum_price": round2(net_sale_price),
            "target_price": round2(replacement_price),
            "closing_costs": round2(replacement_closing),
            "total_acquisition_cost": round2(total_replacement_cost),
            "meets_value_requirement": replacement_price >= net_sale_price,
        },
        "boot_analysis": {
            "boot_amount": round2(boot),
            "boot_tax": round2(boot_tax),
            "boot_description": (
                "No boot — full deferral achieved."
                if boot == 0
                else f"${boot:,.2f} boot recognized. Consider increasing replacement value to avoid."
            ),
        },
        "timeline": timeline,
        "qualification_checklist": qualifications,
        "comparison": comparison,
        "recommendations": recommendations,
    }


def _1031_recommendations(
    taxes_deferred: float,
    boot: float,
    holding_period: float,
    replacement_price: float,
    net_sale_price: float,
) -> list[str]:
    recs: list[str] = []

    if taxes_deferred > 0:
        recs.append(
            f"Exchange defers ${taxes_deferred:,.2f} in taxes. "
            "Strongly consider proceeding if a suitable replacement is available."
        )
    else:
        recs.append(
            "No significant tax benefit from the exchange in this scenario."
        )

    if boot > 0:
        recs.append(
            f"${boot:,.2f} in boot will be taxable. "
            "Increase replacement property value or add debt to eliminate boot."
        )

    if holding_period < 2:
        recs.append(
            "Holding period is under 2 years. IRS may challenge exchange qualification. "
            "Consider holding longer before selling."
        )

    if replacement_price < net_sale_price:
        shortfall = net_sale_price - replacement_price
        recs.append(
            f"Replacement property is ${shortfall:,.2f} below net sale price. "
            "This will create taxable boot."
        )

    recs.append("Engage a Qualified Intermediary before listing the relinquished property.")
    recs.append("Consult a tax advisor for state-specific rules and filing requirements.")
    return recs


# ---------------------------------------------------------------------------
# 3. Wholesale Deal Analysis
# ---------------------------------------------------------------------------

def analyze_wholesale_deal(
    contract_price: float,
    after_repair_value: float,
    estimated_rehab_cost: float,
    assignment_fee: float,
    holding_costs_monthly: float = 0,
    estimated_closing_costs: float = 0,
    target_buyer_type: str = "investor",
    estimated_rehab_months: int = 6,
    ltr_rent_estimate: float | None = None,
) -> dict:
    """Analyze a wholesale real estate deal from both wholesaler and end-buyer perspectives."""

    validate_positive(contract_price, "contract_price")
    validate_positive(after_repair_value, "after_repair_value")
    validate_non_negative(estimated_rehab_cost, "estimated_rehab_cost")
    validate_non_negative(assignment_fee, "assignment_fee")

    # --- End buyer all-in cost ---
    end_buyer_purchase = contract_price + assignment_fee
    total_holding_costs = holding_costs_monthly * estimated_rehab_months
    end_buyer_all_in = end_buyer_purchase + estimated_rehab_cost + estimated_closing_costs + total_holding_costs

    # --- MAO (Maximum Allowable Offer) using 70% rule ---
    mao_70_rule = after_repair_value * 0.70 - estimated_rehab_cost
    mao_with_assignment = mao_70_rule - assignment_fee

    # --- Wholesaler profit ---
    wholesaler_profit = assignment_fee
    wholesaler_roi = (
        (assignment_fee / contract_price * 100) if contract_price > 0 else 0
    )

    # --- End buyer potential profit ---
    # For flipper: ARV - all-in - selling costs (6%)
    selling_costs_pct = 6
    selling_costs = after_repair_value * selling_costs_pct / 100
    end_buyer_gross_profit = after_repair_value - end_buyer_all_in
    end_buyer_net_profit_flip = after_repair_value - end_buyer_all_in - selling_costs
    end_buyer_roi = (
        (end_buyer_net_profit_flip / end_buyer_all_in * 100) if end_buyer_all_in > 0 else 0
    )

    # For landlord: estimate rental income
    monthly_rent_estimate = ltr_rent_estimate if ltr_rent_estimate is not None else after_repair_value * 0.007
    annual_rent = monthly_rent_estimate * 12
    # Assume 50% expense ratio for rental
    annual_noi = annual_rent * 0.50
    cap_rate = (annual_noi / end_buyer_all_in * 100) if end_buyer_all_in > 0 else 0

    # --- Deal viability ---
    meets_70_rule = contract_price <= mao_70_rule
    profit_margin_pct = (
        (end_buyer_net_profit_flip / after_repair_value * 100) if after_repair_value > 0 else 0
    )

    if meets_70_rule and end_buyer_net_profit_flip > 20000 and profit_margin_pct > 10:
        viability = "Strong"
    elif meets_70_rule and end_buyer_net_profit_flip > 10000:
        viability = "Moderate"
    elif end_buyer_net_profit_flip > 0:
        viability = "Marginal"
    else:
        viability = "Not viable"

    # --- Exit strategies ---
    exit_strategies = [
        {
            "strategy": "Fix and Flip",
            "all_in_cost": round2(end_buyer_all_in),
            "expected_sale_price": round2(after_repair_value),
            "selling_costs": round2(selling_costs),
            "net_profit": round2(end_buyer_net_profit_flip),
            "roi": round2(end_buyer_roi),
            "timeline": f"{estimated_rehab_months} months rehab + 3 months sale",
        },
        {
            "strategy": "Buy and Hold (Rental)",
            "all_in_cost": round2(end_buyer_all_in),
            "estimated_monthly_rent": round2(monthly_rent_estimate),
            "annual_noi": round2(annual_noi),
            "cap_rate": round2(cap_rate),
            "forced_equity": round2(after_repair_value - end_buyer_all_in),
        },
        {
            "strategy": "BRRRR",
            "all_in_cost": round2(end_buyer_all_in),
            "after_repair_value": round2(after_repair_value),
            "potential_refinance_amount": round2(after_repair_value * 0.75),
            "cash_left_in_deal": round2(max(end_buyer_all_in - after_repair_value * 0.75, 0)),
            "estimated_monthly_rent": round2(monthly_rent_estimate),
        },
    ]

    # --- Risk assessment ---
    risk_assessment = _wholesale_risk_assessment(
        contract_price, mao_70_rule, end_buyer_net_profit_flip, estimated_rehab_cost,
        after_repair_value, assignment_fee,
    )

    # --- Recommendations ---
    recommendations = _wholesale_recommendations(
        viability, meets_70_rule, assignment_fee, end_buyer_net_profit_flip,
        target_buyer_type, cap_rate,
    )

    return {
        "deal_summary": {
            "contract_price": round2(contract_price),
            "assignment_fee": round2(assignment_fee),
            "after_repair_value": round2(after_repair_value),
            "estimated_rehab_cost": round2(estimated_rehab_cost),
            "target_buyer_type": target_buyer_type,
        },
        "wholesaler_profit": {
            "assignment_fee": round2(assignment_fee),
            "roi_on_contract": round2(wholesaler_roi),
            "note": "Wholesaler profit assumes no earnest money loss risk.",
        },
        "end_buyer_analysis": {
            "purchase_price": round2(end_buyer_purchase),
            "all_in_cost": round2(end_buyer_all_in),
            "potential_gross_profit": round2(end_buyer_gross_profit),
            "potential_net_profit": round2(end_buyer_net_profit_flip),
            "roi": round2(end_buyer_roi),
            "profit_margin_percent": round2(profit_margin_pct),
        },
        "mao_analysis": {
            "mao_70_percent_rule": round2(mao_70_rule),
            "mao_after_assignment_fee": round2(mao_with_assignment),
            "contract_price": round2(contract_price),
            "meets_70_percent_rule": meets_70_rule,
            "spread": round2(mao_70_rule - contract_price),
        },
        "deal_viability": viability,
        "exit_strategies": exit_strategies,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
    }


def _wholesale_risk_assessment(
    contract_price: float,
    mao: float,
    net_profit: float,
    rehab_cost: float,
    arv: float,
    assignment_fee: float,
) -> dict:
    rehab_to_arv = (rehab_cost / arv * 100) if arv > 0 else 0
    assignment_to_arv = (assignment_fee / arv * 100) if arv > 0 else 0

    if rehab_to_arv > 40:
        rehab_risk = "High — rehab exceeds 40% of ARV"
    elif rehab_to_arv > 25:
        rehab_risk = "Moderate — rehab is 25-40% of ARV"
    else:
        rehab_risk = "Low — rehab is under 25% of ARV"

    if assignment_to_arv > 10:
        fee_risk = "High — assignment fee may deter buyers"
    elif assignment_to_arv > 5:
        fee_risk = "Moderate"
    else:
        fee_risk = "Low"

    return {
        "arv_accuracy": "ARV is the biggest variable. Get 3+ comparable sales to validate.",
        "rehab_estimate_risk": rehab_risk,
        "rehab_to_arv_ratio": round2(rehab_to_arv),
        "assignment_fee_risk": fee_risk,
        "assignment_to_arv_ratio": round2(assignment_to_arv),
        "market_risk": "Deal profitability depends on stable or appreciating market conditions.",
    }


def _wholesale_recommendations(
    viability: str,
    meets_70: bool,
    assignment_fee: float,
    net_profit: float,
    buyer_type: str,
    cap_rate: float,
) -> list[str]:
    recs: list[str] = []

    if viability == "Strong":
        recs.append("Deal meets the 70% rule with strong margins. Good candidate for assignment.")
    elif viability == "Moderate":
        recs.append("Deal is workable but margins are thin. Negotiate a lower contract price if possible.")
    elif viability == "Marginal":
        recs.append("Marginal deal — only proceed if rehab estimates are highly reliable.")
    else:
        recs.append("Deal does not appear viable at current numbers. Renegotiate or walk away.")

    if not meets_70:
        recs.append(
            "Contract price exceeds the 70% rule MAO. "
            "Most experienced investors will pass at this price."
        )

    if buyer_type == "landlord" and cap_rate < 6:
        recs.append(
            f"Cap rate of {cap_rate:.1f}% may not attract buy-and-hold investors. "
            "Target flippers instead or renegotiate."
        )
    elif buyer_type == "flipper" and net_profit < 20000:
        recs.append(
            f"Net flip profit of ${net_profit:,.0f} may be too thin for flippers. "
            "Most want $25k+ minimum."
        )

    recs.append("Get multiple contractor bids and verify ARV with recent comps before assigning.")
    return recs


# ---------------------------------------------------------------------------
# 4. Subject-To Deal Analysis
# ---------------------------------------------------------------------------

def analyze_subject_to_deal(
    purchase_price: float,
    existing_loan_balance: float,
    existing_interest_rate: float,
    existing_loan_remaining_years: float,
    monthly_rent: float,
    monthly_expenses: float = 0,
    down_payment_to_seller: float = 0,
    property_value: float | None = None,
    appreciation_rate: float = 3.0,
    rent_growth_rate: float = 2.0,
) -> dict:
    """Analyze a subject-to (existing financing) acquisition.

    appreciation_rate: annual property appreciation as a percentage (default 3%).
    rent_growth_rate: annual rent increase as a percentage (default 2%).
    """

    validate_positive(purchase_price, "purchase_price")
    validate_positive(existing_loan_balance, "existing_loan_balance")
    validate_positive(existing_loan_remaining_years, "existing_loan_remaining_years")
    validate_positive(monthly_rent, "monthly_rent")

    # Compute existing monthly payment from loan parameters
    existing_monthly_payment = calculate_mortgage_payment(
        existing_loan_balance,
        existing_interest_rate / 100 / 12,
        int(existing_loan_remaining_years * 12),
    )

    market_value = property_value if property_value is not None else purchase_price

    # --- Equity analysis ---
    seller_equity = market_value - existing_loan_balance
    instant_equity = market_value - purchase_price
    buyer_equity_at_purchase = market_value - existing_loan_balance - down_payment_to_seller

    # --- Cash flow ---
    total_monthly_outflow = existing_monthly_payment + monthly_expenses
    monthly_cash_flow = monthly_rent - total_monthly_outflow
    annual_cash_flow = monthly_cash_flow * 12

    # --- Cash needed ---
    estimated_closing_costs = purchase_price * 0.02  # estimate 2 %
    total_cash_needed = down_payment_to_seller + estimated_closing_costs
    cash_on_cash = (annual_cash_flow / total_cash_needed * 100) if total_cash_needed > 0 else 0

    # --- Compare to traditional purchase ---
    trad_down_payment = market_value * 0.20
    trad_loan = market_value * 0.80
    trad_rate = 7.0  # current market assumption
    trad_monthly_rate = trad_rate / 100 / 12
    trad_num_payments = 30 * 12
    trad_mortgage = calculate_mortgage_payment(trad_loan, trad_monthly_rate, trad_num_payments)
    trad_monthly_outflow = trad_mortgage + monthly_expenses
    trad_monthly_cash_flow = monthly_rent - trad_monthly_outflow
    trad_annual_cash_flow = trad_monthly_cash_flow * 12
    trad_cash_needed = trad_down_payment + estimated_closing_costs
    trad_coc = (trad_annual_cash_flow / trad_cash_needed * 100) if trad_cash_needed > 0 else 0

    # --- 5-year projection ---
    projection = _subject_to_projection(
        existing_loan_balance,
        existing_interest_rate,
        existing_monthly_payment,
        monthly_rent,
        monthly_expenses,
        market_value,
        years=5,
        appreciation_rate=appreciation_rate / 100,
        rent_growth_rate=rent_growth_rate / 100,
    )

    # --- Investment returns ---
    # IRR: initial outlay, then monthly cash flows, then sale in year 5
    appreciation_rate_dec = appreciation_rate / 100
    future_value_5yr = market_value * (1 + appreciation_rate_dec) ** 5
    remaining_balance_5yr = projection[-1]["remaining_loan_balance"]
    sale_proceeds_5yr = future_value_5yr - remaining_balance_5yr - future_value_5yr * 0.06  # 6 % selling costs
    irr_cash_flows = [-total_cash_needed]
    for year_data in projection:
        irr_cash_flows.append(year_data["annual_cash_flow"])
    irr_cash_flows[-1] += sale_proceeds_5yr  # add sale proceeds to final year
    annual_irr, _ = safe_irr_pct(irr_cash_flows)

    # --- Risk assessment ---
    risk_assessment = _subject_to_risk_assessment(
        existing_loan_balance, market_value, existing_interest_rate,
        monthly_cash_flow, seller_equity, existing_loan_remaining_years,
    )

    # --- Recommendations ---
    recommendations = _subject_to_recommendations(
        cash_on_cash, trad_coc, monthly_cash_flow, trad_monthly_cash_flow,
        total_cash_needed, trad_cash_needed, seller_equity, market_value,
    )

    return {
        "deal_structure": {
            "purchase_price": round2(purchase_price),
            "market_value": round2(market_value),
            "existing_loan_balance": round2(existing_loan_balance),
            "existing_interest_rate": existing_interest_rate,
            "existing_monthly_payment": round2(existing_monthly_payment),
            "remaining_loan_term_years": existing_loan_remaining_years,
            "down_payment_to_seller": round2(down_payment_to_seller),
            "estimated_closing_costs": round2(estimated_closing_costs),
            "total_cash_needed": round2(total_cash_needed),
        },
        "equity_analysis": {
            "market_value": round2(market_value),
            "existing_loan_balance": round2(existing_loan_balance),
            "seller_equity": round2(seller_equity),
            "instant_equity": round2(instant_equity),
            "equity_captured_at_purchase": round2(buyer_equity_at_purchase),
            "loan_to_value_percent": round2(existing_loan_balance / market_value * 100) if market_value > 0 else 0,
        },
        "cash_flow_analysis": {
            "monthly_rent": round2(monthly_rent),
            "existing_mortgage_payment": round2(existing_monthly_payment),
            "monthly_expenses": round2(monthly_expenses),
            "total_monthly_outflow": round2(total_monthly_outflow),
            "monthly_cash_flow": round2(monthly_cash_flow),
            "annual_cash_flow": round2(annual_cash_flow),
        },
        "investment_returns": {
            "cash_on_cash_return": round2(cash_on_cash),
            "annual_irr_5yr": round2(annual_irr),
            "total_cash_invested": round2(total_cash_needed),
            "estimated_5yr_value": round2(future_value_5yr),
            "estimated_5yr_equity": round2(future_value_5yr - remaining_balance_5yr),
        },
        "risk_assessment": risk_assessment,
        "comparison_to_traditional": {
            "subject_to": {
                "cash_needed": round2(total_cash_needed),
                "monthly_payment": round2(existing_monthly_payment),
                "monthly_cash_flow": round2(monthly_cash_flow),
                "annual_cash_flow": round2(annual_cash_flow),
                "cash_on_cash_return": round2(cash_on_cash),
                "interest_rate": existing_interest_rate,
            },
            "traditional_purchase": {
                "cash_needed": round2(trad_cash_needed),
                "monthly_payment": round2(trad_mortgage),
                "monthly_cash_flow": round2(trad_monthly_cash_flow),
                "annual_cash_flow": round2(trad_annual_cash_flow),
                "cash_on_cash_return": round2(trad_coc),
                "interest_rate": trad_rate,
            },
            "subject_to_advantage": {
                "cash_savings": round2(trad_cash_needed - total_cash_needed),
                "monthly_cash_flow_difference": round2(monthly_cash_flow - trad_monthly_cash_flow),
                "rate_advantage": round2(trad_rate - existing_interest_rate),
            },
        },
        "5_year_projection": projection,
        "recommendations": recommendations,
    }


def _subject_to_projection(
    loan_balance: float,
    interest_rate: float,
    monthly_payment: float,
    monthly_rent: float,
    monthly_expenses: float,
    market_value: float,
    years: int = 5,
    appreciation_rate: float = 0.03,
    rent_growth_rate: float = 0.02,
) -> list[dict]:
    """Project year-by-year financials for a subject-to deal."""
    projection: list[dict] = []
    balance = loan_balance
    current_rent = monthly_rent
    current_value = market_value

    for year in range(1, years + 1):
        # Calculate principal paid down this year
        year_start_balance = balance
        for _ in range(12):
            interest = balance * (interest_rate / 100 / 12)
            principal = monthly_payment - interest
            if principal > 0:
                balance = max(balance - principal, 0)

        principal_paid = year_start_balance - balance
        current_value *= (1 + appreciation_rate)
        annual_rent = current_rent * 12
        annual_expenses = monthly_expenses * 12
        annual_mortgage = monthly_payment * 12
        annual_cf = annual_rent - annual_mortgage - annual_expenses

        projection.append({
            "year": year,
            "property_value": round2(current_value),
            "remaining_loan_balance": round2(balance),
            "equity": round2(current_value - balance),
            "monthly_rent": round2(current_rent),
            "annual_cash_flow": round2(annual_cf),
            "principal_paid_down": round2(principal_paid),
            "cumulative_equity_gain": round2(current_value - balance - (market_value - loan_balance)),
        })

        # Rent grows each year
        current_rent *= (1 + rent_growth_rate)

    return projection


def _subject_to_risk_assessment(
    loan_balance: float,
    market_value: float,
    interest_rate: float,
    monthly_cash_flow: float,
    seller_equity: float,
    remaining_years: float,
) -> dict:
    ltv = (loan_balance / market_value * 100) if market_value > 0 else 0

    # Due-on-sale risk level
    if ltv > 90:
        dos_risk = "Low — lender unlikely to call a high-LTV performing loan"
    elif ltv > 70:
        dos_risk = "Moderate — monitor loan status and maintain payments"
    else:
        dos_risk = "Elevated — significant equity may attract lender attention"

    return {
        "due_on_sale_clause": {
            "risk_level": dos_risk,
            "description": (
                "The existing lender has the right to call the loan due upon transfer of ownership. "
                "While rarely enforced on performing loans, it is a real risk."
            ),
            "mitigation": [
                "Keep all loan payments current — never be late.",
                "Maintain property insurance with lender as loss payee.",
                "Consider using a land trust for title transfer.",
                "Have refinance or cash reserves as a backup plan.",
            ],
        },
        "insurance_considerations": {
            "description": (
                "Property insurance must remain active with the existing lender listed. "
                "Work with an insurance agent experienced in subject-to transactions."
            ),
        },
        "loan_to_value": round2(ltv),
        "cash_flow_risk": (
            "Positive" if monthly_cash_flow > 0
            else "Negative — deal loses money monthly"
        ),
        "seller_cooperation_risk": (
            "Seller retains liability on the loan. Ensure clear contractual "
            "agreements and consider an authorization to release information."
        ),
        "interest_rate_risk": (
            f"Locked at {interest_rate}% for remaining {remaining_years:.0f} years. "
            "No rate risk — this is a key advantage of subject-to."
        ),
    }


def _subject_to_recommendations(
    coc: float,
    trad_coc: float,
    monthly_cf: float,
    trad_monthly_cf: float,
    total_cash: float,
    trad_cash: float,
    seller_equity: float,
    market_value: float,
) -> list[str]:
    recs: list[str] = []

    if coc > trad_coc:
        recs.append(
            f"Subject-to yields {coc:.1f}% cash-on-cash vs {trad_coc:.1f}% traditional. "
            "The lower cash requirement makes this attractive."
        )
    else:
        recs.append(
            "Traditional financing produces comparable or better returns. "
            "Subject-to advantage is primarily the lower cash requirement."
        )

    cash_savings = trad_cash - total_cash
    if cash_savings > 0:
        recs.append(
            f"Subject-to saves ${cash_savings:,.2f} in upfront cash vs traditional purchase."
        )

    equity_pct = (seller_equity / market_value * 100) if market_value > 0 else 0
    if equity_pct > 30:
        recs.append(
            f"Seller has {equity_pct:.0f}% equity. Negotiate seller financing for the equity "
            "portion rather than large cash down payment."
        )

    if monthly_cf < 200:
        recs.append(
            "Monthly cash flow is thin. Build reserves for vacancies and maintenance."
        )
    elif monthly_cf > 500:
        recs.append("Strong monthly cash flow provides good margin of safety.")

    recs.append(
        "Consult a real estate attorney experienced in subject-to transactions. "
        "Ensure proper title transfer, insurance, and loan servicing arrangements."
    )
    recs.append(
        "Always have an exit strategy: refinance timeline, cash reserves for "
        "due-on-sale scenario, or ability to sell quickly."
    )
    return recs
