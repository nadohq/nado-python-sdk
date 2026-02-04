Builder Integration
===================

The Builder Code system allows trading interfaces (builders) to earn fees on orders placed through their platforms. When users place orders through a builder's interface, the builder can receive a portion of the trade value as fees.

.. note::

   For more details on the Builder Integration system, see the `official Nado documentation <https://docs.nado.xyz/developer-resources/api/builder-integration>`_.

Overview
--------

How It Works
~~~~~~~~~~~~

1. **Builder Registration**: Contact the Nado team to get registered as a builder
2. **Order Placement**: Users place orders through your interface with your builder ID and fee rate in the order appendix
3. **Fee Collection**: When orders are matched, builder fees are automatically collected
4. **Fee Claiming**: Claim accumulated fees to your subaccount, then withdraw normally

Key Concepts
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Term
     - Description
   * - Builder ID
     - Unique 16-bit identifier for the builder (1-65535)
   * - Builder Fee Rate
     - Fee rate in units of 0.1bps (0.001%)

Fee Rate Units
~~~~~~~~~~~~~~

Builder fee rates are specified in **0.1bps units** (0.001% per unit):

- 1 unit = 0.001% = 0.00001
- 10 units = 0.01% = 1bps
- 50 units = 0.05% = 5bps
- 100 units = 0.1% = 10bps

Placing Orders with Builder Info
--------------------------------

To route orders through your builder and collect fees, include your builder information in the order ``appendix`` using the ``build_appendix`` function.

Basic Example
~~~~~~~~~~~~~

.. code-block:: python

    from nado_protocol.utils.order import build_appendix
    from nado_protocol.utils.expiration import OrderType

    # Create appendix with builder info
    # builder_id: Your registered builder ID
    # builder_fee_rate: Fee rate in 0.1bps units (e.g., 50 = 5bps = 0.05%)
    appendix = build_appendix(
        order_type=OrderType.DEFAULT,
        builder_id=2,
        builder_fee_rate=50  # 5bps = 0.05%
    )

Complete Order Placement Example
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from eth_account import Account
    from nado_protocol.engine_client import EngineClient, EngineClientOpts
    from nado_protocol.engine_client.types.execute import PlaceOrderParams, OrderParams
    from nado_protocol.utils.order import build_appendix
    from nado_protocol.utils.expiration import OrderType, get_expiration_timestamp
    from nado_protocol.utils.math import to_pow_10, to_x18
    from nado_protocol.utils.nonce import gen_order_nonce
    from nado_protocol.utils.subaccount import SubaccountParams

    # Initialize client
    signer = Account.from_key("YOUR_PRIVATE_KEY")
    engine_client = EngineClient(
        opts=EngineClientOpts(url="https://gateway.prod.nado.xyz/v1", signer=signer)
    )

    # Get contracts info
    contracts = engine_client.get_contracts()
    engine_client.endpoint_addr = contracts.endpoint_addr
    engine_client.chain_id = contracts.chain_id

    # Build appendix with builder info
    builder_appendix = build_appendix(
        order_type=OrderType.DEFAULT,
        builder_id=2,           # Your builder ID
        builder_fee_rate=50     # 5bps fee rate
    )

    # Create order
    order = OrderParams(
        sender=SubaccountParams(
            subaccount_owner=signer.address,
            subaccount_name="default"
        ),
        priceX18=to_x18(100000),         # Price in x18 format
        amount=to_pow_10(1, 16),          # 0.01 BTC
        expiration=get_expiration_timestamp(60),  # 60 seconds from now
        nonce=gen_order_nonce(),
        appendix=builder_appendix
    )

    # Place order
    product_id = 2  # BTC-PERP
    result = engine_client.place_order(
        PlaceOrderParams(product_id=product_id, order=order)
    )
    print(f"Order placed: {result}")

Combining Builder with Other Appendix Options
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Builder info can be combined with other order options like IOC, reduce-only, or isolated positions:

.. code-block:: python

    from nado_protocol.utils.order import build_appendix
    from nado_protocol.utils.expiration import OrderType
    from nado_protocol.utils.math import to_x6

    # IOC order with builder fee
    ioc_builder_appendix = build_appendix(
        order_type=OrderType.IOC,
        builder_id=2,
        builder_fee_rate=30  # 3bps
    )

    # Reduce-only order with builder fee
    reduce_only_builder_appendix = build_appendix(
        order_type=OrderType.DEFAULT,
        reduce_only=True,
        builder_id=2,
        builder_fee_rate=25  # 2.5bps
    )

    # Isolated position with builder fee
    isolated_builder_appendix = build_appendix(
        order_type=OrderType.DEFAULT,
        isolated=True,
        isolated_margin=to_x6(1000),  # 1000 USDC margin
        builder_id=2,
        builder_fee_rate=50  # 5bps
    )

