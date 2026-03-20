"""Lending calculators: mortgage affordability, debt-to-income analysis, loan comparison."""

from typing import Any

from ._common import (
    calculate_mortgage_payment,
    round2,
    calculate_fha_loan_amount,
    calculate_fha_ufmip,
    fha_annual_mip_rate,
)
from ._validation import validate_positive, validate_non_negative, validate_range, validate_percent


# ---------------------------------------------------------------------------
# 1. Mortgage Affordability
# ---------------------------------------------------------------------------

def calculate_mortgage_affordability(
    annual_income: float,
    down_payment: float,
    interest_rate: float,
    co_borrower_income: float = 0,
    other_monthly_income: float = 0,
    car_payment: float = 0,
    student_loans: float = 0,
    credit_cards: float = 0,
    other_debts: float = 0,
    down_payment_percent: float = 20,
    loan_term: int = 30,
    property_tax_rate: float = 1.2,
    insurance_annual: float = 1200,
    hoa_monthly: float = 0,
) -> dict:
    """Calculate maximum affordable home price using 28/36 DTI rules."""

    validate_positive(annual_income, "annual_income")
    validate_non_negative(down_payment, "down_payment")
    validate_range(interest_rate, "interest_rate", 0, 100)
    validate_range(loan_term, "loan_term", 1, 50)

    # Income analysis
    total_annual = annual_income + co_borrower_income
    gross_monthly = total_annual / 12 + other_monthly_income

    income_analysis = {
        "primary_annual_income": round2(annual_income),
        "co_borrower_annual_income": round2(co_borrower_income),
        "total_annual_income": round2(total_annual),
        "gross_monthly_income": round2(gross_monthly),
        "other_monthly_income": round2(other_monthly_income),
        "total_monthly_income": round2(gross_monthly),
    }

    # Debt analysis
    total_monthly_debts = car_payment + student_loans + credit_cards + other_debts

    debt_analysis = {
        "car_payment": round2(car_payment),
        "student_loans": round2(student_loans),
        "credit_cards": round2(credit_cards),
        "other_debts": round2(other_debts),
        "total_monthly_debts": round2(total_monthly_debts),
    }

    # DTI limits
    front_end_limit = 0.28
    back_end_limit = 0.36

    max_housing_payment = gross_monthly * front_end_limit
    max_total_payment = gross_monthly * back_end_limit
    max_housing_from_backend = max_total_payment - total_monthly_debts
    effective_max_payment = min(max_housing_payment, max_housing_from_backend)

    # Solve for max home price iteratively
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term * 12

    max_home_price = _solve_max_home_price(
        effective_max_payment, down_payment, monthly_rate, num_payments,
        property_tax_rate, insurance_annual, hoa_monthly,
    )

    loan_amount = max_home_price - down_payment
    actual_dp_pct = (down_payment / max_home_price * 100) if max_home_price > 0 else 0

    # PMI
    ltv = (loan_amount / max_home_price * 100) if max_home_price > 0 else 0
    pmi_required = ltv > 80
    pmi_monthly = (loan_amount * 0.005 / 12) if pmi_required else 0

    # If PMI is required, re-solve accounting for it
    if pmi_required:
        max_home_price = _solve_max_home_price_with_pmi(
            effective_max_payment, down_payment, monthly_rate, num_payments,
            property_tax_rate, insurance_annual, hoa_monthly,
        )
        loan_amount = max_home_price - down_payment
        actual_dp_pct = (down_payment / max_home_price * 100) if max_home_price > 0 else 0
        ltv = (loan_amount / max_home_price * 100) if max_home_price > 0 else 0
        pmi_monthly = (loan_amount * 0.005 / 12) if ltv > 80 else 0

    # Payment breakdown
    pi = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
    prop_tax_monthly = max_home_price * (property_tax_rate / 100) / 12
    insurance_monthly = insurance_annual / 12
    total_monthly_payment = pi + prop_tax_monthly + insurance_monthly + pmi_monthly + hoa_monthly

    monthly_payment_breakdown = {
        "principal_and_interest": round2(pi),
        "property_tax": round2(prop_tax_monthly),
        "insurance": round2(insurance_monthly),
        "pmi": round2(pmi_monthly),
        "hoa": round2(hoa_monthly),
        "total_monthly_payment": round2(total_monthly_payment),
    }

    # DTI ratios
    front_end_ratio = (total_monthly_payment / gross_monthly * 100) if gross_monthly > 0 else 0
    back_end_ratio = ((total_monthly_payment + total_monthly_debts) / gross_monthly * 100) if gross_monthly > 0 else 0

    front_status = _dti_status_simple(front_end_ratio, 28)
    back_status = _dti_status_simple(back_end_ratio, 36)

    debt_to_income_ratios = {
        "front_end_ratio": round2(front_end_ratio),
        "front_end_limit": 28.0,
        "front_end_status": front_status,
        "back_end_ratio": round2(back_end_ratio),
        "back_end_limit": 36.0,
        "back_end_status": back_status,
    }

    # Affordability results
    affordability_results = {
        "max_home_price": round2(max_home_price),
        "loan_amount": round2(loan_amount),
        "down_payment": round2(down_payment),
        "down_payment_percent": round2(actual_dp_pct),
        "ltv": round2(ltv),
        "pmi_required": pmi_required,
        "max_housing_payment_front_end": round2(max_housing_payment),
        "max_housing_payment_back_end": round2(max_housing_from_backend),
        "effective_max_payment": round2(effective_max_payment),
    }

    # Alternative scenarios
    alternative_scenarios = _build_affordability_scenarios(
        gross_monthly, total_monthly_debts, down_payment, monthly_rate,
        num_payments, property_tax_rate, insurance_annual, hoa_monthly,
    )

    # Loan details
    total_interest = (pi * num_payments) - loan_amount
    loan_details = {
        "loan_amount": round2(loan_amount),
        "interest_rate": interest_rate,
        "loan_term_years": loan_term,
        "num_payments": num_payments,
        "total_interest_paid": round2(total_interest),
        "total_cost": round2(pi * num_payments),
    }

    # Recommendations
    recommendations = _affordability_recommendations(
        front_end_ratio, back_end_ratio, pmi_required, actual_dp_pct,
    )

    return {
        "income_analysis": income_analysis,
        "debt_analysis": debt_analysis,
        "affordability_results": affordability_results,
        "monthly_payment_breakdown": monthly_payment_breakdown,
        "debt_to_income_ratios": debt_to_income_ratios,
        "alternative_scenarios": alternative_scenarios,
        "loan_details": loan_details,
        "recommendations": recommendations,
    }


