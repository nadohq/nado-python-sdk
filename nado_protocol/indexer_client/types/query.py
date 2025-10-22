from nado_protocol.utils.enum import StrEnum
from typing import Dict, Optional, Union

from pydantic import Field, validator
from nado_protocol.indexer_client.types.models import (
    IndexerCandlestick,
    IndexerCandlesticksGranularity,
    IndexerEvent,
    IndexerEventType,
    IndexerHistoricalOrder,
    IndexerLiquidatableAccount,
    IndexerMarketMaker,
    IndexerMatch,
    IndexerOraclePrice,
    IndexerPerpContractInfo,
    IndexerProduct,
    IndexerMarketSnapshot,
    IndexerSubaccount,
    IndexerTickerInfo,
    IndexerTokenReward,
    IndexerTradeInfo,
    IndexerTx,
    IndexerMerkleProof,
    IndexerPayment,
)
from nado_protocol.utils.model import NadoBaseModel


class IndexerQueryType(StrEnum):
    """
    Enumeration of query types available in the Indexer service.
    """

    ORDERS = "orders"
    MATCHES = "matches"
    EVENTS = "events"
    SUMMARY = "summary"
    PRODUCTS = "products"
    MARKET_SNAPSHOTS = "market_snapshots"
    CANDLESTICKS = "candlesticks"
    FUNDING_RATE = "funding_rate"
    FUNDING_RATES = "funding_rates"
    PERP_PRICES = "price"
    ORACLE_PRICES = "oracle_price"
    REWARDS = "rewards"
    MAKER_STATISTICS = "maker_statistics"
    LIQUIDATION_FEED = "liquidation_feed"
    LINKED_SIGNER_RATE_LIMIT = "linked_signer_rate_limit"
    REFERRAL_CODE = "referral_code"
    SUBACCOUNTS = "subaccounts"
    USDC_PRICE = "usdc_price"
    ACCOUNT_SNAPSHOTS = "account_snapshots"
    # TODO: revise once this endpoint is live
    TOKEN_MERKLE_PROOFS = "token_merkle_proofs"
    FOUNDATION_REWARDS_MERKLE_PROOFS = "foundation_rewards_merkle_proofs"
    INTEREST_AND_FUNDING = "interest_and_funding"


class IndexerBaseParams(NadoBaseModel):
    """
    Base parameters for the indexer queries.
    """

    idx: Optional[int] = Field(alias="submission_idx")
    max_time: Optional[int]
    limit: Optional[int]

    class Config:
        allow_population_by_field_name = True


class IndexerSubaccountHistoricalOrdersParams(IndexerBaseParams):
    """
    Parameters for querying historical orders by subaccount.
    """

    subaccount: str
    product_ids: Optional[list[int]]
    trigger_types: Optional[list[str]]
    isolated: Optional[bool]


class IndexerHistoricalOrdersByDigestParams(NadoBaseModel):
    """
    Parameters for querying historical orders by digests.
    """

    digests: list[str]


class IndexerMatchesParams(IndexerBaseParams):
    """
    Parameters for querying matches.
    """

    subaccount: Optional[str]
    product_ids: Optional[list[int]]
    isolated: Optional[bool]


class IndexerEventsRawLimit(NadoBaseModel):
    """
    Parameters for limiting by events count.
    """

    raw: int


class IndexerEventsTxsLimit(NadoBaseModel):
    """
    Parameters for limiting events by transaction count.
    """

    txs: int


IndexerEventsLimit = Union[IndexerEventsRawLimit, IndexerEventsTxsLimit]


class IndexerEventsParams(IndexerBaseParams):
    """
    Parameters for querying events.
    """

    subaccount: Optional[str]
    product_ids: Optional[list[int]]
    event_types: Optional[list[IndexerEventType]]
    isolated: Optional[bool]
    limit: Optional[IndexerEventsLimit]  # type: ignore


class IndexerSubaccountSummaryParams(NadoBaseModel):
    """
    Parameters for querying subaccount summary.
    """

    subaccount: str
    timestamp: Optional[int] = None
    active: Optional[bool] = None


class IndexerProductSnapshotsParams(IndexerBaseParams):
    """
    Parameters for querying product snapshots.
    """

    product_id: int


class IndexerMarketSnapshotInterval(NadoBaseModel):
    count: int
    granularity: int
    max_time: Optional[int]