Extracting Builder Info from Appendix
-------------------------------------

You can extract builder information from an existing appendix:

.. code-block:: python

    from nado_protocol.utils.order import (
        build_appendix,
        order_builder_id,
        order_builder_fee_rate,
        order_builder_info
    )
    from nado_protocol.utils.expiration import OrderType

    # Create appendix
    appendix = build_appendix(
        order_type=OrderType.DEFAULT,
        builder_id=2,
        builder_fee_rate=50
    )

    # Extract individual fields
    builder_id = order_builder_id(appendix)
    fee_rate = order_builder_fee_rate(appendix)

    # Or get both as a tuple
    builder_info = order_builder_info(appendix)  # Returns (builder_id, fee_rate) or None

    print(f"Builder ID: {builder_id}")
    print(f"Fee Rate: {fee_rate} (0.1bps units)")
    print(f"Builder Info: {builder_info}")

Querying Orders with Builder Fees
---------------------------------

When querying historical orders or matches, the builder fee is included in the response:

Querying Historical Orders
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from nado_protocol.indexer_client import IndexerClient
    from nado_protocol.utils.order import order_builder_id, order_builder_fee_rate

    indexer = IndexerClient(opts={"url": "https://archive.prod.nado.xyz/v1"})

    # Query order by digest
    orders = indexer.get_historical_orders_by_digest(["0x...order_digest..."])

    if orders.orders:
        order = orders.orders[0]
        print(f"Digest: {order.digest}")
        print(f"Total Fee: {order.fee}")
        print(f"Builder Fee: {order.builder_fee}")

        # Extract builder info from appendix
        if order.appendix:
            appendix_int = int(order.appendix)
            print(f"Builder ID: {order_builder_id(appendix_int)}")
            print(f"Builder Fee Rate: {order_builder_fee_rate(appendix_int)}")

Querying Match Events
~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from nado_protocol.indexer_client import IndexerClient
    from nado_protocol.indexer_client.types.query import IndexerMatchesParams

    indexer = IndexerClient(opts={"url": "https://archive.prod.nado.xyz/v1"})

    # Query matches for a subaccount
    sender_hex = "0x..."  # Your subaccount hex
    matches = indexer.get_matches(
        IndexerMatchesParams(
            subaccounts=[sender_hex],
            product_ids=[2],  # BTC-PERP
            limit=10
        )
    )

    for match in matches.matches:
        print(f"Digest: {match.digest}")
        print(f"Base Filled: {match.base_filled}")
        print(f"Total Fee: {match.fee}")
        print(f"Sequencer Fee: {match.sequencer_fee}")
        print(f"Builder Fee: {match.builder_fee}")

Claiming Builder Fees
---------------------

Builders can claim their accumulated fees using the ``claim_builder_fee`` method on ``NadoContracts``.

.. note::

    Claiming builder fees requires a 1 USDT slow mode fee. Make sure to approve the fee before claiming.

Complete Claiming Example
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: python

    from eth_account import Account
    from nado_protocol.contracts import (
        NadoContracts,
        NadoContractsContext,
        ClaimBuilderFeeParams
    )
    from nado_protocol.contracts.loader import load_deployment
    from nado_protocol.utils.math import to_pow_10

    # Load deployment config
    deployment = load_deployment("mainnet")  # or "testnet"

    # Initialize contracts
    nado_contracts = NadoContracts(
        node_url=deployment.node_url,
        contracts_context=NadoContractsContext(**deployment.dict()),
    )

    signer = Account.from_key("YOUR_PRIVATE_KEY")

    # Approve 1 USDT for slow mode fee
    usdt_token = nado_contracts.get_token_contract_for_product(0)
    slow_mode_fee = to_pow_10(1, 6)  # 1 USDT
    approve_tx = nado_contracts.approve_allowance(usdt_token, slow_mode_fee, signer)
    print(f"Approval tx: {approve_tx}")

    # Wait for approval to be mined
    import time
    time.sleep(5)

    # Claim builder fees
    tx_hash = nado_contracts.claim_builder_fee(
        ClaimBuilderFeeParams(
            subaccount_owner=signer.address,
            subaccount_name="default",
            builder_id=2  # Your builder ID
        ),
        signer
    )
    print(f"Claim tx: {tx_hash}")

Encoding ClaimBuilderFee Transaction Manually
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to encode the transaction manually:

.. code-block:: python

    from nado_protocol.utils.slow_mode import (
        SlowModeTxType,
        encode_claim_builder_fee_tx
    )
    from nado_protocol.utils.bytes32 import subaccount_to_bytes32

    # Encode the transaction
    sender_bytes = subaccount_to_bytes32("0xYourAddress", "default")
    builder_id = 2

    claim_tx = encode_claim_builder_fee_tx(sender_bytes, builder_id)

    # Verify tx type (should be 31)
    assert claim_tx[0] == SlowModeTxType.CLAIM_BUILDER_FEE

    print(f"Encoded tx: {claim_tx.hex()}")

