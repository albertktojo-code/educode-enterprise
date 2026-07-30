from app.comic_reader_analytics.policies import (
    clamp_duration, correlation_label, median, pearson,
    privacy_guard, safe_rate, stable_hash,
)


def test_duration_and_privacy():
    assert clamp_duration(-1) == 0
    assert clamp_duration(99999999) == 1_800_000
    assert privacy_guard(4)["suppressed"] is True
    assert privacy_guard(5)["suppressed"] is False


def test_statistics():
    assert median([1, 2, 3, 4]) == 2.5
    assert safe_rate(2, 4) == 0.5
    assert pearson([1, 2, 3], [10, 20, 30]) == 1.0
    assert correlation_label(1.0) == "STRONG_POSITIVE"


def test_hash_is_stable():
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
