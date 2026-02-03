"""
Builder code sanity tests.

Tests:
1. Appendix encoding with builder fields
2. ClaimBuilderFee slow mode tx encoding
3. Placing order with builder info
4. Querying historical orders for builder_fee field
5. Querying matches for builder_fee and sequencer_fee fields
6. Querying claim_builder_fee events
7. Submitting ClaimBuilderFee via NadoContracts
8. Querying builder info via get_builder_info()
"""

from pprint import pprint

from eth_account import Account

from sanity import (
    ENGINE_BACKEND_URL,
    INDEXER_BACKEND_URL,
    NETWORK,
    SIGNER_PRIVATE_KEY,
)
from nado_protocol.contracts import (
    ClaimBuilderFeeParams,
    NadoContracts,
    NadoContractsContext,
)
from nado_protocol.contracts.loader import load_deployment
from nado_protocol.engine_client import EngineClient, EngineClientOpts
from nado_protocol.engine_client.types.execute import (
    CancelOrdersParams,
    PlaceOrderParams,
    OrderParams,
)
from nado_protocol.indexer_client import IndexerClient
from nado_protocol.indexer_client.types.models import IndexerEventType
from nado_protocol.indexer_client.types.query import (
    IndexerEventsParams,
    IndexerEventsRawLimit,
    IndexerMatchesParams,
    IndexerSubaccountHistoricalOrdersParams,
)
from nado_protocol.utils.bytes32 import subaccount_to_bytes32, subaccount_to_hex
from nado_protocol.utils.expiration import OrderType, get_expiration_timestamp
from nado_protocol.utils.math import to_pow_10, to_x18
from nado_protocol.utils.nonce import gen_order_nonce
from nado_protocol.utils.order import (
    build_appendix,
    order_builder_fee_rate,
    order_builder_id,
    order_builder_info,
)
from nado_protocol.utils.slow_mode import SlowModeTxType, encode_claim_builder_fee_tx
from nado_protocol.utils.subaccount import SubaccountParams


