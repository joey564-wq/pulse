"""Tests for the async HTTP checker."""
import httpx

from pulse.checker import check_many, check_one
from pulse.models import CheckResult


async def test_check_one_returns_checkresult(httpx_mock):
    """check_one() returns a CheckResult instance for a successful request."""
    httpx_mock.add_response(url="https://example.com", status_code=200)
    async with httpx.AsyncClient() as client:
        result = await check_one("https://example.com", client)
    assert isinstance(result, CheckResult)
    assert result.ok is True
    assert result.status == 200


async def test_check_one_500_is_not_ok(httpx_mock):
    """A 500 response means ok=False but status is still recorded."""
    httpx_mock.add_response(url="https://example.com", status_code=500)
    async with httpx.AsyncClient() as client:
        result = await check_one("https://example.com", client)
    assert result.ok is False
    assert result.status == 500


async def test_check_one_handles_network_error(httpx_mock):
    """A connection error produces ok=False with the error message captured."""
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    async with httpx.AsyncClient() as client:
        result = await check_one("https://example.com", client)
    assert result.ok is False
    assert result.status is None
    assert result.error is not None
    assert "boom" in result.error


async def test_check_one_latency_is_reasonable(httpx_mock):
    """Latency is non-negative and within a sane upper bound."""
    httpx_mock.add_response(url="https://example.com", status_code=200)
    async with httpx.AsyncClient() as client:
        result = await check_one("https://example.com", client)
    assert result.latency_ms >= 0
    assert result.latency_ms < 5000


async def test_check_many_runs_all(httpx_mock):
    """check_many returns one result per URL passed in."""
    httpx_mock.add_response(url="https://a.example.com", status_code=200)
    httpx_mock.add_response(url="https://b.example.com", status_code=500)
    results = await check_many(["https://a.example.com", "https://b.example.com"])
    assert len(results) == 2
    by_url = {r.url: r for r in results}
    assert by_url["https://a.example.com"].ok is True
    assert by_url["https://b.example.com"].ok is False