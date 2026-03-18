"""Advanced analysis calculators: sensitivity, Monte Carlo, tax benefits, property comparison."""

import math
import random

from ._common import calculate_mortgage_payment, calculate_irr, calculate_npv, round2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get(d: dict, key: str, default=None):
    """Safely get a value from a dict with a default."""
    return d.get(key, default) if d else default


def _remaining_balance(principal: float, monthly_rate: float, num_payments: int, payments_made: int) -> float:
    """Calculate remaining loan balance after *payments_made* payments."""
    if monthly_rate == 0:
        return principal - (principal / num_payments) * payments_made
    return principal * ((1 + monthly_rate) ** num_payments - (1 + monthly_rate) ** payments_made) / (
        (1 + monthly_rate) ** num_payments - 1
    )


def _scenario_metrics(scenario: dict, discount_rate: float = 10) -> dict:
    """Calculate key metrics for a single investment scenario."""
    purchase_price = scenario.get("purchase_price", 0)
    down_payment_pct = scenario.get("down_payment_percent", 20)
    annual_rental_income = scenario.get("annual_rental_income", 0)
    annual_expenses = scenario.get("annual_expenses", 0)
    vacancy_rate = scenario.get("vacancy_rate", 5)
    interest_rate = scenario.get("interest_rate", 7)
    loan_term_years = scenario.get("loan_term_years", 30)
    appreciation_rate = scenario.get("appreciation_rate", 3)
    holding_period = scenario.get("holding_period_years", 5)

    down_payment = purchase_price * (down_payment_pct / 100)
    loan_amount = purchase_price - down_payment
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term_years * 12
    monthly_mortgage = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
    annual_mortgage = monthly_mortgage * 12

    effective_rental = annual_rental_income * (1 - vacancy_rate / 100)
    noi = effective_rental - annual_expenses
    annual_cash_flow = noi - annual_mortgage
    monthly_cash_flow = annual_cash_flow / 12

    cash_on_cash = (annual_cash_flow / down_payment * 100) if down_payment > 0 else 0

    # Build cash-flow array for IRR / NPV
    cash_flows: list[float] = [-down_payment]
    for yr in range(1, holding_period + 1):
        yr_rental = annual_rental_income * (1 - vacancy_rate / 100) * ((1 + appreciation_rate / 100) ** (yr - 1))
        yr_noi = yr_rental - annual_expenses
        yr_cf = yr_noi - annual_mortgage
        if yr == holding_period:
            future_value = purchase_price * ((1 + appreciation_rate / 100) ** holding_period)
            payments_made = holding_period * 12
            remaining = _remaining_balance(loan_amount, monthly_rate, num_payments, payments_made)
            sale_proceeds = future_value - remaining
            yr_cf += sale_proceeds
        cash_flows.append(yr_cf)

    irr = calculate_irr(cash_flows) * 100
    npv = calculate_npv(cash_flows, discount_rate / 100)

    total_return = sum(cash_flows[1:]) / down_payment * 100 if down_payment > 0 else 0

    return {
        "irr": round2(irr),
        "npv": round2(npv),
        "cash_on_cash": round2(cash_on_cash),
        "total_return": round2(total_return),
        "monthly_cash_flow": round2(monthly_cash_flow),
        "annual_cash_flow": round2(annual_cash_flow),
        "noi": round2(noi),
        "down_payment": round2(down_payment),
        "cash_flows": [round2(cf) for cf in cash_flows],
    }


_VARIABLE_MAP = {
    "purchase_price": "purchase_price",
    "rental_income": "annual_rental_income",
    "expenses": "annual_expenses",
    "vacancy_rate": "vacancy_rate",
    "interest_rate": "interest_rate",
    "appreciation_rate": "appreciation_rate",
}


def _apply_variation(base: dict, variable: str, pct_change: float) -> dict:
    """Return a modified copy of *base* with *variable* changed by *pct_change* %."""
    modified = dict(base)
    key = _VARIABLE_MAP.get(variable, variable)
    original = modified.get(key, 0)
    modified[key] = original * (1 + pct_change / 100)
    return modified


# ---------------------------------------------------------------------------
# 1. analyze_sensitivity
# ---------------------------------------------------------------------------