class IndexerMarketSnapshotsParams(NadoBaseModel):
    """
    Parameters for querying market snapshots.
    """

    interval: IndexerMarketSnapshotInterval
    product_ids: Optional[list[int]]


class IndexerCandlesticksParams(IndexerBaseParams):
    """
    Parameters for querying candlestick data.
    """

    product_id: int
    granularity: IndexerCandlesticksGranularity

    class Config:
        fields = {"idx": {"exclude": True}}


class IndexerFundingRateParams(NadoBaseModel):
    """
    Parameters for querying funding rates.
    """

    product_id: int


class IndexerFundingRatesParams(NadoBaseModel):
    """
    Parameters for querying funding rates.
    """

    product_ids: list


class IndexerPerpPricesParams(NadoBaseModel):
    """
    Parameters for querying perpetual prices.
    """

    product_id: int


class IndexerOraclePricesParams(NadoBaseModel):
    """
    Parameters for querying oracle prices.
    """

    product_ids: list[int]


class IndexerTokenRewardsParams(NadoBaseModel):
    """
    Parameters for querying token rewards.
    """

    address: str


class IndexerMakerStatisticsParams(NadoBaseModel):
    """
    Parameters for querying maker statistics.
    """

    product_id: int
    epoch: int
    interval: int


class IndexerLiquidationFeedParams(NadoBaseModel):
    """
    Parameters for querying liquidation feed.
    """

    pass


class IndexerLinkedSignerRateLimitParams(NadoBaseModel):
    """
    Parameters for querying linked signer rate limits.
    """

    subaccount: str


class IndexerReferralCodeParams(NadoBaseModel):
    """
    Parameters for querying a referral code.
    """

    subaccount: str


class IndexerSubaccountsParams(NadoBaseModel):
    """
    Parameters for querying subaccounts.
    """

    address: Optional[str]
    limit: Optional[int]
    start: Optional[int]


class IndexerUsdcPriceParams(NadoBaseModel):
    """
    Parameters for querying usdc price.
    """

    pass


class IndexerTokenMerkleProofsParams(NadoBaseModel):
    """
    Parameters for querying token merkle proofs.
    """

    address: str


class IndexerFoundationRewardsMerkleProofsParams(NadoBaseModel):
    """
    Parameters for querying Foundation Rewards merkle proofs.
    """

    address: str


class IndexerInterestAndFundingParams(NadoBaseModel):
    """
    Parameters for querying interest and funding payments.
    """

    subaccount: str
    product_ids: list[int]
    max_idx: Optional[Union[str, int]]
    limit: int


class IndexerAccountSnapshotsParams(NadoBaseModel):
    """
    Parameters for querying account snapshots.
    """

    subaccounts: list[str]
    timestamps: list[int]
    isolated: Optional[bool] = None
    active: Optional[bool] = None


IndexerParams = Union[
    IndexerSubaccountHistoricalOrdersParams,
    IndexerHistoricalOrdersByDigestParams,
    IndexerMatchesParams,
    IndexerEventsParams,
    IndexerSubaccountSummaryParams,
    IndexerProductSnapshotsParams,
    IndexerCandlesticksParams,
    IndexerFundingRateParams,
    IndexerPerpPricesParams,
    IndexerOraclePricesParams,
    IndexerTokenRewardsParams,
    IndexerMakerStatisticsParams,
    IndexerLiquidationFeedParams,
    IndexerLinkedSignerRateLimitParams,
    IndexerReferralCodeParams,
    IndexerSubaccountsParams,
    IndexerUsdcPriceParams,
    IndexerMarketSnapshotsParams,
    IndexerTokenMerkleProofsParams,
    IndexerFoundationRewardsMerkleProofsParams,
    IndexerInterestAndFundingParams,
    IndexerAccountSnapshotsParams,
]


class IndexerHistoricalOrdersRequest(NadoBaseModel):
    """
    Request object for querying historical orders.
    """

    orders: Union[
        IndexerSubaccountHistoricalOrdersParams, IndexerHistoricalOrdersByDigestParams
    ]


class IndexerMatchesRequest(NadoBaseModel):
    """
    Request object for querying matches.
    """

    matches: IndexerMatchesParams


class IndexerEventsRequest(NadoBaseModel):
    """
    Request object for querying events.
    """

    events: IndexerEventsParams


class IndexerSubaccountSummaryRequest(NadoBaseModel):
    """
    Request object for querying subaccount summary.
    """

    summary: IndexerSubaccountSummaryParams


