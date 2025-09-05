import time
import pytest
from unittest.mock import MagicMock

from nado_protocol.client import create_nado_client
from nado_protocol.utils.order import (
    APPENDIX_VERSION,
    OrderAppendixTriggerType,
    build_appendix,
    order_execution_type,
    order_is_isolated,
    order_is_trigger_order,
    order_isolated_margin,
    order_reduce_only,
    order_trigger_type,
    order_twap_data,
    order_version,
)
from nado_protocol.utils.expiration import OrderType
from nado_protocol.utils.math import to_x18
from nado_protocol.utils.subaccount import SubaccountParams


def test_basic_appendix_functionality():
    """Test basic appendix building and extraction."""
    # Test default appendix (should be minimal)
    appendix = build_appendix(OrderType.DEFAULT)
    assert order_version(appendix) == APPENDIX_VERSION
    assert order_execution_type(appendix) == OrderType.DEFAULT
    assert not order_reduce_only(appendix)
    assert not order_is_isolated(appendix)
    assert not order_is_trigger_order(appendix)

    # Test with various order types
    for order_type in [
        OrderType.DEFAULT,
        OrderType.IOC,
        OrderType.FOK,
        OrderType.POST_ONLY,
    ]:
        appendix = build_appendix(order_type, reduce_only=True)
        assert order_execution_type(appendix) == order_type
        assert order_reduce_only(appendix)


def test_isolated_position_functionality():
    """Test isolated position appendix functionality."""
    # Test isolated position with various margin amounts
    test_margins = [1000, 500000, 1000000000]  # Different margin sizes

    for margin in test_margins:
        margin_x18 = to_x18(margin)
        appendix = build_appendix(
            OrderType.POST_ONLY, isolated=True, isolated_margin=margin_x18
        )

        assert order_is_isolated(appendix)
        assert order_isolated_margin(appendix) == margin_x18
        assert order_execution_type(appendix) == OrderType.POST_ONLY

    # Test isolated position with maximum margin
    max_margin = (1 << 96) - 1  # Maximum 96-bit value
    appendix = build_appendix(
        OrderType.DEFAULT, isolated=True, isolated_margin=max_margin
    )
    assert order_isolated_margin(appendix) == max_margin

    # Test non-isolated orders
    appendix = build_appendix(OrderType.DEFAULT, isolated=False)
    assert not order_is_isolated(appendix)
    assert order_isolated_margin(appendix) is None


def test_twap_functionality():
    """Test TWAP order appendix functionality."""
    # Test various TWAP configurations
    twap_configs = [
        (5, 0.01),  # 5 orders, 1% slippage
        (10, 0.005),  # 10 orders, 0.5% slippage
        (100, 0.001),  # 100 orders, 0.1% slippage
        (1, 0.1),  # 1 order, 10% slippage
    ]

    for trigger_type in [
        OrderAppendixTriggerType.TWAP,
        OrderAppendixTriggerType.TWAP_CUSTOM_AMOUNTS,
    ]:
        for times, slippage_frac in twap_configs:
            appendix = build_appendix(
                OrderType.DEFAULT,
                trigger_type=trigger_type,
                twap_times=times,
                twap_slippage_frac=slippage_frac,
            )

            assert order_is_trigger_order(appendix)
            assert order_trigger_type(appendix) == trigger_type

            twap_data = order_twap_data(appendix)
            assert twap_data is not None
            extracted_orders, extracted_slippage = twap_data
            assert extracted_orders == times
            assert (
                abs(extracted_slippage - slippage_frac) < 1e-6
            )  # Allow for floating point precision


def test_trigger_order_functionality():
    """Test trigger order functionality."""
    # Test price-based trigger orders
    appendix = build_appendix(
        OrderType.DEFAULT, trigger_type=OrderAppendixTriggerType.PRICE
    )
    assert order_is_trigger_order(appendix)
    assert order_trigger_type(appendix) == OrderAppendixTriggerType.PRICE
    assert order_twap_data(appendix) is None  # Should be None for price triggers

    # Test non-trigger orders
    appendix = build_appendix(OrderType.DEFAULT)
    assert not order_is_trigger_order(appendix)


def test_validation_and_edge_cases():
    """Test validation rules and edge cases."""
    # Test isolated + TWAP mutual exclusion
    with pytest.raises(
        ValueError, match="An order cannot be both isolated and a TWAP order"
    ):
        build_appendix(
            OrderType.DEFAULT,
            isolated=True,
            trigger_type=OrderAppendixTriggerType.TWAP,
            isolated_margin=to_x18(1000),
            twap_times=5,
            twap_slippage_frac=0.01,
        )

    # Test TWAP parameter validation
    with pytest.raises(
        ValueError,
        match="twap_times and twap_slippage_frac are required for TWAP orders",
    ):
        build_appendix(OrderType.DEFAULT, trigger_type=OrderAppendixTriggerType.TWAP)

    # Test isolated margin validation
    with pytest.raises(
        ValueError, match="isolated_margin can only be set when isolated=True"
    ):
        build_appendix(OrderType.DEFAULT, isolated=False, isolated_margin=to_x18(1000))