def _solve_max_home_price(
    max_payment: float,
    down_payment: float,
    monthly_rate: float,
    num_payments: int,
    tax_rate: float,
    insurance_annual: float,
    hoa_monthly: float,
) -> float:
    """Iteratively solve for max home price given a max total housing payment."""
    home_price = 200_000.0
    for _ in range(50):
        prop_tax = home_price * (tax_rate / 100) / 12
        insurance = insurance_annual / 12
        available_pi = max_payment - prop_tax - insurance - hoa_monthly
        if available_pi <= 0:
            home_price *= 0.5
            continue
        if monthly_rate == 0:
            loan = available_pi * num_payments
        else:
            loan = available_pi * ((1 - (1 + monthly_rate) ** -num_payments) / monthly_rate)
        new_price = loan + down_payment
        if new_price < 0:
            new_price = 0
        if abs(new_price - home_price) < 1:
            break
        home_price = new_price
    return max(home_price, 0)


def _solve_max_home_price_with_pmi(
    max_payment: float,
    down_payment: float,
    monthly_rate: float,
    num_payments: int,
    tax_rate: float,
    insurance_annual: float,
    hoa_monthly: float,
) -> float:
    """Solve for max home price accounting for PMI."""
    home_price = 200_000.0
    for _ in range(50):
        loan = home_price - down_payment
        if loan < 0:
            loan = 0
        ltv = (loan / home_price * 100) if home_price > 0 else 0
        pmi = (loan * 0.005 / 12) if ltv > 80 else 0
        prop_tax = home_price * (tax_rate / 100) / 12
        insurance = insurance_annual / 12
        available_pi = max_payment - prop_tax - insurance - hoa_monthly - pmi
        if available_pi <= 0:
            home_price *= 0.5
            continue
        if monthly_rate == 0:
            new_loan = available_pi * num_payments
        else:
            new_loan = available_pi * ((1 - (1 + monthly_rate) ** -num_payments) / monthly_rate)
        new_price = new_loan + down_payment
        if new_price < 0:
            new_price = 0
        if abs(new_price - home_price) < 1:
            break
        home_price = new_price
    return max(home_price, 0)


def _dti_status_simple(ratio: float, limit: float) -> str:
    if ratio <= limit * 0.8:
        return "Excellent"
    if ratio <= limit:
        return "Good"
    if ratio <= limit * 1.1:
        return "Marginal"
    return "Poor"


def _build_affordability_scenarios(
    gross_monthly: float,
    total_debts: float,
    down_payment: float,
    monthly_rate: float,
    num_payments: int,
    tax_rate: float,
    insurance_annual: float,
    hoa_monthly: float,
) -> list[dict]:
    scenarios = [
        {"name": "Conservative", "front_end_pct": 25, "back_end_pct": 25},
        {"name": "Moderate", "front_end_pct": 28, "back_end_pct": 28},
        {"name": "Aggressive", "front_end_pct": 36, "back_end_pct": 36},
    ]
    results = []
    for sc in scenarios:
        max_housing = gross_monthly * (sc["front_end_pct"] / 100)
        max_total = gross_monthly * (sc["back_end_pct"] / 100)
        max_from_back = max_total - total_debts
        effective = min(max_housing, max_from_back)
        price = _solve_max_home_price(
            effective, down_payment, monthly_rate, num_payments,
            tax_rate, insurance_annual, hoa_monthly,
        )
        results.append({
            "name": sc["name"],
            "dti_front_end": sc["front_end_pct"],
            "dti_back_end": sc["back_end_pct"],
            "max_home_price": round2(price),
            "max_monthly_payment": round2(effective),
        })
    return results