class IndexerProductSnapshotsRequest(NadoBaseModel):
    """
    Request object for querying product snapshots.
    """

    products: IndexerProductSnapshotsParams


class IndexerMarketSnapshotsRequest(NadoBaseModel):
    """
    Request object for querying market snapshots.
    """

    market_snapshots: IndexerMarketSnapshotsParams


class IndexerCandlesticksRequest(NadoBaseModel):
    """
    Request object for querying candlestick data.
    """

    candlesticks: IndexerCandlesticksParams


class IndexerFundingRateRequest(NadoBaseModel):
    """
    Request object for querying funding rates.
    """

    funding_rate: IndexerFundingRateParams


class IndexerFundingRatesRequest(NadoBaseModel):
    """
    Request object for querying funding rates.
    """

    funding_rates: IndexerFundingRatesParams


class IndexerPerpPricesRequest(NadoBaseModel):
    """
    Request object for querying perpetual prices.
    """

    price: IndexerPerpPricesParams


class IndexerOraclePricesRequest(NadoBaseModel):
    """
    Request object for querying oracle prices.
    """

    oracle_price: IndexerOraclePricesParams


class IndexerTokenRewardsRequest(NadoBaseModel):
    """
    Request object for querying token rewards.
    """

    rewards: IndexerTokenRewardsParams


class IndexerMakerStatisticsRequest(NadoBaseModel):
    """
    Request object for querying maker statistics.
    """

    maker_statistics: IndexerMakerStatisticsParams


class IndexerLiquidationFeedRequest(NadoBaseModel):
    """
    Request object for querying liquidation feed.
    """

    liquidation_feed: IndexerLiquidationFeedParams


class IndexerLinkedSignerRateLimitRequest(NadoBaseModel):
    """
    Request object for querying linked signer rate limits.
    """

    linked_signer_rate_limit: IndexerLinkedSignerRateLimitParams


class IndexerReferralCodeRequest(NadoBaseModel):
    """
    Request object for querying a referral code.
    """

    referral_code: IndexerReferralCodeParams


class IndexerSubaccountsRequest(NadoBaseModel):
    """
    Request object for querying subaccounts.
    """

    subaccounts: IndexerSubaccountsParams


class IndexerUsdcPriceRequest(NadoBaseModel):
    """
    Request object for querying usdc price.
    """

    usdc_price: IndexerUsdcPriceParams


class IndexerTokenMerkleProofsRequest(NadoBaseModel):
    """
    Request object for querying token merkle proofs.
    """

    token_merkle_proofs: IndexerTokenMerkleProofsParams


class IndexerFoundationRewardsMerkleProofsRequest(NadoBaseModel):
    """
    Request object for querying Foundation Rewards merkle proofs.
    """

    foundation_rewards_merkle_proofs: IndexerFoundationRewardsMerkleProofsParams


class IndexerInterestAndFundingRequest(NadoBaseModel):
    """
    Request object for querying Interest and funding payments.
    """

    interest_and_funding: IndexerInterestAndFundingParams


class IndexerAccountSnapshotsRequest(NadoBaseModel):
    """
    Request object for querying account snapshots.
    """

    account_snapshots: IndexerAccountSnapshotsParams


IndexerRequest = Union[
    IndexerHistoricalOrdersRequest,
    IndexerMatchesRequest,
    IndexerEventsRequest,
    IndexerSubaccountSummaryRequest,
    IndexerProductSnapshotsRequest,
    IndexerCandlesticksRequest,
    IndexerFundingRateRequest,
    IndexerPerpPricesRequest,
    IndexerOraclePricesRequest,
    IndexerTokenRewardsRequest,
    IndexerMakerStatisticsRequest,
    IndexerLiquidationFeedRequest,
    IndexerLinkedSignerRateLimitRequest,
    IndexerReferralCodeRequest,
    IndexerSubaccountsRequest,
    IndexerUsdcPriceRequest,
    IndexerMarketSnapshotsRequest,
    IndexerTokenMerkleProofsRequest,
    IndexerFoundationRewardsMerkleProofsRequest,
    IndexerInterestAndFundingRequest,
    IndexerAccountSnapshotsRequest,
]


class IndexerHistoricalOrdersData(NadoBaseModel):
    """
    Data object for historical orders.
    """

    orders: list[IndexerHistoricalOrder]