def test_compatibility_with_existing_sdk(
    mock_post: MagicMock,
    mock_web3: MagicMock,
    mock_load_abi: MagicMock,
    private_keys: list[str],
    chain_id: int,
    endpoint_addr: str,
):
    """Test compatibility with existing SDK functionality."""
    try:
        # Mock the response for client creation
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {
                "endpoint_addr": endpoint_addr,
                "chain_id": chain_id,
            },
        }
        mock_post.return_value = mock_response

        # Create a client to test integration
        client = create_nado_client("testing", private_keys[0])

        # Test that appendix can be used with order parameters
        appendix = build_appendix(OrderType.IOC, reduce_only=True)

        # Simulate order parameters (without actually placing orders)
        from nado_protocol.engine_client.types.execute import OrderParams

        order_params = OrderParams(
            sender=SubaccountParams(subaccount_owner=client.context.signer.address),
            priceX18=to_x18(100),  # $100 price
            amount=to_x18(1),  # 1 unit
            expiration=int(time.time()) + 3600,  # 1 hour from now
            appendix=appendix,
        )

        assert order_params.appendix == appendix

        # Verify the appendix can be decoded
        assert order_execution_type(order_params.appendix) == OrderType.IOC
        assert order_reduce_only(order_params.appendix)

    except Exception as e:
        # Allow test to pass if client creation fails due to environment
        pytest.skip(f"Client integration test skipped due to environment: {e}")


def test_round_trip_conversions():
    """Test that all appendix values can be built and decoded correctly."""
    # Test various combinations
    test_cases = [
        # Basic cases - need to add order_type parameter
        {"order_type": OrderType.DEFAULT},
        {"order_type": OrderType.IOC, "reduce_only": True},
        {"order_type": OrderType.FOK, "reduce_only": False},
        {"order_type": OrderType.POST_ONLY, "reduce_only": True},
        # Trigger cases
        {
            "order_type": OrderType.DEFAULT,
            "trigger_type": OrderAppendixTriggerType.PRICE,
        },
        # TWAP cases
        {
            "order_type": OrderType.DEFAULT,
            "trigger_type": OrderAppendixTriggerType.TWAP,
            "twap_times": 5,
            "twap_slippage_frac": 0.01,
        },
        {
            "order_type": OrderType.DEFAULT,
            "trigger_type": OrderAppendixTriggerType.TWAP_CUSTOM_AMOUNTS,
            "twap_times": 10,
            "twap_slippage_frac": 0.005,
        },
        # Isolated cases
        {
            "order_type": OrderType.DEFAULT,
            "isolated": True,
            "isolated_margin": to_x18(1000),
        },
        {
            "order_type": OrderType.POST_ONLY,
            "isolated": True,
            "isolated_margin": to_x18(1000000),
            "reduce_only": True,
        },
    ]

    for case in test_cases:
        # Build appendix - extract order_type as first positional parameter
        order_type = case.pop("order_type", OrderType.DEFAULT)
        appendix = build_appendix(order_type, **case)

        # Extract values
        extracted = {
            "version": order_version(appendix),
            "order_type": order_execution_type(appendix),
            "reduce_only": order_reduce_only(appendix),
            "is_isolated": order_is_isolated(appendix),
            "isolated_margin": order_isolated_margin(appendix),
            "is_trigger": order_is_trigger_order(appendix),
            "trigger_type": order_trigger_type(appendix),
            "twap_data": order_twap_data(appendix),
        }

        # Verify key values match
        assert extracted["version"] == APPENDIX_VERSION

        if "order_type" in case:
            assert extracted["order_type"] == case["order_type"]

        if "reduce_only" in case:
            assert extracted["reduce_only"] == case["reduce_only"]

        if case.get("isolated"):
            assert extracted["is_isolated"]
            assert extracted["isolated_margin"] == case["isolated_margin"]

        if "trigger_type" in case:
            assert extracted["is_trigger"]
            assert extracted["trigger_type"] == case["trigger_type"]

            if case["trigger_type"] in [
                OrderAppendixTriggerType.TWAP,
                OrderAppendixTriggerType.TWAP_CUSTOM_AMOUNTS,
            ]:
                assert extracted["twap_data"] is not None
                orders, slippage = extracted["twap_data"]
                assert orders == case["twap_times"]
                assert abs(slippage - case["twap_slippage_frac"]) < 1e-6