def _affordability_recommendations(
    front_ratio: float, back_ratio: float, pmi_required: bool, dp_pct: float,
) -> list[str]:
    recs: list[str] = []
    if front_ratio > 28:
        recs.append("Your front-end DTI exceeds 28%. Consider a less expensive home or increasing income.")
    if back_ratio > 36:
        recs.append("Your back-end DTI exceeds 36%. Pay down existing debts to improve qualification.")
    if pmi_required:
        recs.append("PMI is required because your down payment is less than 20%. Consider saving more for a larger down payment.")
    if dp_pct < 10:
        recs.append("A down payment under 10% means higher PMI costs and less equity protection.")
    if front_ratio <= 25 and back_ratio <= 30:
        recs.append("Your DTI ratios are well within guidelines. You have strong purchasing power.")
    if not recs:
        recs.append("Your financial profile looks solid for the calculated home price.")
    return recs


# ---------------------------------------------------------------------------
# 2. Debt-to-Income Analysis
# ---------------------------------------------------------------------------

_LOAN_TYPE_LIMITS: dict[str, tuple[float, float]] = {
    "conventional": (28, 36),
    "fha": (31, 43),
    "va": (41, 41),
    "usda": (29, 41),
}


def analyze_debt_to_income(
    monthly_income: float,
    proposed_housing_payment: float = 0,
    car_payments: float = 0,
    credit_card_minimums: float = 0,
    student_loans: float = 0,
    personal_loans: float = 0,
    child_support_alimony: float = 0,
    other_debts: float = 0,
    loan_type: str = "conventional",
    purchase_price: float | None = None,
    down_payment: float | None = None,
    interest_rate: float | None = None,
    loan_term_years: int = 30,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    hoa_monthly: float = 0,
    pmi_rate: float = 0.5,
) -> dict:
    """Analyze debt-to-income ratios for loan qualification.

    If purchase_price, down_payment, and interest_rate are provided,
    proposed_housing_payment is computed internally as PITI.

    pmi_rate: annual PMI rate as a percentage of the loan amount (default 0.5%).
    """

    # Compute housing payment from loan details if provided
    if purchase_price is not None and down_payment is not None and interest_rate is not None:
        base_loan = purchase_price - down_payment
        if loan_type == "fha":
            loan_amount = calculate_fha_loan_amount(purchase_price, down_payment)
            ltv = (base_loan / purchase_price * 100) if purchase_price > 0 else 0
            effective_pmi_rate = fha_annual_mip_rate(ltv, loan_term_years)
        else:
            loan_amount = base_loan
            effective_pmi_rate = pmi_rate
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        pi = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
        prop_tax = purchase_price * (property_tax_rate / 100) / 12
        insurance = purchase_price * (insurance_rate / 100) / 12
        dp_pct = (down_payment / purchase_price * 100) if purchase_price > 0 else 0
        pmi = (loan_amount * (effective_pmi_rate / 100) / 12) if dp_pct < 20 else 0
        proposed_housing_payment = pi + prop_tax + insurance + pmi + hoa_monthly

    validate_positive(monthly_income, "monthly_income")
    validate_non_negative(proposed_housing_payment, "proposed_housing_payment")

    if loan_type not in _LOAN_TYPE_LIMITS:
        raise ValueError(f"Invalid loan_type '{loan_type}'. Must be one of: {', '.join(_LOAN_TYPE_LIMITS)}")

    front_limit, back_limit = _LOAN_TYPE_LIMITS[loan_type]

    # Income analysis
    annual_income = monthly_income * 12
    income_analysis = {
        "monthly_income": round2(monthly_income),
        "annual_income": round2(annual_income),
    }

    # Proposed payment
    proposed_payment = {
        "housing_payment": round2(proposed_housing_payment),
    }

    # Debt breakdown
    total_other_debts = (
        car_payments + credit_card_minimums + student_loans
        + personal_loans + child_support_alimony + other_debts
    )
    total_all_debts = proposed_housing_payment + total_other_debts

    debt_breakdown = {
        "car_payments": round2(car_payments),
        "credit_card_minimums": round2(credit_card_minimums),
        "student_loans": round2(student_loans),
        "personal_loans": round2(personal_loans),
        "child_support_alimony": round2(child_support_alimony),
        "other_debts": round2(other_debts),
        "total_non_housing_debts": round2(total_other_debts),
        "total_all_debts": round2(total_all_debts),
    }

    # DTI ratios
    front_end_ratio = (proposed_housing_payment / monthly_income * 100) if monthly_income > 0 else 0
    back_end_ratio = (total_all_debts / monthly_income * 100) if monthly_income > 0 else 0

    front_status = _dti_qualification_status(front_end_ratio, front_limit)
    back_status = _dti_qualification_status(back_end_ratio, back_limit)

    front_over_under = front_limit - front_end_ratio
    back_over_under = back_limit - back_end_ratio

    dti_ratios = {
        "front_end": {
            "ratio": round2(front_end_ratio),
            "limit": front_limit,
            "status": front_status,
            "amount_over_under": round2(front_over_under),
        },
        "back_end": {
            "ratio": round2(back_end_ratio),
            "limit": back_limit,
            "status": back_status,
            "amount_over_under": round2(back_over_under),
        },
        "loan_type": loan_type,
    }

    # Overall qualification
    if front_status == "Poor" or back_status == "Poor":
        overall = "Likely Declined"
    elif front_status == "Marginal" or back_status == "Marginal":
        overall = "Manual Underwriting"
    elif front_status == "Good" or back_status == "Good":
        overall = "Likely Approved"
    else:
        overall = "Excellent Candidate"

    qualification = {
        "overall_status": overall,
        "front_end_status": front_status,
        "back_end_status": back_status,
        "loan_type": loan_type,
        "loan_type_limits": {"front_end": front_limit, "back_end": back_limit},
    }

    # Maximum affordable housing payment based on limits
    max_front = monthly_income * (front_limit / 100)
    max_back = monthly_income * (back_limit / 100) - total_other_debts
    max_affordable_payment = min(max_front, max_back)

    maximum_affordable = {
        "max_housing_from_front_end": round2(max_front),
        "max_housing_from_back_end": round2(max_back),
        "max_affordable_payment": round2(max(max_affordable_payment, 0)),
        "current_proposed": round2(proposed_housing_payment),
        "difference": round2(max_affordable_payment - proposed_housing_payment),
    }

    # Recommendations
    recommendations = _dti_recommendations(
        front_end_ratio, back_end_ratio, front_limit, back_limit,
        overall, total_other_debts,
    )

    # Improvement strategies
    improvement_strategies = _improvement_strategies(
        monthly_income, front_end_ratio, back_end_ratio,
        front_limit, back_limit, total_other_debts, proposed_housing_payment,
    )

    return {
        "income_analysis": income_analysis,
        "proposed_payment": proposed_payment,
        "dti_ratios": dti_ratios,
        "qualification": qualification,
        "maximum_affordable": maximum_affordable,
        "debt_breakdown": debt_breakdown,
        "recommendations": recommendations,
        "improvement_strategies": improvement_strategies,
    }


