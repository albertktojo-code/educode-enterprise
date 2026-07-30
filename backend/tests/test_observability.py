from app.schemas.observability import QuotaWrite
from app.services.observability import RequestMetricsRegistry, compare, normalize_route, percentile


def test_compare_supports_operational_operators() -> None:
    assert compare(5, ">", 4)
    assert compare(5, ">=", 5)
    assert compare(4, "<", 5)
    assert compare(5, "<=", 5)
    assert compare(5, "==", 5)


def test_percentile_and_route_normalization() -> None:
    assert percentile([1, 2, 3, 4, 5], 0.95) == 5
    assert normalize_route("/api/v1/jobs/6f2e41a0-7b1f-46ac-9bc7-484d5b0b0f37") == "/api/v1/jobs/{id}"
    assert normalize_route("/api/v1/items/42") == "/api/v1/items/{id}"


def test_request_metrics_registry_exposes_prometheus() -> None:
    registry = RequestMetricsRegistry()
    registry.begin()
    registry.finish("GET", "/api/v1/health", 200, 10)
    registry.begin()
    registry.finish("POST", "/api/v1/test", 500, 30, exception=True)
    summary = registry.summary()
    assert summary["requests_total"] == 2
    assert summary["error_rate_percent"] == 50
    assert summary["latency_p95_ms"] == 30
    text = registry.prometheus_text(app_version="0.13.1", environment="test")
    assert "educode_http_requests_total" in text
    assert 'status="500"' in text


def test_quota_rejects_inverted_thresholds() -> None:
    try:
        QuotaWrite(
            quota_key="jobs.active",
            limit_value=10,
            warning_percentage=98,
            critical_percentage=90,
        )
    except ValueError as exc:
        assert "faixa de aviso" in str(exc)
    else:
        raise AssertionError("A quota deveria rejeitar percentuais invertidos")
