from unittest.mock import MagicMock
import json
from eth_account import Account
import pytest
from nado_protocol.contracts.eip712.sign import (
    build_eip712_typed_data,
    sign_eip712_typed_data,
)
from eth_account.signers.local import LocalAccount
from nado_protocol.contracts.types import NadoExecuteType
from nado_protocol.engine_client.types.execute import OrderParams
from nado_protocol.trigger_client import TriggerClient
from nado_protocol.trigger_client.types.execute import (
    PlaceTriggerOrderParams,
    PlaceTriggerOrderRequest,
    to_trigger_execute_request,
)
from nado_protocol.trigger_client.types.models import (
    PriceAboveTrigger,
    PriceBelowTrigger,
)
from nado_protocol.utils.bytes32 import (
    bytes32_to_hex,
    hex_to_bytes32,
    subaccount_to_bytes32,
)
from nado_protocol.utils.exceptions import ExecuteFailedException
from nado_protocol.utils.nonce import gen_order_nonce
from nado_protocol.utils.order import (
    gen_order_verifying_contract,
    build_appendix,
    OrderAppendixTriggerType,
)
from nado_protocol.utils.subaccount import SubaccountParams
from nado_protocol.utils.math import to_x18
from nado_protocol.utils.expiration import OrderType


def test_place_trigger_order_params(
    senders: list[str], owners: list[str], order_params: dict
):
    product_id = 1
    sender = hex_to_bytes32(senders[0])
    params_from_dict = PlaceTriggerOrderParams(
        **{
            "product_id": product_id,
            "order": {
                "sender": senders[0],
                "priceX18": order_params["priceX18"],
                "amount": order_params["amount"],
                "expiration": order_params["expiration"],
                "appendix": order_params["appendix"],
            },
            "trigger": {"price_below": "9900000000000000000000"},
        }
    )
    params_from_obj = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=senders[0],
            priceX18=order_params["priceX18"],
            amount=order_params["amount"],
            expiration=order_params["expiration"],
            appendix=order_params["appendix"],
        ),
        trigger=PriceBelowTrigger(price_below="9900000000000000000000"),
    )
    bytes32_sender = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=hex_to_bytes32(senders[0]),
            priceX18=order_params["priceX18"],
            amount=order_params["amount"],
            expiration=order_params["expiration"],
            appendix=order_params["appendix"],
        ),
        trigger=PriceBelowTrigger(price_below="9900000000000000000000"),
    )
    subaccount_params_sender = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=SubaccountParams(
                subaccount_owner=owners[0], subaccount_name="default"
            ),
            priceX18=order_params["priceX18"],
            amount=order_params["amount"],
            expiration=order_params["expiration"],
            appendix=order_params["appendix"],
        ),
        trigger=PriceBelowTrigger(price_below="9900000000000000000000"),
    )

    assert (
        params_from_dict
        == params_from_obj
        == bytes32_sender
        == subaccount_params_sender
    )

    assert params_from_dict.product_id == product_id
    assert params_from_dict.order.sender == sender
    assert params_from_dict.order.amount == order_params["amount"]
    assert params_from_dict.order.priceX18 == order_params["priceX18"]
    assert params_from_dict.order.expiration == order_params["expiration"]
    assert params_from_dict.order.appendix == order_params["appendix"]
    assert params_from_dict.trigger.price_below == "9900000000000000000000"
    assert params_from_dict.signature is None

    params_from_dict.signature = (
        "0x51ba8762bc5f77957a4e896dba34e17b553b872c618ffb83dba54878796f2821"
    )
    params_from_dict.order.nonce = gen_order_nonce()
    place_trigger_order_req = PlaceTriggerOrderRequest(place_order=params_from_dict)
    assert place_trigger_order_req == to_trigger_execute_request(params_from_dict)
    assert place_trigger_order_req.dict() == {
        "place_order": {
            "product_id": product_id,
            "order": {
                "sender": senders[0].lower(),
                "priceX18": str(order_params["priceX18"]),
                "amount": str(order_params["amount"]),
                "expiration": str(order_params["expiration"]),
                "appendix": str(order_params["appendix"]),
                "nonce": str(params_from_dict.order.nonce),
            },
            "signature": params_from_dict.signature,
            "trigger": {"price_below": "9900000000000000000000"},
        }
    }

    params_from_dict.id = 100
    place_trigger_order_req = PlaceTriggerOrderRequest(place_order=params_from_dict)
    assert place_trigger_order_req == to_trigger_execute_request(params_from_dict)
    assert place_trigger_order_req.dict() == {
        "place_order": {
            "id": 100,
            "product_id": product_id,
            "order": {
                "sender": senders[0].lower(),
                "priceX18": str(order_params["priceX18"]),
                "amount": str(order_params["amount"]),
                "expiration": str(order_params["expiration"]),
                "appendix": str(order_params["appendix"]),
                "nonce": str(params_from_dict.order.nonce),
            },
            "signature": params_from_dict.signature,
            "trigger": {"price_below": "9900000000000000000000"},
        }
    }


