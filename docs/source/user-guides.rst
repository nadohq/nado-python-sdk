User guides
===========

Signing
-------

Signing is handled internally when you instantiate the `NadoClient` (:mod:`nado_protocol.client.NadoClient`) with a `signer`. Alternatively, 
you can construct the requisite signatures for each execute using a set utils provided by the SDK (see :mod:`nado_protocol.contracts.eip712` for details).

.. note::

    Check out our docs to learn more about `signing requests <TODO>`_ in Nado.

EIP-712
^^^^^^^

Nado executes are signed using `EIP-712 <https://eips.ethereum.org/EIPS/eip-712>`_ signatures. The following components are needed:

- **types**: The solidity object name and field types of the message being signed.
- **primaryType**: The name of the solidity object being signed.
- **domain**: A protocol-specific object that includes the verifying contract and `chain-id` of the network.
- **message**: The actual message being signed.

You can build the expected EIP-712 typed data for each execute via :mod:`nado_protocol.contracts.eip712.build_eip712_typed_data()`

**Place Order Example:**

.. code-block:: python

    >>> import time
    >>> from nado_protocol.contracts.types import NadoExecuteType
    >>> from nado_protocol.engine_client.types import OrderParams, SubaccountParams
    >>> from nado_protocol.utils import subaccount_to_bytes32, to_x18, to_pow_10, get_expiration_timestamp, gen_order_nonce, OrderType
    >>> from nado_protocol.utils.order import build_appendix, gen_order_verifying_contract
    >>> from nado_protocol.contracts.eip712 import build_eip712_typed_data
    >>> 
    >>> # For place orders, use product-specific verifying contract
    >>> product_id = 1
    >>> verifying_contract = gen_order_verifying_contract(product_id)  # "0x0000000000000000000000000000000000000001"
    >>> chain_id = 421613
    >>> sender = SubaccountParams(subaccount_owner="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266", subaccount_name="default")
    >>> order_nonce = gen_order_nonce()
    >>> order_expiration = get_expiration_timestamp(40)
    >>> appendix = build_appendix(OrderType.POST_ONLY)
    >>> order = OrderParams(amount=to_x18(20000), priceX18=to_pow_10(1, 17), expiration=order_expiration, nonce=order_nonce, sender=sender, appendix=appendix)
    >>> order_typed_data = build_eip712_typed_data(NadoExecuteType.PLACE_ORDER, order.dict(), verifying_contract, chain_id)

**Other Execute Types Example:**

.. code-block:: python

    >>> from nado_protocol.contracts.types import NadoExecuteType
    >>> from nado_protocol.engine_client.types import CancelOrdersParams
    >>> from nado_protocol.contracts.eip712 import build_eip712_typed_data
    >>> 
    >>> # For non-place-order executes, use main endpoint verifying contract
    >>> endpoint_verifying_contract = "0x2279B7A0a67DB372996a5FaB50D91eAA73d2eBe6"  # from get_contracts()
    >>> chain_id = 421613
    >>> cancel_params = CancelOrdersParams(sender=sender, productIds=[1], digests=["0x..."], nonce=1)
    >>> cancel_typed_data = build_eip712_typed_data(NadoExecuteType.CANCEL_ORDERS, cancel_params.dict(), endpoint_verifying_contract, chain_id)

The following object is generated and can be signed via :mod:`nado_protocol.contracts.eip712.sign_eip712_typed_data()`:

.. code-block:: python

    {   
        'types': {
            'EIP712Domain': [
                {'name': 'name', 'type': 'string'},
                {'name': 'version', 'type': 'string'},
                {'name': 'chainId', 'type': 'uint256'},
                {'name': 'verifyingContract', 'type': 'address'}
            ],
            'Order': [
                {'name': 'sender', 'type': 'bytes32'},
                {'name': 'priceX18', 'type': 'int128'},
                {'name': 'amount', 'type': 'int128'},
                {'name': 'expiration', 'type': 'uint64'},
                {'name': 'nonce', 'type': 'uint64'},
                {'name': 'appendix', 'type': 'uint128'}
            ]
        },
        'primaryType': 'Order',
        'domain': {
            'name': 'Nado',
            'version': '0.0.1',
            'chainId': 421613,
            'verifyingContract': '0x0000000000000000000000000000000000000001'  # Product-specific for place orders
        },
        'message': {
            'sender': b'\xf3\x9f\xd6\xe5\x1a\xad\x88\xf6\xf4\xcej\xb8\x82ry\xcf\xff\xb9"fdefault\x00\x00\x00\x00\x00',
            'nonce': 1768628938411606731,
            'priceX18': 100000000000000000,
            'amount': 20000000000000000000000,
            'expiration': 1686695965,
            'appendix': 0
        }
    }