def _dti_qualification_status(ratio: float, limit: float) -> str:
    if ratio <= limit * 0.8:
        return "Excellent"
    if ratio <= limit:
        return "Good"
    if ratio <= limit * 1.1:
        return "Marginal"
    return "Poor"


def _dti_recommendations(
    front: float, back: float, front_limit: float, back_limit: float,
    overall: str, total_debts: float,
) -> list[str]:
    recs: list[str] = []
    if overall == "Excellent Candidate":
        recs.append("Your DTI ratios are excellent. You should have no trouble qualifying.")
    elif overall == "Likely Approved":
        recs.append("Your DTI ratios are within guidelines. You should qualify for this loan type.")
    elif overall == "Manual Underwriting":
        recs.append("Your DTI ratios are borderline. The loan may require manual underwriting review.")
        if front > front_limit:
            recs.append(f"Front-end DTI of {front:.1f}% exceeds the {front_limit}% limit. Consider a lower housing payment.")
        if back > back_limit:
            recs.append(f"Back-end DTI of {back:.1f}% exceeds the {back_limit}% limit. Reduce existing debts.")
    else:
        recs.append("Your DTI ratios exceed acceptable limits. Significant changes are needed to qualify.")
        if total_debts > 0:
            recs.append("Focus on paying down existing debts before applying.")
    return recs


def _improvement_strategies(
    monthly_income: float, front: float, back: float,
    front_limit: float, back_limit: float,
    total_debts: float, housing_payment: float,
) -> list[dict[str, Any]]:
    strategies: list[dict[str, Any]] = []

    if back > back_limit and total_debts > 0:
        excess_back = back - back_limit
        debt_reduction = excess_back / 100 * monthly_income
        strategies.append({
            "strategy": "Reduce monthly debts",
            "details": f"Reduce non-housing debts by ${debt_reduction:,.0f}/month to meet back-end DTI limit.",
            "impact": f"Reduces back-end DTI by {excess_back:.1f}%",
        })

    if front > front_limit:
        excess_front = front - front_limit
        payment_reduction = excess_front / 100 * monthly_income
        strategies.append({
            "strategy": "Lower housing payment",
            "details": f"Reduce housing payment by ${payment_reduction:,.0f}/month to meet front-end DTI limit.",
            "impact": f"Reduces front-end DTI by {excess_front:.1f}%",
        })

    if front > front_limit or back > back_limit:
        worse_excess = max(front - front_limit, back - back_limit)
        needed_income = (housing_payment + total_debts) / (back_limit / 100) - monthly_income
        if needed_income > 0:
            strategies.append({
                "strategy": "Increase income",
                "details": f"Increase monthly income by ${needed_income:,.0f} to meet all DTI limits.",
                "impact": f"Would bring back-end DTI within the {back_limit}% limit.",
            })

    if not strategies:
        strategies.append({
            "strategy": "Maintain current profile",
            "details": "Your current financial profile meets all DTI requirements.",
            "impact": "No changes needed.",
        })

    return strategies