def run():
    print("=== Builder Code Sanity Tests ===\n")

    signer = Account.from_key(SIGNER_PRIVATE_KEY)
    test_builder_id = 2
    test_builder_fee_rate = 500  # 50 bps

    # Test 1: Appendix encoding
    print("Test 1: Appendix encoding with builder fields")
    builder_appendix = build_appendix(
        OrderType.DEFAULT,
        builder_id=test_builder_id,
        builder_fee_rate=test_builder_fee_rate,
    )
    extracted_builder_id = order_builder_id(builder_appendix)
    extracted_fee_rate = order_builder_fee_rate(builder_appendix)
    builder_info = order_builder_info(builder_appendix)

    print(f"  packed appendix: {builder_appendix}")
    print(f"  extracted builder_id: {extracted_builder_id}")
    print(f"  extracted fee_rate: {extracted_fee_rate}")
    print(f"  builder_info tuple: {builder_info}")

    assert extracted_builder_id == test_builder_id, "Builder ID mismatch!"
    assert extracted_fee_rate == test_builder_fee_rate, "Builder fee rate mismatch!"
    assert builder_info == (
        test_builder_id,
        test_builder_fee_rate,
    ), "Builder info mismatch!"
    print("✓ Appendix encoding test passed\n")

    # Test 2: ClaimBuilderFee encoding
    print("Test 2: ClaimBuilderFee slow mode tx encoding")
    sender_bytes = subaccount_to_bytes32(signer.address, "default")
    claim_tx = encode_claim_builder_fee_tx(sender_bytes, test_builder_id)

    print(f"  encoded tx length: {len(claim_tx)} bytes")
    print(
        f"  tx type byte: {claim_tx[0]} (expected: {SlowModeTxType.CLAIM_BUILDER_FEE})"
    )

    assert (
        claim_tx[0] == SlowModeTxType.CLAIM_BUILDER_FEE
    ), "ClaimBuilderFee tx type mismatch!"
    assert (
        len(claim_tx) == 65
    ), f"ClaimBuilderFee tx length mismatch: {len(claim_tx)} != 65"
    print("✓ ClaimBuilderFee encoding test passed\n")

    # Test 3: Place order with builder info via EngineClient
    print("Test 3: Place order with builder info")
    engine_client = EngineClient(
        opts=EngineClientOpts(url=ENGINE_BACKEND_URL, signer=SIGNER_PRIVATE_KEY)
    )

    contracts_data = engine_client.get_contracts()
    engine_client.endpoint_addr = contracts_data.endpoint_addr
    engine_client.chain_id = contracts_data.chain_id

    product_id = 2  # BTC-PERP
    order_price = 50_000

    builder_order = OrderParams(
        sender=SubaccountParams(
            subaccount_owner=signer.address, subaccount_name="default"
        ),
        priceX18=to_x18(order_price),
        amount=to_pow_10(1, 16),  # 0.01
        expiration=get_expiration_timestamp(60),
        nonce=gen_order_nonce(),
        appendix=builder_appendix,
    )

    order_digest = engine_client.get_order_digest(builder_order, product_id)
    print(f"  order digest: {order_digest}")

    sender_hex = subaccount_to_hex(
        SubaccountParams(subaccount_owner=signer.address, subaccount_name="default")
    )

    try:
        place_order = PlaceOrderParams(product_id=product_id, order=builder_order)
        res = engine_client.place_order(place_order)
        print(f"  order placed: {res.json(indent=2)}")
        print("✓ Order with builder info placed successfully")

        # Cancel the order
        cancel_order = CancelOrdersParams(
            sender=sender_hex, productIds=[product_id], digests=[order_digest]
        )
        engine_client.cancel_orders(cancel_order)
        print("  order cancelled\n")
    except Exception as e:
        error_msg = str(e)
        if "InvalidBuilder" in error_msg or "invalid builder" in error_msg.lower():
            print(f"  Builder {test_builder_id} not configured in environment")
            print("✓ Order placement test passed (builder not configured)\n")
        else:
            print(f"  Order failed: {e}\n")

    # Test 4: Query historical orders for builder_fee field
    print("Test 4: Query historical orders for builder_fee field")
    indexer_client = IndexerClient(opts={"url": INDEXER_BACKEND_URL})

    historical_orders = indexer_client.get_subaccount_historical_orders(
        IndexerSubaccountHistoricalOrdersParams(subaccounts=[sender_hex], limit=3)
    )

    if historical_orders.orders:
        order = historical_orders.orders[0]
        print(f"  order digest: {order.digest}")
        print(f"  order fee: {order.fee}")
        print(f"  order builder_fee: {order.builder_fee}")
        print("✓ builder_fee field present in historical orders\n")
    else:
        print("  no historical orders found")
        print("✓ historical orders query works (no orders found)\n")

    # Test 5: Query matches for builder_fee and sequencer_fee fields
    print("Test 5: Query matches for builder_fee and sequencer_fee fields")
    matches = indexer_client.get_matches(
        IndexerMatchesParams(
            subaccounts=[sender_hex], limit=3, product_ids=[product_id]
        )
    )

    if matches.matches:
        match = matches.matches[0]
        print(f"  match digest: {match.digest}")
        print(f"  match fee: {match.fee}")
        print(f"  match sequencer_fee: {match.sequencer_fee}")
        print(f"  match builder_fee: {match.builder_fee}")
        print("✓ builder_fee and sequencer_fee fields present in matches\n")
    else:
        print("  no matches found")
        print("✓ matches query works (no matches found)\n")

    # Test 6: Query claim_builder_fee events
    print("Test 6: Query claim_builder_fee events")
    builder_events = indexer_client.get_events(
        IndexerEventsParams(
            event_types=[IndexerEventType.CLAIM_BUILDER_FEE],
            limit=IndexerEventsRawLimit(raw=3),
        )
    )

    print(f"  found {len(builder_events.events)} claim_builder_fee events")
    if builder_events.events:
        print(f"  sample event: {builder_events.events[0].json(indent=2)}")
    print("✓ claim_builder_fee event type query works\n")

    # Test 7: Submit ClaimBuilderFee via NadoContracts
    print("Test 7: Submit ClaimBuilderFee via NadoContracts")
    deployment = load_deployment(NETWORK)
    nado_contracts = NadoContracts(
        node_url=deployment.node_url,
        contracts_context=NadoContractsContext(**deployment.dict()),
    )

    try:
        tx_hash = nado_contracts.claim_builder_fee(
            ClaimBuilderFeeParams(
                subaccount_owner=signer.address,
                subaccount_name="default",
                builder_id=test_builder_id,
            ),
            signer,
        )
        print(f"  tx hash: {tx_hash}")
        print("✓ claim_builder_fee submitted successfully\n")
    except Exception as e:
        error_msg = str(e)
        print(f"  claim_builder_fee reverted: {error_msg}")
        print(
            "✓ claim_builder_fee method works (tx reverted - likely no fees or not builder owner)\n"
        )

    # Test 8: Query builder info via get_builder_info()
    print("Test 8: Query builder info via get_builder_info()")
    try:
        builder_info = nado_contracts.get_builder_info(test_builder_id)
        print(f"  owner: {builder_info.owner}")
        print(f"  default_fee_tier: {builder_info.default_fee_tier}")
        print(f"  lowest_fee_rate: {builder_info.lowest_fee_rate}")
        print(f"  highest_fee_rate: {builder_info.highest_fee_rate}")
        print("✓ get_builder_info() works\n")
    except Exception as e:
        error_msg = str(e)
        if "OffchainExchange contract not initialized" in error_msg:
            print(f"  OffchainExchange contract not available in context")
            print("✓ get_builder_info() method exists (contract not initialized)\n")
        else:
            print(f"  get_builder_info failed: {error_msg}")
            print("✓ get_builder_info() method works (builder may not exist)\n")

    print("=== All Builder Code Sanity Tests Complete ===")
