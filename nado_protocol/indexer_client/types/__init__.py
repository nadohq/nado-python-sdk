from typing import Union
from pydantic import BaseModel, AnyUrl, field_validator, TypeAdapter
from nado_protocol.indexer_client.types.models import *
from nado_protocol.indexer_client.types.query import *


class IndexerClientOpts(BaseModel):
    """
    Model representing the options for the Indexer Client
    """

    url: str

    @field_validator("url")
    @classmethod
    def clean_url(cls, v: Union[str, AnyUrl]) -> str:
        TypeAdapter(AnyUrl).validate_python(v)
        return str(v).rstrip("/")


__all__ = [
    "IndexerQueryType",
    "IndexerBaseParams",
    "IndexerSubaccountHistoricalOrdersParams",
    "IndexerHistoricalOrdersByDigestParams",
    "IndexerMatchesParams",
    "IndexerEventsRawLimit",
    "IndexerEventsTxsLimit",
    "IndexerEventsLimit",
    "IndexerEventsParams",
    "IndexerProductSnapshotsParams",
    "IndexerCandlesticksParams",
    "IndexerFundingRateParams",
    "IndexerPerpPricesParams",
    "IndexerOraclePricesParams",
    "IndexerLiquidationFeedParams",
    "IndexerLinkedSignerRateLimitParams",
    "IndexerSubaccountsParams",
    "IndexerParams",
    "IndexerHistoricalOrdersRequest",
    "IndexerMatchesRequest",
    "IndexerEventsRequest",
    "IndexerProductSnapshotsRequest",
    "IndexerCandlesticksRequest",
    "IndexerFundingRateRequest",
    "IndexerFundingRatesRequest",
    "IndexerPerpPricesRequest",
    "IndexerOraclePricesRequest",
    "IndexerLiquidationFeedRequest",
    "IndexerLinkedSignerRateLimitRequest",
    "IndexerSubaccountsRequest",
    "IndexerRequest",
    "IndexerHistoricalOrdersData",
    "IndexerMatchesData",
    "IndexerEventsData",
    "IndexerProductSnapshotsData",
    "IndexerCandlesticksData",
    "IndexerFundingRateData",
    "IndexerPerpPricesData",
    "IndexerOraclePricesData",
    "IndexerLinkedSignerRateLimitData",
    "IndexerSubaccountsData",
    "IndexerQuotePriceData",
    "IndexerLiquidationFeedData",
    "IndexerResponseData",
    "IndexerResponse",
    "IndexerEventType",
    "IndexerCandlesticksGranularity",
    "IndexerBaseModel",
    "IndexerBaseOrder",
    "IndexerOrderFill",
    "IndexerHistoricalOrder",
    "IndexerSignedOrder",
    "IndexerMatch",
    "IndexerMatchOrdersTxData",
    "IndexerMatchOrdersTx",
    "IndexerWithdrawCollateralTxData",
    "IndexerWithdrawCollateralTx",
    "IndexerLiquidateSubaccountTxData",
    "IndexerLiquidateSubaccountTx",
    "IndexerMintNlpTxData",
    "IndexerMintNlpTx",
    "IndexerBurnNlpTxData",
    "IndexerBurnNlpTx",
    "IndexerTxData",
    "IndexerTx",
    "IndexerSpotProductBalanceData",
    "IndexerSpotProductData",
    "IndexerPerpProductData",
    "IndexerProductData",
    "IndexerEventTrackedData",
    "IndexerEvent",
    "IndexerProduct",
    "IndexerCandlestick",
    "IndexerOraclePrice",
    "IndexerAddressReward",
    "IndexerGlobalRewards",
    "IndexerTokenReward",
    "IndexerMarketMakerData",
    "IndexerMarketMaker",
    "IndexerLiquidatableAccount",
    "IndexerSubaccount",
    "IndexerUsdcPriceData",
    "IndexerInterestAndFundingParams",
    "IndexerInterestAndFundingRequest",
    "IndexerInterestAndFundingData",
    "IndexerTickerInfo",
    "IndexerPerpContractInfo",
    "IndexerTradeInfo",
    "IndexerTickersData",
    "IndexerPerpContractsData",
    "IndexerHistoricalTradesData",
]
