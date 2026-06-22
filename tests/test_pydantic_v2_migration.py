"""Regression tests pinning the Pydantic v2 migration behaviors.

Each test guards a v1->v2 semantic difference that the SDK explicitly preserves
(see `nado_protocol.utils.model.NadoBaseModel`). If any of these break, the
migration has regressed.
"""

import pydantic
import pytest
from pydantic import ValidationError

from nado_protocol.contracts.eip712.types import EIP712Types
from nado_protocol.engine_client.types import EngineClientOpts
from nado_protocol.engine_client.types.execute import (
    BurnNlpParams,
    BurnNlpRequest,
    ExecuteResponse,
    PlaceOrderParams,
    PlaceOrdersItemResponse,
    to_execute_request,
)
from nado_protocol.engine_client.types.models import MaxOrderSizeDirection
from nado_protocol.engine_client.types.query import (
    ContractsData,
    MarketLiquidityData,
    NoncesData,
    QueryMaxOrderSizeParams,
    QueryStatusParams,
    QuerySymbolsParams,
)
from nado_protocol.indexer_client.types import IndexerClientOpts
from nado_protocol.indexer_client.types.query import (
    IndexerBaseParams,
    IndexerCandlesticksParams,
    IndexerCandlesticksGranularity,
    IndexerHistoricalOrdersByDigestParams,
)
from nado_protocol.utils.backend import NadoClientOpts
from nado_protocol.utils.subaccount import SubaccountParams

SENDER_HEX = "0xBE3faCAE76A38c3b61492E57BF65ae0628c4A80864656661756c740000000000"
OWNER = "0xBE3faCAE76A38c3b61492E57BF65ae0628c4A808"


def test_running_on_pydantic_v2():
    assert pydantic.VERSION.startswith("2.")


def test_optional_fields_default_to_none():
    """v2 does NOT auto-default Optional fields; the migration added `= None`."""
    params = QuerySymbolsParams()
    assert params.product_type is None
    assert params.product_ids is None

    order = PlaceOrderParams(
        product_id=1,
        order={
            "sender": SENDER_HEX,
            "priceX18": 1,
            "amount": 1,
            "expiration": 1,
            "appendix": 0,
        },
    )
    assert order.id is None
    assert order.digest is None
    assert order.spot_leverage is None
    assert order.order.nonce is None

    # A response with only the required status; every other field is optional.
    resp = ExecuteResponse(status="success")
    assert resp.signature is None and resp.error is None and resp.data is None


def test_type_discriminator_is_a_real_field():
    """Untyped `type = ...` became a class-var in v2; it must stay a field."""
    assert QueryStatusParams().dict() == {"type": "status"}
    assert QueryStatusParams.model_fields["type"].default == "status"

    dumped = QueryMaxOrderSizeParams(
        sender=SENDER_HEX,
        product_id=1,
        price_x18="1",
        direction=MaxOrderSizeDirection.LONG,
    ).dict()
    assert dumped["type"] == "max_order_size"


def test_dict_excludes_none_by_default():
    item = PlaceOrdersItemResponse(digest="0x1")
    assert item.dict() == {"digest": "0x1"}
    assert item.dict(exclude_none=False) == {"digest": "0x1", "error": None}


def test_serialize_as_any_preserves_transformed_request_shape():
    """Request validators swap a field for a `TxRequest`; v2 must serialize the
    runtime type (serialize_as_any), not the declared `*Params` type."""
    params = BurnNlpParams(sender=SENDER_HEX, nlpAmount=1000, nonce=100000)
    params.signature = "0xabc"
    req = to_execute_request(params)
    assert isinstance(req, BurnNlpRequest)
    dumped = req.dict()
    assert dumped == {
        "burn_nlp": {
            "tx": {
                "sender": SENDER_HEX.lower(),
                "nlpAmount": "1000",
                "nonce": "100000",
            },
            "signature": "0xabc",
        }
    }


def test_url_validation_rejects_garbage_but_preserves_scheme():
    with pytest.raises(ValidationError):
        EngineClientOpts(url="invalid_url")

    assert EngineClientOpts(url="ws://example.com").url == "ws://example.com"
    # trailing slash stripped, scheme/host preserved exactly (no AnyUrl normalization)
    assert EngineClientOpts(url="http://example.com/").url == "http://example.com"

    with pytest.raises(ValidationError):
        IndexerClientOpts(url="not a url")
    assert IndexerClientOpts(url="https://a.com/").url == "https://a.com"


