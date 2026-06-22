"""Pure builders for WebSocket wire messages.

These produce the exact JSON envelopes accepted by the gateway `/ws` (query +
execute) and `/subscribe` (streaming + control) endpoints. They have no I/O and
are independently testable.
"""

from typing import List, Optional, Union

from nado_protocol.engine_client.types.execute import (
    ExecuteParams,
    ExecuteRequest,
    to_execute_request,
)
from nado_protocol.engine_client.types.query import QueryRequest
from nado_protocol.engine_client.types.stream import StreamAuthenticationParams
from nado_protocol.utils.model import is_instance_of_union
from nado_protocol.ws.streams import StreamSubscription


def query_message(params: QueryRequest) -> dict:
    """Build a `/ws` query message: `{ "type": "<query_type>", ...params }`."""
    return params.dict()


def execute_message(params: Union[ExecuteParams, ExecuteRequest]) -> dict:
    """Build a `/ws` execute message: `{ "<execute_type>": { ...signed params } }`.

    Accepts either signed `*Params` (converted via `to_execute_request`) or an
    already-built `*Request`.
    """
    req = (
        params
        if is_instance_of_union(params, ExecuteRequest)
        else to_execute_request(params)  # type: ignore[arg-type]
    )
    return req.dict()


def subscribe_message(stream: StreamSubscription, id: int) -> dict:
    return {"method": "subscribe", "id": id, "stream": stream.dict()}


def unsubscribe_message(stream: StreamSubscription, id: int) -> dict:
    return {"method": "unsubscribe", "id": id, "stream": stream.dict()}


def subscribe_multi_message(streams: List[StreamSubscription], id: int) -> dict:
    return {
        "method": "subscribe_multi",
        "id": id,
        "streams": [s.dict() for s in streams],
    }


def unsubscribe_multi_message(streams: List[StreamSubscription], id: int) -> dict:
    return {
        "method": "unsubscribe_multi",
        "id": id,
        "streams": [s.dict() for s in streams],
    }


def list_message(id: int) -> dict:
    return {"method": "list", "id": id}


def ping_message(id: int, client_time: Optional[str] = None) -> dict:
    message = {"method": "ping", "id": id}
    if client_time is not None:
        message["client_time"] = client_time
    return message


def time_message(id: int) -> dict:
    return {"method": "time", "id": id}


def authenticate_message(auth: StreamAuthenticationParams, id: int) -> dict:
    """Build a `/subscribe` authenticate message from signed stream-auth params."""
    if auth.signature is None:
        raise ValueError("Missing `signature` for stream authentication")
    return {
        "method": "authenticate",
        "id": id,
        "tx": {"sender": auth.sender.lower(), "expiration": str(auth.expiration)},
        "signature": auth.signature,
    }