class IndexerMatchesData(NadoBaseModel):
    """
    Data object for matches.
    """

    matches: list[IndexerMatch]
    txs: list[IndexerTx]


class IndexerEventsData(NadoBaseModel):
    """
    Data object for events.
    """

    events: list[IndexerEvent]
    txs: list[IndexerTx]


class IndexerSubaccountSummaryData(NadoBaseModel):
    """
    Data object for subaccount summary.
    """

    events: list[IndexerEvent]


class IndexerProductSnapshotsData(NadoBaseModel):
    """
    Data object for product snapshots.
    """

    products: list[IndexerProduct]
    txs: list[IndexerTx]


class IndexerMarketSnapshotsData(NadoBaseModel):
    """
    Data object for market snapshots.
    """

    snapshots: list[IndexerMarketSnapshot]


class IndexerCandlesticksData(NadoBaseModel):
    """
    Data object for candlestick data.
    """

    candlesticks: list[IndexerCandlestick]


class IndexerFundingRateData(NadoBaseModel):
    """
    Data object for funding rates.
    """

    product_id: int
    funding_rate_x18: str
    update_time: str


IndexerFundingRatesData = Dict[str, IndexerFundingRateData]


class IndexerPerpPricesData(NadoBaseModel):
    """
    Data object for perpetual prices.
    """

    product_id: int
    index_price_x18: str
    mark_price_x18: str
    update_time: str


class IndexerOraclePricesData(NadoBaseModel):
    """
    Data object for oracle prices.
    """

    prices: list[IndexerOraclePrice]


class IndexerTokenRewardsData(NadoBaseModel):
    """
    Data object for token rewards.
    """

    rewards: list[IndexerTokenReward]
    update_time: str
    total_referrals: str


class IndexerMakerStatisticsData(NadoBaseModel):
    """
    Data object for maker statistics.
    """

    reward_coefficient: float
    makers: list[IndexerMarketMaker]


class IndexerLinkedSignerRateLimitData(NadoBaseModel):
    """
    Data object for linked signer rate limits.
    """

    remaining_tx: str
    total_tx_limit: str
    wait_time: int
    signer: str


class IndexerReferralCodeData(NadoBaseModel):
    """
    Data object for referral codes.
    """

    referral_code: str

    @validator("referral_code", pre=True, always=True)
    def set_default_referral_code(cls, v):
        return v or ""


class IndexerSubaccountsData(NadoBaseModel):
    """
    Data object for subaccounts response from the indexer.
    """

    subaccounts: list[IndexerSubaccount]


class IndexerUsdcPriceData(NadoBaseModel):
    """
    Data object for the usdc price response from the indexer.
    """

    price_x18: str


class IndexerMerkleProofsData(NadoBaseModel):
    """
    Data object for the merkle proofs response from the indexer.
    """

    merkle_proofs: list[IndexerMerkleProof]


class IndexerInterestAndFundingData(NadoBaseModel):
    """
    Data object for the interest and funding payments response from the indexer.
    """

    interest_payments: list[IndexerPayment]
    funding_payments: list[IndexerPayment]
    next_idx: str


IndexerLiquidationFeedData = list[IndexerLiquidatableAccount]


class IndexerAccountSnapshotsData(NadoBaseModel):
    """
    Data object for subaccount snapshots grouped by subaccount and timestamp.
    """

    snapshots: Dict[str, Dict[str, list[IndexerEvent]]]


IndexerResponseData = Union[
    IndexerHistoricalOrdersData,
    IndexerMatchesData,
    IndexerEventsData,
    IndexerSubaccountSummaryData,
    IndexerProductSnapshotsData,
    IndexerCandlesticksData,
    IndexerFundingRateData,
    IndexerPerpPricesData,
    IndexerOraclePricesData,
    IndexerTokenRewardsData,
    IndexerMakerStatisticsData,
    IndexerLinkedSignerRateLimitData,
    IndexerReferralCodeData,
    IndexerSubaccountsData,
    IndexerUsdcPriceData,
    IndexerMarketSnapshotsData,
    IndexerMerkleProofsData,
    IndexerInterestAndFundingData,
    IndexerLiquidationFeedData,
    IndexerFundingRatesData,
    IndexerAccountSnapshotsData,
]


class IndexerResponse(NadoBaseModel):
    """
    Represents the response returned by the indexer.

    Attributes:
        data (IndexerResponseData): The data contained in the response.
    """

    data: IndexerResponseData


