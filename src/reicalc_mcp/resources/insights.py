"""Insights resource - loads and returns educational articles."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def get_insights() -> dict:
    """Load and return all insights articles."""
    data_path = _DATA_DIR / "insights.json"
    try:
        data = json.loads(data_path.read_text())
        return {
            "articles": data.get("articles", []),
            "categories": data.get("categories", []),
            "total_articles": data.get("total_articles", 0),
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "articles": [],
            "categories": [],
            "total_articles": 0,
        }
