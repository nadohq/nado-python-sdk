"""Tests for v2 API-parity additions: batch place_orders and indexer ink_airdrop."""

from unittest.mock import MagicMock

import pytest

from nado_protocol.client import NadoClient
from nado_protocol.engine_client import EngineClient
from nado_protocol.engine_client.types.execute import (
    OrderParams,
    PlaceOrderParams,
    PlaceOrdersParams,
    PlaceOrdersRequest,
    TransferQuoteParams,
    WithdrawCollateralV2Params,
)
from nado_protocol.indexer_client import IndexerClient
from nado_protocol.indexer_client.types import IndexerClientOpts
from nado_protocol.indexer_client.types.query import IndexerNlpSnapshotsParams


def _query_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"status": "success", "data": data}
    return resp


def _order(sender: str, nonce: int) -> PlaceOrderParams:
    return PlaceOrderParams(
        product_id=1,
        order=OrderParams(
            sender=sender,
            priceX18=1000,
            amount=1000,
            expiration=1000,
            nonce=nonce,
            appendix=0,
        ),
    )


def test_place_orders_signs_each_order(
    engine_client: EngineClient, mock_post: MagicMock, senders: list[str]
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "status": "success",
        "data": {"place_orders": [{"digest": "0x1"}, {"digest": "0x2"}]},
    }
    mock_post.return_value = mock_response

    params = PlaceOrdersParams(
        orders=[_order(senders[0], 1), _order(senders[0], 2)],
        stop_on_failure=True,
    )
    res = engine_client.place_orders(params)
    assert res.status == "success"

    req = PlaceOrdersRequest(**res.req)
    placed = req.place_orders.orders
    assert len(placed) == 2
    # Each order was signed independently and stringified for the wire.
    for order in placed:
        assert order.signature is not None
        assert isinstance(order.order.sender, str)  # bytes32 -> hex on serialize


def test_get_ink_airdrop(mock_post: MagicMock):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"amount": "123456"}
    mock_post.return_value = mock_response

    client = IndexerClient(IndexerClientOpts(url="http://example.com"))
    data = client.get_ink_airdrop("0xBE3faCAE76A38c3b61492E57BF65ae0628c4A808")
    assert data.amount == "123456"

    sent = mock_post.call_args.kwargs["json"]
    assert "ink_airdrop" in sent
    assert sent["ink_airdrop"]["address"] == "0xBE3faCAE76A38c3b61492E57BF65ae0628c4A808"


def test_get_market_prices_batch(engine_client: EngineClient, mock_post: MagicMock):
    mock_post.return_value = _query_response(
        {
            "market_prices": [
                {"product_id": 1, "bid_x18": "100", "ask_x18": "101"},
                {"product_id": 2, "bid_x18": "200", "ask_x18": "201"},
            ]
        }
    )
    data = engine_client.get_market_prices([1, 2])
    assert [p.product_id for p in data.market_prices] == [1, 2]
    assert data.market_prices[0].bid_x18 == "100"
    assert mock_post.call_args.kwargs["json"] == {
        "type": "market_prices",
        "product_ids": [1, 2],
    }


def test_get_insurance(engine_client: EngineClient, mock_post: MagicMock):
    mock_post.return_value = _query_response({"insurance": "123456"})
    data = engine_client.get_insurance()
    assert data.insurance == "123456"
    assert mock_post.call_args.kwargs["json"] == {"type": "insurance"}


def test_get_max_nlp_burnable(engine_client: EngineClient, mock_post: MagicMock):
    mock_post.return_value = _query_response({"max_nlp_amount": "999"})
    data = engine_client.get_max_nlp_burnable("0xabc")
    assert data.max_nlp_amount == "999"
    assert mock_post.call_args.kwargs["json"] == {
        "type": "max_nlp_burnable",
        "sender": "0xabc",
    }