# ---------------------------------------------------------------------------
# 3. Loan Comparison
# ---------------------------------------------------------------------------

def compare_loans(
    home_price: float,
    loans: list[dict[str, Any]],
    property_tax_annual: float = 0,
    home_insurance_annual: float = 0,
    hoa_monthly: float = 0,
    comparison_period_years: int = 5,
) -> dict:
    """Compare multiple loan options side by side."""

    validate_positive(home_price, "home_price")

    prop_tax_monthly = property_tax_annual / 12
    insurance_monthly = home_insurance_annual / 12
    comparison_months = comparison_period_years * 12

    loan_details: list[dict] = []
    for loan_input in loans:
        detail = _analyze_single_loan(
            home_price, loan_input, prop_tax_monthly, insurance_monthly,
            hoa_monthly, comparison_months, comparison_period_years,
        )
        loan_details.append(detail)

    # Best options by metric
    best_options = _find_best_options(loan_details)

    # Side-by-side
    side_by_side = _build_side_by_side(loan_details)

    # Comparison summary
    comparison_summary = {
        "home_price": round2(home_price),
        "num_loans_compared": len(loan_details),
        "comparison_period_years": comparison_period_years,
        "property_tax_monthly": round2(prop_tax_monthly),
        "insurance_monthly": round2(insurance_monthly),
        "hoa_monthly": round2(hoa_monthly),
    }

    # Points analysis
    points_analysis = _analyze_points(loan_details)

    # ARM risk analysis
    arm_risk_analysis = _analyze_arm_risk(loan_details)

    # Recommendations
    recommendations = _loan_comparison_recommendations(
        loan_details, best_options, comparison_period_years,
    )

    return {
        "loan_details": loan_details,
        "comparison_summary": comparison_summary,
        "best_options": best_options,
        "side_by_side": side_by_side,
        "points_analysis": points_analysis,
        "arm_risk_analysis": arm_risk_analysis,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 4. PITI Calculator
# ---------------------------------------------------------------------------

def calculate_piti(
    home_price: float,
    down_payment_percent: float = 20.0,
    interest_rate: float = 7.0,
    loan_term_years: int = 30,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    hoa_monthly: float = 0,
    loan_type: str = "conventional",
    pmi_rate: float | None = None,
) -> dict:
    """Calculate PITI (Principal, Interest, Tax, Insurance) monthly payment.

    Automatically handles FHA UFMIP and correct MIP rates when loan_type="fha".
    If pmi_rate is provided, it overrides the default for the loan type.
    """
    validate_positive(home_price, "home_price")
    validate_range(down_payment_percent, "down_payment_percent", 0, 100)
    validate_range(interest_rate, "interest_rate", 0, 100)

    down_payment = home_price * down_payment_percent / 100
    base_loan = home_price - down_payment

    # Loan amount and PMI/MIP rate
    ufmip = 0.0
    if loan_type == "fha":
        loan_amount = calculate_fha_loan_amount(home_price, down_payment)
        ufmip = calculate_fha_ufmip(base_loan)
        ltv = 100 - down_payment_percent
        effective_pmi_rate = pmi_rate if pmi_rate is not None else fha_annual_mip_rate(ltv, loan_term_years)
    else:
        loan_amount = base_loan
        if pmi_rate is not None:
            effective_pmi_rate = pmi_rate
        elif down_payment_percent >= 20:
            effective_pmi_rate = 0.0
        else:
            effective_pmi_rate = _default_pmi_rate(down_payment_percent, loan_type)

    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term_years * 12

    pi = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
    tax_monthly = home_price * (property_tax_rate / 100) / 12
    insurance_monthly = home_price * (insurance_rate / 100) / 12
    pmi_monthly = (loan_amount * (effective_pmi_rate / 100) / 12) if down_payment_percent < 20 else 0

    total_piti = pi + tax_monthly + insurance_monthly + pmi_monthly
    total_with_hoa = total_piti + hoa_monthly

    result: dict = {
        "monthly_payment": {
            "principal_and_interest": round2(pi),
            "property_tax": round2(tax_monthly),
            "insurance": round2(insurance_monthly),
            "pmi_mip": round2(pmi_monthly),
            "hoa": round2(hoa_monthly),
            "total_piti": round2(total_piti),
            "total_with_hoa": round2(total_with_hoa),
        },
        "loan_details": {
            "home_price": round2(home_price),
            "down_payment": round2(down_payment),
            "down_payment_percent": round2(down_payment_percent),
            "base_loan": round2(base_loan),
            "loan_amount": round2(loan_amount),
            "interest_rate": interest_rate,
            "loan_term_years": loan_term_years,
            "loan_type": loan_type,
        },
        "pmi_details": {
            "pmi_required": pmi_monthly > 0,
            "pmi_rate": round2(effective_pmi_rate),
            "pmi_monthly": round2(pmi_monthly),
        },
    }

    if loan_type == "fha":
        result["fha_details"] = {
            "ufmip": round2(ufmip),
            "ufmip_rate": 1.75,
            "annual_mip_rate": round2(effective_pmi_rate),
            "loan_amount_with_ufmip": round2(loan_amount),
        }

    return result


def _default_pmi_rate(down_payment_pct: float, loan_type: str) -> float:
    """Return default annual PMI rate based on LTV and loan type."""
    if loan_type == "fha":
        ltv = 100 - down_payment_pct
        return fha_annual_mip_rate(ltv)
    if down_payment_pct >= 20:
        return 0.0
    if down_payment_pct >= 15:
        return 0.25
    if down_payment_pct >= 10:
        return 0.45
    if down_payment_pct >= 5:
        return 0.75
    return 1.0


def _closing_cost_rate(loan_type: str) -> float:
    """Estimated closing cost percentage by loan type."""
    rates = {
        "conventional": 2.5,
        "fha": 3.0,
        "va": 2.0,
        "usda": 2.5,
        "jumbo": 2.0,
        "arm": 2.5,
    }
    return rates.get(loan_type, 2.5)


def _analyze_single_loan(
    home_price: float,
    loan_input: dict[str, Any],
    prop_tax_monthly: float,
    insurance_monthly: float,
    hoa_monthly: float,
    comparison_months: int,
    comparison_years: int,
) -> dict:
    name = loan_input.get("loan_name", "Unnamed Loan")
    dp_pct = loan_input.get("down_payment_percent", 20)
    rate = loan_input.get("interest_rate", 0)
    term_years = loan_input.get("loan_term_years", 30)
    loan_type = loan_input.get("loan_type", "conventional")
    points = loan_input.get("points", 0)
    pmi_rate_input = loan_input.get("pmi_rate")
    arm_details = loan_input.get("arm_details")

    down_payment = home_price * dp_pct / 100
    base_loan = home_price - down_payment
    if loan_type == "fha":
        loan_amount = calculate_fha_loan_amount(home_price, down_payment)
        ufmip = calculate_fha_ufmip(base_loan)
    else:
        loan_amount = base_loan
        ufmip = 0.0
    monthly_rate = rate / 100 / 12
    num_payments = term_years * 12

    # PMI
    if pmi_rate_input is not None and pmi_rate_input > 0:
        pmi_annual_rate = pmi_rate_input
    else:
        pmi_annual_rate = _default_pmi_rate(dp_pct, loan_type)

    pmi_monthly = loan_amount * (pmi_annual_rate / 100) / 12

    # Monthly P&I
    pi = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)

    # Upfront costs
    points_cost = loan_amount * points / 100
    closing_rate = _closing_cost_rate(loan_type)
    estimated_closing = loan_amount * closing_rate / 100
    total_upfront = down_payment + points_cost + estimated_closing

    # Total monthly (PITI + PMI + HOA)
    total_monthly = pi + prop_tax_monthly + insurance_monthly + pmi_monthly + hoa_monthly

    # Amortization over comparison period
    balance = loan_amount
    total_interest_paid = 0.0
    total_principal_paid = 0.0
    total_pmi_paid = 0.0
    pmi_drop_month: int | None = None
    origination_ltv = (base_loan / home_price * 100) if home_price > 0 else 0

    for month in range(1, comparison_months + 1):
        interest_portion = balance * monthly_rate
        principal_portion = pi - interest_portion
        total_interest_paid += interest_portion
        total_principal_paid += principal_portion
        balance -= principal_portion

        if pmi_monthly > 0 and pmi_drop_month is None:
            if loan_type == "fha":
                # FHA MIP: >90% origination LTV = life of loan
                # ≤90% origination LTV = drops after 11 years (132 months)
                if origination_ltv > 90:
                    total_pmi_paid += pmi_monthly  # life of loan, never drops
                elif month <= 132:
                    total_pmi_paid += pmi_monthly
                else:
                    pmi_drop_month = month
            else:
                # Conventional: drops when current LTV reaches 78%
                current_ltv = (balance / home_price * 100) if home_price > 0 else 0
                if current_ltv <= 78:
                    pmi_drop_month = month
                else:
                    total_pmi_paid += pmi_monthly
        elif pmi_drop_month is None:
            total_pmi_paid += pmi_monthly

    total_cost_over_period = (
        total_upfront
        + pi * comparison_months
        + prop_tax_monthly * comparison_months
        + insurance_monthly * comparison_months
        + total_pmi_paid
        + hoa_monthly * comparison_months
    )

    equity_at_end = total_principal_paid + down_payment

    return {
        "loan_name": name,
        "loan_type": loan_type,
        "home_price": round2(home_price),
        "down_payment": round2(down_payment),
        "down_payment_percent": round2(dp_pct),
        "loan_amount": round2(loan_amount),
        "interest_rate": rate,
        "loan_term_years": term_years,
        "points": points,
        "points_cost": round2(points_cost),
        "monthly_payment": {
            "principal_and_interest": round2(pi),
            "property_tax": round2(prop_tax_monthly),
            "insurance": round2(insurance_monthly),
            "pmi": round2(pmi_monthly),
            "hoa": round2(hoa_monthly),
            "total": round2(total_monthly),
        },
        "pmi_details": {
            "pmi_required": pmi_monthly > 0,
            "pmi_rate": round2(pmi_annual_rate),
            "pmi_monthly": round2(pmi_monthly),
            "pmi_drop_month": pmi_drop_month,
            "total_pmi_paid": round2(total_pmi_paid),
        },
        "upfront_costs": {
            "down_payment": round2(down_payment),
            "points_cost": round2(points_cost),
            "estimated_closing_costs": round2(estimated_closing),
            "ufmip": round2(ufmip),
            "total_upfront": round2(total_upfront),
        },
        "comparison_period": {
            "years": comparison_years,
            "total_interest_paid": round2(total_interest_paid),
            "total_principal_paid": round2(total_principal_paid),
            "remaining_balance": round2(balance),
            "equity": round2(equity_at_end),
            "total_cost": round2(total_cost_over_period),
        },
        "arm_details": arm_details,
    }


