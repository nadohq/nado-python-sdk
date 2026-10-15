from typing import Optional, Union
import requests
from functools import singledispatchmethod
from eth_account.signers.local import LocalAccount
from nado_protocol.contracts.eip712.sign import (
    build_eip712_typed_data,
    sign_eip712_typed_data,
)
from nado_protocol.contracts.types import NadoTxType
from nado_protocol.utils.bytes32 import bytes32_to_hex, subaccount_to_bytes32
from nado_protocol.utils.subaccount import Subaccount
from nado_protocol.indexer_client.types import IndexerClientOpts
from nado_protocol.indexer_client.types.models import (
    MarketType,
    IndexerHistoricalOrder,
    IndexerEvent,
    IndexerEventType,
    IndexerMatch,
    IndexerTx,
    IndexerPayment,
)
from nado_protocol.indexer_client.types.query import IndexerEventsRawLimit
from nado_protocol.indexer_client.types.query import (
    IndexerCandlesticksParams,
    IndexerCandlesticksData,
    IndexerEventsParams,
    IndexerEventsData,
    IndexerFundingRateParams,
    IndexerFundingRateData,
    IndexerFundingRatesParams,
    IndexerFundingRatesData,
    IndexerHistoricalOrdersByDigestParams,
    IndexerHistoricalOrdersData,
    IndexerSubaccountHistoricalOrdersParams,
    IndexerLinkedSignerRateLimitData,
    IndexerLinkedSignerRateLimitParams,
    IndexerLiquidationFeedData,
    IndexerLiquidationFeedParams,
    IndexerMarketSnapshotsData,
    IndexerMarketSnapshotsParams,
    IndexerMatchesParams,
    IndexerMatchesData,
    IndexerOraclePricesData,
    IndexerOraclePricesParams,
    IndexerParams,
    IndexerPerpPricesData,
    IndexerPerpPricesParams,
    IndexerProductSnapshotsData,
    IndexerProductSnapshotsParams,
    IndexerRequest,
    IndexerResponse,
    IndexerSubaccountsData,
    IndexerSubaccountsParams,
    IndexerQuotePriceParams,
    IndexerQuotePriceData,
    IndexerInterestAndFundingParams,
    IndexerInterestAndFundingData,
    IndexerAccountSnapshotsParams,
    IndexerAccountSnapshotsData,
    IndexerInkAirdropParams,
    IndexerInkAirdropData,
    IndexerBacklogParams,
    IndexerBacklogData,
    IndexerDirectDepositAddressParams,
    IndexerDirectDepositAddressData,
    IndexerNadoPointsParams,
    IndexerNadoPointsData,
    IndexerPrivateAlphaChoiceParams,
    IndexerPrivateAlphaChoiceData,
    IndexerMultiPerpPricesParams,
    IndexerNlpSnapshotsParams,
    IndexerNlpSnapshotsData,
    IndexerFastWithdrawalSignatureParams,
    IndexerFastWithdrawalSignatureData,
    IndexerLeaderboardParams,
    IndexerLeaderboardData,
    IndexerLeaderboardPosition,
    IndexerLeaderboardRankParams,
    IndexerLeaderboardRankData,
    IndexerLeaderboardContestsParams,
    IndexerLeaderboardContestsData,
    IndexerLeaderboardRegistrationsParams,
    IndexerLeaderboardRegistrationsData,
    IndexerListSocialAccountsParams,
    IndexerSocialAccountsData,
    IndexerSocialConnectData,
    IndexerEdgeCandlesticksParams,
    IndexerMarketSnapshotInterval,
    IndexerTickersData,
    IndexerPerpContractsData,
    IndexerHistoricalTradesData,
    to_indexer_request,
)
from nado_protocol.utils.model import (
    NadoBaseModel,
    ensure_data_type,
    is_instance_of_union,
)


class PaginationMeta(NadoBaseModel):
    """Cursor pagination metadata.

    `next_cursor` is the `submission_idx` to pass as `start_cursor` for the next
    page, or None when there are no more results.
    """

    has_more: bool
    next_cursor: Optional[str] = None


class PaginatedOrders(NadoBaseModel):
    """A page of historical orders with pagination metadata."""

    orders: list[IndexerHistoricalOrder]
    meta: PaginationMeta


class PaginatedEvents(NadoBaseModel):
    """A page of events with pagination metadata."""

    events: list[IndexerEvent]
    meta: PaginationMeta


class PaginatedMatches(NadoBaseModel):
    """A page of matches (with their txs) and pagination metadata."""

    matches: list[IndexerMatch]
    txs: list[IndexerTx]
    meta: PaginationMeta


class PaginatedInterestFundingPayments(NadoBaseModel):
    """A page of interest/funding payments with pagination metadata."""

    interest_payments: list[IndexerPayment]
    funding_payments: list[IndexerPayment]
    meta: PaginationMeta