def test_place_order_execute_fails_incomplete_client(
    mock_post: MagicMock,
    url: str,
    chain_id: int,
    private_keys: list[str],
    senders: list[str],
    order_params: dict,
):
    trigger_client = TriggerClient({"url": url})
    place_trigger_order_params = {
        "product_id": 1,
        "order": order_params,
        "trigger": {"price_below": "9900000000000000000000"},
    }

    with pytest.raises(AttributeError, match="Chain ID is not set."):
        trigger_client.place_trigger_order(place_trigger_order_params)

    trigger_client.chain_id = chain_id

    with pytest.raises(AttributeError, match="Signer is not set."):
        trigger_client.place_trigger_order(place_trigger_order_params)

    trigger_client.signer = Account.from_key(private_keys[0])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "signature": "xxx",
    }
    mock_post.return_value = mock_response

    res = trigger_client.place_trigger_order(place_trigger_order_params)
    place_trigger_order_req = PlaceTriggerOrderRequest(**res.req)

    assert (
        place_trigger_order_req.place_order.order.sender.lower() == senders[0].lower()
    )


def test_place_order_execute_success(
    trigger_client: TriggerClient, mock_post: MagicMock, senders: list[str]
):
    product_id = 1
    place_trigger_order_params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=SubaccountParams(subaccount_name="default"),
            priceX18=1000,
            amount=1000,
            expiration=1000,
            nonce=1000,
            appendix=0,
        ),
        trigger=PriceAboveTrigger(price_above=100),
    )

    order = place_trigger_order_params.order.copy(deep=True)
    order.sender = hex_to_bytes32(senders[0])

    with pytest.raises(
        ValueError,
        match="Missing `product_id` to sign place_order execute",
    ):
        trigger_client._sign(NadoExecuteType.PLACE_ORDER, order.dict())

    expected_signature = trigger_client._sign(
        NadoExecuteType.PLACE_ORDER,
        order.dict(),
        product_id=place_trigger_order_params.product_id,
    )
    computed_signature = sign_eip712_typed_data(
        typed_data=build_eip712_typed_data(
            NadoExecuteType.PLACE_ORDER,
            order.dict(),
            gen_order_verifying_contract(product_id),
            trigger_client.chain_id,
        ),
        signer=trigger_client._opts.linked_signer,
    )

    assert expected_signature == computed_signature

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "signature": expected_signature,
        "data": None,
    }
    mock_post.return_value = mock_response

    res = trigger_client.place_trigger_order(place_trigger_order_params)
    place_trigger_order_req = PlaceTriggerOrderRequest(**res.req)

    assert (
        place_trigger_order_req.place_order.signature
        == res.signature
        == expected_signature
    )
    assert (
        place_trigger_order_req.place_order.order.sender.lower() == senders[0].lower()
    )
    assert res.status == "success"
    assert res.error is None
    assert res.data is None

    mock_response.status_code = 200
    json_response = {
        "status": "failure",
        "error_code": 1000,
        "error": "Too Many Requests!",
    }
    mock_response.json.return_value = json_response
    mock_post.return_value.text = json.dumps(json_response)

    with pytest.raises(ExecuteFailedException, match=json.dumps(json_response)):
        trigger_client.place_trigger_order(place_trigger_order_params)

    # deactivate linked signer
    trigger_client.linked_signer = None

    expected_signature = sign_eip712_typed_data(
        typed_data=build_eip712_typed_data(
            NadoExecuteType.PLACE_ORDER,
            order.dict(),
            gen_order_verifying_contract(product_id),
            trigger_client.chain_id,
        ),
        signer=trigger_client._opts.signer,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "signature": expected_signature,
    }
    mock_post.return_value = mock_response

    res = trigger_client.place_trigger_order(place_trigger_order_params)
    place_trigger_order_req = PlaceTriggerOrderRequest(**res.req)

    assert place_trigger_order_req.place_order.signature == expected_signature


