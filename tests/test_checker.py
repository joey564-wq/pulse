import httpx
from pulse.checker import check
from pulse.models import CheckResult


def test_check_returns_a_checkresult(httpx_mock):
    httpx_mock.add_response(url="https://example.com", status_code=200)
    result = check("https://example.com")
    assert isinstance(result, CheckResult)
    assert result.ok is True
    assert result.status == 200
    import httpx
from pulse.checker import check
from pulse.models import CheckResult


def test_check_returns_a_checkresult(httpx_mock):
    httpx_mock.add_response(url="https://example.com", status_code=200)
    result = check("https://example.com")
    assert isinstance(result, CheckResult)
    assert result.ok is True
    assert result.status == 200


def test_check_200_is_ok(httpx_mock):
    httpx_mock.add_response(url="https://example.com", status_code=200)
    result = check("https://example.com")
    assert result.ok is True
    assert result.error is None


def test_check_500_is_not_ok(httpx_mock):
    httpx_mock.add_response(url="https://example.com", status_code=500)
    result = check("https://example.com")
    assert result.ok is False
    assert result.status == 500


def test_check_handles_network_error(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    result = check("https://example.com")
    assert result.ok is False
    assert result.status is None
    assert result.error is not None
    assert "boom" in result.error


def test_check_latency_is_reasonable(httpx_mock):
    httpx_mock.add_response(url="https://example.com", status_code=200)
    result = check("https://example.com")
    assert result.latency_ms >= 0
    assert result.latency_ms < 5000   # mock is instant, well under 5s