def analyze_sensitivity(
    base_scenario: dict,
    sensitivity_variables: list[dict] | None = None,
    analysis_metrics: list[str] | None = None,
    discount_rate: float = 10,
) -> dict:
    """Perform sensitivity analysis on a real estate investment scenario."""
    # Defaults
    defaults = {
        "down_payment_percent": 20,
        "vacancy_rate": 5,
        "interest_rate": 7,
        "loan_term_years": 30,
        "appreciation_rate": 3,
        "holding_period_years": 5,
    }
    scenario = {**defaults, **base_scenario}

    if analysis_metrics is None:
        analysis_metrics = ["irr", "cash_on_cash", "total_return"]

    if sensitivity_variables is None:
        sensitivity_variables = [
            {"variable": "purchase_price", "variations": [-20, -10, 0, 10, 20]},
            {"variable": "rental_income", "variations": [-20, -10, 0, 10, 20]},
        ]
    for sv in sensitivity_variables:
        sv.setdefault("variations", [-20, -10, 0, 10, 20])

    # Base-case metrics
    base_metrics = _scenario_metrics(scenario, discount_rate)
    base_case = {k: base_metrics[k] for k in analysis_metrics if k in base_metrics}

    # One-way sensitivity
    sensitivity_analysis: list[dict] = []
    elasticities: dict[str, float] = {}
    downside_risks: dict[str, float] = {}

    for sv in sensitivity_variables:
        variable = sv["variable"]
        variations = sv["variations"]
        results: list[dict] = []
        for var in variations:
            mod_scenario = _apply_variation(scenario, variable, var)
            metrics = _scenario_metrics(mod_scenario, discount_rate)
            result_entry: dict = {"variation_percent": var}
            for m in analysis_metrics:
                if m in metrics:
                    result_entry[m] = metrics[m]
            results.append(result_entry)

        # Elasticity: % change in IRR per 1% change in variable
        positive = [r for r in results if r["variation_percent"] > 0]
        negative = [r for r in results if r["variation_percent"] < 0]
        if positive and "irr" in analysis_metrics and base_metrics["irr"] != 0:
            p = positive[0]
            elasticity = abs((p["irr"] - base_metrics["irr"]) / base_metrics["irr"]) / abs(p["variation_percent"] / 100)
            elasticities[variable] = round2(elasticity)
        if negative and "irr" in analysis_metrics:
            worst = min(negative, key=lambda r: r.get("irr", 0))
            downside_risks[variable] = round2(base_metrics["irr"] - worst.get("irr", 0))

        sensitivity_analysis.append({
            "variable": variable,
            "results": results,
        })

    # Two-way analysis
    two_way_analysis: list[dict] = []
    if len(sensitivity_variables) >= 2:
        for i in range(len(sensitivity_variables)):
            for j in range(i + 1, len(sensitivity_variables)):
                v1 = sensitivity_variables[i]
                v2 = sensitivity_variables[j]
                matrix: list[dict] = []
                for var1 in v1["variations"]:
                    for var2 in v2["variations"]:
                        mod = _apply_variation(scenario, v1["variable"], var1)
                        mod = _apply_variation(mod, v2["variable"], var2)
                        metrics = _scenario_metrics(mod, discount_rate)
                        entry = {
                            f"{v1['variable']}_variation": var1,
                            f"{v2['variable']}_variation": var2,
                        }
                        for m in analysis_metrics:
                            if m in metrics:
                                entry[m] = metrics[m]
                        matrix.append(entry)
                two_way_analysis.append({
                    "variables": [v1["variable"], v2["variable"]],
                    "results": matrix,
                })

    # Tornado diagram data
    tornado_diagram: list[dict] = []
    for sv in sensitivity_variables:
        variable = sv["variable"]
        variations = sv["variations"]
        if not variations:
            continue
        lo_var = min(variations)
        hi_var = max(variations)
        lo_metrics = _scenario_metrics(_apply_variation(scenario, variable, lo_var), discount_rate)
        hi_metrics = _scenario_metrics(_apply_variation(scenario, variable, hi_var), discount_rate)
        for m in analysis_metrics:
            if m in lo_metrics and m in hi_metrics:
                tornado_diagram.append({
                    "variable": variable,
                    "metric": m,
                    "low_value": lo_metrics[m],
                    "high_value": hi_metrics[m],
                    "base_value": base_metrics.get(m, 0),
                    "range": round2(abs(hi_metrics[m] - lo_metrics[m])),
                })
    tornado_diagram.sort(key=lambda x: x["range"], reverse=True)

    # Critical values (break-even points)
    critical_values: list[dict] = []
    for sv in sensitivity_variables:
        variable = sv["variable"]
        # Search for IRR = 0 break-even
        if "irr" in analysis_metrics:
            be = _find_break_even(scenario, variable, "irr", 0, discount_rate)
            if be is not None:
                critical_values.append({
                    "variable": variable,
                    "metric": "irr",
                    "break_even_variation": round2(be),
                    "break_even_value": round2(
                        scenario.get(_VARIABLE_MAP.get(variable, variable), 0) * (1 + be / 100)
                    ),
                })
        # Search for cash flow = 0 break-even
        if "monthly_cash_flow" in analysis_metrics or True:
            be = _find_break_even(scenario, variable, "monthly_cash_flow", 0, discount_rate)
            if be is not None:
                critical_values.append({
                    "variable": variable,
                    "metric": "monthly_cash_flow",
                    "break_even_variation": round2(be),
                    "break_even_value": round2(
                        scenario.get(_VARIABLE_MAP.get(variable, variable), 0) * (1 + be / 100)
                    ),
                })

    # Risk assessment
    avg_elasticity = sum(elasticities.values()) / len(elasticities) if elasticities else 0
    max_downside = max(downside_risks.values()) if downside_risks else 0
    risk_level = "high" if avg_elasticity > 2 or max_downside > 15 else "medium" if avg_elasticity > 1 or max_downside > 8 else "low"

    risk_assessment = {
        "overall_risk_level": risk_level,
        "elasticities": elasticities,
        "downside_risks": downside_risks,
        "most_sensitive_variable": max(elasticities, key=elasticities.get) if elasticities else None,
        "highest_downside_risk": max(downside_risks, key=downside_risks.get) if downside_risks else None,
    }

    # Recommendations
    recommendations: list[str] = []
    if risk_level == "high":
        recommendations.append("High sensitivity detected. Consider hedging strategies or renegotiating terms.")
    if risk_assessment.get("most_sensitive_variable"):
        recommendations.append(
            f"The investment is most sensitive to {risk_assessment['most_sensitive_variable']}. "
            "Focus due diligence on this variable."
        )
    if base_metrics.get("monthly_cash_flow", 0) < 200:
        recommendations.append("Monthly cash flow is thin. Build adequate reserves.")
    if base_metrics.get("irr", 0) < 10:
        recommendations.append("Base-case IRR is below 10%. Ensure downside scenarios are acceptable.")
    if not recommendations:
        recommendations.append("The investment shows solid fundamentals across sensitivity scenarios.")

    return {
        "base_case": base_case,
        "sensitivity_analysis": sensitivity_analysis,
        "two_way_analysis": two_way_analysis,
        "tornado_diagram": tornado_diagram,
        "critical_values": critical_values,
        "risk_assessment": risk_assessment,
        "recommendations": recommendations,
    }


def _find_break_even(
    scenario: dict,
    variable: str,
    metric: str,
    target: float,
    discount_rate: float,
    lo: float = -80,
    hi: float = 200,
) -> float | None:
    """Binary search for the variation % that makes *metric* equal *target*."""
    lo_val = _scenario_metrics(_apply_variation(scenario, variable, lo), discount_rate).get(metric, 0)
    hi_val = _scenario_metrics(_apply_variation(scenario, variable, hi), discount_rate).get(metric, 0)
    if (lo_val - target) * (hi_val - target) > 0:
        return None
    for _ in range(60):
        mid = (lo + hi) / 2
        mid_val = _scenario_metrics(_apply_variation(scenario, variable, mid), discount_rate).get(metric, 0)
        if abs(mid_val - target) < 0.01:
            return mid
        if (lo_val - target) * (mid_val - target) < 0:
            hi = mid
            hi_val = mid_val
        else:
            lo = mid
            lo_val = mid_val
    return (lo + hi) / 2


# ---------------------------------------------------------------------------
# 2. run_monte_carlo
# ---------------------------------------------------------------------------

def _sample_distribution(dist: dict, rng: random.Random | None = None) -> float:
    """Sample a single value from a distribution specification."""
    dtype = dist.get("type", "normal")
    r = rng or random

    if dtype == "normal":
        mean = dist.get("mean", 0)
        std = dist.get("std_dev", 0)
        val = r.gauss(mean, std)
        # Clamp to min/max if provided
        if "min" in dist:
            val = max(val, dist["min"])
        if "max" in dist:
            val = min(val, dist["max"])
        return val
    elif dtype == "uniform":
        return r.uniform(dist.get("min", 0), dist.get("max", 0))
    elif dtype == "triangular":
        return r.triangular(dist.get("min", 0), dist.get("max", 0), dist.get("mode", None))
    return dist.get("mean", 0)