def test_transfer_quote_signs_and_builds_tx(
    engine_client: EngineClient, mock_post: MagicMock, senders: list[str]
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_post.return_value = mock_response

    params = TransferQuoteParams(
        sender=senders[0], recipient=senders[1], amount=1000, nonce=1
    )
    res = engine_client.transfer_quote(params)
    assert res.status == "success"

    # res.req is the transformed wire request: {transfer_quote: {tx, signature}}
    sent = res.req["transfer_quote"]
    assert sent["tx"]["sender"] == senders[0].lower()
    assert sent["tx"]["recipient"] == senders[1].lower()
    assert sent["tx"]["amount"] == "1000"
    assert sent["tx"]["nonce"] == "1"
    assert sent["signature"] is not None


def test_withdraw_collateral_v2_signs_and_builds_tx(
    engine_client: EngineClient,
    mock_post: MagicMock,
    senders: list[str],
    owners: list[str],
):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "success"}
    mock_post.return_value = mock_response

    params = WithdrawCollateralV2Params(
        sender=senders[0],
        productId=2,
        amount=1000,
        sendTo=owners[1],
        appendix=0,
        nonce=1,
    )
    res = engine_client.withdraw_collateral_v2(params)
    assert res.status == "success"

    tx = res.req["withdraw_collateral_v2"]["tx"]
    assert tx["sender"] == senders[0].lower()
    assert tx["productId"] == 2
    assert tx["amount"] == "1000"
    assert tx["nonce"] == "1"
    assert tx["sendTo"] == owners[1].lower()
    assert tx["appendix"] == "0"
    assert res.req["withdraw_collateral_v2"]["signature"] is not None


# ---- high-level client passthroughs ----


def test_spot_withdraw_v2_passthrough(
    nado_client: NadoClient,
    senders: list[str],
    owners: list[str],
    mock_execute_response: MagicMock,
    mock_tx_nonce: MagicMock,
):
    params = WithdrawCollateralV2Params(
        sender=senders[0], productId=1, amount=10, sendTo=owners[1], nonce=2
    )
    res = nado_client.spot.withdraw_v2(params)
    assert res.status == "success"
    assert "withdraw_collateral_v2" in res.req


def test_spot_transfer_quote_passthrough(
    nado_client: NadoClient,
    senders: list[str],
    mock_execute_response: MagicMock,
    mock_tx_nonce: MagicMock,
):
    params = TransferQuoteParams(
        sender=senders[0], recipient=senders[1], amount=10, nonce=2
    )
    res = nado_client.spot.transfer_quote(params)
    assert res.status == "success"
    assert "transfer_quote" in res.req


def test_market_get_latest_market_prices_passthrough(
    nado_client: NadoClient, mock_post: MagicMock
):
    mock_post.return_value = _query_response(
        {"market_prices": [{"product_id": 1, "bid_x18": "1", "ask_x18": "2"}]}
    )
    data = nado_client.market.get_latest_market_prices([1])
    assert data.market_prices[0].product_id == 1


# ---- read-only indexer queries ----


def _indexer_client(mock_post: MagicMock, data: dict) -> IndexerClient:
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = data
    mock_post.return_value = resp
    return IndexerClient(IndexerClientOpts(url="http://example.com"))


def test_get_sequencer_backlog(mock_post: MagicMock):
    client = _indexer_client(
        mock_post,
        {
            "total_txs": "10",
            "total_submissions": "5",
            "backlog_size": "2",
            "updated_at": "1700",
            "backlog_eta_in_seconds": "3",
            "txs_per_second": "1.5",
        },
    )
    data = client.get_sequencer_backlog()
    assert data.backlog_size == "2" and data.txs_per_second == "1.5"
    assert mock_post.call_args.kwargs["json"] == {"backlog": {}}


def test_get_subaccount_dda(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"v1_address": "0xabc123"})
    data = client.get_subaccount_dda("0xdef")
    assert data.v1_address == "0xabc123"
    assert mock_post.call_args.kwargs["json"] == {
        "direct_deposit_address": {"subaccount": "0xdef"}
    }


def test_get_points(mock_post: MagicMock):
    client = _indexer_client(
        mock_post,
        {
            "points_per_epoch": [
                {
                    "epoch": 1,
                    "description": "epoch 1",
                    "start_time": "100",
                    "end_time": "200",
                    "total_points": "1000",
                    "points": "50",
                    "rank": 3,
                    "tier": 2,
                }
            ],
            "all_time_points": {"points": "50", "rank": 3, "tier": 2},
        },
    )
    data = client.get_points("0xabc")
    assert data.all_time_points.rank == 3
    assert data.points_per_epoch[0].points == "50"
    assert mock_post.call_args.kwargs["json"] == {"nado_points": {"address": "0xabc"}}


def test_get_private_alpha_choice(mock_post: MagicMock):
    client = _indexer_client(
        mock_post, {"points": "100", "fee_refund": "5", "nft_eligibility": True}
    )
    data = client.get_private_alpha_choice("0xabc")
    assert data.points == "100" and data.nft_eligibility is True
    assert mock_post.call_args.kwargs["json"] == {
        "private_alpha_choice": {"address": "0xabc"}
    }


