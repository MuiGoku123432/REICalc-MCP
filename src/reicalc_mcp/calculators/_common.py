"""Shared math utilities for real estate calculators."""

import math
import random


def calculate_mortgage_payment(principal: float, monthly_rate: float, num_payments: int) -> float:
    """Calculate monthly mortgage payment (P&I)."""
    if monthly_rate == 0:
        return principal / num_payments
    return principal * (monthly_rate * (1 + monthly_rate) ** num_payments) / (
        (1 + monthly_rate) ** num_payments - 1
    )


def calculate_irr(cash_flows: list[float], guess: float = 0.1) -> float | None:
    """Calculate Internal Rate of Return using Newton's method.

    Returns None if cash flows have no sign change or if convergence fails.
    """
    if not cash_flows:
        return None

    # Sign-change validation: need both positive and negative cash flows
    has_positive = any(cf > 0 for cf in cash_flows)
    has_negative = any(cf < 0 for cf in cash_flows)
    if not (has_positive and has_negative):
        return None

    max_iterations = 100
    tolerance = 1e-5
    rate = guess

    for _ in range(max_iterations):
        npv = calculate_npv(cash_flows, rate)
        dnpv = _derivative_npv(cash_flows, rate)
        if abs(dnpv) < tolerance:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tolerance:
            return new_rate
        rate = new_rate

    # Try alternative guesses if no convergence
    for alt_guess in [0.0, 0.05, 0.15, 0.25, 0.5, -0.1]:
        result = _irr_with_guess(cash_flows, alt_guess)
        if result is not None:
            return result

    return None


def _irr_with_guess(cash_flows: list[float], guess: float) -> float | None:
    tolerance = 1e-5
    rate = guess
    for _ in range(50):
        npv = calculate_npv(cash_flows, rate)
        dnpv = _derivative_npv(cash_flows, rate)
        if abs(dnpv) < tolerance:
            return None
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < tolerance:
            return new_rate
        rate = new_rate
    return None


def calculate_npv(cash_flows: list[float], rate: float) -> float:
    """Calculate Net Present Value."""
    if not cash_flows:
        return 0.0
    if rate == -1:
        return float("inf")
    return sum(cf / (1 + rate) ** i for i, cf in enumerate(cash_flows))


def _derivative_npv(cash_flows: list[float], rate: float) -> float:
    return sum(-i * cf / (1 + rate) ** (i + 1) for i, cf in enumerate(cash_flows) if i > 0)


def safe_irr_pct(cash_flows: list[float], guess: float = 0.1) -> tuple[float, bool]:
    """Calculate IRR as a percentage, returning (value, converged).

    Returns (0.0, False) when IRR cannot be computed.
    """
    result = calculate_irr(cash_flows, guess)
    if result is None:
        return 0.0, False
    return result * 100, True


def round2(value: float) -> float:
    """Round to 2 decimal places."""
    return round(value, 2)
