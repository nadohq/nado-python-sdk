"""Tests for the gateway edge/cached query client."""

from unittest.mock import MagicMock

from nado_protocol.engine_client import EngineEdgeQueryClient
from nado_protocol.engine_client.types import EngineClientOpts


def _client() -> EngineEdgeQueryClient:
    return EngineEdgeQueryClient(EngineClientOpts(url="http://example.com"))


def _ok(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "data": data}
    return resp


def test_edge_url_includes_path():
    assert _client().url == "http://example.com/edge/query"


def test_get_cached_market_prices(mock_post: MagicMock):
    mock_post.return_value = _ok(
        {"market_prices": [{"product_id": 1, "bid_x18": "10", "ask_x18": "11"}]}
    )
    data = _client().get_cached_market_prices([1])
    assert data.market_prices[0].product_id == 1
    assert mock_post.call_args.kwargs["json"] == {
        "type": "cached_prices",
        "product_ids": [1],
    }


def test_get_cached_market_prices_no_filter(mock_post: MagicMock):
    mock_post.return_value = _ok({"market_prices": []})
    _client().get_cached_market_prices()
    assert mock_post.call_args.kwargs["json"] == {"type": "cached_prices"}


def test_get_cached_contracts(mock_post: MagicMock):
    mock_post.return_value = _ok({"chain_id": "1", "endpoint_addr": "0xabc"})
    data = _client().get_cached_contracts()
    assert data.chain_id == "1" and data.endpoint_addr == "0xabc"
    assert mock_post.call_args.kwargs["json"] == {"type": "cached_contracts"}


def test_get_cached_health_groups(mock_post: MagicMock):
    mock_post.return_value = _ok({"health_groups": [[1, 2], [3, 4]]})
    data = _client().get_cached_health_groups()
    assert data.health_groups == [[1, 2], [3, 4]]


def test_get_cached_bbo_history(mock_post: MagicMock):
    mock_post.return_value = _ok(
        {
            "interval_ms": 1000,
            "limit": 10,
            "history": [
                {"product_id": 1, "timestamp": "1700", "bid": "10", "ask": "11"}
            ],
        }
    )
    data = _client().get_cached_bbo_history(product_ids=[1], interval_ms=1000, limit=10)
    assert data.interval_ms == 1000 and data.limit == 10
    assert data.history[0].bid == "10"
    assert mock_post.call_args.kwargs["json"] == {
        "type": "cached_bbo_history",
        "product_ids": [1],
        "interval_ms": 1000,
        "limit": 10,
    }


def test_edge_ping(mock_post: MagicMock):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"method": "pong", "server_time": "1700", "id": 5}
    mock_post.return_value = resp
    out = _client().ping(client_time="1000", id=5)
    assert out["method"] == "pong"
    assert mock_post.call_args.kwargs["json"] == {
        "type": "ping",
        "id": 5,
        "client_time": "1000",
    }


def test_get_cached_edge_all_products(mock_post: MagicMock):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "status": "success",
        "data": {"763373": {"spot_products": [], "perp_products": []}},
    }
    mock_post.return_value = resp
    data = _client().get_cached_edge_all_products()
    assert "763373" in data
    assert mock_post.call_args.kwargs["json"] == {"type": "cached_edge_all_products"}


def test_get_cached_nlp_pool_info(mock_post: MagicMock):
    mock_post.return_value = _ok({"nlp_pools": []})
    data = _client().get_cached_nlp_pool_info()
    assert data.nlp_pools == []
    assert mock_post.call_args.kwargs["json"] == {"type": "cached_nlp_pool_info"}
