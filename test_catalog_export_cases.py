from downdetector.catalog.export import csv_safe


def test_csv_formula_injection_equals():
    assert csv_safe("=SUM(A1:A5)") == "'=SUM(A1:A5)"


def test_csv_formula_injection_plus():
    assert csv_safe("+cmd") == "'+cmd"


def test_csv_formula_injection_minus():
    assert csv_safe("-cmd") == "'-cmd"


def test_csv_formula_injection_at():
    assert csv_safe("@cmd") == "'@cmd"


def test_normal_value():
    assert csv_safe("YouTube") == "YouTube"


def test_none_value():
    assert csv_safe(None) == ""