def _find_best_options(loan_details: list[dict]) -> dict:
    if not loan_details:
        return {}

    best: dict[str, Any] = {}

    # Lowest monthly payment
    sorted_monthly = sorted(loan_details, key=lambda d: d["monthly_payment"]["total"])
    best["lowest_monthly_payment"] = {
        "loan_name": sorted_monthly[0]["loan_name"],
        "amount": sorted_monthly[0]["monthly_payment"]["total"],
    }

    # Lowest total cost over comparison period
    sorted_cost = sorted(loan_details, key=lambda d: d["comparison_period"]["total_cost"])
    best["lowest_total_cost"] = {
        "loan_name": sorted_cost[0]["loan_name"],
        "amount": sorted_cost[0]["comparison_period"]["total_cost"],
    }

    # Lowest upfront costs
    sorted_upfront = sorted(loan_details, key=lambda d: d["upfront_costs"]["total_upfront"])
    best["lowest_upfront_cost"] = {
        "loan_name": sorted_upfront[0]["loan_name"],
        "amount": sorted_upfront[0]["upfront_costs"]["total_upfront"],
    }

    # Most equity at end of comparison period
    sorted_equity = sorted(loan_details, key=lambda d: d["comparison_period"]["equity"], reverse=True)
    best["most_equity"] = {
        "loan_name": sorted_equity[0]["loan_name"],
        "amount": sorted_equity[0]["comparison_period"]["equity"],
    }

    # Lowest interest paid
    sorted_interest = sorted(loan_details, key=lambda d: d["comparison_period"]["total_interest_paid"])
    best["lowest_interest_paid"] = {
        "loan_name": sorted_interest[0]["loan_name"],
        "amount": sorted_interest[0]["comparison_period"]["total_interest_paid"],
    }

    return best