def test_get_multi_perp_prices(mock_post: MagicMock):
    client = _indexer_client(
        mock_post,
        {
            "1": {
                "product_id": 1,
                "index_price_x18": "100",
                "mark_price_x18": "101",
                "update_time": "1700",
            }
        },
    )
    data = client.get_multi_perp_prices([1])
    assert data["1"].mark_price_x18 == "101"
    assert mock_post.call_args.kwargs["json"] == {"perp_prices": {"product_ids": [1]}}


# ---- pagination helpers ----


def _order_row(idx: str) -> dict:
    return {
        "submission_idx": idx,
        "timestamp": "1700",
        "digest": "0x" + idx.zfill(2),
        "base_filled": "0",
        "quote_filled": "0",
        "fee": "0",
        "builder_fee": "0",
        "subaccount": "0xabc",
        "product_id": 1,
        "amount": "1",
        "price_x18": "1",
        "expiration": "1",
        "nonce": "1",
        "appendix": "0",
        "isolated": False,
    }


def test_get_paginated_subaccount_orders(mock_post: MagicMock):
    client = _indexer_client(
        mock_post, {"orders": [_order_row("1"), _order_row("2"), _order_row("3")]}
    )
    page = client.get_paginated_subaccount_orders("0xabc", limit=2)
    assert len(page.orders) == 2
    assert page.meta.has_more is True
    assert page.meta.next_cursor == "3"
    # fetched limit + 1
    assert mock_post.call_args.kwargs["json"]["orders"]["limit"] == 3


def test_get_paginated_subaccount_orders_last_page(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"orders": [_order_row("1")]})
    page = client.get_paginated_subaccount_orders("0xabc", limit=2)
    assert len(page.orders) == 1
    assert page.meta.has_more is False
    assert page.meta.next_cursor is None


def test_get_paginated_subaccount_events_request_shape(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"events": [], "txs": []})
    page = client.get_paginated_subaccount_events(
        "0xabc", limit=5, event_types=["deposit_collateral"]
    )
    assert page.events == [] and page.meta.has_more is False
    sent = mock_post.call_args.kwargs["json"]["events"]
    assert sent["limit"] == {"raw": 6}
    assert sent["subaccounts"] == ["0xabc"]
    assert sent["event_types"] == ["deposit_collateral"]


def test_get_nlp_snapshots(mock_post: MagicMock):
    snap = {
        "submission_idx": "1",
        "timestamp": "1700",
        "cumulative_volume": "100",
        "cumulative_trades": "10",
        "cumulative_mint_quote": "50",
        "cumulative_burn_quote": "5",
        "cumulative_pnl": "20",
        "oracle_price_x18": "1000000000000000000",
        "depositors": "3",
        "tvl": "9999",
    }
    client = _indexer_client(mock_post, {"snapshots": [snap]})
    data = client.get_nlp_snapshots(count=10, granularity=3600, max_time=1700)
    assert data.snapshots[0].tvl == "9999"
    sent = mock_post.call_args.kwargs["json"]["nlp_snapshots"]
    assert sent["interval"] == {"count": 10, "granularity": 3600, "max_time": 1700}
    assert sent["max_time"] == 1700


def test_get_nlp_snapshots_cursor_mode(mock_post: MagicMock):
    snap = {
        "submission_idx": "5",
        "timestamp": "1800",
        "cumulative_volume": "200",
        "cumulative_trades": "20",
        "cumulative_mint_quote": "100",
        "cumulative_burn_quote": "10",
        "cumulative_pnl": "40",
        "oracle_price_x18": "1000000000000000000",
        "depositors": "5",
        "tvl": "19999",
    }
    client = _indexer_client(mock_post, {"snapshots": [snap]})
    data = client.get_nlp_snapshots(idx=5, limit=20)
    assert data.snapshots[0].tvl == "19999"
    sent = mock_post.call_args.kwargs["json"]["nlp_snapshots"]
    assert "interval" not in sent
    assert sent["idx"] == 5
    assert sent["limit"] == 20


def test_get_nlp_snapshots_with_params_object(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"snapshots": []})
    params = IndexerNlpSnapshotsParams(idx=10, limit=15)
    data = client.get_nlp_snapshots(params)
    assert data.snapshots == []
    sent = mock_post.call_args.kwargs["json"]["nlp_snapshots"]
    assert "interval" not in sent
    assert sent["idx"] == 10
    assert sent["limit"] == 15