def test_place_order_execute_provide_full_params(
    mock_post: MagicMock, url: str, chain_id: int, private_keys: list[str]
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "signature": "xxx",
    }
    mock_post.return_value = mock_response

    trigger_client = TriggerClient({"url": url})
    signer: LocalAccount = Account.from_key(private_keys[0])
    sender = subaccount_to_bytes32(signer.address, "default")
    product_id = 1
    order_params = {
        "priceX18": 10000,
        "amount": 10000,
        "sender": sender,
        "nonce": gen_order_nonce(),
        "appendix": 0,
        "expiration": 10000,
    }
    signature = trigger_client.sign(
        NadoExecuteType.PLACE_ORDER,
        order_params,
        gen_order_verifying_contract(product_id),
        chain_id,
        signer,
    )
    order_params["sender"] = bytes32_to_hex(order_params["sender"])
    res = trigger_client.place_trigger_order(
        {
            "product_id": product_id,
            "order": order_params,
            "signature": signature,
            "trigger": {"price_above": "100"},
        }
    )
    req = PlaceTriggerOrderRequest(**res.req)

    assert req.place_order.signature == signature
    assert req.place_order.order.amount == str(order_params["amount"])
    assert req.place_order.order.priceX18 == str(order_params["priceX18"])
    assert req.place_order.order.sender == order_params["sender"]
    assert req.place_order.order.nonce == str(order_params["nonce"])
    assert req.place_order.order.expiration == str(order_params["expiration"])
    assert req.place_order.order.appendix == str(order_params["appendix"])
    assert req.place_order.trigger.price_above == "100"


def test_place_trigger_order_with_basic_appendix(senders: list[str]):
    """Test placing trigger order with basic appendix functionality."""
    product_id = 1
    sender = hex_to_bytes32(senders[0])

    # Test with IOC order type
    ioc_appendix = build_appendix(
        OrderType.IOC, trigger_type=OrderAppendixTriggerType.PRICE
    )
    params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=28898000000000000000000,
            amount=-10000000000000000,
            expiration=4611687701117784255,
            appendix=ioc_appendix,
        ),
        trigger=PriceAboveTrigger(price_above="30000000000000000000000"),
    )

    assert params.order.appendix == ioc_appendix

    # Test with reduce-only flag
    reduce_only_appendix = build_appendix(
        OrderType.POST_ONLY,
        reduce_only=True,
        trigger_type=OrderAppendixTriggerType.PRICE,
    )
    params_reduce = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=28898000000000000000000,
            amount=-10000000000000000,
            expiration=4611687701117784255,
            appendix=reduce_only_appendix,
        ),
        trigger=PriceBelowTrigger(price_below="28000000000000000000000"),
    )

    assert params_reduce.order.appendix == reduce_only_appendix


def test_place_trigger_order_with_price_trigger_appendix(senders: list[str]):
    """Test placing trigger order with price trigger appendix."""
    product_id = 1
    sender = hex_to_bytes32(senders[0])

    # This creates a compound trigger: price-based trigger in the API + price-based trigger in appendix
    # This might be useful for complex trigger strategies
    trigger_appendix = build_appendix(
        OrderType.IOC, reduce_only=True, trigger_type=OrderAppendixTriggerType.PRICE
    )

    params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=28898000000000000000000,
            amount=-5000000000000000,  # Partial close
            expiration=4611687701117784255,
            appendix=trigger_appendix,
        ),
        trigger=PriceAboveTrigger(price_above="29000000000000000000000"),
    )

    assert params.order.appendix == trigger_appendix


def test_place_trigger_order_with_isolated_position_appendix(senders: list[str]):
    """Test placing trigger order with isolated position appendix."""
    product_id = 1
    sender = hex_to_bytes32(senders[0])
    margin = 2000000  # 2M units margin

    isolated_appendix = build_appendix(
        OrderType.POST_ONLY,
        isolated=True,
        reduce_only=False,
        isolated_margin=margin,
        trigger_type=OrderAppendixTriggerType.PRICE,
    )

    params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=28898000000000000000000,
            amount=10000000000000000,  # Long position
            expiration=4611687701117784255,
            appendix=isolated_appendix,
        ),
        trigger=PriceBelowTrigger(price_below="28000000000000000000000"),  # Buy the dip
    )

    assert params.order.appendix == isolated_appendix


