"""Market data resource - loads current mortgage rates and market conditions."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def get_market_data() -> dict:
    """Load and return current market data."""
    data_path = _DATA_DIR / "market-data.json"
    try:
        data = json.loads(data_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    mortgage_rates = data.get("mortgage_rates", {})
    home_prices = data.get("home_prices", {})
    rental_market = data.get("rental_market", {})
    economic_indicators = data.get("economic_indicators", {})
    market_trends = data.get("market_trends", [])

    current_rates = mortgage_rates.get("current", {}).get("rates", {})

    def _rate(key, default):
        return current_rates.get(key, {}).get("rate", default)

    national = home_prices.get("national", {})
    top_markets = home_prices.get("top_markets", [])
    top_rental = rental_market.get("top_rental_markets", [])

    return {
        "mortgage_rates": {
            "conventional_30_year": _rate("30_year_fixed", 7.125),
            "conventional_15_year": _rate("15_year_fixed", 6.625),
            "fha_30_year": _rate("fha_30_year", 6.875),
            "va_30_year": _rate("va_30_year", 6.750),
            "jumbo_30_year": _rate("jumbo_30_year", 7.375),
            "arm_5_1": _rate("5_1_arm", 5.95),
            "trends": {
                "week_over_week": current_rates.get("30_year_fixed", {}).get("change_from_last_week", 0),
                "direction": current_rates.get("30_year_fixed", {}).get("trend", "stable"),
            },
            "last_updated": mortgage_rates.get("current", {}).get("date", ""),
        },
        "market_trends": {
            "home_price_appreciation_yoy": national.get("year_over_year_change", 3.2),
            "inventory_months_supply": national.get("inventory_months", 3.8),
            "median_home_price": national.get("median_price", 412000),
            "price_per_sqft": national.get("price_per_sqft", 225),
            "market_insights": market_trends,
        },
        "economic_indicators": {
            "inflation_rate": economic_indicators.get("inflation_rate", 3.2),
            "fed_funds_rate": economic_indicators.get("fed_funds_rate", 5.5),
            "unemployment_rate": economic_indicators.get("unemployment_rate", 3.9),
            "gdp_growth": economic_indicators.get("gdp_growth", 2.1),
            "consumer_confidence": economic_indicators.get("consumer_confidence", 104.7),
        },
        "rental_metrics": {
            "national_average_rent": rental_market.get("national_average_rent", 1895),
            "rent_growth_yoy": rental_market.get("year_over_year_change", 2.8),
            "vacancy_rate": rental_market.get("vacancy_rate", 6.2),
            "rent_to_price_ratio": rental_market.get("rent_to_price_ratio", 0.0046),
        },
        "regional_data": {
            "hottest_markets": [m["metro"] for m in top_markets if m.get("market_temp") == "hot"],
            "cooling_markets": [m["metro"] for m in top_markets if m.get("market_temp") == "cooling"],
            "best_cash_flow_markets": [m.get("city", "") for m in top_rental],
            "balanced_markets": [m["metro"] for m in top_markets if m.get("market_temp") == "balanced"],
        },
    }