def test_numbers_coerced_to_str_for_response_models():
    """v1 coerced int->str; preserved via coerce_numbers_to_str."""
    contracts = ContractsData(chain_id=1337, endpoint_addr="0xabc")
    assert contracts.chain_id == "1337"

    nonces = NoncesData(tx_nonce=1, order_nonce=2)
    assert nonces.tx_nonce == "1" and nonces.order_nonce == "2"


def test_model_validate_returns_fresh_copy():
    """revalidate_instances='always' restores v1 parse_obj copy semantics."""
    original = BurnNlpParams(sender=SENDER_HEX, nlpAmount=1000)
    revalidated = BurnNlpParams.model_validate(original)
    assert revalidated is not original
    revalidated.nonce = 999
    assert original.nonce is None


def test_sender_validator_serializes_to_bytes32():
    order = PlaceOrderParams(
        product_id=1,
        order={
            "sender": SENDER_HEX,
            "priceX18": 1,
            "amount": 1,
            "expiration": 1,
            "appendix": 0,
        },
    )
    assert isinstance(order.order.sender, bytes)
    assert len(order.order.sender) == 32

    # SubaccountParams with no owner cannot resolve yet -> left intact.
    pending = PlaceOrderParams(
        product_id=1,
        order={
            "sender": SubaccountParams(subaccount_name="default"),
            "priceX18": 1,
            "amount": 1,
            "expiration": 1,
            "appendix": 0,
        },
    )
    assert isinstance(pending.order.sender, SubaccountParams)


def test_linked_signer_requires_signer_model_validator():
    pk = "0x4c9ce2e6c4f38c801410a8603350108f2ac23a6f7cf6217a946c216ec0ec3bec"
    with pytest.raises(
        ValidationError, match="linked_signer cannot be set if signer is not set"
    ):
        NadoClientOpts(url="http://example.com", linked_signer=pk)


def test_bool_fields_serialize_to_lowercase_str():
    params = QueryMaxOrderSizeParams(
        sender=SENDER_HEX,
        product_id=1,
        price_x18="1",
        direction=MaxOrderSizeDirection.LONG,
        reduce_only=True,
        isolated=False,
    )
    assert params.reduce_only == "true"
    assert params.isolated == "false"
    assert params.direction == "long"

    # Unset optional bool stays None (validator must not coerce the default).
    params_default = QueryMaxOrderSizeParams(
        sender=SENDER_HEX,
        product_id=1,
        price_x18="1",
        direction=MaxOrderSizeDirection.SHORT,
    )
    assert params_default.reduce_only is None


def test_conlist_market_liquidity_length_constraint():
    ok = MarketLiquidityData(bids=[["1", "2"]], asks=[["3", "4"]], timestamp="0")
    assert ok.bids[0] == ["1", "2"]

    with pytest.raises(ValidationError):
        MarketLiquidityData(bids=[["1"]], asks=[["3", "4"]], timestamp="0")


def test_indexer_idx_alias_and_populate_by_name():
    by_alias = IndexerBaseParams(submission_idx=5)
    by_name = IndexerBaseParams(idx=5)
    assert by_alias.idx == 5 and by_name.idx == 5

    # Candlesticks excludes idx from serialization (was Config.fields exclude).
    candles = IndexerCandlesticksParams(
        product_id=1, granularity=IndexerCandlesticksGranularity.ONE_MINUTE
    )
    assert "idx" not in candles.dict(exclude_none=False)


def test_extra_forbid_disambiguates_union_members():
    with pytest.raises(ValidationError):
        IndexerHistoricalOrdersByDigestParams(digests=["0x1"], subaccounts=["0xabc"])


def test_eip712_types_extra_allow_round_trips():
    types = EIP712Types(
        EIP712Domain=[{"name": "name", "type": "string"}],
        Order=[{"name": "sender", "type": "bytes32"}],
    )
    dumped = types.model_dump()
    assert dumped["Order"] == [{"name": "sender", "type": "bytes32"}]