def _build_side_by_side(loan_details: list[dict]) -> dict:
    """Build side-by-side comparison table structure."""
    metrics = [
        "loan_amount", "interest_rate", "loan_term_years", "down_payment",
    ]
    payment_metrics = [
        "principal_and_interest", "property_tax", "insurance", "pmi", "hoa", "total",
    ]
    period_metrics = [
        "total_interest_paid", "total_principal_paid", "remaining_balance", "equity", "total_cost",
    ]

    rows: dict[str, list] = {}
    for m in metrics:
        rows[m] = [d[m] for d in loan_details]
    for m in payment_metrics:
        rows[f"monthly_{m}"] = [d["monthly_payment"][m] for d in loan_details]
    for m in period_metrics:
        rows[f"period_{m}"] = [d["comparison_period"][m] for d in loan_details]

    return {
        "loan_names": [d["loan_name"] for d in loan_details],
        "metrics": rows,
    }


def _analyze_points(loan_details: list[dict]) -> list[dict]:
    """For each loan with points, calculate break-even months."""
    results: list[dict] = []
    # Need at least one loan without points to compare
    no_points = [d for d in loan_details if d["points"] == 0]
    with_points = [d for d in loan_details if d["points"] > 0]

    if not no_points or not with_points:
        return results

    baseline = no_points[0]
    baseline_monthly = baseline["monthly_payment"]["total"]

    for d in with_points:
        monthly_savings = baseline_monthly - d["monthly_payment"]["total"]
        if monthly_savings > 0:
            break_even_months = d["upfront_costs"]["points_cost"] / monthly_savings
            results.append({
                "loan_name": d["loan_name"],
                "compared_to": baseline["loan_name"],
                "points_cost": d["upfront_costs"]["points_cost"],
                "monthly_savings": round2(monthly_savings),
                "break_even_months": round(break_even_months),
                "break_even_years": round2(break_even_months / 12),
                "worth_it": break_even_months < d["loan_term_years"] * 12,
            })
        else:
            results.append({
                "loan_name": d["loan_name"],
                "compared_to": baseline["loan_name"],
                "points_cost": d["upfront_costs"]["points_cost"],
                "monthly_savings": round2(monthly_savings),
                "break_even_months": None,
                "break_even_years": None,
                "worth_it": False,
            })

    return results


