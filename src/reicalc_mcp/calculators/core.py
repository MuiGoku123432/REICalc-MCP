"""Core real estate calculators: affordability, BRRRR, house hack, portfolio, syndication."""

import math

from ._common import calculate_mortgage_payment, round2


def calculate_affordability(
    annual_income: float,
    monthly_debts: float,
    down_payment: float,
    interest_rate: float,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    hoa_monthly: float = 0,
    loan_term_years: int = 30,
) -> dict:
    """Calculate how much house you can afford based on income, debts, and down payment."""
    monthly_income = annual_income / 12
    front_end_ratio = 0.28
    back_end_ratio = 0.36

    max_housing_payment = monthly_income * front_end_ratio
    max_total_debt_payment = monthly_income * back_end_ratio
    max_payment_after_debts = max_total_debt_payment - monthly_debts
    max_monthly_payment = min(max_housing_payment, max_payment_after_debts)

    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    property_tax_monthly = (property_tax_rate / 100) / 12
    insurance_monthly = (insurance_rate / 100) / 12

    if monthly_rate == 0:
        max_loan_amount = (max_monthly_payment - hoa_monthly) * num_payments
    else:
        home_price = 200000.0
        for _ in range(20):
            tax_and_insurance = home_price * (property_tax_monthly + insurance_monthly)
            available = max_monthly_payment - tax_and_insurance - hoa_monthly
            new_loan = available * ((1 - (1 + monthly_rate) ** -num_payments) / monthly_rate)
            new_home_price = new_loan + down_payment
            if abs(new_home_price - home_price) < 100:
                break
            home_price = new_home_price
        max_loan_amount = home_price - down_payment

    max_home_price = max_loan_amount + down_payment
    down_payment_percent = (down_payment / max_home_price) * 100

    pmi_required = down_payment_percent < 20
    pmi_monthly = max_loan_amount * 0.005 if pmi_required else 0

    if pmi_required:
        available_after_pmi = max_monthly_payment - pmi_monthly
        tax_and_insurance = max_home_price * (property_tax_monthly + insurance_monthly)
        available = available_after_pmi - tax_and_insurance - hoa_monthly
        max_loan_amount = available * ((1 - (1 + monthly_rate) ** -num_payments) / monthly_rate)
        max_home_price = max_loan_amount + down_payment
        down_payment_percent = (down_payment / max_home_price) * 100

    principal_interest = calculate_mortgage_payment(max_loan_amount, monthly_rate, num_payments)
    property_tax = max_home_price * property_tax_monthly
    insurance = max_home_price * insurance_monthly
    total_monthly = principal_interest + property_tax + insurance + pmi_monthly + hoa_monthly

    front_end_actual = (total_monthly / monthly_income) * 100
    back_end_actual = ((total_monthly + monthly_debts) / monthly_income) * 100

    return {
        "max_home_price": round(max_home_price),
        "max_loan_amount": round(max_loan_amount),
        "down_payment": down_payment,
        "down_payment_percent": f"{down_payment_percent:.1f}",
        "monthly_payment_breakdown": {
            "principal_interest": round(principal_interest),
            "property_tax": round(property_tax),
            "insurance": round(insurance),
            "pmi": round(pmi_monthly),
            "hoa": hoa_monthly,
            "total": round(total_monthly),
        },
        "debt_to_income": {
            "front_end_ratio": f"{front_end_actual:.1f}",
            "back_end_ratio": f"{back_end_actual:.1f}",
            "front_end_limit": f"{front_end_ratio * 100:.0f}",
            "back_end_limit": f"{back_end_ratio * 100:.0f}",
        },
        "loan_details": {
            "interest_rate": interest_rate,
            "loan_term_years": loan_term_years,
            "total_payments": num_payments,
            "pmi_required": pmi_required,
        },
        "affordability_summary": {
            "monthly_income": round(monthly_income),
            "max_housing_payment": round(max_monthly_payment),
            "current_monthly_debts": monthly_debts,
            "remaining_for_housing": round(max_monthly_payment),
        },
    }