def test_place_trigger_order_appendix_combinations(senders: list[str]):
    """Test various valid appendix combinations with trigger orders."""
    product_id = 1
    sender = hex_to_bytes32(senders[0])

    # Test all order types with reduce-only and price triggers
    order_types = [OrderType.DEFAULT, OrderType.IOC, OrderType.FOK, OrderType.POST_ONLY]

    for order_type in order_types:
        appendix = build_appendix(
            order_type, reduce_only=True, trigger_type=OrderAppendixTriggerType.PRICE
        )

        params = PlaceTriggerOrderParams(
            product_id=product_id,
            order=OrderParams(
                sender=sender,
                priceX18=28898000000000000000000,
                amount=-10000000000000000,
                expiration=4611687701117784255,
                appendix=appendix,
            ),
            trigger=PriceAboveTrigger(price_above="29500000000000000000000"),
        )

        assert params.order.appendix == appendix

    # Test isolated position with different trigger types
    for trigger_price in ["27000000000000000000000", "31000000000000000000000"]:
        isolated_appendix = build_appendix(
            OrderType.DEFAULT,
            isolated=True,
            isolated_margin=to_x18(1500000),
            trigger_type=OrderAppendixTriggerType.PRICE,
        )

        trigger = (
            PriceBelowTrigger(price_below=trigger_price)
            if trigger_price.startswith("27")
            else PriceAboveTrigger(price_above=trigger_price)
        )

        params = PlaceTriggerOrderParams(
            product_id=product_id,
            order=OrderParams(
                sender=sender,
                priceX18=28898000000000000000000,
                amount=10000000000000000,
                expiration=4611687701117784255,
                appendix=isolated_appendix,
            ),
            trigger=trigger,
        )

        assert params.order.appendix == isolated_appendix


def test_place_trigger_order_complex_scenarios(senders: list[str]):
    """Test complex real-world scenarios with trigger orders and appendix."""
    product_id = 1
    sender = hex_to_bytes32(senders[0])

    # Scenario 1: Stop-loss with reduce-only
    stop_loss_appendix = build_appendix(
        OrderType.IOC,  # Execute immediately when triggered
        reduce_only=True,  # Only reduce position, don't increase
        trigger_type=OrderAppendixTriggerType.PRICE,
    )

    stop_loss_params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=27000000000000000000000,  # Lower than current price
            amount=-10000000000000000,  # Sell to close long
            expiration=4611687701117784255,
            appendix=stop_loss_appendix,
        ),
        trigger=PriceBelowTrigger(
            price_below="27500000000000000000000"
        ),  # Trigger below current
    )

    assert stop_loss_params.order.appendix == stop_loss_appendix

    # Scenario 2: Take-profit with post-only to avoid paying fees
    take_profit_appendix = build_appendix(
        OrderType.POST_ONLY,  # Only add liquidity
        reduce_only=True,  # Only reduce position
        trigger_type=OrderAppendixTriggerType.PRICE,
    )

    take_profit_params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=32000000000000000000000,  # Higher than current price
            amount=-10000000000000000,  # Sell to close long
            expiration=4611687701117784255,
            appendix=take_profit_appendix,
        ),
        trigger=PriceAboveTrigger(
            price_above="31500000000000000000000"
        ),  # Trigger above current
    )

    assert take_profit_params.order.appendix == take_profit_appendix

    # Scenario 3: Isolated position entry on breakout
    breakout_appendix = build_appendix(
        OrderType.IOC,  # Execute immediately on breakout
        isolated=True,
        isolated_margin=to_x18(5000000),  # 5M units of isolated margin
        trigger_type=OrderAppendixTriggerType.PRICE,
    )

    breakout_params = PlaceTriggerOrderParams(
        product_id=product_id,
        order=OrderParams(
            sender=sender,
            priceX18=31000000000000000000000,  # Above breakout level
            amount=15000000000000000,  # Larger position for breakout
            expiration=4611687701117784255,
            appendix=breakout_appendix,
        ),
        trigger=PriceAboveTrigger(
            price_above="30500000000000000000000"
        ),  # Breakout trigger
    )

    assert breakout_params.order.appendix == breakout_appendix
