"""Input validation helpers for real estate calculators."""


def validate_positive(value: float, name: str) -> None:
    """Raise ValueError if value is not positive."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def validate_non_negative(value: float, name: str) -> None:
    """Raise ValueError if value is negative."""
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")


def validate_range(value: float, name: str, low: float, high: float) -> None:
    """Raise ValueError if value is outside [low, high]."""
    if value < low or value > high:
        raise ValueError(f"{name} must be between {low} and {high}, got {value}")


def validate_percent(value: float, name: str) -> None:
    """Raise ValueError if value is not in [0, 100]."""
    validate_range(value, name, 0, 100)


def validate_non_empty_list(lst: list, name: str) -> None:
    """Raise ValueError if list is empty."""
    if not lst:
        raise ValueError(f"{name} must not be empty")