Verifying Contracts
^^^^^^^^^^^^^^^^^^^^

**Important**: Different execute types use different verifying contracts for signatures:

- **Place Order (`PLACE_ORDER`)**: Uses a product-specific verifying contract generated via :mod:`nado_protocol.utils.order.gen_order_verifying_contract(product_id)`

  .. code-block:: python
  
      from nado_protocol.utils.order import gen_order_verifying_contract
      verifying_contract = gen_order_verifying_contract(1)  # "0x0000000000000000000000000000000000000001"

- **All other executes** (`CANCEL_ORDERS`, `WITHDRAW_COLLATERAL`, etc.): Use the main endpoint verifying contract from :mod:`nado_protocol.engine_client.EngineQueryClient.get_contracts()`

  .. code-block:: python
  
      contracts = client.context.engine_client.get_contracts()
      verifying_contract = contracts.endpoint_addr

.. note::

    - You can retrieve the main endpoint verifying contracts using :mod:`nado_protocol.engine_client.EngineQueryClient.get_contracts()`. Provided via **client.context.engine_client.get_contracts()** on a `NadoClient` instance.
    - You can also just use the engine client's sign utility :mod:`nado_protocol.engine_client.EngineExecuteClient.sign()`. Provided via **client.context.engine_client.sign()** on a `NadoClient` instance.

TWAP and Trigger Orders
-----------------------

The SDK provides comprehensive support for Time-Weighted Average Price (TWAP) orders and conditional price trigger orders through the :mod:`nado_protocol.trigger_client` module.

TWAP Orders
^^^^^^^^^^^

TWAP (Time-Weighted Average Price) orders allow you to execute large trades over time with controlled slippage and timing. This is particularly useful for:

- **Dollar Cost Averaging (DCA)**: Building positions gradually over time
- **Large Order Execution**: Minimizing market impact when trading large amounts
- **Automated Trading**: Setting up systematic trading strategies

**Basic TWAP Order:**

.. code-block:: python

    from nado_protocol.trigger_client import TriggerClient
    from nado_protocol.trigger_client.types import TriggerClientOpts
    from nado_protocol.utils.math import to_x18
    from nado_protocol.utils.expiration import get_expiration_timestamp

    # Create trigger client
    trigger_client = TriggerClient(
        opts=TriggerClientOpts(url=TRIGGER_BACKEND_URL, signer=private_key)
    )

    # Place a TWAP order to buy 5 BTC over 2 hours
    twap_result = trigger_client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(50_000)),        # Max $50k per execution
        total_amount_x18=str(to_x18(5)),      # Buy 5 BTC total
        expiration=get_expiration_timestamp(60 * 24),  # 24 hours
        nonce=client.order_nonce(),
        times=10,                             # Split into 10 executions
        slippage_frac=0.005,                  # 0.5% slippage tolerance
        interval_seconds=720,                 # 12 minutes between executions
    )

**TWAP with Custom Amounts:**

For advanced strategies, you can specify custom amounts for each execution:

.. code-block:: python

    # Decreasing size strategy: larger amounts first
    custom_amounts = [
        str(to_x18(2)),      # 2 BTC first
        str(to_x18(1.5)),    # 1.5 BTC second
        str(to_x18(1)),      # 1 BTC third
        str(to_x18(0.5)),    # 0.5 BTC last
    ]

    custom_twap_result = trigger_client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(51_000)),
        total_amount_x18=str(to_x18(5)),      # 5 BTC total
        expiration=get_expiration_timestamp(60 * 12),
        nonce=client.order_nonce(),
        times=4,                              # 4 executions
        slippage_frac=0.01,                   # 1% slippage
        interval_seconds=1800,                # 30 minutes
        custom_amounts_x18=custom_amounts,
        reduce_only=False,                    # Can increase position
    )

