"""Advanced real-estate calculators: rent-vs-buy, capital gains tax, joint ventures, market comps."""

from __future__ import annotations

import math
import statistics
from typing import Any

from ._common import calculate_mortgage_payment, calculate_irr, round2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _remaining_balance(
    principal: float, monthly_rate: float, num_payments: int, payments_made: int
) -> float:
    """Return the remaining loan balance after *payments_made* payments."""
    if monthly_rate == 0:
        return principal - (principal / num_payments) * payments_made
    return principal * (
        (1 + monthly_rate) ** num_payments - (1 + monthly_rate) ** payments_made
    ) / ((1 + monthly_rate) ** num_payments - 1)


def _interest_paid_in_year(
    principal: float, monthly_rate: float, num_payments: int, year: int
) -> float:
    """Return total interest paid during *year* (1-indexed)."""
    monthly_payment = calculate_mortgage_payment(principal, monthly_rate, num_payments)
    total_interest = 0.0
    balance = _remaining_balance(principal, monthly_rate, num_payments, (year - 1) * 12)
    for _ in range(12):
        interest = balance * monthly_rate
        total_interest += interest
        principal_paid = monthly_payment - interest
        balance -= principal_paid
    return total_interest


def _principal_paid_in_year(
    principal: float, monthly_rate: float, num_payments: int, year: int
) -> float:
    """Return total principal paid during *year* (1-indexed)."""
    monthly_payment = calculate_mortgage_payment(principal, monthly_rate, num_payments)
    return monthly_payment * 12 - _interest_paid_in_year(
        principal, monthly_rate, num_payments, year
    )


_STATE_CG_RATES: dict[str, float] = {
    "CA": 13.3, "NY": 10.9, "NJ": 10.75, "OR": 9.9, "MN": 9.85,
    "HI": 11.0, "VT": 8.75, "IA": 8.53, "WI": 7.65, "SC": 7.0,
    "ME": 7.15, "CT": 6.99, "ID": 6.0, "MT": 6.75, "NE": 6.84,
    "DE": 6.6, "WV": 6.5, "GA": 5.75, "VA": 5.75, "MA": 5.0,
    "NC": 5.25, "RI": 5.99, "KS": 5.7, "IL": 4.95, "MI": 4.25,
    "OH": 3.99, "PA": 3.07, "IN": 3.23, "ND": 2.9, "AZ": 2.5,
    "CO": 4.4, "NM": 5.9, "AL": 5.0, "MS": 5.0, "LA": 4.25,
    "AR": 4.9, "MO": 5.3, "OK": 4.75, "KY": 4.5, "UT": 4.85,
    "TX": 0.0, "FL": 0.0, "NV": 0.0, "WA": 7.0, "TN": 0.0,
    "WY": 0.0, "SD": 0.0, "AK": 0.0, "NH": 0.0,
}


def _federal_ltcg_rate(taxable_income: float, filing_status: str) -> float:
    """Return the federal long-term capital gains rate (0, 15, or 20 %)."""
    if filing_status == "married":
        if taxable_income <= 89_250:
            return 0.0
        elif taxable_income <= 553_850:
            return 15.0
        else:
            return 20.0
    else:  # single
        if taxable_income <= 44_625:
            return 0.0
        elif taxable_income <= 492_300:
            return 15.0
        else:
            return 20.0


def _niit_threshold(filing_status: str) -> float:
    """Net Investment Income Tax threshold."""
    return 250_000 if filing_status == "married" else 200_000


# ---------------------------------------------------------------------------
# 1. analyze_rent_vs_buy
# ---------------------------------------------------------------------------

