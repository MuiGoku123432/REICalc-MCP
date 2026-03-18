"""Calculator examples resource - hardcoded example scenarios."""


def get_calculator_examples() -> dict:
    """Return example scenarios for each calculator."""
    return {
        "affordability": [
            {
                "title": "First-Time Buyer - Median Income",
                "description": "Single person with median US income, minimal debt, saving for first home",
                "inputs": {
                    "annual_income": 75000,
                    "monthly_debts": 500,
                    "down_payment": 20000,
                    "interest_rate": 6.85,
                    "property_tax_rate": 1.2,
                    "insurance_rate": 0.5,
                    "hoa_monthly": 0,
                    "loan_term_years": 30,
                },
                "expected_outcome": "Can afford approximately $285,000-$305,000 home",
            },
            {
                "title": "Dual Income - High Debt",
                "description": "Married couple with good income but student loans and car payments",
                "inputs": {
                    "annual_income": 135000,
                    "monthly_debts": 2200,
                    "down_payment": 50000,
                    "interest_rate": 6.85,
                    "property_tax_rate": 1.5,
                    "insurance_rate": 0.6,
                    "hoa_monthly": 250,
                    "loan_term_years": 30,
                },
                "expected_outcome": "Can afford approximately $425,000-$450,000 home",
            },
            {
                "title": "High Earner - 15-Year Mortgage",
                "description": "Tech professional seeking faster payoff with 15-year term",
                "inputs": {
                    "annual_income": 185000,
                    "monthly_debts": 800,
                    "down_payment": 100000,
                    "interest_rate": 6.02,
                    "property_tax_rate": 1.1,
                    "insurance_rate": 0.4,
                    "hoa_monthly": 0,
                    "loan_term_years": 15,
                },
                "expected_outcome": "Can afford approximately $600,000-$650,000 home",
            },
        ],
        "brrrr": [
            {
                "title": "Midwest Single Family BRRRR",
                "description": "Classic BRRRR in Cleveland area - distressed property rehabilitation",
                "inputs": {
                    "purchase_price": 85000,
                    "rehab_cost": 45000,
                    "after_repair_value": 175000,
                    "monthly_rent": 1400,
                    "refinance_ltv": 0.75,
                    "holding_costs_monthly": 800,
                    "holding_period_months": 4,
                },
                "expected_outcome": "Cash out ~$1,250, monthly cash flow ~$200-250",
            },
            {
                "title": "Small Multi-Family BRRRR",
                "description": "Duplex BRRRR in growing secondary market",
                "inputs": {
                    "purchase_price": 225000,
                    "rehab_cost": 65000,
                    "after_repair_value": 385000,
                    "monthly_rent": 3200,
                    "refinance_ltv": 0.70,
                    "holding_costs_monthly": 1500,
                    "holding_period_months": 6,
                },
                "expected_outcome": "Cash out ~$20,000, monthly cash flow ~$400-500",
            },
        ],
        "house_hacking": [
            {
                "title": "FHA Duplex House Hack",
                "description": "First-time buyer using FHA 3.5% down on duplex",
                "inputs": {
                    "purchase_price": 385000,
                    "down_payment": 13475,
                    "monthly_rent_unit2": 1800,
                    "owner_expenses": 900,
                    "interest_rate": 6.45,
                    "property_tax_rate": 1.2,
                    "insurance_rate": 0.6,
                    "pmi_rate": 0.85,
                },
                "expected_outcome": "Net housing cost ~$900/month vs $2,400 renting",
            },
        ],
        "portfolio_growth": [
            {
                "title": "Conservative Buy & Hold",
                "description": "Starting with one rental, acquiring one every 2 years",
                "inputs": {
                    "starting_capital": 50000,
                    "annual_savings": 15000,
                    "initial_property_value": 200000,
                    "annual_appreciation": 3.5,
                    "annual_rent_growth": 3.0,
                    "target_cash_flow_per_property": 300,
                    "acquisition_pace_years": 2,
                },
                "expected_outcome": "10 properties, $3M+ portfolio value in 20 years",
            },
        ],
        "syndication": [
            {
                "title": "Class B Multi-Family Value-Add",
                "description": "200-unit apartment complex in growing Sun Belt market",
                "inputs": {
                    "minimum_investment": 50000,
                    "total_raise": 8500000,
                    "preferred_return": 7,
                    "profit_split_after_pref": 70,
                    "projected_hold_period": 5,
                    "projected_irr": 15.5,
                    "projected_equity_multiple": 1.95,
                },
                "expected_outcome": "$97,500 total return on $50k investment",
            },
        ],
        "tips": [
            "Always run multiple scenarios with different assumptions",
            "Include all costs: closing, holding, maintenance, property management",
            "Be conservative with rent estimates and aggressive with expense estimates",
            "Factor in vacancy rates: 5-10% for SFR, 10-15% for multi-family",
            "Don't forget reserves: 6 months of expenses minimum per property",
        ],
    }