def test_get_nlp_snapshots_partial_interval_raises(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"snapshots": []})
    with pytest.raises(ValueError, match="Both 'count' and 'granularity' must be provided"):
        client.get_nlp_snapshots(count=10)

    with pytest.raises(ValueError, match="Both 'count' and 'granularity' must be provided"):
        client.get_nlp_snapshots(granularity=3600)


def test_market_api_get_nlp_snapshots(mock_post: MagicMock, nado_client: NadoClient):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"snapshots": []}
    mock_post.return_value = resp
    data = nado_client.market.get_nlp_snapshots(count=5, granularity=60)
    assert data.snapshots == []
    sent = mock_post.call_args.kwargs["json"]["nlp_snapshots"]
    assert sent["interval"] == {"count": 5, "granularity": 60}


def test_get_fast_withdrawal_signature(mock_post: MagicMock):
    client = _indexer_client(
        mock_post,
        {
            "idx": "42",
            "tx": {"sender": "0xabc", "productId": 1, "amount": "100", "nonce": "2"},
            "tx_bytes": "0xdeadbeef",
            "signatures": ["0xsig1", "0xsig2"],
        },
    )
    data = client.get_fast_withdrawal_signature(42)
    assert data.idx == "42"
    assert data.tx.productId == 1
    assert data.tx_v2 is None
    assert data.signatures == ["0xsig1", "0xsig2"]
    assert mock_post.call_args.kwargs["json"] == {
        "fast_withdrawal_signature": {"idx": 42}
    }


# ---- leaderboard + social (read-only) ----


def test_get_leaderboard(mock_post: MagicMock):
    pos = {
        "subaccount": "0xabc",
        "contest_id": 1,
        "account_value": "1000.5",
        "update_time": "1700",
        "tracks": {"pnl": {"rank": 1}},
        "social_accounts": [],
    }
    client = _indexer_client(mock_post, {"positions": [pos]})
    data = client.get_leaderboard(contest_id=1, order="DESC", limit=10)
    assert data.positions[0].account_value == "1000.5"
    assert data.positions[0].tracks == {"pnl": {"rank": 1}}
    sent = mock_post.call_args.kwargs["json"]["leaderboard"]
    assert sent["contest_id"] == 1 and sent["order"] == "DESC" and sent["limit"] == 10


def test_get_leaderboard_participant(mock_post: MagicMock):
    pos = {
        "subaccount": "0xabc",
        "contest_id": 1,
        "account_value": "5",
        "update_time": "1",
    }
    client = _indexer_client(mock_post, {"positions": {"1": pos}})
    data = client.get_leaderboard_participant("0xabc", [1])
    assert data.positions["1"].contest_id == 1
    assert mock_post.call_args.kwargs["json"]["leaderboard_rank"] == {
        "contest_ids": [1],
        "subaccount": "0xabc",
    }


def test_get_leaderboard_contests(mock_post: MagicMock):
    contest = {
        "contest_id": 1,
        "start_time": "100",
        "end_time": "200",
        "count": "5",
        "last_updated": "150",
        "product_ids": [1, 2],
        "active": True,
        "title": "Q1",
        "description": "contest",
        "tracks": [{"type": "pnl"}],
    }
    client = _indexer_client(mock_post, {"contests": [contest]})
    data = client.get_leaderboard_contests(active=True)
    assert data.contests[0].title == "Q1" and data.contests[0].active is True


def test_get_leaderboard_registrations(mock_post: MagicMock):
    reg = {"subaccount": "0xabc", "contest_id": 1, "update_time": "1700"}
    client = _indexer_client(mock_post, {"registrations": [reg]})
    data = client.get_leaderboard_registrations("0xabc")
    assert data.registrations[0].contest_id == 1


def test_list_social_accounts(mock_post: MagicMock):
    acct = {
        "provider": "twitter",
        "username": "nadotrader",
        "display_name": "Nado Trader",
        "profile_image_url": "http://img",
    }
    client = _indexer_client(mock_post, {"accounts": [acct]})
    data = client.list_social_accounts("0xabc")
    assert data.accounts[0].username == "nadotrader"
    assert mock_post.call_args.kwargs["json"] == {
        "list_social_accounts": {"address": "0xabc"}
    }


# ---- signed indexer writes (EIP-712) ----