def _mc_scenario_result(params: dict, samples: dict) -> dict:
    """Calculate metrics for a single Monte Carlo simulation run."""
    purchase_price = params.get("purchase_price", 0)
    dp_pct = params.get("down_payment_percent", 20)
    closing_costs = params.get("closing_costs", 0)
    holding_period = params.get("holding_period_years", 5)
    interest_rate = params.get("loan_interest_rate", 7)
    loan_term = params.get("loan_term_years", 30)

    down_payment = purchase_price * (dp_pct / 100)
    total_initial = down_payment + closing_costs
    loan_amount = purchase_price - down_payment
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term * 12
    monthly_mortgage = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)
    annual_mortgage = monthly_mortgage * 12

    rental_income = samples.get("rental_income", 0)
    vacancy = samples.get("vacancy_rate", 5)
    opex = samples.get("operating_expenses", 0)
    appreciation = samples.get("appreciation_rate", 3)
    exit_cap = samples.get("exit_cap_rate", 6)

    effective_income = rental_income * 12 * (1 - vacancy / 100)
    noi = effective_income - opex
    annual_cf = noi - annual_mortgage
    monthly_cf = annual_cf / 12

    coc = (annual_cf / total_initial * 100) if total_initial > 0 else 0

    # Cash flows for IRR
    cash_flows: list[float] = [-total_initial]
    for yr in range(1, holding_period + 1):
        yr_income = rental_income * 12 * (1 - vacancy / 100) * ((1 + appreciation / 100) ** (yr - 1))
        yr_noi = yr_income - opex
        yr_cf = yr_noi - annual_mortgage
        if yr == holding_period:
            # Exit based on cap rate or appreciation
            future_noi = yr_noi * (1 + appreciation / 100)
            if exit_cap > 0:
                sale_price = future_noi / (exit_cap / 100)
            else:
                sale_price = purchase_price * ((1 + appreciation / 100) ** holding_period)
            remaining = _remaining_balance(loan_amount, monthly_rate, num_payments, holding_period * 12)
            yr_cf += sale_price - remaining
        cash_flows.append(yr_cf)

    irr = calculate_irr(cash_flows) * 100
    total_return = sum(cash_flows[1:]) / total_initial * 100 if total_initial > 0 else 0
    equity_multiple = (total_initial + sum(cash_flows[1:])) / total_initial if total_initial > 0 else 0

    return {
        "irr": irr,
        "total_return": total_return,
        "cash_on_cash": coc,
        "equity_multiple": equity_multiple,
        "monthly_cash_flow": monthly_cf,
        "annual_cash_flow": annual_cf,
        "noi": noi,
    }


