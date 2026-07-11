# Feature parity roadmap (vs. TypeScript SDK)

This tracks API coverage of the Python SDK against the TypeScript SDK, as of the
v2 (`2.0.0`) work.

Legend: ✅ done in v2 · ⏳ remaining

## Engine client

| Capability | Wire type | Status |
| --- | --- | --- |
| Batch place orders | execute `place_orders` | ✅ `place_orders` |
| Query/execute over WebSocket | `/ws` | ✅ `NadoWebSocketClient` |
| Transfer quote | execute `transfer_quote` | ✅ `transfer_quote` |
| Withdraw collateral V2 | execute `withdraw_collateral_v2` | ✅ `withdraw_collateral_v2` |
| Batch market prices | query `market_prices` | ✅ `get_market_prices` |
| Max burnable NLP | query `max_nlp_burnable` | ✅ `get_max_nlp_burnable` |
| Insurance fund | query `insurance` | ✅ `get_insurance` |
| NLP pool info | query `nlp_pool_info` | ✅ `get_nlp_pool_info` (fully typed: `SubaccountInfoData` + `OrderData`) |
| NLP locked balances | query `nlp_locked_balances` | ✅ `get_nlp_locked_balances` |
| Edge all markets | query `edge_all_products` | ✅ `get_edge_all_products` |
| Edge/cached queries | `/edge/query` (`cached_*`, `ping`, `time`) | ✅ `EngineEdgeQueryClient` (cached prices/symbols/contracts/status/all-products/edge-all-products/health-groups/nlp-pool-info/bbo-history + ping/time) |
| Web/gateway helpers | `GET /ip`, `/time`, `/cf-check` | ✅ `EngineWebClient` |

## Indexer client

| Capability | Wire type | Status |
| --- | --- | --- |
| Ink airdrop allocation | `ink_airdrop` | ✅ `get_ink_airdrop` |
| Streaming subscriptions | `/subscribe` | ✅ `NadoSubscriptionClient` |
| Multi-product perp prices | `perp_prices` (batch) | ✅ `get_multi_perp_prices` |
| Multi-product snapshots | `product_snapshots` (batch) | ✅ `get_multi_product_snapshots` |
| V2 symbols (market hours / boost) | `GET /v2/symbols` | ✅ `get_v2_symbols` |
| Leaderboard suite (read) | `leaderboard`, `leaderboard_rank`, `leaderboard_contests`, `leaderboard_registrations` | ✅ `get_leaderboard` / `get_leaderboard_participant` / `get_leaderboard_contests` / `get_leaderboard_registrations` |
| Leaderboard register (signed) | `leaderboard_register` | ✅ `register_leaderboard` (EIP-712) |
| Social accounts (read) | `list_social_accounts` | ✅ `list_social_accounts` |
| Social connect/revoke (signed) | `social_connect`, `revoke_social_account` | ✅ `connect_social_account` / `revoke_social_account` (EIP-712) |
| Points / private alpha | `nado_points`, `private_alpha_choice` | ✅ `get_points` / `get_private_alpha_choice` |
| Edge candlesticks / market snapshots | `edge_candlesticks`, `edge_market_snapshots` | ✅ `get_edge_candlesticks` / `get_edge_market_snapshots` |
| Fast withdrawal signature | `fast_withdrawal_signature` | ✅ `get_fast_withdrawal_signature` |
| NLP snapshots | `nlp_snapshots` | ✅ `get_nlp_snapshots` |
| Direct deposit address | `direct_deposit_address` | ✅ `get_subaccount_dda` |
| Sequencer backlog | `backlog` | ✅ `get_sequencer_backlog` |
| Pagination helpers | (client-side `getPaginated*`) | ✅ orders, events (generic), collateral, nlp, settlement, liquidation, match, interest-funding, leaderboard |

## High-level client (`apis/`)

| Capability | Status |
| --- | --- |
| `ws` API group (message builders) | ✅ via `nado_protocol.ws` |
| Multi-product `get_latest_market_prices` | ✅ `market.get_latest_market_prices` |
| Cached/edge market methods (`getCached*`, `getEdge*`) | ✅ via `EngineEdgeQueryClient` + indexer `get_edge_candlesticks` / `get_edge_market_snapshots` |
| `withdraw_v2`, `transfer_quote` passthroughs | ✅ `spot.withdraw_v2` / `spot.transfer_quote` |
| Group-placement alignment (`getHealthGroups`, isolated positions, NLP mint/burn) | ⏳ (functionally present, different API group) |

## Notes for implementers

- Executes that require new EIP-712 structs must add the struct to
  `contracts/eip712/types.py:get_nado_eip712_type` with the exact field order and
  solidity types, or signed payloads will be rejected.
- New response models go through `NadoBaseModel`, so they inherit the v2
  serialization/coercion behavior automatically.