def _signing_ctx(private_keys, chain_id, endpoint_addr, senders):
    from eth_account import Account

    return {
        "signer": Account.from_key(private_keys[0]),
        "chain_id": chain_id,
        "verifying_contract": endpoint_addr,
        "sender": senders[0],
    }


def test_register_leaderboard(
    mock_post: MagicMock, private_keys, chain_id, endpoint_addr, senders
):
    client = _indexer_client(
        mock_post,
        {"registrations": [{"subaccount": "0xabc", "contest_id": 1, "update_time": "1"}]},
    )
    ctx = _signing_ctx(private_keys, chain_id, endpoint_addr, senders)
    data = client.register_leaderboard(
        ctx["signer"], ctx["chain_id"], ctx["verifying_contract"],
        ctx["sender"], contest_ids=[1, 2], expiration=1700,
    )
    assert data.registrations[0].contest_id == 1
    sent = mock_post.call_args.kwargs["json"]["leaderboard_register"]["update_registration"]
    assert sent["tx"]["contestIds"] == [1, 2]
    assert sent["tx"]["expiration"] == "1700"
    assert len(sent["signature"]) > 0


def test_connect_social_account(
    mock_post: MagicMock, private_keys, chain_id, endpoint_addr, senders
):
    client = _indexer_client(mock_post, {"url": "https://oauth.example/connect"})
    ctx = _signing_ctx(private_keys, chain_id, endpoint_addr, senders)
    data = client.connect_social_account(
        ctx["signer"], ctx["chain_id"], ctx["verifying_contract"],
        ctx["sender"], provider="twitter", expiration=1700,
    )
    assert data.url == "https://oauth.example/connect"
    sent = mock_post.call_args.kwargs["json"]["social_connect"]["update_social_account"]
    assert sent["tx"]["provider"] == "twitter"
    assert len(sent["signature"]) > 0


def test_revoke_social_account(
    mock_post: MagicMock, private_keys, chain_id, endpoint_addr, senders
):
    client = _indexer_client(
        mock_post,
        {"accounts": [{"provider": "twitter", "username": "u", "display_name": "d", "profile_image_url": "i"}]},
    )
    ctx = _signing_ctx(private_keys, chain_id, endpoint_addr, senders)
    data = client.revoke_social_account(
        ctx["signer"], ctx["chain_id"], ctx["verifying_contract"],
        ctx["sender"], provider="twitter", expiration=1700,
    )
    assert data.accounts[0].provider == "twitter"
    assert "revoke_social_account" in mock_post.call_args.kwargs["json"]


# ---- edge candlesticks + market snapshots ----


def test_get_edge_candlesticks(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"candlesticks": []})
    data = client.get_edge_candlesticks(product_id=1, granularity=60, limit=100)
    assert data.candlesticks == []
    sent = mock_post.call_args.kwargs["json"]["edge_candlesticks"]
    assert sent["product_id"] == 1 and sent["granularity"] == 60 and sent["limit"] == 100


def test_get_edge_market_snapshots(mock_post: MagicMock):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"snapshots": {"1700": [{"product_id": 1}]}}
    mock_post.return_value = resp
    client = IndexerClient(IndexerClientOpts(url="http://example.com"))
    data = client.get_edge_market_snapshots(count=10, granularity=3600, max_time=1700)
    assert data == {"1700": [{"product_id": 1}]}
    assert mock_post.call_args.kwargs["json"] == {
        "edge_market_snapshots": {
            "interval": {"count": 10, "granularity": 3600, "max_time": 1700}
        }
    }


# ---- NLP pool queries (engine) + multi-product snapshots (indexer) ----


_SUBACCOUNT_INFO = {
    "subaccount": "0xabc",
    "exists": True,
    "healths": [],
    "health_contributions": [],
    "spot_count": 0,
    "perp_count": 0,
    "spot_balances": [],
    "perp_balances": [],
    "spot_products": [],
    "perp_products": [],
}


def _spot_balance(amount: str) -> dict:
    return {"product_id": 0, "balance": {"amount": amount}}


def test_get_nlp_pool_info(engine_client: EngineClient, mock_post: MagicMock):
    mock_post.return_value = _query_response(
        {
            "nlp_pools": [
                {
                    "pool_id": 1,
                    "subaccount": "0xabc",
                    "owner": "0xdef",
                    "balance_weight_x18": "1000",
                    "subaccount_info": _SUBACCOUNT_INFO,
                    "open_orders": [],
                }
            ]
        }
    )
    data = engine_client.get_nlp_pool_info()
    assert data.nlp_pools[0].pool_id == 1
    assert data.nlp_pools[0].subaccount_info.exists is True
    assert mock_post.call_args.kwargs["json"] == {"type": "nlp_pool_info"}


