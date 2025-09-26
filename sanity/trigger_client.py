import time
from sanity import ENGINE_BACKEND_URL, SIGNER_PRIVATE_KEY, TRIGGER_BACKEND_URL
from nado_protocol.engine_client import EngineClient
from nado_protocol.engine_client.types import EngineClientOpts
from nado_protocol.engine_client.types.execute import OrderParams
from nado_protocol.trigger_client import TriggerClient
from nado_protocol.trigger_client.types import TriggerClientOpts
from nado_protocol.trigger_client.types.execute import (
    PlaceTriggerOrderParams,
    CancelTriggerOrdersParams,
)
from nado_protocol.trigger_client.types.models import (
    PriceTrigger,
    LastPriceAbove,
    LastPriceBelow,
)
from nado_protocol.trigger_client.types.query import (
    ListTriggerOrdersParams,
    ListTriggerOrdersTx,
)
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.expiration import OrderType, get_expiration_timestamp
from nado_protocol.utils.order import OrderAppendixTriggerType, build_appendix
from nado_protocol.utils.math import to_pow_10, to_x18
from nado_protocol.utils.subaccount import SubaccountParams
from nado_protocol.utils.time import now_in_millis


def run():
    print("setting up trigger client...")
    client = TriggerClient(
        opts=TriggerClientOpts(url=TRIGGER_BACKEND_URL, signer=SIGNER_PRIVATE_KEY)
    )

    engine_client = EngineClient(
        opts=EngineClientOpts(url=ENGINE_BACKEND_URL, signer=SIGNER_PRIVATE_KEY)
    )

    contracts_data = engine_client.get_contracts()
    client.endpoint_addr = contracts_data.endpoint_addr
    client.chain_id = contracts_data.chain_id

    print("placing trigger order...")
    order_price = 100_000

    product_id = 1
    order = OrderParams(
        sender=SubaccountParams(
            subaccount_owner=client.signer.address, subaccount_name="default"
        ),
        priceX18=to_x18(order_price),
        amount=to_pow_10(1, 17),
        expiration=get_expiration_timestamp(40),
        appendix=build_appendix(
            OrderType.DEFAULT, trigger_type=OrderAppendixTriggerType.PRICE
        ),
        nonce=client.order_nonce(),
    )
    order_digest = client.get_order_digest(order, product_id)
    print("order digest:", order_digest)

    place_order = PlaceTriggerOrderParams(
        product_id=product_id,
        order=order,
        trigger=PriceTrigger(price_requirement=LastPriceAbove(last_price_above=str(to_x18(120_000)))),
    )
    res = client.place_trigger_order(place_order)
    print("trigger order result:", res.json(indent=2))

    sender = subaccount_to_hex(order.sender)

    cancel_orders = CancelTriggerOrdersParams(
        sender=sender, productIds=[product_id], digests=[order_digest]
    )
    res = client.cancel_trigger_orders(cancel_orders)
    print("cancel trigger order result:", res.json(indent=2))

    product_id = 2
    order = OrderParams(
        sender=SubaccountParams(
            subaccount_owner=client.signer.address, subaccount_name="default"
        ),
        priceX18=to_x18(order_price),
        amount=to_pow_10(1, 17),
        expiration=get_expiration_timestamp(40),
        appendix=build_appendix(
            OrderType.DEFAULT, trigger_type=OrderAppendixTriggerType.PRICE
        ),
        nonce=client.order_nonce(),
    )
    order_digest = client.get_order_digest(order, product_id)
    print("order digest:", order_digest)

    place_order = PlaceTriggerOrderParams(
        product_id=product_id,
        order=order,
        trigger=PriceTrigger(price_requirement=LastPriceAbove(last_price_above=str(to_x18(120_000)))),
    )
    res = client.place_trigger_order(place_order)

    print("listing trigger orders...")
    trigger_orders = client.list_trigger_orders(
        ListTriggerOrdersParams(
            tx=ListTriggerOrdersTx(
                sender=SubaccountParams(
                    subaccount_owner=client.signer.address, subaccount_name="default"
                ),
                recvTime=now_in_millis(90),
            ),
            pending=True,
            product_id=2,
        )
    )
    print("trigger orders:", trigger_orders.json(indent=2))

    print("\n" + "="*50)
    print("TWAP ORDER EXAMPLES")
    print("="*50)

    # Example 1: Basic TWAP order using convenience method
    print("\n1. Basic TWAP order (DCA strategy)")
    print("-" * 40)
    
    twap_res = client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(52_000)),  # Max $52k per execution
        total_amount_x18=str(to_pow_10(5, 18)),  # Buy 5 BTC total
        expiration=get_expiration_timestamp(60 * 24),  # 24 hours
        nonce=client.order_nonce(),
        times=10,  # Split into 10 executions
        slippage_frac=0.005,  # 0.5% slippage tolerance
        interval_seconds=3600,  # 1 hour intervals
    )
    print(f"TWAP order result: {twap_res.json(indent=2)}")

    # Example 2: TWAP order with custom amounts
    print("\n2. TWAP order with custom amounts (decreasing size)")
    print("-" * 55)
    
    # Custom amounts that decrease over time: 2 BTC, 1.5 BTC, 1 BTC, 0.5 BTC
    custom_amounts = [
        str(to_pow_10(2, 18)),    # 2 BTC
        str(to_pow_10(15, 17)),   # 1.5 BTC  
        str(to_pow_10(1, 18)),    # 1 BTC
        str(to_pow_10(5, 17)),    # 0.5 BTC
    ]
    total_amount = str(to_pow_10(5, 18))  # 5 BTC total
    
    custom_twap_res = client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(51_000)),  # Max $51k per execution
        total_amount_x18=total_amount,
        expiration=get_expiration_timestamp(60 * 12),  # 12 hours
        nonce=client.order_nonce(),
        times=4,  # 4 executions
        slippage_frac=0.01,  # 1% slippage tolerance
        interval_seconds=2700,  # 45 minute intervals
        custom_amounts_x18=custom_amounts,
    )
    print(f"Custom TWAP order result: {custom_twap_res.json(indent=2)}")

    # Example 3: TWAP sell order with reduce_only
    print("\n3. TWAP sell order (reduce-only position closing)")
    print("-" * 50)
    
    reduce_twap_res = client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(48_000)),  # Min $48k per execution
        total_amount_x18=str(-to_pow_10(3, 18)),  # Sell 3 BTC total (negative)
        expiration=get_expiration_timestamp(60 * 6),  # 6 hours
        nonce=client.order_nonce(),
        times=6,  # Split into 6 executions
        slippage_frac=0.0075,  # 0.75% slippage tolerance
        interval_seconds=1800,  # 30 minute intervals
        reduce_only=True,  # Only reduce existing position
    )
    print(f"Reduce-only TWAP result: {reduce_twap_res.json(indent=2)}")

    print("\n" + "="*50)
    print("PRICE TRIGGER ORDER EXAMPLES")
    print("="*50)

    # Example 4: Stop-loss order using convenience method
    print("\n4. Stop-loss order (last price below)")
    print("-" * 40)
    
    stop_loss_res = client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(45_000)),  # Sell at $45k
        amount_x18=str(-to_pow_10(1, 18)),  # Sell 1 BTC
        expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(46_000)),  # Trigger below $46k
        trigger_type="last_price_below",
        reduce_only=True,
    )
    print(f"Stop-loss order result: {stop_loss_res.json(indent=2)}")

    # Example 5: Take-profit order
    print("\n5. Take-profit order (last price above)")
    print("-" * 40)
    
    take_profit_res = client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(55_000)),  # Sell at $55k
        amount_x18=str(-to_pow_10(1, 18)),  # Sell 1 BTC
        expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(54_000)),  # Trigger above $54k
        trigger_type="last_price_above",
        reduce_only=True,
    )
    print(f"Take-profit order result: {take_profit_res.json(indent=2)}")

    # Example 6: Oracle-based trigger order
    print("\n6. Oracle price trigger order")
    print("-" * 35)
    
    oracle_trigger_res = client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(50_500)),  # Buy at $50.5k
        amount_x18=str(to_pow_10(1, 18)),  # Buy 1 BTC
        expiration=get_expiration_timestamp(60 * 24),  # 24 hours
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(50_000)),  # Trigger above $50k oracle price
        trigger_type="oracle_price_above",
    )
    print(f"Oracle trigger order result: {oracle_trigger_res.json(indent=2)}")

    # Example 7: Mid price trigger order
    print("\n7. Mid price trigger order")
    print("-" * 30)
    
    mid_price_trigger_res = client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(49_500)),  # Buy at $49.5k
        amount_x18=str(to_pow_10(5, 17)),  # Buy 0.5 BTC
        expiration=get_expiration_timestamp(60 * 12),  # 12 hours
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(49_000)),  # Trigger below $49k mid price
        trigger_type="mid_price_below",
    )
    print(f"Mid price trigger result: {mid_price_trigger_res.json(indent=2)}")

    print("\n" + "="*50)
    print("ADVANCED INTEGRATION SCENARIOS")
    print("="*50)

    # Example 8: Complete trading strategy - stop loss + take profit + DCA
    print("\n8. Complete trading strategy")
    print("-" * 30)
    print("Setting up: Stop-loss + Take-profit + DCA TWAP")
    
    # Stop-loss
    strategy_stop_loss = client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(44_000)),
        amount_x18=str(-to_pow_10(2, 18)),  # Close 2 BTC
        expiration=get_expiration_timestamp(60 * 24 * 30),  # 30 days
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(45_000)),
        trigger_type="last_price_below",
        reduce_only=True,
    )
    print(f"Strategy stop-loss: {strategy_stop_loss.status}")
    
    # Take-profit
    strategy_take_profit = client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(58_000)),
        amount_x18=str(-to_pow_10(2, 18)),  # Close 2 BTC
        expiration=get_expiration_timestamp(60 * 24 * 30),  # 30 days
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(57_000)),
        trigger_type="last_price_above",
        reduce_only=True,
    )
    print(f"Strategy take-profit: {strategy_take_profit.status}")
    
    # DCA TWAP
    strategy_dca = client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(52_000)),
        total_amount_x18=str(to_pow_10(10, 18)),  # Buy 10 BTC over time
        expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
        nonce=client.order_nonce(),
        times=20,  # 20 executions
        slippage_frac=0.005,
        interval_seconds=1800,  # 30 minutes
    )
    print(f"Strategy DCA TWAP: {strategy_dca.status}")
    
    print("\nComplete trading strategy deployed successfully!")
    print("- Stop-loss at $45k (protects downside)")
    print("- Take-profit at $57k (captures upside)")  
    print("- DCA TWAP over 1 week (builds position gradually)")

    print("\n" + "="*50)
    print("TWAP AND PRICE TRIGGER EXAMPLES COMPLETED")
    print("="*50)