def analyze_rent_vs_buy(
    monthly_rent: float,
    annual_rent_increase: float = 3.0,
    home_price: float = 0.0,
    down_payment_percent: float = 20.0,
    interest_rate: float = 7.0,
    loan_term_years: int = 30,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    maintenance_percent: float = 1.0,
    hoa_monthly: float = 0.0,
    annual_appreciation: float = 3.0,
    marginal_tax_rate: float = 22.0,
    investment_return_rate: float = 7.0,
    analysis_period_years: int = 10,
    closing_costs_percent: float = 3.0,
    selling_costs_percent: float = 6.0,
) -> dict[str, Any]:
    """Compare the financial outcome of renting versus buying over *analysis_period_years*."""

    # ---- Derived constants ------------------------------------------------
    down_payment = home_price * (down_payment_percent / 100)
    closing_costs = home_price * (closing_costs_percent / 100)
    loan_amount = home_price - down_payment
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    monthly_mortgage = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)

    renter_insurance_monthly = monthly_rent * 0.02  # ~2 % of rent

    # ---- Year-by-year analysis -------------------------------------------
    annual_comparison: list[dict[str, Any]] = []
    cumulative_rent_cost = 0.0
    cumulative_buy_cost = 0.0
    cumulative_tax_benefit = 0.0

    # Renter invests down payment + closing costs in stocks
    renter_investment = down_payment + closing_costs

    crossover_year: int | None = None

    for yr in range(1, analysis_period_years + 1):
        # -- Renting -------------------------------------------------------
        current_rent = monthly_rent * (1 + annual_rent_increase / 100) ** (yr - 1)
        annual_rent = current_rent * 12
        annual_renter_insurance = renter_insurance_monthly * 12 * (
            (1 + annual_rent_increase / 100) ** (yr - 1)
        )
        total_rent_cost = annual_rent + annual_renter_insurance

        # Renter investment grows
        renter_investment *= 1 + investment_return_rate / 100
        # Renter also invests monthly savings (buy cost - rent cost of prior year)
        # We track savings separately below after computing buy cost.

        # -- Buying --------------------------------------------------------
        annual_mortgage = monthly_mortgage * 12
        current_home_value = home_price * (1 + annual_appreciation / 100) ** yr
        annual_property_tax = current_home_value * (property_tax_rate / 100)
        annual_insurance = current_home_value * (insurance_rate / 100)
        annual_maintenance = current_home_value * (maintenance_percent / 100)
        annual_hoa = hoa_monthly * 12

        interest_this_year = _interest_paid_in_year(
            loan_amount, monthly_rate, num_payments, yr
        )
        principal_this_year = _principal_paid_in_year(
            loan_amount, monthly_rate, num_payments, yr
        )

        # Tax deduction for mortgage interest + property tax (simplified)
        tax_deduction = (interest_this_year + annual_property_tax) * (
            marginal_tax_rate / 100
        )

        total_buy_cost = (
            annual_mortgage
            + annual_property_tax
            + annual_insurance
            + annual_maintenance
            + annual_hoa
            - tax_deduction
        )

        cumulative_rent_cost += total_rent_cost
        cumulative_buy_cost += total_buy_cost
        cumulative_tax_benefit += tax_deduction

        # -- Equity --------------------------------------------------------
        remaining_balance = _remaining_balance(
            loan_amount, monthly_rate, num_payments, yr * 12
        )
        equity = current_home_value - remaining_balance
        selling_costs_amt = current_home_value * (selling_costs_percent / 100)
        net_equity = equity - selling_costs_amt

        # -- Net wealth comparison -----------------------------------------
        # Buyer net wealth = net equity (after selling costs)
        buyer_net_wealth = net_equity
        # Renter net wealth = investment portfolio
        renter_net_wealth = renter_investment

        if crossover_year is None and buyer_net_wealth >= renter_net_wealth:
            crossover_year = yr

        annual_comparison.append({
            "year": yr,
            "renting": {
                "monthly_rent": round2(current_rent),
                "annual_rent": round2(annual_rent),
                "renter_insurance": round2(annual_renter_insurance),
                "total_cost": round2(total_rent_cost),
            },
            "buying": {
                "mortgage_payment": round2(annual_mortgage),
                "property_tax": round2(annual_property_tax),
                "insurance": round2(annual_insurance),
                "maintenance": round2(annual_maintenance),
                "hoa": round2(annual_hoa),
                "tax_deduction": round2(tax_deduction),
                "total_cost": round2(total_buy_cost),
                "home_value": round2(current_home_value),
                "remaining_balance": round2(remaining_balance),
                "equity": round2(equity),
                "principal_paid": round2(principal_this_year),
                "interest_paid": round2(interest_this_year),
            },
        })

    # ---- Cumulative comparison -------------------------------------------
    cumulative_comparison = {
        "total_rent_cost": round2(cumulative_rent_cost),
        "total_buy_cost": round2(cumulative_buy_cost),
        "buy_minus_rent": round2(cumulative_buy_cost - cumulative_rent_cost),
    }

    # ---- Net wealth analysis ---------------------------------------------
    final_home_value = home_price * (1 + annual_appreciation / 100) ** analysis_period_years
    final_remaining = _remaining_balance(
        loan_amount, monthly_rate, num_payments, analysis_period_years * 12
    )
    final_equity = final_home_value - final_remaining
    final_selling_costs = final_home_value * (selling_costs_percent / 100)
    buyer_final_wealth = final_equity - final_selling_costs

    net_wealth_analysis = {
        "buyer_net_wealth": round2(buyer_final_wealth),
        "renter_net_wealth": round2(renter_investment),
        "wealth_difference": round2(buyer_final_wealth - renter_investment),
        "buying_is_better": buyer_final_wealth > renter_investment,
    }

    # ---- Crossover analysis ----------------------------------------------
    crossover_analysis = {
        "break_even_year": crossover_year,
        "break_even_found": crossover_year is not None,
        "message": (
            f"Buying becomes financially better than renting in year {crossover_year}."
            if crossover_year
            else "Buying does not surpass renting within the analysis period."
        ),
    }

    # ---- Tax benefit analysis --------------------------------------------
    tax_benefit_analysis = {
        "total_tax_benefit": round2(cumulative_tax_benefit),
        "average_annual_benefit": round2(cumulative_tax_benefit / analysis_period_years),
        "marginal_tax_rate_used": marginal_tax_rate,
    }

    # ---- Total cost summary ----------------------------------------------
    total_initial_buy = down_payment + closing_costs
    total_cost_summary = {
        "renting": {
            "total_payments": round2(cumulative_rent_cost),
            "opportunity_cost_of_not_buying": round2(
                max(0, buyer_final_wealth - renter_investment)
            ),
        },
        "buying": {
            "initial_outlay": round2(total_initial_buy),
            "total_payments": round2(cumulative_buy_cost),
            "final_equity": round2(final_equity),
            "selling_costs": round2(final_selling_costs),
            "net_proceeds": round2(buyer_final_wealth),
        },
    }

    # ---- Recommendations -------------------------------------------------
    recommendations: list[str] = []
    if buyer_final_wealth > renter_investment:
        recommendations.append(
            "Buying appears financially advantageous over the analysis period."
        )
    else:
        recommendations.append(
            "Renting and investing the difference appears financially advantageous."
        )
    if crossover_year and crossover_year > 5:
        recommendations.append(
            "The break-even point is beyond 5 years; ensure you plan to stay long enough."
        )
    if cumulative_tax_benefit > 0:
        recommendations.append(
            f"Mortgage interest and property tax deductions save ~${round2(cumulative_tax_benefit / analysis_period_years):,.0f}/yr."
        )
    if annual_appreciation < 2:
        recommendations.append(
            "Low appreciation assumption reduces the case for buying."
        )

    return {
        "annual_comparison": annual_comparison,
        "cumulative_comparison": cumulative_comparison,
        "net_wealth_analysis": net_wealth_analysis,
        "crossover_analysis": crossover_analysis,
        "tax_benefit_analysis": tax_benefit_analysis,
        "total_cost_summary": total_cost_summary,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 2. calculate_capital_gains_tax
# ---------------------------------------------------------------------------

def calculate_capital_gains_tax(
    sale_price: float,
    purchase_price: float,
    selling_costs_percent: float = 6.0,
    improvements_cost: float = 0.0,
    depreciation_taken: float = 0.0,
    holding_period_years: float = 1.0,
    is_primary_residence: bool = False,
    years_lived_in: float = 0.0,
    filing_status: str = "single",
    other_income: float = 0.0,
    state: str = "CA",
    installment_sale: bool = False,
    installment_years: int = 5,
) -> dict[str, Any]:
    """Calculate capital gains tax liability for a property sale."""

    selling_costs = sale_price * (selling_costs_percent / 100)
    adjusted_basis = purchase_price + improvements_cost - depreciation_taken
    net_sale_price = sale_price - selling_costs
    total_gain = net_sale_price - adjusted_basis

    is_long_term = holding_period_years >= 1.0

    # ---- Primary residence exclusion -------------------------------------
    exclusion_amount = 0.0
    exclusion_eligible = False
    if is_primary_residence and years_lived_in >= 2.0:
        exclusion_eligible = True
        max_exclusion = 500_000 if filing_status == "married" else 250_000
        exclusion_amount = min(max(total_gain, 0), max_exclusion)

    taxable_gain = max(total_gain - exclusion_amount, 0)

    # Separate depreciation recapture from remaining gain
    depreciation_recapture_gain = min(depreciation_taken, taxable_gain)
    remaining_gain = taxable_gain - depreciation_recapture_gain

    # ---- Federal tax -----------------------------------------------------
    taxable_income = other_income + remaining_gain
    if is_long_term:
        federal_rate = _federal_ltcg_rate(taxable_income, filing_status)
    else:
        # Short-term gains taxed as ordinary income – approximate top bracket
        federal_rate = 37.0 if taxable_income > 578_125 else (
            35.0 if taxable_income > 231_250 else (
            32.0 if taxable_income > 182_100 else (
            24.0 if taxable_income > 95_375 else (
            22.0 if taxable_income > 44_725 else (
            12.0 if taxable_income > 11_000 else 10.0)))))

    federal_tax = remaining_gain * (federal_rate / 100)

    # Depreciation recapture at 25 %
    depreciation_recapture_tax = depreciation_recapture_gain * 0.25

    # ---- Net Investment Income Tax (3.8 %) -------------------------------
    agi = other_income + taxable_gain
    niit_threshold = _niit_threshold(filing_status)
    niit = 0.0
    if agi > niit_threshold:
        niit_base = min(taxable_gain, agi - niit_threshold)
        niit = niit_base * 0.038

    # ---- State tax -------------------------------------------------------
    state_rate = _STATE_CG_RATES.get(state.upper(), 5.0)
    state_tax = taxable_gain * (state_rate / 100)

    total_tax = federal_tax + depreciation_recapture_tax + niit + state_tax

    # ---- Installment sale analysis ---------------------------------------
    installment_sale_analysis: dict[str, Any] | None = None
    if installment_sale and installment_years > 0:
        annual_gain = taxable_gain / installment_years
        annual_depr_recap = depreciation_recapture_gain / installment_years
        annual_remaining = annual_gain - annual_depr_recap

        installment_schedule: list[dict[str, Any]] = []
        total_installment_tax = 0.0
        for yr in range(1, installment_years + 1):
            yr_income = other_income + annual_remaining
            if is_long_term:
                yr_fed_rate = _federal_ltcg_rate(yr_income, filing_status)
            else:
                yr_fed_rate = federal_rate  # simplified
            yr_fed_tax = annual_remaining * (yr_fed_rate / 100)
            yr_recap_tax = annual_depr_recap * 0.25
            yr_state_tax = annual_gain * (state_rate / 100)
            yr_agi = other_income + annual_gain
            yr_niit = 0.0
            if yr_agi > niit_threshold:
                yr_niit_base = min(annual_gain, yr_agi - niit_threshold)
                yr_niit = yr_niit_base * 0.038
            yr_total = yr_fed_tax + yr_recap_tax + yr_state_tax + yr_niit
            total_installment_tax += yr_total
            installment_schedule.append({
                "year": yr,
                "recognized_gain": round2(annual_gain),
                "federal_tax": round2(yr_fed_tax),
                "depreciation_recapture_tax": round2(yr_recap_tax),
                "state_tax": round2(yr_state_tax),
                "niit": round2(yr_niit),
                "total_tax": round2(yr_total),
            })

        installment_sale_analysis = {
            "installment_years": installment_years,
            "annual_recognized_gain": round2(annual_gain),
            "total_tax_installment": round2(total_installment_tax),
            "total_tax_lump_sum": round2(total_tax),
            "tax_savings": round2(total_tax - total_installment_tax),
            "schedule": installment_schedule,
        }

    # ---- Effective tax rate ----------------------------------------------
    effective_rate = (total_tax / total_gain * 100) if total_gain > 0 else 0.0

    # ---- Optimization strategies -----------------------------------------
    optimization_strategies: list[str] = []
    if not is_long_term and holding_period_years > 0.5:
        optimization_strategies.append(
            "Consider holding longer than 1 year to qualify for long-term capital gains rates."
        )
    if is_primary_residence and not exclusion_eligible and years_lived_in < 2:
        optimization_strategies.append(
            "Living in the property for at least 2 of the last 5 years enables the primary residence exclusion."
        )
    if depreciation_taken > 0:
        optimization_strategies.append(
            "Consider a 1031 exchange to defer both capital gains and depreciation recapture taxes."
        )
    if not installment_sale and taxable_gain > 200_000:
        optimization_strategies.append(
            "An installment sale could spread the gain over multiple years, potentially lowering the effective rate."
        )
    if state_rate > 5:
        optimization_strategies.append(
            f"{state} has a high state CG rate ({state_rate}%). Explore opportunity-zone reinvestment or charitable remainder trusts."
        )

    # ---- Net proceeds ----------------------------------------------------
    net_proceeds = net_sale_price - total_tax

    # ---- Recommendations -------------------------------------------------
    recommendations: list[str] = []
    if effective_rate > 30:
        recommendations.append(
            "Your effective tax rate is high. Explore 1031 exchanges or installment sales."
        )
    if exclusion_eligible:
        recommendations.append(
            f"Primary residence exclusion saves ${round2(exclusion_amount):,.0f} in taxable gain."
        )
    if installment_sale_analysis and installment_sale_analysis["tax_savings"] > 0:
        recommendations.append(
            f"Installment sale saves ~${round2(installment_sale_analysis['tax_savings']):,.0f} vs lump-sum recognition."
        )
    if not recommendations:
        recommendations.append("Review with a CPA for entity-level strategies and timing optimization.")

    return {
        "gain_calculation": {
            "sale_price": round2(sale_price),
            "selling_costs": round2(selling_costs),
            "net_sale_price": round2(net_sale_price),
            "purchase_price": round2(purchase_price),
            "improvements_cost": round2(improvements_cost),
            "depreciation_taken": round2(depreciation_taken),
            "adjusted_basis": round2(adjusted_basis),
            "total_gain": round2(total_gain),
            "exclusion_amount": round2(exclusion_amount),
            "taxable_gain": round2(taxable_gain),
            "is_long_term": is_long_term,
        },
        "tax_liability": {
            "federal": round2(federal_tax),
            "federal_rate": round2(federal_rate),
            "state": round2(state_tax),
            "state_rate": round2(state_rate),
            "niit": round2(niit),
            "depreciation_recapture": round2(depreciation_recapture_tax),
            "total": round2(total_tax),
        },
        "primary_residence_exclusion": {
            "eligible": exclusion_eligible,
            "exclusion_amount": round2(exclusion_amount),
            "years_lived_in": years_lived_in,
            "requirement": "Must live in property 2 of last 5 years",
        },
        "installment_sale_analysis": installment_sale_analysis,
        "effective_tax_rate": round2(effective_rate),
        "optimization_strategies": optimization_strategies,
        "net_proceeds": round2(net_proceeds),
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 3. analyze_joint_venture
# ---------------------------------------------------------------------------

def analyze_joint_venture(
    total_project_cost: float,
    projected_profit: float,
    project_duration_months: int,
    partners: list[dict[str, Any]],
    profit_split_method: str = "pro_rata",
    preferred_return_rate: float = 8.0,
    waterfall_tiers: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Analyze a real-estate joint venture among multiple partners."""

    # ---- Capital structure ------------------------------------------------
    total_capital = sum(p.get("capital_contribution", 0) for p in partners)
    if total_capital == 0:
        total_capital = total_project_cost  # avoid division by zero

    partner_details: list[dict[str, Any]] = []
    for p in partners:
        contribution = p.get("capital_contribution", 0)
        ownership_pct = (contribution / total_capital) * 100 if total_capital else 0
        partner_details.append({
            "name": p.get("name", "Unknown"),
            "capital_contribution": round2(contribution),
            "ownership_percent": round2(ownership_pct),
            "role": p.get("role", "capital"),
            "responsibilities": p.get("responsibilities", []),
        })

    capital_structure = {
        "total_project_cost": round2(total_project_cost),
        "total_capital_raised": round2(total_capital),
        "funding_gap": round2(max(total_project_cost - total_capital, 0)),
        "partners": partner_details,
    }

    # ---- Profit distribution ---------------------------------------------
    distributable = projected_profit

    partner_distributions: list[dict[str, Any]] = []

    if profit_split_method == "pro_rata":
        for pd in partner_details:
            share = distributable * (pd["ownership_percent"] / 100)
            partner_distributions.append({
                "name": pd["name"],
                "distribution": round2(share),
                "method": "pro_rata",
            })

    elif profit_split_method == "preferred_return":
        # First: preferred return on capital
        preferred_pool = 0.0
        pref_distributions: dict[str, float] = {}
        duration_years = project_duration_months / 12
        for pd in partner_details:
            pref = pd["capital_contribution"] * (preferred_return_rate / 100) * duration_years
            pref_distributions[pd["name"]] = pref
            preferred_pool += pref

        remaining_after_pref = max(distributable - preferred_pool, 0)
        # If not enough profit for full preferred return, prorate
        if distributable < preferred_pool and preferred_pool > 0:
            scale = distributable / preferred_pool
            for name in pref_distributions:
                pref_distributions[name] *= scale
            remaining_after_pref = 0

        for pd in partner_details:
            pref_share = pref_distributions[pd["name"]]
            residual_share = remaining_after_pref * (pd["ownership_percent"] / 100)
            total_share = pref_share + residual_share
            partner_distributions.append({
                "name": pd["name"],
                "preferred_return": round2(pref_share),
                "residual_share": round2(residual_share),
                "distribution": round2(total_share),
                "method": "preferred_return",
            })

    elif profit_split_method == "waterfall":
        tiers = waterfall_tiers or [
            {"threshold_percent": preferred_return_rate, "lp_share": 100, "gp_share": 0},
            {"threshold_percent": 100, "lp_share": 70, "gp_share": 30},
        ]

        # Identify GP vs LP partners
        gp_names = [p.get("name", "") for p in partners if p.get("role") in ("operating", "both")]
        lp_names = [p.get("name", "") for p in partners if p.get("role") == "capital"]
        if not gp_names:
            gp_names = [partners[0].get("name", "")]
        if not lp_names:
            lp_names = [p.get("name", "") for p in partners if p.get("name", "") not in gp_names]

        lp_capital = sum(
            pd["capital_contribution"] for pd in partner_details if pd["name"] in lp_names
        )
        gp_capital = sum(
            pd["capital_contribution"] for pd in partner_details if pd["name"] in gp_names
        )

        remaining = distributable
        tier_results: list[dict[str, Any]] = []
        lp_total = 0.0
        gp_total = 0.0
        duration_years = project_duration_months / 12

        for i, tier in enumerate(tiers):
            if remaining <= 0:
                break
            threshold_pct = tier.get("threshold_percent", 100)
            lp_pct = tier.get("lp_share", 70)
            gp_pct = tier.get("gp_share", 30)

            if i == 0:
                # First tier: preferred return hurdle
                hurdle = total_capital * (threshold_pct / 100) * duration_years
            else:
                hurdle = remaining  # consume the rest

            tier_amount = min(remaining, hurdle)
            lp_amount = tier_amount * (lp_pct / 100)
            gp_amount = tier_amount * (gp_pct / 100)
            lp_total += lp_amount
            gp_total += gp_amount
            remaining -= tier_amount

            tier_results.append({
                "tier": i + 1,
                "threshold_percent": threshold_pct,
                "amount_distributed": round2(tier_amount),
                "lp_share_percent": lp_pct,
                "gp_share_percent": gp_pct,
                "lp_amount": round2(lp_amount),
                "gp_amount": round2(gp_amount),
            })

        # Distribute among individual LPs/GPs proportionally
        for pd in partner_details:
            if pd["name"] in lp_names:
                share_of_pool = (
                    pd["capital_contribution"] / lp_capital if lp_capital else 0
                )
                dist = lp_total * share_of_pool
            else:
                share_of_pool = (
                    pd["capital_contribution"] / gp_capital if gp_capital else 1 / len(gp_names)
                )
                dist = gp_total * share_of_pool
            partner_distributions.append({
                "name": pd["name"],
                "distribution": round2(dist),
                "method": "waterfall",
            })

        capital_structure["waterfall_tiers"] = tier_results
    else:
        # Fallback to pro-rata
        for pd in partner_details:
            share = distributable * (pd["ownership_percent"] / 100)
            partner_distributions.append({
                "name": pd["name"],
                "distribution": round2(share),
                "method": "pro_rata",
            })

    # ---- Return analysis -------------------------------------------------
    duration_years = project_duration_months / 12
    return_analysis: list[dict[str, Any]] = []
    for pd, dist in zip(partner_details, partner_distributions):
        contribution = pd["capital_contribution"]
        distribution = dist["distribution"]
        roi = (distribution / contribution * 100) if contribution > 0 else 0
        equity_multiple = (
            (contribution + distribution) / contribution if contribution > 0 else 0
        )
        # IRR: initial outflow, then profit at end of period
        cash_flows = [-contribution] + [0.0] * max(int(duration_years) - 1, 0) + [contribution + distribution]
        irr = calculate_irr(cash_flows) * 100

        return_analysis.append({
            "name": pd["name"],
            "capital_contribution": round2(contribution),
            "total_distribution": round2(distribution),
            "roi_percent": round2(roi),
            "irr_percent": round2(irr),
            "equity_multiple": round2(equity_multiple),
        })

    # ---- Fairness analysis -----------------------------------------------
    fairness_analysis: list[dict[str, Any]] = []
    for pd, dist in zip(partner_details, partner_distributions):
        contribution_ratio = pd["ownership_percent"]
        profit_ratio = (
            (dist["distribution"] / projected_profit * 100) if projected_profit > 0 else 0
        )
        fairness_analysis.append({
            "name": pd["name"],
            "capital_contribution_percent": round2(contribution_ratio),
            "profit_share_percent": round2(profit_ratio),
            "difference": round2(profit_ratio - contribution_ratio),
            "assessment": (
                "Proportional"
                if abs(profit_ratio - contribution_ratio) < 2
                else (
                    "Favorable" if profit_ratio > contribution_ratio else "Unfavorable"
                )
            ),
        })

    # ---- Risk allocation -------------------------------------------------
    risk_allocation: list[dict[str, Any]] = []
    for p in partners:
        contribution = p.get("capital_contribution", 0)
        risk_pct = (contribution / total_capital * 100) if total_capital else 0
        role = p.get("role", "capital")
        risk_type = "Financial" if role == "capital" else (
            "Operational" if role == "operating" else "Financial + Operational"
        )
        risk_allocation.append({
            "name": p.get("name", "Unknown"),
            "capital_at_risk": round2(contribution),
            "risk_percent": round2(risk_pct),
            "risk_type": risk_type,
        })

    # ---- Legal considerations --------------------------------------------
    legal_considerations = [
        "Execute a formal Joint Venture or Operating Agreement before funding.",
        "Define decision-making authority, dispute resolution, and exit provisions.",
        "Consult a real-estate attorney regarding entity structure (LLC recommended).",
        "Address capital call procedures and default remedies.",
        "Include buy-sell (shotgun) clauses for partner exit scenarios.",
    ]

    # ---- Recommendations -------------------------------------------------
    recommendations: list[str] = []
    max_diff = max(abs(f["difference"]) for f in fairness_analysis) if fairness_analysis else 0
    if max_diff > 10:
        recommendations.append(
            "Large disparity between contribution and profit share — review split terms."
        )
    if profit_split_method == "pro_rata" and any(
        p.get("role") == "operating" for p in partners
    ):
        recommendations.append(
            "Consider preferred return or waterfall structure to compensate the operating partner."
        )
    if projected_profit / total_capital < 0.15 and total_capital > 0:
        recommendations.append(
            "Projected profit margin is thin relative to capital at risk; stress-test assumptions."
        )
    if not recommendations:
        recommendations.append(
            "Structure appears balanced. Proceed with legal documentation."
        )

    return {
        "partnership_summary": {
            "total_project_cost": round2(total_project_cost),
            "projected_profit": round2(projected_profit),
            "project_duration_months": project_duration_months,
            "number_of_partners": len(partners),
            "profit_split_method": profit_split_method,
        },
        "capital_structure": capital_structure,
        "profit_distribution": partner_distributions,
        "return_analysis": return_analysis,
        "fairness_analysis": fairness_analysis,
        "risk_allocation": risk_allocation,
        "legal_considerations": legal_considerations,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 4. analyze_market_comps
# ---------------------------------------------------------------------------

_CONDITION_SCORES: dict[str, int] = {
    "poor": 1, "fair": 2, "average": 3, "good": 4, "excellent": 5,
}


def analyze_market_comps(
    subject_property: dict[str, Any],
    comparable_properties: list[dict[str, Any]],
    adjustments: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Perform a Comparative Market Analysis (CMA) for the subject property."""

    adj = adjustments or {}
    price_per_sqft_adj = adj.get("price_per_sqft_adjustment", 25.0)
    bedroom_adj = adj.get("bedroom_adjustment", 10_000.0)
    bathroom_adj = adj.get("bathroom_adjustment", 8_000.0)
    condition_adj = adj.get("condition_adjustment", 15_000.0)
    age_adj_per_year = adj.get("age_adjustment_per_year", 1_000.0)

    subj_sqft = subject_property.get("square_feet", 0)
    subj_beds = subject_property.get("bedrooms", 0)
    subj_baths = subject_property.get("bathrooms", 0)
    subj_year = subject_property.get("year_built", 2000)
    subj_lot = subject_property.get("lot_size", 0)
    subj_condition = _CONDITION_SCORES.get(
        str(subject_property.get("condition", "average")).lower(), 3
    )

    comparable_analyses: list[dict[str, Any]] = []
    adjusted_prices: list[float] = []
    weights: list[float] = []

    for comp in comparable_properties:
        sale_price = comp.get("sale_price", 0)
        comp_sqft = comp.get("square_feet", subj_sqft)
        comp_beds = comp.get("bedrooms", subj_beds)
        comp_baths = comp.get("bathrooms", subj_baths)
        comp_year = comp.get("year_built", subj_year)
        comp_lot = comp.get("lot_size", subj_lot)
        comp_condition = _CONDITION_SCORES.get(
            str(comp.get("condition", "average")).lower(), 3
        )
        comp_distance = comp.get("distance_miles", 1.0)
        comp_sale_date = comp.get("sale_date", "")

        # ---- Calculate adjustments ---------------------------------------
        sqft_diff = subj_sqft - comp_sqft
        sqft_adjustment = sqft_diff * price_per_sqft_adj

        bed_diff = subj_beds - comp_beds
        bed_adjustment = bed_diff * bedroom_adj

        bath_diff = subj_baths - comp_baths
        bath_adjustment = bath_diff * bathroom_adj

        condition_diff = subj_condition - comp_condition
        cond_adjustment = condition_diff * condition_adj

        age_diff = comp_year - subj_year  # positive = comp is newer → subject worth less
        age_adjustment = -age_diff * age_adj_per_year

        lot_diff = subj_lot - comp_lot
        # Rough lot-size adjustment: $2 per sqft of lot difference
        lot_adj_rate = adj.get("lot_adjustment_per_sqft", 2.0)
        lot_adjustment = lot_diff * lot_adj_rate

        total_adjustment = (
            sqft_adjustment + bed_adjustment + bath_adjustment
            + cond_adjustment + age_adjustment + lot_adjustment
        )
        adjusted_price = sale_price + total_adjustment

        # ---- Weighting ---------------------------------------------------
        # More recent sales and closer proximity → higher weight
        # Recency weight (assume sale_date is "YYYY-MM-DD"; fallback weight 0.5)
        recency_weight = 1.0
        if comp_sale_date:
            try:
                parts = comp_sale_date.split("-")
                sale_year = int(parts[0])
                sale_month = int(parts[1]) if len(parts) > 1 else 6
                months_ago = (2026 - sale_year) * 12 + (3 - sale_month)  # approx from now
                recency_weight = max(1.0 - months_ago / 24, 0.2)  # decay over 24 months
            except (ValueError, IndexError):
                recency_weight = 0.5

        proximity_weight = max(1.0 - comp_distance / 5.0, 0.2)  # decay over 5 miles

        # Penalize large adjustments
        adjustment_magnitude = abs(total_adjustment) / max(sale_price, 1)
        adjustment_weight = max(1.0 - adjustment_magnitude, 0.3)

        weight = recency_weight * proximity_weight * adjustment_weight
        weights.append(weight)
        adjusted_prices.append(adjusted_price)

        comparable_analyses.append({
            "address": comp.get("address", "Unknown"),
            "sale_price": round2(sale_price),
            "sale_date": comp_sale_date,
            "distance_miles": comp_distance,
            "adjustments": {
                "square_feet": round2(sqft_adjustment),
                "bedrooms": round2(bed_adjustment),
                "bathrooms": round2(bath_adjustment),
                "condition": round2(cond_adjustment),
                "age": round2(age_adjustment),
                "lot_size": round2(lot_adjustment),
                "total": round2(total_adjustment),
            },
            "adjusted_price": round2(adjusted_price),
            "weight": round2(weight),
        })

    # ---- Valuation summary -----------------------------------------------
    if adjusted_prices:
        total_weight = sum(weights)
        if total_weight > 0:
            estimated_value = sum(
                p * w for p, w in zip(adjusted_prices, weights)
            ) / total_weight
        else:
            estimated_value = statistics.mean(adjusted_prices)

        sorted_prices = sorted(adjusted_prices)
        price_low = sorted_prices[0]
        price_high = sorted_prices[-1]
        price_mid = estimated_value
        mean_price = statistics.mean(adjusted_prices)
        median_price = statistics.median(adjusted_prices)
        std_dev = statistics.stdev(adjusted_prices) if len(adjusted_prices) > 1 else 0.0
    else:
        estimated_value = 0
        price_low = price_high = price_mid = mean_price = median_price = std_dev = 0

    # ---- Confidence score ------------------------------------------------
    # Based on: number of comps, adjustment magnitude, price spread
    num_comps = len(comparable_properties)
    comp_count_score = min(num_comps / 6, 1.0)  # max score at 6+ comps

    avg_adj_pct = (
        statistics.mean(
            abs(ca["adjustments"]["total"]) / max(ca["sale_price"], 1)
            for ca in comparable_analyses
        )
        if comparable_analyses
        else 1.0
    )
    adjustment_score = max(1.0 - avg_adj_pct * 2, 0.0)

    spread_score = (
        max(1.0 - (price_high - price_low) / max(estimated_value, 1), 0.0)
        if estimated_value
        else 0.0
    )

    confidence_score = round2(
        (comp_count_score * 0.35 + adjustment_score * 0.35 + spread_score * 0.30) * 100
    )
    confidence_score = min(max(confidence_score, 0), 100)

    confidence_label = (
        "High" if confidence_score >= 75 else ("Medium" if confidence_score >= 50 else "Low")
    )

    valuation_summary = {
        "estimated_value": round2(estimated_value),
        "price_range": {
            "low": round2(price_low),
            "mid": round2(price_mid),
            "high": round2(price_high),
        },
        "confidence_score": confidence_score,
        "confidence_label": confidence_label,
    }

    # ---- Adjustment summary ----------------------------------------------
    adjustment_summary = {
        "price_per_sqft_adjustment": price_per_sqft_adj,
        "bedroom_adjustment": bedroom_adj,
        "bathroom_adjustment": bathroom_adj,
        "condition_adjustment": condition_adj,
        "age_adjustment_per_year": age_adj_per_year,
    }

    # ---- Statistical analysis --------------------------------------------
    statistical_analysis = {
        "mean_adjusted_price": round2(mean_price),
        "median_adjusted_price": round2(median_price),
        "std_deviation": round2(std_dev),
        "price_per_sqft": round2(estimated_value / subj_sqft) if subj_sqft > 0 else 0,
        "number_of_comps": num_comps,
    }

    # ---- CMA report ------------------------------------------------------
    cma_report = {
        "subject": subject_property,
        "analysis_date": "2026-03-18",
        "estimated_market_value": round2(estimated_value),
        "value_range": f"${round2(price_low):,.0f} – ${round2(price_high):,.0f}",
        "confidence": confidence_label,
        "comps_used": num_comps,
    }

    # ---- Recommendations -------------------------------------------------
    recommendations: list[str] = []
    if num_comps < 3:
        recommendations.append(
            "Fewer than 3 comps; consider expanding search radius or criteria."
        )
    if confidence_score < 50:
        recommendations.append(
            "Low confidence — large adjustments or wide price spread. Obtain a professional appraisal."
        )
    if std_dev > estimated_value * 0.15 and estimated_value > 0:
        recommendations.append(
            "High variance among comps suggests heterogeneous market; weight closest comps more."
        )
    if not recommendations:
        recommendations.append(
            "Analysis shows reasonable confidence. Use as starting point for pricing decisions."
        )

    return {
        "subject_property": subject_property,
        "comparable_analyses": comparable_analyses,
        "valuation_summary": valuation_summary,
        "adjustment_summary": adjustment_summary,
        "statistical_analysis": statistical_analysis,
        "cma_report": cma_report,
        "recommendations": recommendations,
    }
