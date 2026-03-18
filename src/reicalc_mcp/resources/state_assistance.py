"""State assistance resource - loads down payment assistance programs."""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"


def get_state_assistance() -> dict:
    """Load and return all state assistance programs."""
    data_path = _DATA_DIR / "state-programs.json"
    try:
        data = json.loads(data_path.read_text())
        programs = data.get("programs", [])
        states_obj = {}
        for state_data in programs:
            states_obj[state_data["state"]] = {
                "programs": state_data.get("programs", []),
                "income_limits": state_data.get("income_limits", ""),
                "contact": state_data.get("contact", ""),
            }
        return {
            "states": states_obj,
            "federal_programs": data.get("federal_programs", []),
            "tips": data.get("tips", []),
            "total_states": len(programs),
            "last_updated": data.get("last_updated", ""),
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {
            "states": {},
            "federal_programs": [],
            "tips": [],
            "total_states": 0,
            "last_updated": "",
        }
