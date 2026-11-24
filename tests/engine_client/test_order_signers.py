from unittest.mock import MagicMock

import pytest
from eth_abi import encode
from eth_utils import keccak, to_checksum_address

from nado_protocol.client import NadoClient
from nado_protocol.contracts.eip712.sign import (
    build_eip712_typed_data,
    get_eip712_typed_data_digest,
)
from nado_protocol.contracts.types import NadoExecuteType, NadoTxType
from nado_protocol.engine_client import EngineClient
from nado_protocol.engine_client.types.execute import (
    AddOrderSignerParams,
    AddOrderSignerRequest,
    DeleteOrderSignerParams,
    DeleteOrderSignerRequest,
    to_execute_request,
)
from nado_protocol.engine_client.types.query import OrderSignersData
from nado_protocol.indexer_client import IndexerClient
from nado_protocol.indexer_client.types.query import (
    IndexerOrderSignerEventsData,
    IndexerOrderSignerEventsParams,
    IndexerOrderSignerRateLimitData,
)
from nado_protocol.utils.bytes32 import hex_to_bytes32, subaccount_to_bytes32

# Verbatim from nado-core contracts/Verifier.sol.
CONTRACT_TYPE_STRINGS = {
    NadoTxType.LINK_SIGNER: "LinkSigner(bytes32 sender,bytes32 signer,uint64 nonce)",
    NadoTxType.ADD_ORDER_SIGNER: "AddOrderSigner(bytes32 sender,bytes32 signer,uint64 nonce)",
    NadoTxType.DELETE_ORDER_SIGNER: "DeleteOrderSigner(bytes32 sender,bytes32 signer,uint64 nonce)",
}


@pytest.mark.parametrize(
    "params_cls, request_cls, field",
    [
        (AddOrderSignerParams, AddOrderSignerRequest, "add_order_signer"),
        (DeleteOrderSignerParams, DeleteOrderSignerRequest, "delete_order_signer"),
    ],
)
def test_order_signer_request(
    params_cls, request_cls, field, senders: list[str], owners: list[str]
):
    sender = senders[0]
    signer = owners[1]
    params = params_cls(sender=sender, signer=signer, nonce=7, signature="0xabcd")

    assert params.signer == hex_to_bytes32(signer)
    assert params == params_cls(
        sender=hex_to_bytes32(sender),
        signer=signer + "00" * 12,
        nonce=7,
        signature="0xabcd",
    )

    req = request_cls(**{field: params})
    assert req == to_execute_request(params)
    assert req.dict() == {
        field: {
            "tx": {
                "sender": sender.lower(),
                "signer": (signer + "00" * 12).lower(),
                "nonce": "7",
            },
            "signature": "0xabcd",
        }
    }


def test_order_signer_digests_match_contract(
    senders: list[str], owners: list[str], endpoint_addr: str, chain_id: int
):
    sender = subaccount_to_bytes32(senders[0])
    signer = hex_to_bytes32(owners[1])
    nonce = 7
    domain_separator = keccak(
        encode(
            ["bytes32", "bytes32", "bytes32", "uint256", "address"],
            [
                keccak(
                    text="EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"
                ),
                keccak(text="Nado"),
                keccak(text="0.0.1"),
                chain_id,
                to_checksum_address(endpoint_addr),
            ],
        )
    )

    digests = set()
    for tx, type_string in CONTRACT_TYPE_STRINGS.items():
        struct_hash = keccak(
            encode(
                ["bytes32", "bytes32", "bytes32", "uint64"],
                [keccak(text=type_string), sender, signer, nonce],
            )
        )
        expected = "0x" + keccak(b"\x19\x01" + domain_separator + struct_hash).hex()
        typed_data = build_eip712_typed_data(
            tx,
            {"sender": sender, "signer": signer, "nonce": nonce},
            endpoint_addr,
            chain_id,
        )
        digest = get_eip712_typed_data_digest(typed_data)
        assert digest == expected
        digests.add(digest)

    assert len(digests) == 3


@pytest.mark.parametrize(
    "params_cls, method, execute_type",
    [
        (AddOrderSignerParams, "add_order_signer", NadoExecuteType.ADD_ORDER_SIGNER),
        (
            DeleteOrderSignerParams,
            "delete_order_signer",
            NadoExecuteType.DELETE_ORDER_SIGNER,
        ),
    ],
)
def test_subaccount_api_order_signer_executes(
    params_cls,
    method,
    execute_type,
    nado_client: NadoClient,
    senders: list[str],
    owners: list[str],
    mock_execute_response: MagicMock,
    mock_tx_nonce: MagicMock,
):
    params = params_cls(sender=senders[0], signer=owners[1])
    res = getattr(nado_client.subaccount, method)(params)

    engine_client = nado_client.context.engine_client
    signature = engine_client.sign(
        execute_type,
        params_cls(sender=senders[0], signer=owners[1], nonce=1).dict(),
        engine_client.endpoint_addr,
        engine_client.chain_id,
        engine_client.signer,
    )
    assert res.req == {
        execute_type.value: {
            "tx": {
                "sender": senders[0].lower(),
                "signer": (owners[1] + "00" * 12).lower(),
                "nonce": "1",
            },
            "signature": signature,
        }
    }
    assert params.nonce is None


def test_get_order_signers(mock_post: MagicMock, url: str, senders: list[str]):
    engine_client = EngineClient({"url": url})
    signers = ["0xeae27ae6412147ed6d5692fd91709dad6dbfc342"]
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": {"order_signers": signers},
        "request_type": "query_order_signers",
    }
    mock_post.return_value = mock_response

    res = engine_client.get_order_signers(senders[0])

    assert res == OrderSignersData(order_signers=signers)
    assert mock_post.call_args.kwargs["json"] == {
        "type": "order_signers",
        "subaccount": senders[0],
    }


def test_get_order_signer_rate_limits(
    mock_post: MagicMock, url: str, senders: list[str]
):
    indexer_client = IndexerClient({"url": url})
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "remaining_tx": "49",
        "wait_time": "0",
        "total_tx_limit": "50",
        "order_signers": ["0xeae27ae6412147ed6d5692fd91709dad6dbfc342"],
    }
    mock_post.return_value = mock_response

    res = indexer_client.get_order_signer_rate_limits(senders[0])

    assert isinstance(res, IndexerOrderSignerRateLimitData)
    assert res.remaining_tx == "49" and res.wait_time == 0
    assert mock_post.call_args.kwargs["json"] == {
        "order_signer_rate_limit": {"subaccount": senders[0]}
    }


def test_get_order_signer_events(mock_post: MagicMock, url: str, senders: list[str]):
    indexer_client = IndexerClient({"url": url})
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "events": [
            {
                "subaccount": senders[0],
                "signer": "0xeae27ae6412147ed6d5692fd91709dad6dbfc342",
                "submission_idx": 1352436,
                "added": False,
                "update_time": 1763553718,
            }
        ]
    }
    mock_post.return_value = mock_response

    res = indexer_client.get_order_signer_events(
        IndexerOrderSignerEventsParams(subaccount=senders[0], limit=10)
    )

    assert isinstance(res, IndexerOrderSignerEventsData)
    assert res.events[0].added is False
    assert res.events[0].submission_idx == 1352436
    assert mock_post.call_args.kwargs["json"] == {
        "order_signer_events": {"subaccount": senders[0], "limit": 10}
    }
