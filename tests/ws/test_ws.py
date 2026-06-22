"""Tests for the WebSocket message builders, stream params, and transport."""

import json

import pytest

from nado_protocol.engine_client.types.execute import (
    CancelOrdersParams,
    CancelOrdersRequest,
)
from nado_protocol.engine_client.types.query import QueryAllProductsParams
from nado_protocol.engine_client.types.stream import StreamAuthenticationParams
from nado_protocol.utils.bytes32 import hex_to_bytes32
from nado_protocol.ws import messages
from nado_protocol.ws.client import (
    NadoSubscriptionClient,
    NadoWebSocketClient,
    http_url_to_ws,
)
from nado_protocol.ws.streams import (
    AllBboStream,
    FillStream,
    LatestCandlestickStream,
    OrderUpdateStream,
    TradeStream,
)

SENDER = "0xBE3faCAE76A38c3b61492E57BF65ae0628c4A80864656661756c740000000000"
DIGEST = "0x51ba8762bc5f77957a4e896dba34e17b553b872c618ffb83dba54878796f2821"


# ---- stream param serialization ----


def test_stream_dict_shapes():
    assert TradeStream(product_id=1).dict() == {"type": "trade", "product_id": 1}
    assert AllBboStream().dict() == {"type": "all_bbo"}
    assert LatestCandlestickStream(product_id=2, granularity=60).dict() == {
        "type": "latest_candlestick",
        "product_id": 2,
        "granularity": 60,
    }


def test_fill_stream_optional_product_omitted_and_subaccount_lowercased():
    assert FillStream(subaccount="0xABCD").dict() == {
        "type": "fill",
        "subaccount": "0xabcd",
    }
    assert FillStream(subaccount="0xABCD", product_id=3).dict() == {
        "type": "fill",
        "subaccount": "0xabcd",
        "product_id": 3,
    }


# ---- control / subscribe message builders ----


def test_subscribe_and_unsubscribe_messages():
    stream = TradeStream(product_id=4)
    assert messages.subscribe_message(stream, 1) == {
        "method": "subscribe",
        "id": 1,
        "stream": {"type": "trade", "product_id": 4},
    }
    assert messages.unsubscribe_message(stream, 2) == {
        "method": "unsubscribe",
        "id": 2,
        "stream": {"type": "trade", "product_id": 4},
    }


def test_subscribe_multi_message():
    streams = [TradeStream(product_id=1), OrderUpdateStream(subaccount="0xAB")]
    assert messages.subscribe_multi_message(streams, 9) == {
        "method": "subscribe_multi",
        "id": 9,
        "streams": [
            {"type": "trade", "product_id": 1},
            {"type": "order_update", "subaccount": "0xab"},
        ],
    }


def test_list_ping_time_messages():
    assert messages.list_message(5) == {"method": "list", "id": 5}
    assert messages.time_message(6) == {"method": "time", "id": 6}
    assert messages.ping_message(7) == {"method": "ping", "id": 7}
    assert messages.ping_message(7, "1000") == {
        "method": "ping",
        "id": 7,
        "client_time": "1000",
    }


def test_authenticate_message():
    auth = StreamAuthenticationParams(
        sender=SENDER, expiration=1700000000, signature="0xsig"
    )
    assert messages.authenticate_message(auth, 3) == {
        "method": "authenticate",
        "id": 3,
        "tx": {"sender": SENDER.lower(), "expiration": "1700000000"},
        "signature": "0xsig",
    }


def test_authenticate_message_requires_signature():
    auth = StreamAuthenticationParams(sender=SENDER, expiration=1)
    with pytest.raises(ValueError, match="Missing `signature`"):
        messages.authenticate_message(auth, 1)


# ---- /ws query + execute message builders ----


def test_query_message():
    assert messages.query_message(QueryAllProductsParams()) == {"type": "all_products"}


def test_execute_message_from_params_and_request():
    params = CancelOrdersParams(
        sender=hex_to_bytes32(SENDER),
        productIds=[4],
        digests=[hex_to_bytes32(DIGEST)],
        nonce=1,
    )
    params.signature = "0xsig"
    from_params = messages.execute_message(params)
    assert "cancel_orders" in from_params
    assert from_params["cancel_orders"]["signature"] == "0xsig"
    assert from_params["cancel_orders"]["tx"]["digests"] == [DIGEST]

    # An already-built request serializes identically.
    req = CancelOrdersRequest(cancel_orders=params)
    assert messages.execute_message(req) == from_params


# ---- url derivation ----


@pytest.mark.parametrize(
    "base,path,expected",
    [
        ("https://gateway.test.nado.xyz/v1", "/ws", "wss://gateway.test.nado.xyz/v1/ws"),
        ("http://localhost:80", "/subscribe", "ws://localhost:80/subscribe"),
        ("https://a.com/", "/ws", "wss://a.com/ws"),
        ("ws://already.ws", "/subscribe", "ws://already.ws/subscribe"),
    ],
)
def test_http_url_to_ws(base, path, expected):
    assert http_url_to_ws(base, path) == expected


# ---- transport (mocked socket) ----


class FakeWebSocket:
    def __init__(self, inbound):
        self.sent = []
        self._inbound = list(inbound)
        self.closed = False

    def send(self, payload):
        self.sent.append(payload)

    def recv(self, timeout=None):
        return self._inbound.pop(0)

    def close(self):
        self.closed = True


def test_subscription_client_sends_and_receives():
    client = NadoSubscriptionClient("https://gateway.test.nado.xyz/v1")
    client.ws = FakeWebSocket(inbound=[json.dumps({"result": None, "id": 1})])

    ack = client.subscribe(TradeStream(product_id=1))
    assert ack == {"result": None, "id": 1}
    assert json.loads(client.ws.sent[0]) == {
        "method": "subscribe",
        "id": 1,
        "stream": {"type": "trade", "product_id": 1},
    }


def test_websocket_client_query_roundtrip():
    client = NadoWebSocketClient("https://gateway.test.nado.xyz/v1")
    client.ws = FakeWebSocket(inbound=[json.dumps({"status": "success"})])
    resp = client.query(QueryAllProductsParams())
    assert resp == {"status": "success"}
    assert json.loads(client.ws.sent[0]) == {"type": "all_products"}


def test_client_requires_connection():
    client = NadoWebSocketClient("https://gateway.test.nado.xyz/v1")
    with pytest.raises(RuntimeError, match="not connected"):
        client.query(QueryAllProductsParams())