def run_monte_carlo(
    investment_parameters: dict,
    variable_distributions: dict,
    simulation_settings: dict | None = None,
    target_metrics: dict | None = None,
) -> dict:
    """Run Monte Carlo simulation on a real estate investment."""
    settings = simulation_settings or {}
    num_sims = settings.get("num_simulations", 10000)
    seed = settings.get("random_seed", None)
    confidence_levels = settings.get("confidence_levels", [5, 10, 25, 50, 75, 90, 95])

    targets = target_metrics or {}
    min_irr = targets.get("minimum_irr", 10)
    min_cf = targets.get("minimum_cash_flow", 0)
    max_loss = targets.get("maximum_loss", 0)

    rng = random.Random(seed) if seed is not None else random.Random()

    # Run simulations
    all_results: list[dict] = []
    all_samples: list[dict] = []

    for _ in range(num_sims):
        samples: dict = {}
        for var_name, dist in variable_distributions.items():
            samples[var_name] = _sample_distribution(dist, rng)
        result = _mc_scenario_result(investment_parameters, samples)
        all_results.append(result)
        all_samples.append(samples)

    # Collect metric arrays
    metric_keys = ["irr", "total_return", "cash_on_cash", "equity_multiple", "monthly_cash_flow"]
    metric_arrays: dict[str, list[float]] = {k: [r[k] for r in all_results] for k in metric_keys}

    # Summary statistics
    summary_statistics: dict = {}
    for key, values in metric_arrays.items():
        sorted_vals = sorted(values)
        n = len(values)
        mean = sum(values) / n
        median = sorted_vals[n // 2] if n % 2 else (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2
        variance = sum((v - mean) ** 2 for v in values) / n
        std_dev = math.sqrt(variance)
        skewness = (sum((v - mean) ** 3 for v in values) / n) / (std_dev ** 3) if std_dev > 0 else 0
        kurtosis = (sum((v - mean) ** 4 for v in values) / n) / (std_dev ** 4) - 3 if std_dev > 0 else 0

        summary_statistics[key] = {
            "mean": round2(mean),
            "median": round2(median),
            "std_dev": round2(std_dev),
            "min": round2(sorted_vals[0]),
            "max": round2(sorted_vals[-1]),
            "skewness": round2(skewness),
            "kurtosis": round2(kurtosis),
        }

    # Distributions (histograms)
    distributions: dict = {}
    for key, values in metric_arrays.items():
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        num_bins = 20
        lo = sorted_vals[0]
        hi = sorted_vals[-1]
        bin_width = (hi - lo) / num_bins if hi != lo else 1
        bins: list[dict] = []
        for b in range(num_bins):
            bin_lo = lo + b * bin_width
            bin_hi = bin_lo + bin_width
            count = sum(1 for v in values if bin_lo <= v < bin_hi) if b < num_bins - 1 else sum(1 for v in values if bin_lo <= v <= bin_hi)
            bins.append({
                "range_start": round2(bin_lo),
                "range_end": round2(bin_hi),
                "count": count,
                "frequency": round2(count / n * 100),
            })
        percentiles = {}
        for p in confidence_levels:
            idx = int(n * p / 100)
            idx = min(idx, n - 1)
            percentiles[f"p{p}"] = round2(sorted_vals[idx])
        distributions[key] = {"histogram": bins, "percentiles": percentiles}

    # Risk metrics
    irr_sorted = sorted(metric_arrays["irr"])
    cf_sorted = sorted(metric_arrays["monthly_cash_flow"])
    n = len(irr_sorted)

    var_5_idx = int(n * 0.05)
    var_5_irr = irr_sorted[var_5_idx]
    cvar_5_irr = sum(irr_sorted[:var_5_idx + 1]) / (var_5_idx + 1) if var_5_idx >= 0 else 0

    prob_loss = sum(1 for v in metric_arrays["irr"] if v < 0) / n * 100
    prob_below_target_irr = sum(1 for v in metric_arrays["irr"] if v < min_irr) / n * 100
    prob_negative_cf = sum(1 for v in metric_arrays["monthly_cash_flow"] if v < min_cf) / n * 100

    mean_irr = summary_statistics["irr"]["mean"]
    std_irr = summary_statistics["irr"]["std_dev"]
    downside_values = [v for v in metric_arrays["irr"] if v < mean_irr]
    downside_dev = math.sqrt(sum((v - mean_irr) ** 2 for v in downside_values) / n) if downside_values else 0
    risk_free_rate = 4.0
    sharpe_ratio = (mean_irr - risk_free_rate) / std_irr if std_irr > 0 else 0
    sortino_ratio = (mean_irr - risk_free_rate) / downside_dev if downside_dev > 0 else 0

    risk_metrics = {
        "value_at_risk": {
            "var_5_percent": round2(var_5_irr),
            "cvar_5_percent": round2(cvar_5_irr),
        },
        "probability_of_loss": round2(prob_loss),
        "probability_below_target_irr": round2(prob_below_target_irr),
        "probability_negative_cash_flow": round2(prob_negative_cf),
        "downside_deviation": round2(downside_dev),
        "sharpe_ratio": round2(sharpe_ratio),
        "sortino_ratio": round2(sortino_ratio),
    }

    # Probability analysis
    probability_analysis = {
        "irr_above_target": round2(100 - prob_below_target_irr),
        "positive_cash_flow": round2(100 - prob_negative_cf),
        "loss_probability": round2(prob_loss),
        "target_metrics": {
            "minimum_irr": min_irr,
            "minimum_cash_flow": min_cf,
            "maximum_loss": max_loss,
        },
    }

    # Correlations (Pearson)
    correlations: dict = {}
    sample_keys = list(variable_distributions.keys())
    sample_arrays: dict[str, list[float]] = {k: [s[k] for s in all_samples] for k in sample_keys}

    for sk in sample_keys:
        svals = sample_arrays[sk]
        corr_entry: dict = {}
        s_mean = sum(svals) / n
        s_std = math.sqrt(sum((v - s_mean) ** 2 for v in svals) / n)
        for mk in metric_keys:
            mvals = metric_arrays[mk]
            m_mean = sum(mvals) / n
            m_std = math.sqrt(sum((v - m_mean) ** 2 for v in mvals) / n)
            if s_std > 0 and m_std > 0:
                covariance = sum((svals[i] - s_mean) * (mvals[i] - m_mean) for i in range(n)) / n
                corr_entry[mk] = round2(covariance / (s_std * m_std))
            else:
                corr_entry[mk] = 0.0
        correlations[sk] = corr_entry

    # Key scenarios
    irr_values = metric_arrays["irr"]
    best_idx = irr_values.index(max(irr_values))
    worst_idx = irr_values.index(min(irr_values))
    median_irr = summary_statistics["irr"]["median"]
    median_idx = min(range(n), key=lambda i: abs(irr_values[i] - median_irr))

    scenario_analysis = {
        "best_case": {
            "inputs": all_samples[best_idx],
            "results": {k: round2(all_results[best_idx][k]) for k in metric_keys},
        },
        "worst_case": {
            "inputs": all_samples[worst_idx],
            "results": {k: round2(all_results[worst_idx][k]) for k in metric_keys},
        },
        "median_case": {
            "inputs": all_samples[median_idx],
            "results": {k: round2(all_results[median_idx][k]) for k in metric_keys},
        },
    }

    # Confidence intervals
    confidence_intervals: dict = {}
    for key in metric_keys:
        sorted_vals = sorted(metric_arrays[key])
        intervals: dict = {}
        for cl in confidence_levels:
            lo_idx = int(n * (50 - cl / 2) / 100)
            hi_idx = int(n * (50 + cl / 2) / 100)
            lo_idx = max(0, min(lo_idx, n - 1))
            hi_idx = max(0, min(hi_idx, n - 1))
            intervals[f"{cl}%"] = {
                "lower": round2(sorted_vals[lo_idx]),
                "upper": round2(sorted_vals[hi_idx]),
            }
        confidence_intervals[key] = intervals

    # Recommendations
    recommendations: list[str] = []
    if prob_loss > 20:
        recommendations.append("High probability of loss. Consider reducing purchase price or increasing income.")
    if prob_below_target_irr > 40:
        recommendations.append(f"Less than 60% chance of achieving {min_irr}% IRR target. Review assumptions.")
    if prob_negative_cf > 30:
        recommendations.append("Significant risk of negative cash flow. Ensure adequate reserves.")
    if sharpe_ratio < 0.5:
        recommendations.append("Risk-adjusted returns are low. Consider alternative investments.")
    if sharpe_ratio >= 1.0:
        recommendations.append("Strong risk-adjusted returns. Investment shows favorable risk-reward profile.")
    if not recommendations:
        recommendations.append("Simulation results indicate a well-balanced investment opportunity.")

    return {
        "summary_statistics": summary_statistics,
        "distributions": distributions,
        "risk_metrics": risk_metrics,
        "probability_analysis": probability_analysis,
        "correlations": correlations,
        "scenario_analysis": scenario_analysis,
        "confidence_intervals": confidence_intervals,
        "recommendations": recommendations,
        "simulation_metadata": {
            "num_simulations": num_sims,
            "random_seed": seed,
            "confidence_levels": confidence_levels,
            "variables_simulated": sample_keys,
        },
    }


# ---------------------------------------------------------------------------
# 3. calculate_tax_benefits
# ---------------------------------------------------------------------------

_FEDERAL_BRACKETS_SINGLE = [
    (11600, 0.10),
    (47150, 0.12),
    (100525, 0.22),
    (191950, 0.24),
    (243725, 0.32),
    (609350, 0.35),
    (float("inf"), 0.37),
]

_DEPRECIATION_LIVES = {
    "residential_rental": 27.5,
    "commercial": 39.0,
}


def _federal_tax(taxable_income: float) -> float:
    """Calculate federal income tax for single filer using 2024 brackets."""
    if taxable_income <= 0:
        return 0.0
    tax = 0.0
    prev = 0.0
    for threshold, rate in _FEDERAL_BRACKETS_SINGLE:
        bracket_income = min(taxable_income, threshold) - prev
        if bracket_income <= 0:
            break
        tax += bracket_income * rate
        prev = threshold
    return tax


def _marginal_rate(taxable_income: float) -> float:
    """Return the marginal federal tax rate for a given taxable income."""
    for threshold, rate in _FEDERAL_BRACKETS_SINGLE:
        if taxable_income <= threshold:
            return rate
    return 0.37


def _state_tax_rate(state: str) -> float:
    """Return a simplified effective state income tax rate."""
    rates: dict[str, float] = {
        "CA": 9.3, "NY": 6.85, "NJ": 6.37, "IL": 4.95, "TX": 0, "FL": 0,
        "WA": 0, "NV": 0, "OH": 3.99, "PA": 3.07, "MA": 5.0, "CT": 6.99,
        "OR": 9.9, "MN": 9.85, "HI": 11.0, "CO": 4.4, "AZ": 2.5,
    }
    return rates.get(state.upper(), 5.0)


def calculate_tax_benefits(
    property_details: dict,
    income_expenses: dict,
    loan_details: dict,
    taxpayer_info: dict,
    cost_segregation_breakdown: dict | None = None,
    analysis_options: dict | None = None,
) -> dict:
    """Calculate comprehensive tax benefits for a rental property."""
    # Extract parameters
    purchase_price = property_details.get("purchase_price", 0)
    land_value = property_details.get("land_value", 0)
    closing_costs = property_details.get("closing_costs", 0)
    property_type = property_details.get("property_type", "residential_rental")
    cost_seg_enabled = property_details.get("cost_segregation", False)

    annual_rental_income = income_expenses.get("annual_rental_income", 0)
    operating_expenses = income_expenses.get("operating_expenses", {})
    total_opex = sum(operating_expenses.values()) if operating_expenses else 0

    loan_amount = loan_details.get("loan_amount", 0)
    interest_rate = loan_details.get("interest_rate", 0)
    loan_term = loan_details.get("loan_term_years", 30)
    points_paid = loan_details.get("points_paid", 0)

    filing_status = taxpayer_info.get("filing_status", "single")
    other_income = taxpayer_info.get("other_income", 0)
    state = taxpayer_info.get("state", "CA")
    re_professional = taxpayer_info.get("real_estate_professional", False)
    active_participation = taxpayer_info.get("active_participation", True)

    cs_breakdown = cost_segregation_breakdown or {}
    personal_property_5yr = cs_breakdown.get("personal_property_5yr", 0)
    land_improvements_15yr = cs_breakdown.get("land_improvements_15yr", 0)
    bonus_eligible = cs_breakdown.get("bonus_depreciation_eligible", True)

    options = analysis_options or {}
    projection_years = options.get("projection_years", 10)
    include_state_tax = options.get("include_state_tax", True)
    bonus_rate = options.get("bonus_depreciation_rate", 60)

    # Depreciable basis
    depreciable_basis = purchase_price - land_value + closing_costs * 0.8
    useful_life = _DEPRECIATION_LIVES.get(property_type, 27.5)

    # Build depreciation schedule
    depreciation_schedule: list[dict] = []

    # Standard straight-line for building
    if cost_seg_enabled:
        building_basis = depreciable_basis - personal_property_5yr - land_improvements_15yr
    else:
        building_basis = depreciable_basis
        personal_property_5yr = 0
        land_improvements_15yr = 0

    annual_building_dep = building_basis / useful_life if useful_life > 0 else 0

    # Cost segregation components
    bonus_amount = 0.0
    if cost_seg_enabled and bonus_eligible:
        bonus_amount = (personal_property_5yr + land_improvements_15yr) * (bonus_rate / 100)

    remaining_5yr = personal_property_5yr - (personal_property_5yr * (bonus_rate / 100) if cost_seg_enabled and bonus_eligible else 0)
    remaining_15yr = land_improvements_15yr - (land_improvements_15yr * (bonus_rate / 100) if cost_seg_enabled and bonus_eligible else 0)

    annual_5yr_dep = remaining_5yr / 5 if remaining_5yr > 0 else 0
    annual_15yr_dep = remaining_15yr / 15 if remaining_15yr > 0 else 0

    for yr in range(1, projection_years + 1):
        building = annual_building_dep if yr <= useful_life else 0
        five_yr = annual_5yr_dep if yr <= 5 else 0
        fifteen_yr = annual_15yr_dep if yr <= 15 else 0
        bonus = bonus_amount if yr == 1 else 0

        total_dep = building + five_yr + fifteen_yr + bonus

        depreciation_schedule.append({
            "year": yr,
            "building_depreciation": round2(building),
            "personal_property_5yr": round2(five_yr),
            "land_improvements_15yr": round2(fifteen_yr),
            "bonus_depreciation": round2(bonus),
            "total_depreciation": round2(total_dep),
        })

    # Mortgage interest schedule
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term * 12
    monthly_payment = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)

    interest_schedule: list[dict] = []
    balance = loan_amount
    for yr in range(1, projection_years + 1):
        year_interest = 0.0
        year_principal = 0.0
        for _ in range(12):
            if balance <= 0:
                break
            month_interest = balance * monthly_rate
            month_principal = monthly_payment - month_interest
            if month_principal > balance:
                month_principal = balance
            year_interest += month_interest
            year_principal += month_principal
            balance -= month_principal
        interest_schedule.append({
            "year": yr,
            "interest_paid": round2(year_interest),
            "principal_paid": round2(year_principal),
            "remaining_balance": round2(max(balance, 0)),
        })

    # Annual tax analysis
    annual_tax_analysis: list[dict] = []
    total_tax_savings = 0.0
    total_depreciation = 0.0
    cumulative_passive_losses = 0.0
    passive_loss_carryforwards: list[dict] = []
    state_rate = _state_tax_rate(state) / 100

    for yr in range(1, projection_years + 1):
        dep = depreciation_schedule[yr - 1]["total_depreciation"]
        interest = interest_schedule[yr - 1]["interest_paid"]
        points_deduction = points_paid / loan_term if yr <= loan_term else 0

        taxable_rental = annual_rental_income - total_opex - dep - interest - points_deduction
        total_depreciation += dep

        # Passive activity loss rules
        rental_loss = min(taxable_rental, 0)
        allowed_loss = rental_loss

        if not re_professional and rental_loss < 0:
            agi = other_income + max(taxable_rental, 0)
            if active_participation:
                if agi <= 100000:
                    allowance = 25000
                elif agi < 150000:
                    allowance = 25000 - (agi - 100000) * 0.5
                else:
                    allowance = 0
                allowed_loss = max(rental_loss, -allowance)
            else:
                allowed_loss = 0

            suspended_loss = rental_loss - allowed_loss
            cumulative_passive_losses += abs(suspended_loss)
        else:
            suspended_loss = 0.0

        # Tax calculations
        total_taxable = other_income + allowed_loss
        tax_with_property = _federal_tax(total_taxable)
        tax_without = _federal_tax(other_income)
        federal_savings = tax_without - tax_with_property

        state_savings = 0.0
        if include_state_tax:
            state_savings = abs(allowed_loss) * state_rate if allowed_loss < 0 else 0

        total_savings = federal_savings + state_savings
        total_tax_savings += total_savings

        effective_rate = (tax_with_property / total_taxable * 100) if total_taxable > 0 else 0

        annual_tax_analysis.append({
            "year": yr,
            "rental_income": round2(annual_rental_income),
            "operating_expenses": round2(total_opex),
            "depreciation": round2(dep),
            "mortgage_interest": round2(interest),
            "taxable_rental_income": round2(taxable_rental),
            "allowed_loss": round2(allowed_loss),
            "suspended_loss": round2(suspended_loss),
            "federal_tax_savings": round2(federal_savings),
            "state_tax_savings": round2(state_savings),
            "total_tax_savings": round2(total_savings),
            "effective_tax_rate": round2(effective_rate),
        })

        passive_loss_carryforwards.append({
            "year": yr,
            "suspended_loss": round2(suspended_loss),
            "cumulative_suspended": round2(cumulative_passive_losses),
        })

    # Summary metrics
    avg_annual_savings = total_tax_savings / projection_years if projection_years > 0 else 0
    marginal = _marginal_rate(other_income)

    summary_metrics = {
        "total_tax_savings": round2(total_tax_savings),
        "average_annual_savings": round2(avg_annual_savings),
        "total_depreciation": round2(total_depreciation),
        "depreciable_basis": round2(depreciable_basis),
        "useful_life_years": useful_life,
        "marginal_tax_rate": round2(marginal * 100),
        "points_deduction_annual": round2(points_paid / loan_term) if loan_term > 0 else 0,
    }

    # Passive loss analysis
    passive_loss_analysis = {
        "is_real_estate_professional": re_professional,
        "active_participation": active_participation,
        "agi_for_phaseout": other_income,
        "max_allowance": 25000 if active_participation and not re_professional else "unlimited",
        "phaseout_start": 100000,
        "phaseout_end": 150000,
        "cumulative_suspended_losses": round2(cumulative_passive_losses),
        "annual_details": passive_loss_carryforwards,
    }

    # Cost segregation analysis
    if cost_seg_enabled:
        standard_yr1 = building_basis / useful_life if useful_life > 0 else 0
        cs_yr1 = depreciation_schedule[0]["total_depreciation"]
        cs_benefit = (cs_yr1 - standard_yr1) * marginal
        cost_segregation_analysis = {
            "enabled": True,
            "personal_property_5yr": round2(personal_property_5yr),
            "land_improvements_15yr": round2(land_improvements_15yr),
            "bonus_depreciation_rate": bonus_rate,
            "bonus_depreciation_amount": round2(bonus_amount),
            "year_1_standard_depreciation": round2(standard_yr1),
            "year_1_with_cost_segregation": round2(cs_yr1),
            "additional_year_1_deduction": round2(cs_yr1 - standard_yr1),
            "year_1_tax_benefit": round2(cs_benefit),
        }
    else:
        cost_segregation_analysis = {
            "enabled": False,
            "recommendation": "Consider a cost segregation study for properties over $500,000.",
        }

    # Tax strategies
    tax_strategies: list[dict] = []
    tax_strategies.append({
        "strategy": "Depreciation",
        "description": f"Annual depreciation deduction of ${annual_building_dep:,.0f} over {useful_life} years.",
        "annual_benefit": round2(annual_building_dep * marginal),
    })
    if not cost_seg_enabled and purchase_price > 500000:
        tax_strategies.append({
            "strategy": "Cost Segregation Study",
            "description": "Accelerate depreciation by reclassifying building components.",
            "potential_benefit": "Significant first-year tax savings through bonus depreciation.",
        })
    if not re_professional:
        tax_strategies.append({
            "strategy": "Real Estate Professional Status",
            "description": "Qualify to deduct all rental losses against ordinary income.",
            "requirement": "750+ hours in real estate activities, more than any other profession.",
        })
    tax_strategies.append({
        "strategy": "1031 Exchange",
        "description": "Defer capital gains taxes by exchanging into like-kind property.",
        "potential_benefit": "Full deferral of depreciation recapture and capital gains.",
    })

    # Effective tax rates
    yr1_analysis = annual_tax_analysis[0] if annual_tax_analysis else {}
    effective_tax_rates = {
        "marginal_federal_rate": round2(marginal * 100),
        "effective_federal_rate": yr1_analysis.get("effective_tax_rate", 0),
        "state_rate": round2(state_rate * 100),
        "combined_marginal_rate": round2((marginal + state_rate) * 100),
    }

    # Recommendations
    recommendations: list[str] = []
    if total_tax_savings > 0:
        recommendations.append(
            f"Total projected tax savings of ${total_tax_savings:,.0f} over {projection_years} years."
        )
    if cumulative_passive_losses > 0:
        recommendations.append(
            f"${cumulative_passive_losses:,.0f} in suspended passive losses. "
            "These can be used when the property is sold or against future passive income."
        )
    if not cost_seg_enabled and purchase_price > 500000:
        recommendations.append(
            "A cost segregation study could significantly accelerate depreciation deductions."
        )
    if not re_professional and other_income > 150000:
        recommendations.append(
            "High AGI limits passive loss deductions. Consider qualifying as a real estate professional."
        )
    if not recommendations:
        recommendations.append("Review with a tax professional to optimize your real estate tax strategy.")

    return {
        "depreciation_analysis": {
            "depreciable_basis": round2(depreciable_basis),
            "useful_life_years": useful_life,
            "annual_depreciation": round2(annual_building_dep),
            "schedule": depreciation_schedule,
        },
        "annual_tax_analysis": annual_tax_analysis,
        "summary_metrics": summary_metrics,
        "passive_loss_analysis": passive_loss_analysis,
        "cost_segregation_analysis": cost_segregation_analysis,
        "tax_strategies": tax_strategies,
        "effective_tax_rates": effective_tax_rates,
        "recommendations": recommendations,
    }