def test_get_nlp_locked_balances(engine_client: EngineClient, mock_post: MagicMock):
    mock_post.return_value = _query_response(
        {
            "balance_locked": _spot_balance("10"),
            "balance_unlocked": _spot_balance("5"),
            "locked_balances": [
                {"balance": _spot_balance("3"), "unlocked_at": "1700"}
            ],
        }
    )
    data = engine_client.get_nlp_locked_balances("0xabc")
    assert data.locked_balances[0].unlocked_at == "1700"
    assert data.locked_balances[0].balance.balance.amount == "3"
    assert mock_post.call_args.kwargs["json"] == {
        "type": "nlp_locked_balances",
        "subaccount": "0xabc",
    }


def test_get_multi_product_snapshots(mock_post: MagicMock):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"1700": {"1": {"product": {}, "submission_idx": "5"}}}
    mock_post.return_value = resp
    client = IndexerClient(IndexerClientOpts(url="http://example.com"))
    data = client.get_multi_product_snapshots([1], max_time=[1700])
    assert data == {"1700": {"1": {"product": {}, "submission_idx": "5"}}}
    assert mock_post.call_args.kwargs["json"] == {
        "product_snapshots": {"product_ids": [1], "max_time": [1700]}
    }


def test_get_v2_symbols(mock_get: MagicMock):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {
        "BTC-PERP": {"product_id": 2, "market_hours": {"is_open": True}}
    }
    mock_get.return_value = resp
    client = IndexerClient(IndexerClientOpts(url="http://example.com/v1"))
    data = client.get_v2_symbols(product_type="perp", product_ids=[2, 4])
    assert data["BTC-PERP"]["market_hours"]["is_open"] is True
    called_url = mock_get.call_args.args[0]
    assert called_url.endswith("/v2/symbols?product_type=perp&product_ids=2,4")


def test_get_edge_all_products(engine_client: EngineClient, mock_post: MagicMock):
    mock_post.return_value = _query_response(
        {"edge_all_products": {"763373": {"spot_products": [], "perp_products": []}}}
    )
    data = engine_client.get_edge_all_products()
    assert "763373" in data.edge_all_products
    assert mock_post.call_args.kwargs["json"] == {"type": "edge_all_products"}


# ---- additional pagination variants ----


def test_paginated_collateral_events_sets_event_types(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"events": [], "txs": []})
    page = client.get_paginated_subaccount_collateral_events("0xabc", limit=5)
    assert page.meta.has_more is False
    sent = mock_post.call_args.kwargs["json"]["events"]
    assert sent["event_types"] == [
        "deposit_collateral",
        "withdraw_collateral",
        "transfer_quote",
    ]


def test_paginated_match_events(mock_post: MagicMock):
    client = _indexer_client(mock_post, {"matches": [], "txs": []})
    page = client.get_paginated_subaccount_match_events("0xabc", limit=3)
    assert page.matches == [] and page.txs == [] and page.meta.has_more is False
    sent = mock_post.call_args.kwargs["json"]["matches"]
    assert sent["limit"] == 4 and sent["subaccounts"] == ["0xabc"]


def test_paginated_interest_funding(mock_post: MagicMock):
    client = _indexer_client(
        mock_post,
        {"interest_payments": [], "funding_payments": [], "next_idx": "100"},
    )
    page = client.get_paginated_subaccount_interest_funding_payments(
        "0xabc", product_ids=[1], limit=10
    )
    assert page.meta.has_more is True and page.meta.next_cursor == "100"
    sent = mock_post.call_args.kwargs["json"]["interest_and_funding"]
    assert sent["product_ids"] == [1] and sent["limit"] == 10


def test_paginated_leaderboard(mock_post: MagicMock):
    pos = lambda i: {  # noqa: E731
        "subaccount": f"0x{i}",
        "contest_id": 1,
        "account_value": "10",
        "update_time": "1",
    }
    client = _indexer_client(mock_post, {"positions": [pos(1), pos(2), pos(3)]})
    page = client.get_paginated_leaderboard(contest_id=1, limit=2)
    assert len(page.positions) == 2
    assert page.meta.has_more is True and page.meta.next_cursor == "2"
    assert mock_post.call_args.kwargs["json"]["leaderboard"]["limit"] == 3
