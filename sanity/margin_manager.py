"""
Margin Manager Sanity Test

This script demonstrates the margin manager functionality using read-only access.
It can analyze any public subaccount without requiring a private key.

Usage:
    python -m sanity.margin_manager

To analyze a specific wallet, set the TEST_WALLET constant below.
"""

import sys
import time
from decimal import Decimal
from nado_protocol.engine_client import EngineQueryClient, EngineClientOpts
from nado_protocol.indexer_client import IndexerQueryClient, IndexerClientOpts
from nado_protocol.indexer_client.types.query import IndexerAccountSnapshotsParams
from nado_protocol.utils.bytes32 import subaccount_to_hex
from nado_protocol.utils.math import from_x18
from nado_protocol.utils.margin_manager import MarginManager, print_account_summary

# Wallet to analyze (can be any public wallet address)
# Example wallet from margin manager screenshot
TEST_WALLET = "0x8D7d64d6cF1D4F018Dd101482Ac71Ad49e30c560"


def run():
    """Test margin manager with a real subaccount."""
    print("\n" + "=" * 80)
    print("MARGIN MANAGER SANITY TEST")
    print(f"Testing wallet: {TEST_WALLET}")
    print("=" * 80)

    # Setup clients (read-only, no private key needed)
    print("\n[1/6] Setting up clients...")
    engine_client = EngineQueryClient(
        EngineClientOpts(url="https://gateway.test.nado-backend.xyz/v1")
    )
    indexer_client = IndexerQueryClient(
        IndexerClientOpts(url="https://archive.test.nado-backend.xyz/v1")
    )
    subaccount = subaccount_to_hex(TEST_WALLET, "default")
    print(f"  Subaccount: {subaccount}")

    # Fetch subaccount info
    print("\n[2/6] Fetching subaccount information...")
    try:
        subaccount_info = engine_client.get_subaccount_info(subaccount)
        print(f"  ✓ Found {len(subaccount_info.spot_balances)} spot balances")
        print(f"  ✓ Found {len(subaccount_info.perp_balances)} perp balances")
    except Exception as e:
        print(f"  ✗ Error fetching subaccount: {e}")
        sys.exit(1)

    # Fetch isolated positions
    print("\n[3/6] Fetching isolated positions...")
    try:
        isolated_positions_data = engine_client.get_isolated_positions(subaccount)
        isolated_positions = isolated_positions_data.isolated_positions
        print(f"  ✓ Found {len(isolated_positions)} isolated positions")
    except Exception as e:
        print(f"  ⚠ Warning: Could not fetch isolated positions: {e}")
        isolated_positions = []

    # Fetch indexer snapshot for Est. PnL calculation
    print("\n[4/6] Fetching indexer snapshot...")
    try:
        current_timestamp = int(time.time())
        snapshot_response = indexer_client.get_multi_subaccount_snapshots(
            IndexerAccountSnapshotsParams(
                subaccounts=[subaccount],
                timestamps=[current_timestamp],
                isolated=False,
                active=True,
            )
        )
        snapshots_for_subaccount = snapshot_response.snapshots.get(subaccount, {})
        requested_key = str(current_timestamp)
        snapshot_events = snapshots_for_subaccount.get(requested_key)

        if snapshot_events is None and snapshots_for_subaccount:
            latest_key = max(snapshots_for_subaccount.keys(), key=int)
            snapshot_events = snapshots_for_subaccount[latest_key]

        if snapshot_events:
            indexer_snapshot_events = snapshot_events
            print(f"  ✓ Fetched snapshot with {len(snapshot_events)} balances")
        else:
            indexer_snapshot_events = []
            print("  ⚠ Warning: No snapshot data found for requested timestamps")
    except Exception as e:
        print(f"  ⚠ Warning: Could not fetch indexer snapshot: {e}")
        import traceback

        traceback.print_exc()
        indexer_snapshot_events = []

    # Debug: Print snapshot structure
    if indexer_snapshot_events:
        print("\n[DEBUG] Indexer snapshot structure:")
        print(f"  Number of balances: {len(indexer_snapshot_events)}")
        first_balance = indexer_snapshot_events[0]
        print(f"  First balance fields: {list(first_balance.__fields__.keys())}")
        print(f"  First balance product_id: {first_balance.product_id}")
        print(
            "  Tracked vars: net_entry_unrealized, net_entry_cumulative, net_funding_unrealized, net_funding_cumulative, net_interest_unrealized, net_interest_cumulative"
        )

    # Create margin manager
    print("\n[5/6] Initializing margin manager...")
    margin_manager = MarginManager(
        subaccount_info,
        isolated_positions,
        indexer_snapshot_events=indexer_snapshot_events,
    )
    print("  ✓ Margin manager initialized")

    # Calculate summary
    print("\n[6/6] Calculating account summary...")
    try:
        summary = margin_manager.calculate_account_summary()
        print("  ✓ Calculations complete")
    except Exception as e:
        print(f"  ✗ Error calculating summary: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

    # Display results
    print_account_summary(summary)

    # Additional detailed analysis
    print("\n" + "=" * 80)
    print("DETAILED ANALYSIS")
    print("=" * 80)

    # Show raw health values from engine
    # healths is a list: [initial, maintenance, unweighted]
    print("\n📋 RAW HEALTH VALUES (from engine)")
    print(
        f"  Initial Assets:      ${from_x18(int(subaccount_info.healths[0].assets)):,.2f}"
    )
    print(
        f"  Initial Liabilities: ${from_x18(int(subaccount_info.healths[0].liabilities)):,.2f}"
    )
    print(
        f"  Initial Health:      ${from_x18(int(subaccount_info.healths[0].health)):,.2f}"
    )
    print()
    print(
        f"  Maint Assets:        ${from_x18(int(subaccount_info.healths[1].assets)):,.2f}"
    )
    print(
        f"  Maint Liabilities:   ${from_x18(int(subaccount_info.healths[1].liabilities)):,.2f}"
    )
    print(
        f"  Maint Health:        ${from_x18(int(subaccount_info.healths[1].health)):,.2f}"
    )
    print()
    print(
        f"  Unweighted Health:   ${from_x18(int(subaccount_info.healths[2].health)):,.2f}"
    )

    # Show spot balances in detail
    if subaccount_info.spot_balances:
        print("\n💵 SPOT BALANCES DETAIL")
        for i, (balance, product) in enumerate(
            zip(subaccount_info.spot_balances, subaccount_info.spot_products)
        ):
            amount = Decimal(from_x18(int(balance.balance.amount)))
            oracle_price = Decimal(from_x18(int(product.oracle_price_x18)))
            value = amount * oracle_price

            if amount == 0:
                continue

            balance_type = "Deposit" if amount > 0 else "Borrow"
            print(f"\n  [{i}] Product ID {balance.product_id}")
            print(f"      Type:         {balance_type}")
            print(f"      Amount:       {amount:,.6f}")
            print(f"      Oracle Price: ${oracle_price:,.2f}")
            print(f"      Value:        ${value:,.2f}")
            print(f"      Weights:")
            print(
                f"        Long Initial:  {from_x18(int(product.risk.long_weight_initial_x18)):.4f}"
            )
            print(
                f"        Long Maint:    {from_x18(int(product.risk.long_weight_maintenance_x18)):.4f}"
            )
            print(
                f"        Short Initial: {from_x18(int(product.risk.short_weight_initial_x18)):.4f}"
            )
            print(
                f"        Short Maint:   {from_x18(int(product.risk.short_weight_maintenance_x18)):.4f}"
            )

    # Show perp balances in detail
    if subaccount_info.perp_balances:
        print("\n🔄 PERP BALANCES DETAIL")
        for i, (balance, product) in enumerate(
            zip(subaccount_info.perp_balances, subaccount_info.perp_products)
        ):
            amount = Decimal(from_x18(int(balance.balance.amount)))
            if amount == 0:
                continue

            oracle_price = Decimal(from_x18(int(product.oracle_price_x18)))
            v_quote = Decimal(from_x18(int(balance.balance.v_quote_balance)))
            notional = abs(amount * oracle_price)
            position_value = amount * oracle_price + v_quote

            position_type = "Long" if amount > 0 else "Short"
            print(f"\n  [{i}] Product ID {balance.product_id}")
            print(f"      Type:          {position_type}")
            print(f"      Size:          {amount:,.6f}")
            print(f"      Oracle Price:  ${oracle_price:,.2f}")
            print(f"      Notional:      ${notional:,.2f}")
            print(f"      V Quote:       ${v_quote:,.2f}")
            print(f"      Position Value: ${position_value:,.2f}")
            print(f"      Weights:")
            print(
                f"        Long Initial:  {from_x18(int(product.risk.long_weight_initial_x18)):.4f}"
            )
            print(
                f"        Long Maint:    {from_x18(int(product.risk.long_weight_maintenance_x18)):.4f}"
            )

    # Key insights
    print("\n" + "=" * 80)
    print("KEY INSIGHTS")
    print("=" * 80)

    liquidation_risk = summary.maint_margin_usage_fraction * 100
    if liquidation_risk > 90:
        risk_level = "CRITICAL 🔴"
    elif liquidation_risk > 75:
        risk_level = "HIGH 🟠"
    elif liquidation_risk > 50:
        risk_level = "MEDIUM 🟡"
    else:
        risk_level = "LOW 🟢"

    print(f"\n• Liquidation Risk: {risk_level} ({liquidation_risk:.1f}%)")
    print(f"• Account Leverage: {summary.account_leverage:.2f}x")
    print(f"• Can Open New Positions: {'Yes' if summary.funds_available > 0 else 'No'}")

    if summary.funds_available > 0:
        print(f"  → Available capital: ${summary.funds_available:,.2f}")
    else:
        print(f"  → Need to reduce leverage by ${abs(summary.initial_health):,.2f}")

    if summary.funds_until_liquidation > 0:
        print(f"• Distance to Liquidation: ${summary.funds_until_liquidation:,.2f}")
    else:
        print("• ⚠️  ACCOUNT IS UNDERWATER - Liquidation risk!")

    print("\n" + "=" * 80)
    print("TEST COMPLETE ✓")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run()
