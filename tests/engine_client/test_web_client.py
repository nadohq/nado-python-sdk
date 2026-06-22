"""Tests for the gateway web/connectivity helper client."""

from unittest.mock import MagicMock

from nado_protocol.engine_client import EngineWebClient


def _resp(status_code=200, json_data=None, headers=None) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    return resp


def test_ip_block_status_not_blocked(mock_get: MagicMock):
    mock_get.return_value = _resp(status_code=200)
    assert EngineWebClient("http://example.com").get_ip_block_status() is None


def test_ip_block_status_query_only(mock_get: MagicMock):
    mock_get.return_value = _resp(
        status_code=403, json_data={"blocked": True, "reason": "ip_query_only"}
    )
    assert EngineWebClient("http://example.com").get_ip_block_status() == "query_only"


def test_ip_block_status_blocked(mock_get: MagicMock):
    mock_get.return_value = _resp(
        status_code=403, json_data={"blocked": True, "reason": "sanctioned"}
    )
    assert EngineWebClient("http://example.com").get_ip_block_status() == "blocked"


def test_ip_block_status_403_but_not_blocked(mock_get: MagicMock):
    mock_get.return_value = _resp(status_code=403, json_data={"blocked": False})
    assert EngineWebClient("http://example.com").get_ip_block_status() is None


def test_country_code(mock_get: MagicMock):
    mock_get.return_value = _resp(headers={"x-nado-country": "US"})
    assert EngineWebClient("http://example.com").get_country_code() == "US"
    mock_get.return_value = _resp(headers={})
    assert EngineWebClient("http://example.com").get_country_code() is None


def test_requires_cloudflare_auth(mock_get: MagicMock):
    mock_get.return_value = _resp(
        status_code=403, headers={"cf-mitigated": "challenge"}
    )
    assert EngineWebClient("http://example.com").get_requires_cloudflare_auth() is True

    mock_get.return_value = _resp(status_code=200)
    assert EngineWebClient("http://example.com").get_requires_cloudflare_auth() is False


def test_get_time(mock_get: MagicMock):
    mock_get.return_value = _resp(json_data=1700000000000)
    assert EngineWebClient("http://example.com").get_time() == 1700000000000