# ---------------------------------------------------------------------------
# 4. compare_properties
# ---------------------------------------------------------------------------

def _analyze_single_property(
    prop: dict,
    loan_terms: dict,
    holding_period: int,
) -> dict:
    """Analyze a single property for the comparison tool."""
    purchase_price = prop.get("purchase_price", 0)
    dp_pct = prop.get("down_payment_percent", 20)
    closing_costs = prop.get("closing_costs", 0)
    units = prop.get("units", 1)
    sqft = prop.get("square_feet", 0)
    year_built = prop.get("year_built", 0)
    monthly_rent = prop.get("monthly_rent", 0)
    monthly_expenses = prop.get("monthly_expenses", {})
    vacancy_rate = prop.get("vacancy_rate", 5)
    appreciation_rate = prop.get("appreciation_rate", 3)
    location_score = prop.get("location_score", {})

    interest_rate = loan_terms.get("interest_rate", 7)
    loan_term = loan_terms.get("loan_term_years", 30)

    total_monthly_expenses = sum(monthly_expenses.values()) if monthly_expenses else 0
    annual_expenses = total_monthly_expenses * 12

    down_payment = purchase_price * (dp_pct / 100)
    total_investment = down_payment + closing_costs
    loan_amount = purchase_price - down_payment
    monthly_rate = interest_rate / 100 / 12
    num_payments = loan_term * 12
    monthly_mortgage = calculate_mortgage_payment(loan_amount, monthly_rate, num_payments)

    effective_rent = monthly_rent * (1 - vacancy_rate / 100)
    monthly_cf = effective_rent - total_monthly_expenses - monthly_mortgage
    annual_cf = monthly_cf * 12

    annual_rental = monthly_rent * 12
    effective_annual = effective_rent * 12
    noi = effective_annual - annual_expenses

    # Return metrics
    cap_rate = (noi / purchase_price * 100) if purchase_price > 0 else 0
    coc = (annual_cf / total_investment * 100) if total_investment > 0 else 0
    grm = purchase_price / annual_rental if annual_rental > 0 else 0
    roi = (annual_cf / total_investment * 100) if total_investment > 0 else 0

    # Build cash flows for IRR
    cash_flows: list[float] = [-total_investment]
    for yr in range(1, holding_period + 1):
        yr_rental = effective_annual * ((1 + appreciation_rate / 100) ** (yr - 1))
        yr_cf = yr_rental - annual_expenses - monthly_mortgage * 12
        if yr == holding_period:
            future_val = purchase_price * ((1 + appreciation_rate / 100) ** holding_period)
            remaining = _remaining_balance(loan_amount, monthly_rate, num_payments, holding_period * 12)
            yr_cf += future_val - remaining
        cash_flows.append(yr_cf)

    irr = calculate_irr(cash_flows) * 100

    # Valuation metrics
    price_per_sqft = purchase_price / sqft if sqft > 0 else 0
    price_per_unit = purchase_price / units if units > 0 else 0
    one_pct_rule = (monthly_rent / purchase_price * 100) if purchase_price > 0 else 0
    meets_one_pct = one_pct_rule >= 1.0

    # Future projections
    projections: list[dict] = []
    for yr in range(1, holding_period + 1):
        future_value = purchase_price * ((1 + appreciation_rate / 100) ** yr)
        remaining = _remaining_balance(loan_amount, monthly_rate, num_payments, yr * 12)
        equity = future_value - remaining
        yr_rent = monthly_rent * ((1 + appreciation_rate / 100) ** yr)
        projections.append({
            "year": yr,
            "property_value": round2(future_value),
            "remaining_balance": round2(remaining),
            "equity": round2(equity),
            "monthly_rent": round2(yr_rent),
        })

    # Location analysis
    loc_school = location_score.get("schools", 5)
    loc_crime = location_score.get("crime", 5)
    loc_transit = location_score.get("transit", 5)
    loc_employment = location_score.get("employment", 5)
    loc_amenities = location_score.get("amenities", 5)
    loc_avg = (loc_school + loc_crime + loc_transit + loc_employment + loc_amenities) / 5

    location_analysis = {
        "scores": {
            "schools": loc_school,
            "crime": loc_crime,
            "transit": loc_transit,
            "employment": loc_employment,
            "amenities": loc_amenities,
        },
        "overall_score": round2(loc_avg),
    }

    # Risk metrics
    dscr = noi / (monthly_mortgage * 12) if monthly_mortgage > 0 else float("inf")
    expense_ratio = annual_expenses / effective_annual * 100 if effective_annual > 0 else 0
    break_even_occupancy = (annual_expenses + monthly_mortgage * 12) / annual_rental * 100 if annual_rental > 0 else 100

    risk_metrics = {
        "debt_service_coverage_ratio": round2(dscr),
        "expense_ratio": round2(expense_ratio),
        "break_even_occupancy": round2(break_even_occupancy),
        "cash_flow_cushion": round2(monthly_cf),
    }

    return {
        "name": prop.get("name", "Unknown"),
        "purchase_price": purchase_price,
        "cash_flow": {
            "monthly_rent": monthly_rent,
            "effective_rent": round2(effective_rent),
            "monthly_expenses": round2(total_monthly_expenses),
            "monthly_mortgage": round2(monthly_mortgage),
            "monthly_cash_flow": round2(monthly_cf),
            "annual_cash_flow": round2(annual_cf),
        },
        "return_metrics": {
            "cap_rate": round2(cap_rate),
            "cash_on_cash": round2(coc),
            "grm": round2(grm),
            "roi": round2(roi),
            "irr": round2(irr),
        },
        "valuation_metrics": {
            "price_per_sqft": round2(price_per_sqft),
            "price_per_unit": round2(price_per_unit),
            "one_percent_rule": round2(one_pct_rule),
            "meets_one_percent": meets_one_pct,
        },
        "future_projections": projections,
        "location_analysis": location_analysis,
        "risk_metrics": risk_metrics,
        "total_investment": round2(total_investment),
        "down_payment": round2(down_payment),
        "loan_amount": round2(loan_amount),
    }


