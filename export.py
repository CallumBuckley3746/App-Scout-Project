from typing import Any


def csv_safe(value: Any) -> str:
    """Convert a CSV value to text and neutralize spreadsheet formulas."""
    if value is None:
        return ""

    text = str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
        return "'" + text
    return text
