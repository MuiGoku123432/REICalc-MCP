"""FastMCP server for REICalc real estate investment calculators."""

from mcp.server.fastmcp import FastMCP

from .calculators.core import (
    calculate_affordability,
    analyze_brrrr_deal,
    evaluate_house_hack,
    project_portfolio_growth,
    analyze_syndication,
)
from .calculators.lending import (
    calculate_mortgage_affordability,
    analyze_debt_to_income,
    compare_loans,
)
from .calculators.metrics import (
    calculate_irr_tool,
    analyze_fix_flip,
    calculate_npv_tool,
    calculate_cocr,
    calculate_dscr,
    analyze_breakeven,
)
from .calculators.analysis import (
    analyze_sensitivity,
    run_monte_carlo,
    calculate_tax_benefits,
    compare_properties,
)
from .calculators.financing import (
    analyze_refinance,
    analyze_construction_loan,
    analyze_hard_money_loan,
    analyze_seller_financing,
)
from .calculators.strategies import (
    analyze_airbnb_str,
    analyze_1031_exchange,
    analyze_wholesale_deal,
    analyze_subject_to_deal,
)
from .calculators.management import (
    analyze_property_management,
    track_property_expenses,
    track_deal_pipeline,
)
from .calculators.advanced import (
    analyze_rent_vs_buy,
    calculate_capital_gains_tax,
    analyze_joint_venture,
    analyze_market_comps,
)
from .resources.insights import get_insights
from .resources.state_assistance import get_state_assistance
from .resources.market_data import get_market_data
from .resources.calculator_examples import get_calculator_examples

mcp = FastMCP("reicalc-mcp")

# ── Core calculators ──────────────────────────────────────────────────────────

@mcp.tool()
def calculate_affordability_tool(
    annual_income: float,
    monthly_debts: float,
    down_payment: float,
    interest_rate: float,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    hoa_monthly: float = 0,
    loan_term_years: int = 30,
    pmi_rate: float = 0.5,
) -> dict:
    """Calculate how much house you can afford based on income, debts, and down payment."""
    return calculate_affordability(
        annual_income=annual_income, monthly_debts=monthly_debts,
        down_payment=down_payment, interest_rate=interest_rate,
        property_tax_rate=property_tax_rate, insurance_rate=insurance_rate,
        hoa_monthly=hoa_monthly, loan_term_years=loan_term_years,
        pmi_rate=pmi_rate,
    )


@mcp.tool()
def analyze_brrrr_deal_tool(
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
    purchase_loan_term_years: int = 30,
    refinance_loan_term_years: int = 30,
) -> dict:
    """Analyze a BRRRR (Buy, Rehab, Rent, Refinance, Repeat) real estate deal."""
    return analyze_brrrr_deal(
        purchase_price=purchase_price, rehab_cost=rehab_cost,
        after_repair_value=after_repair_value, monthly_rent=monthly_rent,
        down_payment_percent=down_payment_percent,
        purchase_interest_rate=purchase_interest_rate,
        refinance_ltv=refinance_ltv,
        refinance_interest_rate=refinance_interest_rate,
        closing_costs=closing_costs,
        refinance_closing_costs=refinance_closing_costs,
        monthly_expenses=monthly_expenses, vacancy_rate=vacancy_rate,
        holding_months=holding_months,
        purchase_loan_term_years=purchase_loan_term_years,
        refinance_loan_term_years=refinance_loan_term_years,
    )


@mcp.tool()
def evaluate_house_hack_tool(
    purchase_price: float,
    down_payment: float,
    monthly_rent_unit2: float,
    interest_rate: float,
    loan_term_years: int = 30,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    hoa_monthly: float = 0,
    pmi_rate: float = 0.5,
    additional_expenses: float = 0,
) -> dict:
    """Calculate returns from house hacking (living in one unit and renting others). Computes PITI internally."""
    return evaluate_house_hack(
        purchase_price=purchase_price, down_payment=down_payment,
        monthly_rent_unit2=monthly_rent_unit2, interest_rate=interest_rate,
        loan_term_years=loan_term_years, property_tax_rate=property_tax_rate,
        insurance_rate=insurance_rate, hoa_monthly=hoa_monthly,
        pmi_rate=pmi_rate, additional_expenses=additional_expenses,
    )


