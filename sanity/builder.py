"""
Builder code sanity tests.

Tests:
1. Appendix encoding with builder fields
2. ClaimBuilderFee slow mode tx encoding
3. Placing order with builder info
4. Querying historical order for builder fee
5. Querying match events
6. Submitting ClaimBuilderFee slow mode transaction
7. Polling for claim_builder_fee event
Cleanup: Cancel order if still open
"""

import time
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
    test_builder_fee_rate = 50  # 5 bps (within builder 2's range of 0.2-5 bps)

    # Test 1: Appendix encoding with builder fields
    print("Test 1: Testing appendix encoding with builder fields")
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

    assert extracted_builder_id == test_builder_id, "Builder ID mismatch!"
    assert extracted_fee_rate == test_builder_fee_rate, "Builder fee rate mismatch!"
    assert builder_info == (
        test_builder_id,
        test_builder_fee_rate,
    ), "Builder info mismatch!"
    print("✓ Appendix encoding test passed\n")

    # Test 2: ClaimBuilderFee encoding
    print("Test 2: Testing ClaimBuilderFee encoding")
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

    # Test 3: Place order with builder info
    print("Test 3: Placing order with builder info")
    engine_client = EngineClient(
        opts=EngineClientOpts(url=ENGINE_BACKEND_URL, signer=SIGNER_PRIVATE_KEY)
    )

    contracts_data = engine_client.get_contracts()
    engine_client.endpoint_addr = contracts_data.endpoint_addr
    engine_client.chain_id = contracts_data.chain_id

    product_id = 2  # BTC-PERP

    # Get oracle price to ensure order is within 80-120% range
    all_products = engine_client.get_all_products()
    perp_product = next(
        (p for p in all_products.perp_products if p.product_id == product_id), None
    )
    if perp_product is None:
        raise Exception(f"Product {product_id} not found")
    oracle_price_x18 = int(perp_product.oracle_price_x18)

    # Place a buy order well above market to ensure fill (110% of oracle)
    # Round down to nearest price_increment_x18 (1e18)
    price_increment = 10**18
    order_price_x18 = int(oracle_price_x18 * 1.10)
    order_price_x18 = (order_price_x18 // price_increment) * price_increment

    builder_order = OrderParams(
        sender=SubaccountParams(
            subaccount_owner=signer.address, subaccount_name="default"
        ),
        priceX18=order_price_x18,
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

    order_placed = False
    try:
        place_order = PlaceOrderParams(product_id=product_id, order=builder_order)
        res = engine_client.place_order(place_order)
        print(f"  order placed: digest={order_digest}")
        print("✓ Order with builder info placed successfully")
        order_placed = True
    except Exception as e:
        error_msg = str(e)
        if "InvalidBuilder" in error_msg or "invalid builder" in error_msg.lower():
            print(f"  Builder {test_builder_id} not configured in test environment.")
            print("  Skipping order-based tests.")
            print("✓ Builder tests complete (encoding tests passed)\n")
            return
        raise e

    # Wait for order to process
    print("  waiting for order to process...")
    time.sleep(2)

    # Test 4: Query historical order for builder fee
    print("\nTest 4: Querying historical order for builder fee")
    indexer_client = IndexerClient(opts={"url": INDEXER_BACKEND_URL})

    historical_orders = indexer_client.get_historical_orders_by_digest([order_digest])

    if historical_orders.orders:
        order = historical_orders.orders[0]
        print(f"  Order found: digest={order.digest}")
        print(f"  baseFilled: {order.base_filled}")
        print(f"  totalFee: {order.fee}")
        print(f"  builderFee: {order.builder_fee}")
        if order.builder_fee and int(order.builder_fee) > 0:
            print("✓ Builder fee charged")

        # Check appendix has builder info
        if order.appendix:
            appendix_int = int(order.appendix)
            appendix_builder_id = order_builder_id(appendix_int)
            appendix_fee_rate = order_builder_fee_rate(appendix_int)
            print(f"  appendix.builder.builderId: {appendix_builder_id}")
            print(f"  appendix.builder.builderFeeRate: {appendix_fee_rate}")
            if appendix_builder_id != test_builder_id:
                raise Exception(
                    f"Order appendix builderId mismatch: expected {test_builder_id}, got {appendix_builder_id}"
                )
            print("✓ Builder info verified in order appendix")
    else:
        print("  Order not found in indexer yet")

    # Test 5: Query match events
    print("\nTest 5: Querying match events")
    matches = indexer_client.get_matches(
        IndexerMatchesParams(
            subaccounts=[sender_hex], limit=10, product_ids=[product_id]
        )
    )

    match_for_order = next(
        (m for m in matches.matches if m.digest == order_digest), None
    )
    if match_for_order:
        print(f"  Match found for order: digest={match_for_order.digest}")
        print(f"  baseFilled: {match_for_order.base_filled}")
        print(f"  totalFee: {match_for_order.fee}")
        print(f"  sequencerFee: {match_for_order.sequencer_fee}")
        print(f"  builderFee: {match_for_order.builder_fee}")
        if match_for_order.builder_fee and int(match_for_order.builder_fee) > 0:
            print("✓ Builder fee charged in match")
    else:
        print("  No match found for order yet (order may be unfilled)")

    # Test 6: Submit ClaimBuilderFee slow mode transaction
    print("\nTest 6: Submitting ClaimBuilderFee slow mode transaction")
    deployment = load_deployment(NETWORK)
    nado_contracts = NadoContracts(
        node_url=deployment.node_url,
        contracts_context=NadoContractsContext(**deployment.dict()),
    )

    # Approve 1 USDT for slow mode fee
    print("  approving slow mode fee (1 USDT)...")
    usdt_token = nado_contracts.get_token_contract_for_product(0)
    slow_mode_fee = to_pow_10(1, 6)  # 1 USDT
    try:
        approve_tx = nado_contracts.approve_allowance(usdt_token, slow_mode_fee, signer)
        print(f"  ✓ Slow mode fee approved: {approve_tx}")
        time.sleep(5)  # Wait for approval tx to be mined
    except Exception as e:
        print(f"  approval failed (may already be approved): {e}")

    claim_submit_time = int(time.time())

    try:
        tx_hash = nado_contracts.claim_builder_fee(
            ClaimBuilderFeeParams(
                subaccount_owner=signer.address,
                subaccount_name="default",
                builder_id=test_builder_id,
            ),
            signer,
        )
        print(f"✓ ClaimBuilderFee submitted, tx hash: {tx_hash}")

        # Test 7: Poll for claim_builder_fee event
        print("\nTest 7: Polling for claim_builder_fee event...")
        max_attempts = 10
        poll_interval = 2
        found = False

        for attempt in range(1, max_attempts + 1):
            if found:
                break
            time.sleep(poll_interval)
            events_data = indexer_client.get_events(
                IndexerEventsParams(
                    subaccounts=[sender_hex],
                    event_types=[IndexerEventType.CLAIM_BUILDER_FEE],
                    limit=IndexerEventsRawLimit(raw=5),
                )
            )

            # Match events to txs by submission_idx to get timestamp
            for event in events_data.events:
                tx = next(
                    (
                        t
                        for t in events_data.txs
                        if t.submission_idx == event.submission_idx
                    ),
                    None,
                )
                if tx and tx.timestamp and int(tx.timestamp) >= claim_submit_time - 10:
                    print(
                        f"  Found claim_builder_fee event on attempt {attempt} (timestamp: {tx.timestamp})"
                    )
                    print("✓ ClaimBuilderFee event verified")
                    found = True
                    break

            if not found:
                print(f"  Attempt {attempt}/{max_attempts}: not found yet...")

        if not found:
            print(
                "  No recent claim_builder_fee event found after polling (no fees accumulated or not builder owner)"
            )

    except Exception as e:
        error_msg = str(e)
        if "TF" in error_msg:
            print(
                "⚠ ClaimBuilderFee skipped: Slow mode requires 1 USDT0 fee (account may not have approved/funded)"
            )
        else:
            print(f"⚠ ClaimBuilderFee skipped: {error_msg}")
        # Not fatal - might not be builder owner, no fees, or insufficient USDT0

    # Cleanup: Cancel the order if it wasn't filled
    print("\nCleanup: Cancelling order if still open")
    if order_placed:
        try:
            cancel_order = CancelOrdersParams(
                sender=sender_hex, productIds=[product_id], digests=[order_digest]
            )
            engine_client.cancel_orders(cancel_order)
            print("✓ Order cancelled")
        except Exception:
            print("  Order already filled or cancelled")

    print("\n=== Builder E2E Tests Complete ===")