def _analyze_arm_risk(loan_details: list[dict]) -> list[dict]:
    """Analyze ARM risk for loans with ARM details."""
    results: list[dict] = []
    for d in loan_details:
        arm = d.get("arm_details")
        if not arm:
            continue

        fixed_period = arm.get("fixed_period_years", 5)
        initial_rate = d["interest_rate"]
        rate_cap_periodic = arm.get("rate_cap_periodic", 2)
        rate_cap_lifetime = arm.get("rate_cap_lifetime", 5)
        rate_floor = arm.get("rate_floor", initial_rate)

        worst_case_rate = initial_rate + rate_cap_lifetime
        loan_amount = d["loan_amount"]
        remaining_term = d["loan_term_years"] - fixed_period
        remaining_payments = remaining_term * 12

        # Approximate remaining balance at end of fixed period
        monthly_rate = initial_rate / 100 / 12
        total_payments = d["loan_term_years"] * 12
        pi = d["monthly_payment"]["principal_and_interest"]
        balance = loan_amount
        for _ in range(fixed_period * 12):
            interest = balance * monthly_rate
            principal = pi - interest
            balance -= principal

        # Worst-case monthly payment after fixed period
        worst_monthly_rate = worst_case_rate / 100 / 12
        worst_pi = calculate_mortgage_payment(balance, worst_monthly_rate, remaining_payments) if remaining_payments > 0 else 0

        # First adjustment
        first_adj_rate = min(initial_rate + rate_cap_periodic, worst_case_rate)
        first_adj_monthly_rate = first_adj_rate / 100 / 12
        first_adj_pi = calculate_mortgage_payment(balance, first_adj_monthly_rate, remaining_payments) if remaining_payments > 0 else 0

        results.append({
            "loan_name": d["loan_name"],
            "fixed_period_years": fixed_period,
            "initial_rate": initial_rate,
            "rate_cap_periodic": rate_cap_periodic,
            "rate_cap_lifetime": rate_cap_lifetime,
            "worst_case_rate": round2(worst_case_rate),
            "current_pi": round2(pi),
            "estimated_balance_at_adjustment": round2(balance),
            "first_adjustment_rate": round2(first_adj_rate),
            "first_adjustment_pi": round2(first_adj_pi),
            "worst_case_pi": round2(worst_pi),
            "payment_increase_worst": round2(worst_pi - pi),
            "payment_increase_pct_worst": round2((worst_pi - pi) / pi * 100) if pi > 0 else 0,
        })

    return results


def _loan_comparison_recommendations(
    loan_details: list[dict],
    best_options: dict,
    comparison_years: int,
) -> list[str]:
    recs: list[str] = []

    if not loan_details:
        return ["No loans provided for comparison."]

    lowest_monthly = best_options.get("lowest_monthly_payment", {}).get("loan_name")
    lowest_cost = best_options.get("lowest_total_cost", {}).get("loan_name")

    if lowest_monthly and lowest_cost:
        if lowest_monthly == lowest_cost:
            recs.append(
                f'"{lowest_monthly}" offers both the lowest monthly payment and lowest total cost '
                f"over {comparison_years} years."
            )
        else:
            recs.append(
                f'"{lowest_monthly}" has the lowest monthly payment, while "{lowest_cost}" '
                f"has the lowest total cost over {comparison_years} years."
            )

    # Check if any ARM loans
    arm_loans = [d for d in loan_details if d.get("arm_details")]
    if arm_loans:
        recs.append(
            "ARM loans carry rate-adjustment risk. Consider your expected time in the home "
            "when evaluating ARM options."
        )

    # Check PMI
    pmi_loans = [d for d in loan_details if d["pmi_details"]["pmi_required"]]
    no_pmi_loans = [d for d in loan_details if not d["pmi_details"]["pmi_required"]]
    if pmi_loans and no_pmi_loans:
        recs.append(
            "Some loan options require PMI. Compare total costs including PMI to determine true value."
        )

    if not recs:
        recs.append("Review the side-by-side comparison to identify the best loan for your situation.")

    return recs
