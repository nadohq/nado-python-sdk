"""Synchronous WebSocket clients for the gateway `/ws` and `/subscribe` endpoints.

These are thin transports over the `websockets` library's synchronous client.
The gateway requires `permessage-deflate` compression on the handshake (which
`websockets` negotiates by default); message construction lives in
`nado_protocol.ws.messages`.
"""

import json
from typing import Iterator, List, Optional, Union

from websockets.sync.client import ClientConnection, connect

from nado_protocol.engine_client.types.execute import ExecuteParams, ExecuteRequest
from nado_protocol.engine_client.types.query import QueryRequest
from nado_protocol.engine_client.types.stream import StreamAuthenticationParams
from nado_protocol.ws import messages
from nado_protocol.ws.streams import StreamSubscription


def http_url_to_ws(url: str, path: str = "") -> str:
    """Derive a WebSocket URL from an http(s) base URL, appending `path`.

    `https` -> `wss`, `http` -> `ws`; `ws`/`wss` URLs pass through. Trailing
    slashes on the base are removed before joining.
    """
    base = url.rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://") :]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://") :]
    return base + path


class _BaseWebSocketClient:
    def __init__(self, url: str, path: str):
        self.url = http_url_to_ws(url, path)
        self.ws: Optional[ClientConnection] = None
        self._id = 0

    def connect(self, **kwargs) -> "_BaseWebSocketClient":
        """Open the WebSocket connection. Extra kwargs go to `websockets` connect."""
        self.ws = connect(self.url, **kwargs)
        return self

    def _require_conn(self) -> ClientConnection:
        if self.ws is None:
            raise RuntimeError("WebSocket is not connected; call connect() first")
        return self.ws

    def next_id(self) -> int:
        self._id += 1
        return self._id

    def send(self, message: dict) -> None:
        self._require_conn().send(json.dumps(message))

    def recv(self, timeout: Optional[float] = None) -> dict:
        return json.loads(self._require_conn().recv(timeout=timeout))

    def close(self) -> None:
        if self.ws is not None:
            self.ws.close()
            self.ws = None

    def __enter__(self) -> "_BaseWebSocketClient":
        return self.connect()

    def __exit__(self, *_exc) -> None:
        self.close()


class NadoWebSocketClient(_BaseWebSocketClient):
    """Client for the `/ws` endpoint (query + execute over a socket)."""

    def __init__(self, url: str):
        super().__init__(url, "/ws")

    def query(self, params: QueryRequest) -> dict:
        """Send a query and return the server's response."""
        self.send(messages.query_message(params))
        return self.recv()

    def execute(self, params: Union[ExecuteParams, ExecuteRequest]) -> dict:
        """Send a (signed) execute and return the server's response."""
        self.send(messages.execute_message(params))
        return self.recv()


class NadoSubscriptionClient(_BaseWebSocketClient):
    """Client for the `/subscribe` endpoint (streaming + control messages)."""

    def __init__(self, url: str):
        super().__init__(url, "/subscribe")

    def subscribe(self, stream: StreamSubscription, id: Optional[int] = None) -> dict:
        self.send(messages.subscribe_message(stream, id or self.next_id()))
        return self.recv()

    def unsubscribe(self, stream: StreamSubscription, id: Optional[int] = None) -> dict:
        self.send(messages.unsubscribe_message(stream, id or self.next_id()))
        return self.recv()

    def subscribe_multi(
        self, streams: List[StreamSubscription], id: Optional[int] = None
    ) -> dict:
        self.send(messages.subscribe_multi_message(streams, id or self.next_id()))
        return self.recv()

    def unsubscribe_multi(
        self, streams: List[StreamSubscription], id: Optional[int] = None
    ) -> dict:
        self.send(messages.unsubscribe_multi_message(streams, id or self.next_id()))
        return self.recv()

    def list_subscriptions(self, id: Optional[int] = None) -> dict:
        self.send(messages.list_message(id or self.next_id()))
        return self.recv()

    def ping(self, client_time: Optional[str] = None, id: Optional[int] = None) -> dict:
        self.send(messages.ping_message(id or self.next_id(), client_time))
        return self.recv()

    def time(self, id: Optional[int] = None) -> dict:
        self.send(messages.time_message(id or self.next_id()))
        return self.recv()

    def authenticate(
        self, auth: StreamAuthenticationParams, id: Optional[int] = None
    ) -> dict:
        self.send(messages.authenticate_message(auth, id or self.next_id()))
        return self.recv()

    def listen(self, timeout: Optional[float] = None) -> Iterator[dict]:
        """Yield pushed event messages until the connection closes."""
        while self.ws is not None:
            yield self.recv(timeout=timeout)