Querying Builder Info
---------------------

You can query a builder's configuration:

.. code-block:: python

    from nado_protocol.contracts import NadoContracts, NadoContractsContext
    from nado_protocol.contracts.loader import load_deployment

    deployment = load_deployment("mainnet")
    nado_contracts = NadoContracts(
        node_url=deployment.node_url,
        contracts_context=NadoContractsContext(**deployment.dict()),
    )

    # Query builder info
    builder_id = 2
    builder_info = nado_contracts.get_builder_info(builder_id)

    print(f"Owner: {builder_info.owner}")
    print(f"Default Fee Tier: {builder_info.default_fee_tier}")
    print(f"Lowest Fee Rate: {builder_info.lowest_fee_rate}")
    print(f"Highest Fee Rate: {builder_info.highest_fee_rate}")

Querying Claim Events
---------------------

Query ``claim_builder_fee`` events from the indexer:

.. code-block:: python

    from nado_protocol.indexer_client import IndexerClient
    from nado_protocol.indexer_client.types.models import IndexerEventType
    from nado_protocol.indexer_client.types.query import (
        IndexerEventsParams,
        IndexerEventsRawLimit
    )

    indexer = IndexerClient(opts={"url": "https://archive.prod.nado.xyz/v1"})

    # Query claim events for your subaccount
    sender_hex = "0x..."  # Your subaccount hex
    events_data = indexer.get_events(
        IndexerEventsParams(
            subaccounts=[sender_hex],
            event_types=[IndexerEventType.CLAIM_BUILDER_FEE],
            limit=IndexerEventsRawLimit(raw=10)
        )
    )

    for event in events_data.events:
        # Find corresponding tx for timestamp
        tx = next(
            (t for t in events_data.txs if t.submission_idx == event.submission_idx),
            None
        )
        if tx:
            print(f"Claim event at timestamp: {tx.timestamp}")
            print(f"Pre-balance: {event.pre_balance}")
            print(f"Post-balance: {event.post_balance}")

Fee Calculation
---------------

Builder fees are calculated based on the trade's notional value:

.. code-block::

    builder_fee = maker_price × |base_filled| × builder_fee_rate / 10^18

**Example**: Buying 0.1 BTC at $100,000 with a 5bps (50 units) builder fee:

- Notional = $100,000 × 0.1 = $10,000
- Fee rate in x18 = 50 × 10^13 = 5 × 10^14
- Builder fee = $10,000 × 5 × 10^14 / 10^18 = $5

Validation Rules
----------------

Orders with builder information must satisfy:

1. **Builder Must Exist**: The builder ID must be registered
2. **Fee Rate Within Bounds**: Fee rate must be within your configured bounds (lowest_fee_rate to highest_fee_rate)
3. **No Fee Without Builder**: If ``builder_id == 0``, then ``builder_fee_rate`` must also be 0

Error Codes
~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - Error Code
     - Error Value
     - Description
   * - 2118
     - InvalidBuilder
     - Builder ID is invalid, not registered, or fee rate is outside allowed bounds

Getting Started
---------------

1. **Contact Nado Team**: Reach out to get registered as a builder
2. **Activate Subaccount**: Make a minimum $5 deposit to activate your subaccount
3. **Integrate**: Update your order placement to include builder info in the appendix
4. **Claim & Withdraw**: Periodically claim fees and withdraw to your wallet

API Reference
-------------

Order Appendix Functions
~~~~~~~~~~~~~~~~~~~~~~~~

- :func:`nado_protocol.utils.order.build_appendix` - Build an appendix with builder info
- :func:`nado_protocol.utils.order.order_builder_id` - Extract builder ID from appendix
- :func:`nado_protocol.utils.order.order_builder_fee_rate` - Extract fee rate from appendix
- :func:`nado_protocol.utils.order.order_builder_info` - Extract (builder_id, fee_rate) tuple

Slow Mode Functions
~~~~~~~~~~~~~~~~~~~

- :func:`nado_protocol.utils.slow_mode.encode_claim_builder_fee_tx` - Encode ClaimBuilderFee transaction
- :class:`nado_protocol.utils.slow_mode.SlowModeTxType` - Slow mode transaction types

Contract Methods
~~~~~~~~~~~~~~~~

- :meth:`nado_protocol.contracts.NadoContracts.claim_builder_fee` - Claim accumulated builder fees
- :meth:`nado_protocol.contracts.NadoContracts.get_builder_info` - Query builder configuration

See Also
--------

- :doc:`order-appendix` - Detailed appendix field documentation
- :doc:`getting-started` - Getting started with the SDK
- :doc:`user-reference` - API reference