def analyze_brrrr_deal(
    purchase_price: float,
    rehab_cost: float,
    after_repair_value: float,
    monthly_rent: float,
    down_payment_percent: float = 20,
    purchase_interest_rate: float = 8.0,
    refinance_ltv: float = 0.75,
    refinance_interest_rate: float = 7.0,
    closing_costs: float = 3000,
    refinance_closing_costs: float = 3000,
    monthly_expenses: float = 600,
    vacancy_rate: float = 5,
    holding_months: int = 6,
) -> dict:
    """Analyze a BRRRR (Buy, Rehab, Rent, Refinance, Repeat) deal."""
    dp = purchase_price * (down_payment_percent / 100)
    initial_loan = purchase_price - dp
    cash_needed = dp + rehab_cost + closing_costs

    initial_monthly_rate = purchase_interest_rate / 100 / 12
    initial_payment = calculate_mortgage_payment(initial_loan, initial_monthly_rate, 360)
    holding_costs = holding_months * (initial_payment + monthly_expenses)
    total_cash_invested = cash_needed + holding_costs

    refinance_amount = after_repair_value * refinance_ltv
    cash_out = refinance_amount - initial_loan - refinance_closing_costs
    cash_left = total_cash_invested - cash_out

    refi_monthly_rate = refinance_interest_rate / 100 / 12
    refi_payment = calculate_mortgage_payment(refinance_amount, refi_monthly_rate, 360)

    effective_rent = monthly_rent * (1 - vacancy_rate / 100)
    monthly_cf = effective_rent - refi_payment - monthly_expenses
    annual_cf = monthly_cf * 12

    cocr = (annual_cf / cash_left) * 100 if cash_left > 0 else float("inf")
    total_project_cost = purchase_price + rehab_cost + closing_costs
    total_return_y1 = annual_cf + (after_repair_value - total_project_cost)
    roi = (total_return_y1 / total_cash_invested) * 100

    equity_after = after_repair_value - refinance_amount
    equity_capture = after_repair_value - total_project_cost
    purchase_to_arv = (purchase_price / after_repair_value) * 100
    all_in_to_arv = (total_project_cost / after_repair_value) * 100
    rtv = (monthly_rent / after_repair_value) * 100

    success = {
        "positive_cash_flow": monthly_cf > 0,
        "cash_recovery": cash_out >= total_cash_invested * 0.8,
        "equity_creation": equity_capture > 0,
        "safe_ltv": refinance_ltv <= 0.75,
        "good_cash_on_cash": cocr > 8,
        "meets_one_percent": rtv >= 1,
    }
    score = sum(1 for v in success.values() if v)
    rating = "Excellent" if score >= 5 else "Good" if score >= 4 else "Fair" if score >= 3 else "Poor"

    return {
        "initial_investment": {
            "purchase_price": purchase_price,
            "down_payment": round(dp),
            "rehab_cost": rehab_cost,
            "closing_costs": closing_costs,
            "holding_costs": round(holding_costs),
            "total_cash_needed": round(total_cash_invested),
        },
        "refinance_results": {
            "after_repair_value": after_repair_value,
            "refinance_loan_amount": round(refinance_amount),
            "cash_out_amount": round(cash_out),
            "cash_left_in_deal": round(cash_left),
            "new_monthly_payment": round(refi_payment),
        },
        "cash_flow_analysis": {
            "gross_monthly_rent": monthly_rent,
            "effective_monthly_rent": round(effective_rent),
            "monthly_expenses": monthly_expenses,
            "monthly_mortgage": round(refi_payment),
            "net_monthly_cash_flow": round(monthly_cf),
            "annual_cash_flow": round(annual_cf),
        },
        "returns": {
            "cash_on_cash_return": "Infinite" if cocr == float("inf") else f"{cocr:.1f}%",
            "total_roi": f"{roi:.1f}%",
            "equity_captured": round(equity_capture),
            "equity_position": round(equity_after),
        },
        "deal_metrics": {
            "purchase_to_arv": f"{purchase_to_arv:.1f}%",
            "all_in_to_arv": f"{all_in_to_arv:.1f}%",
            "rent_to_value": f"{rtv:.2f}%",
            "ltv_after_refi": f"{refinance_ltv * 100:.0f}%",
        },
        "success_indicators": success,
        "overall_rating": {
            "score": f"{score}/6",
            "rating": rating,
            "recommendation": (
                "Strong BRRRR candidate" if rating == "Excellent"
                else "Proceed with caution" if rating == "Good"
                else "Consider negotiating better terms"
            ),
        },
    }


def evaluate_house_hack(
    purchase_price: float,
    down_payment: float,
    monthly_rent_unit2: float,
    owner_expenses: float,
) -> dict:
    """Calculate returns from house hacking."""
    net_housing_cost = owner_expenses - monthly_rent_unit2
    return {
        "gross_housing_cost": owner_expenses,
        "rental_income": monthly_rent_unit2,
        "net_housing_cost": net_housing_cost,
        "monthly_savings": owner_expenses - net_housing_cost,
        "annual_savings": (owner_expenses - net_housing_cost) * 12,
    }


def project_portfolio_growth(
    starting_capital: float,
    years_to_project: int = 20,
) -> dict:
    """Project real estate portfolio growth over time."""
    return {
        "starting_capital": starting_capital,
        "projected_years": years_to_project,
        "estimated_portfolio_value": starting_capital * (1.08 ** years_to_project),
        "estimated_properties": (starting_capital // 50000) * 3,
    }


def analyze_syndication(
    investment_amount: float,
    projected_irr: float,
    hold_period: int,
    preferred_return: float = 8,
) -> dict:
    """Evaluate a real estate syndication investment opportunity."""
    total_return = investment_amount * (1 + projected_irr / 100) ** hold_period
    return {
        "investment_amount": investment_amount,
        "projected_total_return": round(total_return),
        "total_profit": round(total_return - investment_amount),
        "average_annual_return": projected_irr,
        "preferred_return_threshold": preferred_return,
    }
