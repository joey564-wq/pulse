"""Tests for pulse.checker."""

import httpx
import pytest
from pytest_httpx import HTTPXMock

from pulse.checker import check


def test_check_returns_expected_keys() -> None:
    """The result dict should always have these keys."""
    # Hitting a real URL here is fine — example.com is reliable.
    result = check("https://example.com")
    assert set(result.keys()) == {"url", "status", "ok", "latency_ms", "error"}


def test_check_200_is_ok(httpx_mock: HTTPXMock) -> None:
    """A 200 response should be marked ok."""
    httpx_mock.add_response(url="https://fake.test", status_code=200)
    result = check("https://fake.test")
    assert result["ok"] is True
    assert result["status"] == 200
    assert result["error"] is None


def test_check_500_is_not_ok(httpx_mock: HTTPXMock) -> None:
    """A 500 response should be marked not ok."""
    httpx_mock.add_response(url="https://fake.test", status_code=500)
    result = check("https://fake.test")
    assert result["ok"] is False
    assert result["status"] == 500


def test_check_handles_network_error(httpx_mock: HTTPXMock) -> None:
    """A connection error should produce ok=False and an error string."""
    httpx_mock.add_exception(httpx.ConnectError("boom"))
    result = check("https://fake.test")
    assert result["ok"] is False
    assert result["status"] is None
    assert "boom" in result["error"]


def test_check_latency_is_reasonable(httpx_mock: HTTPXMock) -> None:
    """Latency should be a positive number."""
    httpx_mock.add_response(url="https://fake.test", status_code=200)
    result = check("https://fake.test")
    assert result["latency_ms"] >= 0