Price Trigger Orders
^^^^^^^^^^^^^^^^^^^^

Price trigger orders are conditional orders that execute when specific price conditions are met. Common use cases include:

- **Stop-Loss Orders**: Automatically close positions to limit losses
- **Take-Profit Orders**: Automatically realize gains at target prices  
- **Breakout Trading**: Enter positions when price breaks key levels
- **Automated Risk Management**: Set up protective orders

**Supported Trigger Types:**

- ``"last_price_above"``: Trigger when last traded price goes above threshold
- ``"last_price_below"``: Trigger when last traded price goes below threshold  
- ``"oracle_price_above"``: Trigger when oracle price goes above threshold
- ``"oracle_price_below"``: Trigger when oracle price goes below threshold
- ``"mid_price_above"``: Trigger when mid price (bid+ask)/2 goes above threshold
- ``"mid_price_below"``: Trigger when mid price (bid+ask)/2 goes below threshold

**Stop-Loss Example:**

.. code-block:: python

    # Stop-loss order: sell if price drops below $45k
    stop_loss = trigger_client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(44_000)),        # Sell at $44k
        amount_x18=str(-to_x18(1)),           # Sell 1 BTC (negative for sell)
        expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(45_000)), # Trigger below $45k
        trigger_type="last_price_below",
        reduce_only=True,                     # Only reduce existing position
    )

**Take-Profit Example:**

.. code-block:: python

    # Take-profit order: sell if price rises above $55k
    take_profit = trigger_client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(56_000)),        # Sell at $56k
        amount_x18=str(-to_x18(1)),           # Sell 1 BTC
        expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(55_000)), # Trigger above $55k
        trigger_type="last_price_above",
        reduce_only=True,                     # Only reduce position
    )

Complete Trading Strategy
^^^^^^^^^^^^^^^^^^^^^^^^^

Here's how to implement a complete automated trading strategy combining multiple order types:

.. code-block:: python

    # 1. Protective stop-loss
    stop_loss = trigger_client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(44_000)),
        amount_x18=str(-to_x18(2)),           # Close 2 BTC position
        expiration=get_expiration_timestamp(60 * 24 * 30),  # 30 days
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(45_000)),
        trigger_type="last_price_below",
        reduce_only=True,
    )

    # 2. Profit-taking target
    take_profit = trigger_client.place_price_trigger_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(58_000)),
        amount_x18=str(-to_x18(2)),           # Close 2 BTC position
        expiration=get_expiration_timestamp(60 * 24 * 30),  # 30 days
        nonce=client.order_nonce(),
        trigger_price_x18=str(to_x18(57_000)),
        trigger_type="last_price_above", 
        reduce_only=True,
    )

    # 3. Gradual position building with TWAP
    dca_strategy = trigger_client.place_twap_order(
        product_id=1,
        sender=client.signer.address,
        price_x18=str(to_x18(52_000)),        # Max $52k per buy
        total_amount_x18=str(to_x18(10)),     # Buy 10 BTC over time
        expiration=get_expiration_timestamp(60 * 24 * 7),  # 1 week
        nonce=client.order_nonce(),
        times=20,                             # 20 executions
        slippage_frac=0.005,                  # 0.5% slippage tolerance
        interval_seconds=1800,                # 30 minutes between buys
    )

.. note::

    **Best Practices for TWAP and Trigger Orders:**
    
    - Use ``reduce_only=True`` for risk management orders (stop-loss, take-profit)
    - Set appropriate ``slippage_frac`` values (0.5-1% is common for liquid markets)
    - Consider market hours and liquidity when setting ``interval_seconds``
    - Always set reasonable ``expiration`` times to avoid stale orders
    - Test strategies with small amounts before scaling up