def compare_properties(
    properties: list[dict],
    loan_terms: dict | None = None,
    comparison_criteria: dict | None = None,
) -> dict:
    """Compare multiple properties side-by-side with scoring and ranking."""
    loan = loan_terms or {}
    loan.setdefault("interest_rate", 7)
    loan.setdefault("loan_term_years", 30)

    criteria = comparison_criteria or {}
    holding_period = criteria.get("holding_period_years", 5)
    target_cf = criteria.get("target_cash_flow", 200)
    target_cap = criteria.get("target_cap_rate", 6)
    weights = criteria.get("weights", {
        "cash_flow": 25,
        "appreciation": 25,
        "cap_rate": 25,
        "location": 25,
    })

    # Analyze each property
    property_analyses: list[dict] = []
    for prop in properties:
        analysis = _analyze_single_property(prop, loan, holding_period)
        property_analyses.append(analysis)

    # Comparison matrix
    metrics_to_compare = ["cap_rate", "cash_on_cash", "grm", "roi", "irr"]
    comparison_matrix: dict = {}
    for metric in metrics_to_compare:
        comparison_matrix[metric] = {
            a["name"]: a["return_metrics"].get(metric, 0) for a in property_analyses
        }
    comparison_matrix["monthly_cash_flow"] = {
        a["name"]: a["cash_flow"]["monthly_cash_flow"] for a in property_analyses
    }
    comparison_matrix["price_per_sqft"] = {
        a["name"]: a["valuation_metrics"]["price_per_sqft"] for a in property_analyses
    }

    # Score and rank
    def _normalize(values: list[float], higher_is_better: bool = True) -> list[float]:
        if not values:
            return []
        lo, hi = min(values), max(values)
        if hi == lo:
            return [50.0] * len(values)
        if higher_is_better:
            return [(v - lo) / (hi - lo) * 100 for v in values]
        return [(hi - v) / (hi - lo) * 100 for v in values]

    n = len(property_analyses)
    cf_scores = _normalize([a["cash_flow"]["monthly_cash_flow"] for a in property_analyses], True)
    cap_scores = _normalize([a["return_metrics"]["cap_rate"] for a in property_analyses], True)
    loc_scores = _normalize([a["location_analysis"]["overall_score"] for a in property_analyses], True)

    # Appreciation score based on future equity growth
    appreciation_scores: list[float] = []
    for a in property_analyses:
        projs = a.get("future_projections", [])
        if projs:
            equity_growth = projs[-1]["equity"] - a["down_payment"]
            appreciation_scores.append(equity_growth)
        else:
            appreciation_scores.append(0)
    app_scores = _normalize(appreciation_scores, True)

    w_cf = weights.get("cash_flow", 25) / 100
    w_app = weights.get("appreciation", 25) / 100
    w_cap = weights.get("cap_rate", 25) / 100
    w_loc = weights.get("location", 25) / 100

    total_scores: list[dict] = []
    for i, a in enumerate(property_analyses):
        score = (
            cf_scores[i] * w_cf
            + app_scores[i] * w_app
            + cap_scores[i] * w_cap
            + loc_scores[i] * w_loc
        )
        total_scores.append({
            "name": a["name"],
            "total_score": round2(score),
            "component_scores": {
                "cash_flow": round2(cf_scores[i]),
                "appreciation": round2(app_scores[i]),
                "cap_rate": round2(cap_scores[i]),
                "location": round2(loc_scores[i]),
            },
        })

    total_scores.sort(key=lambda x: x["total_score"], reverse=True)
    rankings: list[dict] = []
    for rank, ts in enumerate(total_scores, 1):
        rankings.append({
            "rank": rank,
            "name": ts["name"],
            "total_score": ts["total_score"],
            "component_scores": ts["component_scores"],
        })

    # Best options by category
    best_options: dict = {}
    if property_analyses:
        best_options["best_cash_flow"] = max(property_analyses, key=lambda a: a["cash_flow"]["monthly_cash_flow"])["name"]
        best_options["best_cap_rate"] = max(property_analyses, key=lambda a: a["return_metrics"]["cap_rate"])["name"]
        best_options["best_irr"] = max(property_analyses, key=lambda a: a["return_metrics"]["irr"])["name"]
        best_options["best_location"] = max(property_analyses, key=lambda a: a["location_analysis"]["overall_score"])["name"]
        best_options["lowest_risk"] = max(property_analyses, key=lambda a: a["risk_metrics"]["debt_service_coverage_ratio"] if a["risk_metrics"]["debt_service_coverage_ratio"] != float("inf") else 999)["name"]
        best_options["best_overall"] = rankings[0]["name"] if rankings else None

    # Risk-return analysis
    risk_return_analysis: list[dict] = []
    for a in property_analyses:
        risk_return_analysis.append({
            "name": a["name"],
            "irr": a["return_metrics"]["irr"],
            "dscr": a["risk_metrics"]["debt_service_coverage_ratio"],
            "break_even_occupancy": a["risk_metrics"]["break_even_occupancy"],
            "expense_ratio": a["risk_metrics"]["expense_ratio"],
            "risk_level": (
                "low" if a["risk_metrics"]["debt_service_coverage_ratio"] > 1.5
                else "medium" if a["risk_metrics"]["debt_service_coverage_ratio"] > 1.2
                else "high"
            ),
        })

    # Sensitivity comparison (simplified)
    sensitivity_comparison: list[dict] = []
    for a in property_analyses:
        # Quick sensitivity: how much can rent drop before negative CF
        mcf = a["cash_flow"]["monthly_cash_flow"]
        rent = a["cash_flow"]["monthly_rent"]
        rent_cushion = (mcf / rent * 100) if rent > 0 else 0
        sensitivity_comparison.append({
            "name": a["name"],
            "rent_drop_to_breakeven": round2(rent_cushion),
            "monthly_cash_flow_cushion": round2(mcf),
        })

    # Timeline comparison
    timeline_comparison: dict = {}
    for yr in range(1, holding_period + 1):
        year_data: dict = {}
        for a in property_analyses:
            projs = a.get("future_projections", [])
            if yr <= len(projs):
                year_data[a["name"]] = {
                    "property_value": projs[yr - 1]["property_value"],
                    "equity": projs[yr - 1]["equity"],
                    "monthly_rent": projs[yr - 1]["monthly_rent"],
                }
        timeline_comparison[f"year_{yr}"] = year_data

    # Insights
    insights: list[str] = []
    if rankings:
        insights.append(f"{rankings[0]['name']} ranks #1 overall with a score of {rankings[0]['total_score']}.")
    for a in property_analyses:
        if a["cash_flow"]["monthly_cash_flow"] < target_cf:
            insights.append(
                f"{a['name']} falls below target cash flow of ${target_cf}/month "
                f"(actual: ${a['cash_flow']['monthly_cash_flow']}/month)."
            )
        if a["return_metrics"]["cap_rate"] < target_cap:
            insights.append(
                f"{a['name']} cap rate ({a['return_metrics']['cap_rate']}%) is below target of {target_cap}%."
            )
        if a["valuation_metrics"]["meets_one_percent"]:
            insights.append(f"{a['name']} meets the 1% rule, indicating strong rent-to-price ratio.")

    # Recommendations
    recommendations: list[str] = []
    if rankings:
        recommendations.append(f"Top pick: {rankings[0]['name']} based on weighted scoring criteria.")
    high_risk = [a["name"] for a in property_analyses if a["risk_metrics"]["debt_service_coverage_ratio"] < 1.2]
    if high_risk:
        recommendations.append(f"Caution: {', '.join(high_risk)} have low debt service coverage ratios.")
    neg_cf = [a["name"] for a in property_analyses if a["cash_flow"]["monthly_cash_flow"] < 0]
    if neg_cf:
        recommendations.append(f"Negative cash flow: {', '.join(neg_cf)}. These require monthly out-of-pocket funding.")
    if not recommendations:
        recommendations.append("All properties show reasonable fundamentals. Review location-specific factors.")

    return {
        "property_analyses": property_analyses,
        "comparison_matrix": comparison_matrix,
        "rankings": rankings,
        "best_options": best_options,
        "risk_return_analysis": risk_return_analysis,
        "sensitivity_comparison": sensitivity_comparison,
        "timeline_comparison": timeline_comparison,
        "insights": insights,
        "recommendations": recommendations,
    }