class PaginatedLeaderboard(NadoBaseModel):
    """A page of leaderboard positions with (offset-based) pagination metadata."""

    positions: list[IndexerLeaderboardPosition]
    meta: PaginationMeta


class IndexerQueryClient:
    """
    Client for querying data from the indexer service.

    Attributes:
        _opts (IndexerClientOpts): Client configuration options for connecting and interacting with the indexer service.
        url (str): URL of the indexer service.
    """

    def __init__(self, opts: IndexerClientOpts):
        """
        Initializes the IndexerQueryClient with the provided options.

        Args:
            opts (IndexerClientOpts): Client configuration options for connecting and interacting with the indexer service.
        """
        self._opts = IndexerClientOpts.model_validate(opts)
        self.url = self._opts.url
        self.url_v2: str = self.url.replace("/v1", "") + "/v2"
        self.session = requests.Session()
        self.session.headers.update({"Accept-Encoding": "gzip"})

    @singledispatchmethod
    def query(self, params: Union[IndexerParams, IndexerRequest]) -> IndexerResponse:
        """
        Sends a query request to the indexer service and returns the response.

        The `query` method is overloaded to accept either `IndexerParams` or a dictionary or `IndexerRequest`
        as the input parameters. Based on the type of the input, the appropriate internal method is invoked
        to process the query request.

        Args:
            params (IndexerParams | dict | IndexerRequest): The parameters for the query request.

        Returns:
            IndexerResponse: The response from the indexer service.
        """
        req: IndexerRequest = (
            params if is_instance_of_union(params, IndexerRequest) else to_indexer_request(params)  # type: ignore
        )
        return self._query(req)

    @query.register
    def _(self, req: dict) -> IndexerResponse:
        return self._query(NadoBaseModel.model_validate(req))  # type: ignore

    def _query(self, req: IndexerRequest) -> IndexerResponse:
        res = self.session.post(self.url, json=req.dict())
        if res.status_code != 200:
            raise Exception(res.text)
        try:
            indexer_res = IndexerResponse(data=res.json())
        except Exception:
            raise Exception(res.text)
        return indexer_res

    def _query_v2(self, url):
        res = self.session.get(url)
        if res.status_code != 200:
            raise Exception(res.text)
        return res.json()

    def get_subaccount_historical_orders(
        self, params: IndexerSubaccountHistoricalOrdersParams
    ) -> IndexerHistoricalOrdersData:
        """
        Retrieves the historical orders associated with a specific subaccount.

        Args:
            params (IndexerSubaccountHistoricalOrdersParams): The parameters specifying the subaccount for which to retrieve historical orders.

        Returns:
            IndexerHistoricalOrdersData: The historical orders associated with the specified subaccount.
        """
        return ensure_data_type(
            self.query(IndexerSubaccountHistoricalOrdersParams.model_validate(params)).data,
            IndexerHistoricalOrdersData,
        )

    def get_paginated_subaccount_orders(
        self,
        subaccount: str,
        limit: int,
        start_cursor: Optional[str] = None,
        max_time: Optional[int] = None,
        product_ids: Optional[list[int]] = None,
        trigger_types: Optional[list[str]] = None,
        isolated: Optional[bool] = None,
    ) -> PaginatedOrders:
        """
        Retrieves a single page of a subaccount's historical orders.

        Fetches `limit + 1` rows to determine whether more pages exist; the extra
        row's `submission_idx` becomes `next_cursor`.

        Args:
            subaccount (str): The subaccount (bytes32 hex).
            limit (int): Page size.
            start_cursor (str, optional): `submission_idx` to start from (exclusive upper bound).
            max_time (int, optional): Upper bound timestamp.
            product_ids (list[int], optional): Filter by products.
            trigger_types (list[str], optional): Filter by trigger types.
            isolated (bool, optional): Filter isolated vs cross.

        Returns:
            PaginatedOrders: The page of orders plus pagination metadata.
        """
        result = self.get_subaccount_historical_orders(
            IndexerSubaccountHistoricalOrdersParams(
                submission_idx=int(start_cursor) if start_cursor is not None else None,
                max_time=max_time,
                limit=limit + 1,
                subaccounts=[subaccount],
                product_ids=product_ids,
                trigger_types=trigger_types,
                isolated=isolated,
            )
        )
        orders = result.orders
        page = orders[:limit]
        has_more = len(orders) > limit
        next_cursor = orders[limit].submission_idx if has_more else None
        return PaginatedOrders(
            orders=page, meta=PaginationMeta(has_more=has_more, next_cursor=next_cursor)
        )

    def get_paginated_subaccount_events(
        self,
        subaccount: str,
        limit: int,
        event_types: Optional[list[IndexerEventType]] = None,
        start_cursor: Optional[str] = None,
        max_time: Optional[int] = None,
        product_ids: Optional[list[int]] = None,
        isolated: Optional[bool] = None,
    ) -> PaginatedEvents:
        """
        Retrieves a single page of a subaccount's events.

        Args:
            subaccount (str): The subaccount (bytes32 hex).
            limit (int): Page size.
            event_types (list[IndexerEventType], optional): Filter by event type
                (e.g. deposit/withdraw for collateral, mint_nlp/burn_nlp for NLP).
            start_cursor (str, optional): `submission_idx` to start from.
            max_time (int, optional): Upper bound timestamp.
            product_ids (list[int], optional): Filter by products.
            isolated (bool, optional): Filter isolated vs cross.

        Returns:
            PaginatedEvents: The page of events plus pagination metadata.
        """
        result = self.get_events(
            IndexerEventsParams(
                submission_idx=int(start_cursor) if start_cursor is not None else None,
                max_time=max_time,
                limit=IndexerEventsRawLimit(raw=limit + 1),
                subaccounts=[subaccount],
                product_ids=product_ids,
                event_types=event_types,
                isolated=isolated,
            )
        )
        events = result.events
        page = events[:limit]
        has_more = len(events) > limit
        next_cursor = events[limit].submission_idx if has_more else None
        return PaginatedEvents(
            events=page, meta=PaginationMeta(has_more=has_more, next_cursor=next_cursor)
        )

    def get_paginated_subaccount_collateral_events(
        self, subaccount: str, limit: int, **kwargs
    ) -> PaginatedEvents:
        """Paginated deposit/withdraw/transfer collateral events for a subaccount."""
        return self.get_paginated_subaccount_events(
            subaccount,
            limit,
            event_types=[
                IndexerEventType.DEPOSIT_COLLATERAL,
                IndexerEventType.WITHDRAW_COLLATERAL,
                IndexerEventType.TRANSFER_QUOTE,
            ],
            **kwargs,
        )

    def get_paginated_subaccount_nlp_events(
        self, subaccount: str, limit: int, **kwargs
    ) -> PaginatedEvents:
        """Paginated mint/burn NLP events for a subaccount."""
        return self.get_paginated_subaccount_events(
            subaccount,
            limit,
            event_types=[IndexerEventType.MINT_NLP, IndexerEventType.BURN_NLP],
            **kwargs,
        )

    def get_paginated_subaccount_settlement_events(
        self, subaccount: str, limit: int, **kwargs
    ) -> PaginatedEvents:
        """Paginated settle-PnL events for a subaccount."""
        return self.get_paginated_subaccount_events(
            subaccount, limit, event_types=[IndexerEventType.SETTLE_PNL], **kwargs
        )

    def get_paginated_subaccount_liquidation_events(
        self, subaccount: str, limit: int, **kwargs
    ) -> PaginatedEvents:
        """Paginated liquidation events for a subaccount."""
        return self.get_paginated_subaccount_events(
            subaccount,
            limit,
            event_types=[IndexerEventType.LIQUIDATE_SUBACCOUNT],
            **kwargs,
        )

    def get_paginated_subaccount_match_events(
        self,
        subaccount: str,
        limit: int,
        start_cursor: Optional[str] = None,
        max_time: Optional[int] = None,
        product_ids: Optional[list[int]] = None,
        isolated: Optional[bool] = None,
    ) -> PaginatedMatches:
        """
        Retrieves a single page of a subaccount's match events (with their txs).
        """
        result = self.get_matches(
            IndexerMatchesParams(
                submission_idx=int(start_cursor) if start_cursor is not None else None,
                max_time=max_time,
                limit=limit + 1,
                subaccounts=[subaccount],
                product_ids=product_ids,
                isolated=isolated,
            )
        )
        matches = result.matches
        page = matches[:limit]
        has_more = len(matches) > limit
        next_cursor = matches[limit].submission_idx if has_more else None
        return PaginatedMatches(
            matches=page,
            txs=result.txs,
            meta=PaginationMeta(has_more=has_more, next_cursor=next_cursor),
        )

    def get_paginated_subaccount_interest_funding_payments(
        self,
        subaccount: str,
        product_ids: list[int],
        limit: int,
        start_cursor: Optional[str] = None,
    ) -> PaginatedInterestFundingPayments:
        """
        Retrieves a single page of a subaccount's interest/funding payments.

        Uses the server-provided `next_idx` as the cursor (`next_cursor`).
        """
        data = self.get_interest_and_funding_payments(
            IndexerInterestAndFundingParams(
                subaccount=subaccount,
                product_ids=product_ids,
                max_idx=start_cursor,
                limit=limit,
            )
        )
        has_more = bool(data.next_idx)
        return PaginatedInterestFundingPayments(
            interest_payments=data.interest_payments,
            funding_payments=data.funding_payments,
            meta=PaginationMeta(
                has_more=has_more, next_cursor=data.next_idx if has_more else None
            ),
        )

    def get_paginated_leaderboard(
        self,
        contest_id: int,
        limit: int,
        rank_type: Optional[str] = None,
        start: int = 0,
        order: Optional[str] = None,
    ) -> PaginatedLeaderboard:
        """
        Retrieves a single page of a contest leaderboard (offset pagination).

        `next_cursor` is the next `start` offset to pass, or None on the last page.
        """
        result = self.get_leaderboard(
            contest_id=contest_id,
            rank_type=rank_type,
            start=start,
            limit=limit + 1,
            order=order,
        )
        positions = result.positions
        page = positions[:limit]
        has_more = len(positions) > limit
        next_cursor = str(start + limit) if has_more else None
        return PaginatedLeaderboard(
            positions=page,
            meta=PaginationMeta(has_more=has_more, next_cursor=next_cursor),
        )

    def get_historical_orders_by_digest(
        self, digests: list[str]
    ) -> IndexerHistoricalOrdersData:
        """
        Retrieves historical orders using their unique digests.

        Args:
            digests (list[str]): A list of order digests.

        Returns:
            IndexerHistoricalOrdersData: The historical orders corresponding to the provided digests.
        """
        return ensure_data_type(
            self.query(IndexerHistoricalOrdersByDigestParams(digests=digests)).data,
            IndexerHistoricalOrdersData,
        )

    def get_matches(self, params: IndexerMatchesParams) -> IndexerMatchesData:
        """
        Retrieves match data based on provided parameters.

        Args:
            params (IndexerMatchesParams): The parameters for the match data retrieval request.

        Returns:
            IndexerMatchesData: The match data corresponding to the provided parameters.
        """
        return ensure_data_type(
            self.query(IndexerMatchesParams.model_validate(params)).data, IndexerMatchesData
        )

    def get_ink_airdrop(self, address: str) -> IndexerInkAirdropData:
        """
        Retrieves the Ink airdrop allocation for an address.

        Args:
            address (str): The address to query the allocation for.

        Returns:
            IndexerInkAirdropData: The airdrop allocation amount.
        """
        return ensure_data_type(
            self.query(IndexerInkAirdropParams(address=address)).data,
            IndexerInkAirdropData,
        )

    def get_sequencer_backlog(self) -> IndexerBacklogData:
        """
        Retrieves the current sequencer backlog statistics.

        Returns:
            IndexerBacklogData: Backlog size, throughput, and ETA.
        """
        return ensure_data_type(
            self.query(IndexerBacklogParams()).data, IndexerBacklogData
        )

    def get_subaccount_dda(self, subaccount: str) -> IndexerDirectDepositAddressData:
        """
        Retrieves the V1 direct-deposit address for a subaccount.

        Args:
            subaccount (str): The subaccount (bytes32 hex).

        Returns:
            IndexerDirectDepositAddressData: The V1 direct-deposit address.
        """
        return ensure_data_type(
            self.query(
                IndexerDirectDepositAddressParams(subaccount=subaccount)
            ).data,
            IndexerDirectDepositAddressData,
        )

    def get_points(self, address: str) -> IndexerNadoPointsData:
        """
        Retrieves Nado points for an address, per-epoch and all-time.

        Args:
            address (str): The wallet address.

        Returns:
            IndexerNadoPointsData: The points breakdown.
        """
        return ensure_data_type(
            self.query(IndexerNadoPointsParams(address=address)).data,
            IndexerNadoPointsData,
        )

    def get_private_alpha_choice(
        self, address: str
    ) -> IndexerPrivateAlphaChoiceData:
        """
        Retrieves private alpha choice info (points, fee refund, NFT eligibility).

        Args:
            address (str): The wallet address.

        Returns:
            IndexerPrivateAlphaChoiceData: The private alpha choice info.
        """
        return ensure_data_type(
            self.query(IndexerPrivateAlphaChoiceParams(address=address)).data,
            IndexerPrivateAlphaChoiceData,
        )

    def get_events(self, params: IndexerEventsParams) -> IndexerEventsData:
        """
        Retrieves event data based on provided parameters.

        Args:
            params (IndexerEventsParams): The parameters for the event data retrieval request.

        Returns:
            IndexerEventsData: The event data corresponding to the provided parameters.
        """
        return ensure_data_type(
            self.query(IndexerEventsParams.model_validate(params)).data, IndexerEventsData
        )

    def get_product_snapshots(
        self, params: IndexerProductSnapshotsParams
    ) -> IndexerProductSnapshotsData:
        """
        Retrieves snapshot data for specific products.

        Args:
            params (IndexerProductSnapshotsParams): Parameters specifying the products for which to retrieve snapshot data.

        Returns:
            IndexerProductSnapshotsData: The product snapshot data corresponding to the provided parameters.
        """
        return ensure_data_type(
            self.query(IndexerProductSnapshotsParams.model_validate(params)).data,
            IndexerProductSnapshotsData,
        )

    def get_market_snapshots(
        self, params: IndexerMarketSnapshotsParams
    ) -> IndexerMarketSnapshotsData:
        """
        Retrieves historical market snapshots.

        Args:
            params (IndexerMarketSnapshotsParams): Parameters specifying the historical market snapshot request.

        Returns:
            IndexerMarketSnapshotsData: The market snapshot data corresponding to the provided parameters.
        """
        return ensure_data_type(
            self.query(IndexerMarketSnapshotsParams.model_validate(params)).data,
            IndexerMarketSnapshotsData,
        )

    def get_candlesticks(
        self, params: IndexerCandlesticksParams
    ) -> IndexerCandlesticksData:
        """
        Retrieves candlestick data based on provided parameters.

        Args:
            params (IndexerCandlesticksParams): The parameters for retrieving candlestick data.

        Returns:
            IndexerCandlesticksData: The candlestick data corresponding to the provided parameters.
        """
        return ensure_data_type(
            self.query(IndexerCandlesticksParams.model_validate(params)).data,
            IndexerCandlesticksData,
        )

    def get_perp_funding_rate(self, product_id: int) -> IndexerFundingRateData:
        """
        Retrieves the funding rate data for a specific perp product.

        Args:
            product_id (int): The identifier of the perp product.

        Returns:
            IndexerFundingRateData: The funding rate data for the specified perp product.
        """
        return ensure_data_type(
            self.query(IndexerFundingRateParams(product_id=product_id)).data,
            IndexerFundingRateData,
        )

    def get_perp_funding_rates(self, product_ids: list) -> IndexerFundingRatesData:
        """
        Fetches the latest funding rates for a list of perp products.

        Args:
            product_ids (list): List of identifiers for the perp products.

        Returns:
            dict: A dictionary mapping each product_id to its latest funding rate and related details.
        """
        return ensure_data_type(
            self.query(IndexerFundingRatesParams(product_ids=product_ids)).data, dict
        )

    def get_perp_prices(self, product_id: int) -> IndexerPerpPricesData:
        """
        Retrieves the price data for a specific perp product.

        Args:
            product_id (int): The identifier of the perp product.

        Returns:
            IndexerPerpPricesData: The price data for the specified perp product.
        """
        return ensure_data_type(
            self.query(IndexerPerpPricesParams(product_id=product_id)).data,
            IndexerPerpPricesData,
        )

    def get_multi_perp_prices(self, product_ids: list[int]) -> dict:
        """
        Retrieves price data for multiple perp products at once.

        Args:
            product_ids (list[int]): The identifiers of the perp products.

        Returns:
            dict: Mapping of product_id (str) to its perp price data.
        """
        return ensure_data_type(
            self.query(IndexerMultiPerpPricesParams(product_ids=product_ids)).data,
            dict,
        )

    def get_nlp_snapshots(
        self,
        count: Optional[Union[int, IndexerNlpSnapshotsParams]] = None,
        granularity: Optional[int] = None,
        max_time: Optional[int] = None,
        idx: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> IndexerNlpSnapshotsData:
        """
        Retrieves NLP pool snapshots sampled over an interval or by submission index/cursor.

        Args:
            count (int | IndexerNlpSnapshotsParams, optional): Number of samples in the interval,
                or an IndexerNlpSnapshotsParams instance.
            granularity (int, optional): Seconds between samples.
            max_time (int, optional): Upper bound timestamp.
            idx (int, optional): Submission index cursor.
            limit (int, optional): Maximum snapshots to return.

        Returns:
            IndexerNlpSnapshotsData: The NLP pool snapshots.
        """
        if isinstance(count, IndexerNlpSnapshotsParams):
            params = count
        else:
            if (count is None) ^ (granularity is None):
                raise ValueError(
                    "Both 'count' and 'granularity' must be provided together for interval-based NLP snapshot queries."
                )
            interval = (
                IndexerMarketSnapshotInterval(
                    count=count, granularity=granularity, max_time=max_time
                )
                if count is not None and granularity is not None
                else None
            )
            params = IndexerNlpSnapshotsParams(
                interval=interval,
                idx=idx,
                max_time=max_time,
                limit=limit,
            )

        data = self.query(params).data
        if isinstance(data, IndexerMarketSnapshotsData) and not data.snapshots:
            data = IndexerNlpSnapshotsData(snapshots=[])
        return ensure_data_type(
            data,
            IndexerNlpSnapshotsData,
        )

    def get_fast_withdrawal_signature(
        self, idx: Union[str, int]
    ) -> IndexerFastWithdrawalSignatureData:
        """
        Retrieves the fast-withdrawal signature for a withdrawal by submission index.

        Args:
            idx (str | int): The withdrawal submission index.

        Returns:
            IndexerFastWithdrawalSignatureData: The signed withdrawal tx and signatures.
        """
        return ensure_data_type(
            self.query(IndexerFastWithdrawalSignatureParams(idx=idx)).data,
            IndexerFastWithdrawalSignatureData,
        )

    def get_leaderboard(
        self,
        contest_id: int,
        rank_type: Optional[str] = None,
        start: Optional[int] = None,
        limit: Optional[int] = None,
        order: Optional[str] = None,
    ) -> IndexerLeaderboardData:
        """
        Retrieves the leaderboard for a contest.

        Args:
            contest_id (int): The contest to rank.
            rank_type (str, optional): The track/rank type to sort by.
            start (int, optional): Pagination start offset.
            limit (int, optional): Maximum positions to return.
            order (str, optional): Sort order ("ASC" or "DESC").

        Returns:
            IndexerLeaderboardData: The leaderboard positions.
        """
        return ensure_data_type(
            self.query(
                IndexerLeaderboardParams(
                    contest_id=contest_id,
                    rank_type=rank_type,
                    start=start,
                    limit=limit,
                    order=order,
                )
            ).data,
            IndexerLeaderboardData,
        )

    def get_leaderboard_participant(
        self, subaccount: str, contest_ids: list[int]
    ) -> IndexerLeaderboardRankData:
        """
        Retrieves a subaccount's leaderboard positions across contests.

        Args:
            subaccount (str): The subaccount (bytes32 hex).
            contest_ids (list[int]): Contests to query.

        Returns:
            IndexerLeaderboardRankData: Positions keyed by contest id.
        """
        return ensure_data_type(
            self.query(
                IndexerLeaderboardRankParams(
                    contest_ids=contest_ids, subaccount=subaccount
                )
            ).data,
            IndexerLeaderboardRankData,
        )

    def get_leaderboard_contests(
        self,
        contest_ids: Optional[list[int]] = None,
        active: Optional[bool] = None,
    ) -> IndexerLeaderboardContestsData:
        """
        Retrieves leaderboard contests.

        Args:
            contest_ids (list[int], optional): Filter to specific contests.
            active (bool, optional): Filter by active status.

        Returns:
            IndexerLeaderboardContestsData: The contests.
        """
        return ensure_data_type(
            self.query(
                IndexerLeaderboardContestsParams(
                    contest_ids=contest_ids, active=active
                )
            ).data,
            IndexerLeaderboardContestsData,
        )

    def get_leaderboard_registrations(
        self,
        subaccount: str,
        contest_ids: Optional[list[int]] = None,
        active: Optional[bool] = None,
    ) -> IndexerLeaderboardRegistrationsData:
        """
        Retrieves a subaccount's leaderboard registrations.

        Args:
            subaccount (str): The subaccount (bytes32 hex).
            contest_ids (list[int], optional): Filter to specific contests.
            active (bool, optional): Filter by active status.

        Returns:
            IndexerLeaderboardRegistrationsData: The registrations.
        """
        return ensure_data_type(
            self.query(
                IndexerLeaderboardRegistrationsParams(
                    subaccount=subaccount, contest_ids=contest_ids, active=active
                )
            ).data,
            IndexerLeaderboardRegistrationsData,
        )

    def list_social_accounts(self, address: str) -> IndexerSocialAccountsData:
        """
        Lists the social accounts connected to an address.

        Args:
            address (str): The wallet address.

        Returns:
            IndexerSocialAccountsData: The connected social accounts.
        """
        return ensure_data_type(
            self.query(IndexerListSocialAccountsParams(address=address)).data,
            IndexerSocialAccountsData,
        )

    def _signed_query(self, request: dict, data_type):
        res = self.session.post(self.url, json=request)
        if res.status_code != 200:
            raise Exception(res.text)
        try:
            indexer_res = IndexerResponse(data=res.json())
        except Exception:
            raise Exception(res.text)
        return ensure_data_type(indexer_res.data, data_type)

    def register_leaderboard(
        self,
        signer: LocalAccount,
        chain_id: int,
        verifying_contract: str,
        sender: Subaccount,
        contest_ids: list[int],
        expiration: int,
    ) -> IndexerLeaderboardRegistrationsData:
        """
        Registers (or updates registration) a subaccount for leaderboard contests.

        This is a signed indexer write: the `LeaderboardAuthentication` payload is
        EIP-712 signed against the endpoint domain.

        Args:
            signer (LocalAccount): The account signing the authentication.
            chain_id (int): The network chain id.
            verifying_contract (str): The endpoint address (EIP-712 verifying contract).
            sender (Subaccount): The subaccount registering.
            contest_ids (list[int]): The contests to register for.
            expiration (int): Signature expiration (unix seconds).

        Returns:
            IndexerLeaderboardRegistrationsData: The resulting registrations.
        """
        sender_bytes = subaccount_to_bytes32(sender)
        signature = sign_eip712_typed_data(
            build_eip712_typed_data(
                NadoTxType.LEADERBOARD_AUTHENTICATION,
                {
                    "sender": sender_bytes,
                    "expiration": expiration,
                    "contestIds": contest_ids,
                },
                verifying_contract,
                chain_id,
            ),
            signer,
        )
        request = {
            "leaderboard_register": {
                "update_registration": {
                    "tx": {
                        "sender": bytes32_to_hex(sender_bytes),
                        "expiration": str(expiration),
                        "contestIds": contest_ids,
                    },
                    "signature": signature,
                }
            }
        }
        return self._signed_query(request, IndexerLeaderboardRegistrationsData)

    def connect_social_account(
        self,
        signer: LocalAccount,
        chain_id: int,
        verifying_contract: str,
        sender: Subaccount,
        provider: str,
        expiration: int,
    ) -> IndexerSocialConnectData:
        """
        Begins connecting a social account, returning an OAuth URL to complete it.

        Signed indexer write (`SocialAuthentication`, EIP-712).

        Returns:
            IndexerSocialConnectData: The OAuth URL to complete the connection.
        """
        return self._social_account_update(
            "social_connect",
            signer,
            chain_id,
            verifying_contract,
            sender,
            provider,
            expiration,
            IndexerSocialConnectData,
        )

    def revoke_social_account(
        self,
        signer: LocalAccount,
        chain_id: int,
        verifying_contract: str,
        sender: Subaccount,
        provider: str,
        expiration: int,
    ) -> IndexerSocialAccountsData:
        """
        Revokes a connected social account.

        Signed indexer write (`SocialAuthentication`, EIP-712).

        Returns:
            IndexerSocialAccountsData: The remaining connected accounts.
        """
        return self._social_account_update(
            "revoke_social_account",
            signer,
            chain_id,
            verifying_contract,
            sender,
            provider,
            expiration,
            IndexerSocialAccountsData,
        )

    def _social_account_update(
        self,
        method: str,
        signer: LocalAccount,
        chain_id: int,
        verifying_contract: str,
        sender: Subaccount,
        provider: str,
        expiration: int,
        data_type,
    ):
        sender_bytes = subaccount_to_bytes32(sender)
        signature = sign_eip712_typed_data(
            build_eip712_typed_data(
                NadoTxType.SOCIAL_AUTHENTICATION,
                {
                    "sender": sender_bytes,
                    "expiration": expiration,
                    "provider": provider,
                },
                verifying_contract,
                chain_id,
            ),
            signer,
        )
        request = {
            method: {
                "update_social_account": {
                    "tx": {
                        "sender": bytes32_to_hex(sender_bytes),
                        "expiration": str(expiration),
                        "provider": provider,
                    },
                    "signature": signature,
                }
            }
        }
        return self._signed_query(request, data_type)

    def get_edge_candlesticks(
        self,
        product_id: int,
        granularity: int,
        max_time: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> IndexerCandlesticksData:
        """
        Retrieves edge candlestick data for a product.

        Args:
            product_id (int): The product id.
            granularity (int): Candle granularity in seconds.
            max_time (int, optional): Upper bound timestamp.
            limit (int, optional): Maximum candles to return.

        Returns:
            IndexerCandlesticksData: The candlesticks.
        """
        return ensure_data_type(
            self.query(
                IndexerEdgeCandlesticksParams(
                    product_id=product_id,
                    granularity=granularity,
                    max_time=max_time,
                    limit=limit,
                )
            ).data,
            IndexerCandlesticksData,
        )

    def get_edge_market_snapshots(
        self, count: int, granularity: int, max_time: Optional[int] = None
    ) -> dict:
        """
        Retrieves edge market snapshots over an interval, keyed by timestamp.

        Args:
            count (int): Number of samples.
            granularity (int): Seconds between samples.
            max_time (int, optional): Upper bound timestamp.

        Returns:
            dict: Mapping of timestamp to a list of market snapshots.
        """
        interval: dict = {"count": count, "granularity": granularity}
        if max_time is not None:
            interval["max_time"] = max_time
        request = {"edge_market_snapshots": {"interval": interval}}
        res = self.session.post(self.url, json=request)
        if res.status_code != 200:
            raise Exception(res.text)
        body = res.json()
        return body.get("snapshots", body)

    def get_multi_product_snapshots(
        self,
        product_ids: list[int],
        max_time: Optional[Union[int, list[int]]] = None,
    ) -> dict:
        """
        Retrieves product snapshots for multiple products.

        Args:
            product_ids (list[int]): The products to query.
            max_time (int | list[int], optional): Upper-bound timestamp(s), inclusive.

        Returns:
            dict: Nested mapping of timestamp -> product_id -> snapshot.
        """
        request: dict = {"product_snapshots": {"product_ids": product_ids}}
        if max_time is not None:
            request["product_snapshots"]["max_time"] = max_time
        res = self.session.post(self.url, json=request)
        if res.status_code != 200:
            raise Exception(res.text)
        return res.json()

    def get_oracle_prices(self, product_ids: list[int]) -> IndexerOraclePricesData:
        """
        Retrieves the oracle price data for specific products.

        Args:
            product_ids (list[int]): A list of product identifiers.

        Returns:
            IndexerOraclePricesData: The oracle price data for the specified products.
        """
        return ensure_data_type(
            self.query(IndexerOraclePricesParams(product_ids=product_ids)).data,
            IndexerOraclePricesData,
        )

    def get_liquidation_feed(self) -> IndexerLiquidationFeedData:
        """
        Retrieves the liquidation feed data.

        Returns:
            IndexerLiquidationFeedData: The latest liquidation feed data.
        """
        return ensure_data_type(self.query(IndexerLiquidationFeedParams()).data, list)

    def get_linked_signer_rate_limits(
        self, subaccount: str
    ) -> IndexerLinkedSignerRateLimitData:
        """
        Retrieves the rate limits for a linked signer of a specific subaccount.

        Args:
            subaccount (str): The identifier of the subaccount.

        Returns:
            IndexerLinkedSignerRateLimitData: The rate limits for the linked signer of the specified subaccount.
        """
        return ensure_data_type(
            self.query(IndexerLinkedSignerRateLimitParams(subaccount=subaccount)).data,
            IndexerLinkedSignerRateLimitData,
        )

    def get_subaccounts(
        self, params: IndexerSubaccountsParams
    ) -> IndexerSubaccountsData:
        """
        Retrieves subaccounts via the indexer.

        Args:
            params (IndexerSubaccountsParams): The filter parameters for retrieving subaccounts.

        Returns:
            IndexerSubaccountsData: List of subaccounts found.
        """
        return ensure_data_type(
            self.query(params).data,
            IndexerSubaccountsData,
        )

    def get_quote_price(self) -> IndexerQuotePriceData:
        return ensure_data_type(
            self.query(IndexerQuotePriceParams()).data,
            IndexerQuotePriceData,
        )

    def get_interest_and_funding_payments(
        self, params: IndexerInterestAndFundingParams
    ) -> IndexerInterestAndFundingData:
        return ensure_data_type(
            self.query(
                params,
            ).data,
            IndexerInterestAndFundingData,
        )

    def get_tickers(
        self, market_type: Optional[MarketType] = None
    ) -> IndexerTickersData:
        url = f"{self.url_v2}/tickers"
        if market_type is not None:
            url += f"?market={str(market_type)}"
        return ensure_data_type(self._query_v2(url), dict)

    def get_perp_contracts_info(self) -> IndexerPerpContractsData:
        return ensure_data_type(self._query_v2(f"{self.url_v2}/contracts"), dict)

    def get_v2_symbols(
        self,
        product_type: Optional[str] = None,
        product_ids: Optional[list[int]] = None,
    ) -> dict:
        """
        Retrieves the v2 symbols map, including market hours and boost metadata.

        Args:
            product_type (str, optional): Filter by product type.
            product_ids (list[int], optional): Filter to specific products.

        Returns:
            dict: Mapping of symbol to its config (increments, fees, weights,
            market hours, boost, etc.).
        """
        url = f"{self.url_v2}/symbols"
        params = []
        if product_type is not None:
            params.append(f"product_type={product_type}")
        if product_ids is not None:
            params.append("product_ids=" + ",".join(str(p) for p in product_ids))
        if params:
            url += "?" + "&".join(params)
        return ensure_data_type(self._query_v2(url), dict)

    def get_historical_trades(
        self, ticker_id: str, limit: Optional[int], max_trade_id: Optional[int] = None
    ) -> IndexerHistoricalTradesData:
        url = f"{self.url_v2}/trades?ticker_id={ticker_id}"
        if limit is not None:
            url += f"&limit={limit}"
        if max_trade_id is not None:
            url += f"&max_trade_id={max_trade_id}"
        return ensure_data_type(self._query_v2(url), list)

    def get_multi_subaccount_snapshots(
        self, params: IndexerAccountSnapshotsParams
    ) -> IndexerAccountSnapshotsData:
        """
        Retrieves subaccount snapshots at specified timestamps.
        Each snapshot is a view of the subaccount's balances at that point in time,
        with tracked variables for interest, funding, etc.

        Args:
            params (IndexerAccountSnapshotsParams): Parameters specifying subaccounts,
                timestamps, and whether to include isolated positions.

        Returns:
            IndexerAccountSnapshotsData: Dict mapping subaccount hex -> timestamp -> snapshot data.
                Each snapshot contains balances with trackedVars including netEntryUnrealized.
        """
        return ensure_data_type(
            self.query(IndexerAccountSnapshotsParams.model_validate(params)).data,
            IndexerAccountSnapshotsData,
        )