def to_indexer_request(params: IndexerParams) -> IndexerRequest:
    """
    Converts an IndexerParams object to the corresponding IndexerRequest object.

    Args:
        params (IndexerParams): The IndexerParams object to convert.

    Returns:
        IndexerRequest: The converted IndexerRequest object.
    """
    indexer_request_mapping = {
        IndexerSubaccountHistoricalOrdersParams: (
            IndexerHistoricalOrdersRequest,
            IndexerQueryType.ORDERS.value,
        ),
        IndexerHistoricalOrdersByDigestParams: (
            IndexerHistoricalOrdersRequest,
            IndexerQueryType.ORDERS.value,
        ),
        IndexerMatchesParams: (IndexerMatchesRequest, IndexerQueryType.MATCHES.value),
        IndexerEventsParams: (IndexerEventsRequest, IndexerQueryType.EVENTS.value),
        IndexerSubaccountSummaryParams: (
            IndexerSubaccountSummaryRequest,
            IndexerQueryType.SUMMARY.value,
        ),
        IndexerProductSnapshotsParams: (
            IndexerProductSnapshotsRequest,
            IndexerQueryType.PRODUCTS.value,
        ),
        IndexerMarketSnapshotsParams: (
            IndexerMarketSnapshotsRequest,
            IndexerQueryType.MARKET_SNAPSHOTS.value,
        ),
        IndexerCandlesticksParams: (
            IndexerCandlesticksRequest,
            IndexerQueryType.CANDLESTICKS.value,
        ),
        IndexerFundingRateParams: (
            IndexerFundingRateRequest,
            IndexerQueryType.FUNDING_RATE.value,
        ),
        IndexerFundingRatesParams: (
            IndexerFundingRatesRequest,
            IndexerQueryType.FUNDING_RATES.value,
        ),
        IndexerPerpPricesParams: (
            IndexerPerpPricesRequest,
            IndexerQueryType.PERP_PRICES.value,
        ),
        IndexerOraclePricesParams: (
            IndexerOraclePricesRequest,
            IndexerQueryType.ORACLE_PRICES.value,
        ),
        IndexerTokenRewardsParams: (
            IndexerTokenRewardsRequest,
            IndexerQueryType.REWARDS.value,
        ),
        IndexerMakerStatisticsParams: (
            IndexerMakerStatisticsRequest,
            IndexerQueryType.MAKER_STATISTICS.value,
        ),
        IndexerLiquidationFeedParams: (
            IndexerLiquidationFeedRequest,
            IndexerQueryType.LIQUIDATION_FEED.value,
        ),
        IndexerLinkedSignerRateLimitParams: (
            IndexerLinkedSignerRateLimitRequest,
            IndexerQueryType.LINKED_SIGNER_RATE_LIMIT.value,
        ),
        IndexerReferralCodeParams: (
            IndexerReferralCodeRequest,
            IndexerQueryType.REFERRAL_CODE.value,
        ),
        IndexerSubaccountsParams: (
            IndexerSubaccountsRequest,
            IndexerQueryType.SUBACCOUNTS.value,
        ),
        IndexerUsdcPriceParams: (
            IndexerUsdcPriceRequest,
            IndexerQueryType.USDC_PRICE.value,
        ),
        IndexerTokenMerkleProofsParams: (
            IndexerTokenMerkleProofsRequest,
            IndexerQueryType.TOKEN_MERKLE_PROOFS.value,
        ),
        IndexerFoundationRewardsMerkleProofsParams: (
            IndexerFoundationRewardsMerkleProofsRequest,
            IndexerQueryType.FOUNDATION_REWARDS_MERKLE_PROOFS.value,
        ),
        IndexerInterestAndFundingParams: (
            IndexerInterestAndFundingRequest,
            IndexerQueryType.INTEREST_AND_FUNDING.value,
        ),
        IndexerAccountSnapshotsParams: (
            IndexerAccountSnapshotsRequest,
            IndexerQueryType.ACCOUNT_SNAPSHOTS.value,
        ),
    }

    RequestClass, field_name = indexer_request_mapping[type(params)]
    return RequestClass(**{field_name: params})


IndexerTickersData = Dict[str, IndexerTickerInfo]

IndexerPerpContractsData = Dict[str, IndexerPerpContractInfo]

IndexerHistoricalTradesData = list[IndexerTradeInfo]
