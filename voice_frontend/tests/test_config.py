from voice_frontend.config import _split_csv


def test_split_csv_basic():
    assert _split_csv("a,b,c") == ("a", "b", "c")


def test_split_csv_strips_whitespace():
    assert _split_csv(" a , b ,c") == ("a", "b", "c")


def test_split_csv_empty_string_returns_empty_tuple():
    assert _split_csv("") == ()


def test_split_csv_drops_empty_entries():
    assert _split_csv("a,,b,") == ("a", "b")


def test_split_csv_single_value():
    assert _split_csv("neeve") == ("neeve",)