@mcp.tool()
def project_portfolio_growth_tool(
    starting_capital: float,
    years_to_project: int = 20,
    annual_growth_rate: float = 8.0,
    avg_property_cost: float = 50000,
    leverage_multiplier: float = 3.0,
) -> dict:
    """Project real estate portfolio growth over time."""
    return project_portfolio_growth(
        starting_capital=starting_capital,
        years_to_project=years_to_project,
        annual_growth_rate=annual_growth_rate,
        avg_property_cost=avg_property_cost,
        leverage_multiplier=leverage_multiplier,
    )


@mcp.tool()
def analyze_syndication_tool(
    investment_amount: float,
    projected_irr: float,
    hold_period: int,
    preferred_return: float = 8,
) -> dict:
    """Evaluate a real estate syndication investment opportunity."""
    return analyze_syndication(
        investment_amount=investment_amount, projected_irr=projected_irr,
        hold_period=hold_period, preferred_return=preferred_return,
    )


# ── Lending calculators ───────────────────────────────────────────────────────

@mcp.tool()
def calculate_mortgage_affordability_tool(
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
    """Advanced mortgage affordability calculator with dual income and detailed DTI analysis."""
    return calculate_mortgage_affordability(
        annual_income=annual_income, down_payment=down_payment,
        interest_rate=interest_rate,
        co_borrower_income=co_borrower_income,
        other_monthly_income=other_monthly_income,
        car_payment=car_payment, student_loans=student_loans,
        credit_cards=credit_cards, other_debts=other_debts,
        down_payment_percent=down_payment_percent, loan_term=loan_term,
        property_tax_rate=property_tax_rate,
        insurance_annual=insurance_annual, hoa_monthly=hoa_monthly,
    )


@mcp.tool()
def analyze_debt_to_income_tool(
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
    """Analyze debt-to-income ratios for mortgage qualification. Can compute PITI from loan details."""
    return analyze_debt_to_income(
        monthly_income=monthly_income,
        proposed_housing_payment=proposed_housing_payment,
        car_payments=car_payments,
        credit_card_minimums=credit_card_minimums,
        student_loans=student_loans, personal_loans=personal_loans,
        child_support_alimony=child_support_alimony,
        other_debts=other_debts, loan_type=loan_type,
        purchase_price=purchase_price, down_payment=down_payment,
        interest_rate=interest_rate, loan_term_years=loan_term_years,
        property_tax_rate=property_tax_rate,
        insurance_rate=insurance_rate, hoa_monthly=hoa_monthly,
        pmi_rate=pmi_rate,
    )


@mcp.tool()
def compare_loans_tool(
    home_price: float,
    loans: list[dict],
    property_tax_annual: float = 0,
    home_insurance_annual: float = 0,
    hoa_monthly: float = 0,
    comparison_period_years: int = 5,
) -> dict:
    """Compare multiple mortgage loan scenarios side by side to find the best option."""
    return compare_loans(
        home_price=home_price, loans=loans,
        property_tax_annual=property_tax_annual,
        home_insurance_annual=home_insurance_annual,
        hoa_monthly=hoa_monthly,
        comparison_period_years=comparison_period_years,
    )


# ── Metrics calculators ──────────────────────────────────────────────────────

@mcp.tool()
def calculate_irr(
    initial_investment: float,
    annual_cash_flows: list[float],
    projected_sale_price: float,
    selling_costs_percent: float = 7,
    loan_balance_at_sale: float = 0,
    target_irr: float = 15,
    holding_period_years: int | None = None,
) -> dict:
    """Calculate Internal Rate of Return (IRR) for real estate investments with cash flow analysis."""
    return calculate_irr_tool(
        initial_investment=initial_investment,
        annual_cash_flows=annual_cash_flows,
        projected_sale_price=projected_sale_price,
        selling_costs_percent=selling_costs_percent,
        loan_balance_at_sale=loan_balance_at_sale,
        target_irr=target_irr,
        holding_period_years=holding_period_years,
    )


@mcp.tool()
def analyze_fix_flip_tool(
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
    """Analyze profitability of fix and flip real estate investments with detailed cost breakdown."""
    return analyze_fix_flip(
        purchase_price=purchase_price, rehab_budget=rehab_budget,
        after_repair_value=after_repair_value,
        purchase_closing_costs=purchase_closing_costs,
        holding_period_months=holding_period_months,
        financing_type=financing_type,
        down_payment_percent=down_payment_percent,
        interest_rate=interest_rate, loan_points=loan_points,
        monthly_holding_costs=monthly_holding_costs,
        selling_costs_percent=selling_costs_percent,
        contingency_percent=contingency_percent,
    )


@mcp.tool()
def calculate_npv(
    initial_investment: float,
    cash_flows: list[dict],
    discount_rate: float,
    terminal_value: float = 0,
    terminal_period: int | None = None,
    inflation_rate: float = 0,
    comparison_investment: float | None = None,
) -> dict:
    """Calculate Net Present Value for real estate investment decisions."""
    return calculate_npv_tool(
        initial_investment=initial_investment, cash_flows=cash_flows,
        discount_rate=discount_rate, terminal_value=terminal_value,
        terminal_period=terminal_period, inflation_rate=inflation_rate,
        comparison_investment=comparison_investment,
    )


@mcp.tool()
def calculate_cocr_tool(
    purchase_price: float,
    down_payment: float,
    annual_rental_income: float,
    closing_costs: float = 0,
    renovation_costs: float = 0,
    annual_expenses: dict | None = None,
    vacancy_rate: float = 5,
    loan_details: dict | None = None,
    reserve_fund_percent: float = 5,
    rent_growth: float = 0.03,
    expense_growth: float = 0.025,
    appreciation_rate: float = 0.04,
) -> dict:
    """Calculate Cash-on-Cash Return with detailed expense analysis and projections."""
    return calculate_cocr(
        purchase_price=purchase_price, down_payment=down_payment,
        closing_costs=closing_costs, renovation_costs=renovation_costs,
        annual_rental_income=annual_rental_income,
        annual_expenses=annual_expenses or {},
        vacancy_rate=vacancy_rate, loan_details=loan_details or {},
        reserve_fund_percent=reserve_fund_percent,
        rent_growth=rent_growth, expense_growth=expense_growth,
        appreciation_rate=appreciation_rate,
    )


@mcp.tool()
def calculate_dscr_tool(
    property_income: dict,
    loan_details: dict,
    property_expenses: dict | None = None,
    property_details: dict | None = None,
) -> dict:
    """Calculate Debt Service Coverage Ratio for investment property loans."""
    return calculate_dscr(
        property_income=property_income,
        property_expenses=property_expenses or {},
        loan_details=loan_details,
        property_details=property_details or {},
    )


@mcp.tool()
def analyze_breakeven_tool(
    property_costs: dict,
    revenue_streams: dict,
    fixed_costs: dict | None = None,
    variable_costs: dict | None = None,
    analysis_parameters: dict | None = None,
) -> dict:
    """Calculate breakeven points for occupancy, rent, and ROI for real estate investments."""
    return analyze_breakeven(
        property_costs=property_costs,
        revenue_streams=revenue_streams,
        fixed_costs=fixed_costs or {},
        variable_costs=variable_costs or {},
        analysis_parameters=analysis_parameters or {},
    )


# ── Analysis calculators ─────────────────────────────────────────────────────

@mcp.tool()
def analyze_sensitivity_tool(
    base_scenario: dict,
    sensitivity_variables: list[dict] | None = None,
    analysis_metrics: list[str] | None = None,
    discount_rate: float = 10,
) -> dict:
    """Perform multi-variable sensitivity analysis on real estate investments."""
    return analyze_sensitivity(
        base_scenario=base_scenario,
        sensitivity_variables=sensitivity_variables,
        analysis_metrics=analysis_metrics,
        discount_rate=discount_rate,
    )


@mcp.tool()
def run_monte_carlo_tool(
    investment_parameters: dict,
    variable_distributions: dict,
    simulation_settings: dict | None = None,
    target_metrics: dict | None = None,
) -> dict:
    """Run Monte Carlo simulation to assess investment risk and return probabilities."""
    return run_monte_carlo(
        investment_parameters=investment_parameters,
        variable_distributions=variable_distributions,
        simulation_settings=simulation_settings or {},
        target_metrics=target_metrics or {},
    )


@mcp.tool()
def calculate_tax_benefits_tool(
    property_details: dict,
    income_expenses: dict,
    taxpayer_info: dict,
    loan_details: dict | None = None,
    cost_segregation_breakdown: dict | None = None,
    analysis_options: dict | None = None,
) -> dict:
    """Calculate depreciation, deductions, and tax savings for real estate investments."""
    return calculate_tax_benefits(
        property_details=property_details,
        income_expenses=income_expenses,
        loan_details=loan_details or {},
        taxpayer_info=taxpayer_info,
        cost_segregation_breakdown=cost_segregation_breakdown or {},
        analysis_options=analysis_options or {},
    )


@mcp.tool()
def compare_properties_tool(
    properties: list[dict],
    loan_terms: dict | None = None,
    comparison_criteria: dict | None = None,
) -> dict:
    """Compare multiple investment properties side by side with comprehensive analysis."""
    return compare_properties(
        properties=properties, loan_terms=loan_terms or {},
        comparison_criteria=comparison_criteria or {},
    )


# ── Financing calculators ────────────────────────────────────────────────────

@mcp.tool()
def analyze_refinance_tool(
    current_loan_balance: float,
    current_interest_rate: float,
    current_remaining_years: float,
    new_interest_rate: float,
    new_loan_term_years: int = 30,
    new_closing_costs: float = 0,
    cash_out_amount: float = 0,
    property_value: float = 0,
) -> dict:
    """Analyze whether refinancing your mortgage makes financial sense. Computes current payment internally."""
    return analyze_refinance(
        current_loan_balance=current_loan_balance,
        current_interest_rate=current_interest_rate,
        current_remaining_years=current_remaining_years,
        new_interest_rate=new_interest_rate,
        new_loan_term_years=new_loan_term_years,
        new_closing_costs=new_closing_costs,
        cash_out_amount=cash_out_amount,
        property_value=property_value,
    )


@mcp.tool()
def analyze_construction_loan_tool(
    land_cost: float,
    construction_budget: float,
    total_project_cost: float | None = None,
    construction_period_months: int = 12,
    interest_rate: float = 8,
    down_payment_percent: float = 20,
    permanent_loan_rate: float = 7,
    permanent_loan_term: int = 30,
    contingency_percent: float = 10,
    draw_schedule: list[dict] | None = None,
) -> dict:
    """Analyze construction loan financing, draw schedules, interest costs, and permanent conversion."""
    return analyze_construction_loan(
        land_cost=land_cost, construction_budget=construction_budget,
        total_project_cost=total_project_cost,
        construction_period_months=construction_period_months,
        interest_rate=interest_rate,
        down_payment_percent=down_payment_percent,
        permanent_loan_rate=permanent_loan_rate,
        permanent_loan_term=permanent_loan_term,
        contingency_percent=contingency_percent,
        draw_schedule=draw_schedule,
    )


@mcp.tool()
def analyze_hard_money_loan_tool(
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
    """Analyze hard money loans for real estate projects with cost analysis and risk assessment."""
    return analyze_hard_money_loan(
        property_value=property_value, purchase_price=purchase_price,
        rehab_budget=rehab_budget, loan_to_value=loan_to_value,
        interest_rate=interest_rate, loan_term_months=loan_term_months,
        origination_points=origination_points,
        exit_strategy=exit_strategy,
        after_repair_value=after_repair_value,
    )


@mcp.tool()
def analyze_seller_financing_tool(
    purchase_price: float,
    down_payment: float,
    interest_rate: float,
    loan_term_years: int,
    balloon_payment_years: int | None = None,
    monthly_payment_override: float | None = None,
    market_interest_rate: float = 7,
    buyer_credit_score: int | None = None,
) -> dict:
    """Analyze seller financing deals with comprehensive terms, benefits, and risk assessment."""
    return analyze_seller_financing(
        purchase_price=purchase_price, down_payment=down_payment,
        interest_rate=interest_rate, loan_term_years=loan_term_years,
        balloon_payment_years=balloon_payment_years,
        monthly_payment_override=monthly_payment_override,
        market_interest_rate=market_interest_rate,
        buyer_credit_score=buyer_credit_score,
    )


# ── Strategy calculators ─────────────────────────────────────────────────────

@mcp.tool()
def analyze_airbnb_str_tool(
    purchase_price: float,
    average_daily_rate: float,
    occupancy_rate: float = 65,
    down_payment_percent: float = 20,
    interest_rate: float = 7,
    monthly_expenses: float = 0,
    management_fee_percent: float = 20,
    cleaning_fee_per_turnover: float = 100,
    average_stay_nights: float = 3,
    seasonal_adjustment: dict | None = None,
    furnishing_cost: float = 0,
    platform_fee_percent: float = 3,
    ltr_rent_estimate: float | None = None,
) -> dict:
    """Analyze Airbnb/short-term rental income potential with seasonal variations and risk assessment."""
    return analyze_airbnb_str(
        purchase_price=purchase_price, average_daily_rate=average_daily_rate,
        down_payment_percent=down_payment_percent, interest_rate=interest_rate,
        occupancy_rate=occupancy_rate, monthly_expenses=monthly_expenses,
        management_fee_percent=management_fee_percent,
        cleaning_fee_per_turnover=cleaning_fee_per_turnover,
        average_stay_nights=average_stay_nights,
        seasonal_adjustment=seasonal_adjustment,
        furnishing_cost=furnishing_cost, platform_fee_percent=platform_fee_percent,
        ltr_rent_estimate=ltr_rent_estimate,
    )


@mcp.tool()
def analyze_1031_exchange_tool(
    relinquished_property: dict,
    replacement_property: dict,
    holding_period_years: int = 0,
    filing_status: str = "single",
    capital_gains_rate: float = 15,
    state_tax_rate: float = 5,
) -> dict:
    """Analyze 1031 like-kind exchange tax benefits, qualification requirements, and alternative strategies."""
    return analyze_1031_exchange(
        relinquished_property=relinquished_property,
        replacement_property=replacement_property,
        holding_period_years=holding_period_years,
        filing_status=filing_status,
        capital_gains_rate=capital_gains_rate,
        state_tax_rate=state_tax_rate,
    )


@mcp.tool()
def analyze_wholesale_deal_tool(
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
    """Analyze wholesale real estate deals with assignment fees, profit margins, and exit strategies."""
    return analyze_wholesale_deal(
        contract_price=contract_price,
        after_repair_value=after_repair_value,
        estimated_rehab_cost=estimated_rehab_cost,
        assignment_fee=assignment_fee,
        holding_costs_monthly=holding_costs_monthly,
        estimated_closing_costs=estimated_closing_costs,
        target_buyer_type=target_buyer_type,
        estimated_rehab_months=estimated_rehab_months,
        ltr_rent_estimate=ltr_rent_estimate,
    )


@mcp.tool()
def analyze_subject_to_deal_tool(
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
    """Analyze subject-to real estate deals. Computes existing payment from loan terms."""
    return analyze_subject_to_deal(
        purchase_price=purchase_price,
        existing_loan_balance=existing_loan_balance,
        existing_interest_rate=existing_interest_rate,
        existing_loan_remaining_years=existing_loan_remaining_years,
        monthly_rent=monthly_rent, monthly_expenses=monthly_expenses,
        down_payment_to_seller=down_payment_to_seller,
        property_value=property_value,
        appreciation_rate=appreciation_rate,
        rent_growth_rate=rent_growth_rate,
    )


# ── Management calculators ───────────────────────────────────────────────────

@mcp.tool()
def analyze_property_management_tool(
    monthly_rent: float,
    self_management: dict,
    professional_management: dict | None = None,
    num_units: int = 1,
    property_value: float = 0,
    annual_maintenance_cost: float = 0,
    current_vacancy_rate: float = 5,
    avg_tenant_stay_months: int = 24,
) -> dict:
    """Compare self-management vs professional property management with cost-benefit analysis."""
    return analyze_property_management(
        monthly_rent=monthly_rent, num_units=num_units,
        property_value=property_value,
        self_management=self_management,
        professional_management=professional_management or {},
        annual_maintenance_cost=annual_maintenance_cost,
        current_vacancy_rate=current_vacancy_rate,
        avg_tenant_stay_months=avg_tenant_stay_months,
    )


@mcp.tool()
def track_property_expenses_tool(
    expenses: list[dict],
    property_value: float = 0,
    monthly_rent: float = 0,
    annual_budget: dict | None = None,
) -> dict:
    """Track and analyze property expenses across categories with benchmarking and budget variance."""
    return track_property_expenses(
        expenses=expenses, property_value=property_value,
        monthly_rent=monthly_rent, annual_budget=annual_budget,
    )


@mcp.tool()
def track_deal_pipeline_tool(
    deals: list[dict],
) -> dict:
    """Track and analyze multiple real estate deals through various stages with performance metrics."""
    return track_deal_pipeline(deals=deals)


# ── Advanced calculators ─────────────────────────────────────────────────────

@mcp.tool()
def analyze_rent_vs_buy_tool(
    monthly_rent: float,
    home_price: float,
    annual_rent_increase: float = 3,
    down_payment_percent: float = 20,
    interest_rate: float = 7,
    loan_term_years: int = 30,
    property_tax_rate: float = 1.2,
    insurance_rate: float = 0.5,
    maintenance_percent: float = 1,
    hoa_monthly: float = 0,
    annual_appreciation: float = 3,
    marginal_tax_rate: float = 22,
    investment_return_rate: float = 7,
    analysis_period_years: int = 10,
    closing_costs_percent: float = 3,
    selling_costs_percent: float = 6,
) -> dict:
    """Compare the costs and benefits of renting vs buying a home."""
    return analyze_rent_vs_buy(
        monthly_rent=monthly_rent, annual_rent_increase=annual_rent_increase,
        home_price=home_price,
        down_payment_percent=down_payment_percent,
        interest_rate=interest_rate, loan_term_years=loan_term_years,
        property_tax_rate=property_tax_rate,
        insurance_rate=insurance_rate,
        maintenance_percent=maintenance_percent,
        hoa_monthly=hoa_monthly,
        annual_appreciation=annual_appreciation,
        marginal_tax_rate=marginal_tax_rate,
        investment_return_rate=investment_return_rate,
        analysis_period_years=analysis_period_years,
        closing_costs_percent=closing_costs_percent,
        selling_costs_percent=selling_costs_percent,
    )


@mcp.tool()
def calculate_capital_gains_tax_tool(
    sale_price: float,
    purchase_price: float,
    holding_period_years: float,
    selling_costs_percent: float = 6,
    improvements_cost: float = 0,
    depreciation_taken: float = 0,
    is_primary_residence: bool = False,
    years_lived_in: float = 0,
    filing_status: str = "single",
    other_income: float = 0,
    state: str = "CA",
    installment_sale: bool = False,
    installment_years: int = 5,
) -> dict:
    """Calculate capital gains tax liability for real estate sales with optimization strategies."""
    return calculate_capital_gains_tax(
        sale_price=sale_price, purchase_price=purchase_price,
        selling_costs_percent=selling_costs_percent,
        improvements_cost=improvements_cost,
        depreciation_taken=depreciation_taken,
        holding_period_years=holding_period_years,
        is_primary_residence=is_primary_residence,
        years_lived_in=years_lived_in, filing_status=filing_status,
        other_income=other_income, state=state,
        installment_sale=installment_sale,
        installment_years=installment_years,
    )


@mcp.tool()
def analyze_joint_venture_tool(
    total_project_cost: float,
    projected_profit: float,
    project_duration_months: int,
    partners: list[dict],
    profit_split_method: str = "pro_rata",
    preferred_return_rate: float = 8,
    waterfall_tiers: list[dict] | None = None,
) -> dict:
    """Analyze joint venture partnerships for real estate investments with profit splitting and risk assessment."""
    return analyze_joint_venture(
        total_project_cost=total_project_cost,
        projected_profit=projected_profit,
        project_duration_months=project_duration_months,
        partners=partners, profit_split_method=profit_split_method,
        preferred_return_rate=preferred_return_rate,
        waterfall_tiers=waterfall_tiers,
    )


@mcp.tool()
def analyze_market_comps_tool(
    subject_property: dict,
    comparable_properties: list[dict],
    adjustments: dict | None = None,
) -> dict:
    """Analyze market conditions with comparable property analysis, CMA, and investment metrics."""
    return analyze_market_comps(
        subject_property=subject_property,
        comparable_properties=comparable_properties,
        adjustments=adjustments or {},
    )


# ── Resources ────────────────────────────────────────────────────────────────

@mcp.resource("realvest://insights")
def insights_resource() -> str:
    """Search and access RealVest.ai educational articles and market insights."""
    import json
    return json.dumps(get_insights(), indent=2)


@mcp.resource("realvest://state-assistance")
def state_assistance_resource() -> str:
    """Access down payment assistance programs for all 50 states."""
    import json
    return json.dumps(get_state_assistance(), indent=2)


@mcp.resource("realvest://market-data")
def market_data_resource() -> str:
    """Get current mortgage rates and market conditions."""
    import json
    return json.dumps(get_market_data(), indent=2)


@mcp.resource("realvest://calculator-examples")
def calculator_examples_resource() -> str:
    """Example scenarios for each calculator."""
    import json
    return json.dumps(get_calculator_examples(), indent=2)


def main():
    """Run the MCP server."""
    mcp.run()
