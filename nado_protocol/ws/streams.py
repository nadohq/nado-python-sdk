"""Stream subscription parameter models for the `/subscribe` endpoint.

Each model serializes (via `.dict()`) to the `{ "type": "<stream>", ...params }`
object the server expects. `chain_id` is never sent — the gateway injects it from
the connection host. Subaccounts are normalized to lowercase hex.
"""

from typing import Optional, Union

from pydantic import field_validator

from nado_protocol.utils.model import NadoBaseModel


class TradeStream(NadoBaseModel):
    type: str = "trade"
    product_id: int


class BestBidOfferStream(NadoBaseModel):
    type: str = "best_bid_offer"
    product_id: int


class BookDepthStream(NadoBaseModel):
    type: str = "book_depth"
    product_id: int


class FillStream(NadoBaseModel):
    type: str = "fill"
    subaccount: str
    product_id: Optional[int] = None

    @field_validator("subaccount")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class PositionChangeStream(NadoBaseModel):
    type: str = "position_change"
    subaccount: str
    product_id: Optional[int] = None

    @field_validator("subaccount")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class OrderUpdateStream(NadoBaseModel):
    type: str = "order_update"
    subaccount: str
    product_id: Optional[int] = None

    @field_validator("subaccount")
    @classmethod
    def _lower(cls, v: str) -> str:
        return v.lower()


class LiquidationStream(NadoBaseModel):
    type: str = "liquidation"
    product_id: Optional[int] = None


class LatestCandlestickStream(NadoBaseModel):
    type: str = "latest_candlestick"
    product_id: int
    granularity: int


class FundingPaymentStream(NadoBaseModel):
    type: str = "funding_payment"
    product_id: int


class FundingRateStream(NadoBaseModel):
    type: str = "funding_rate"
    product_id: Optional[int] = None


class AllBboStream(NadoBaseModel):
    type: str = "all_bbo"


StreamSubscription = Union[
    TradeStream,
    BestBidOfferStream,
    BookDepthStream,
    FillStream,
    PositionChangeStream,
    OrderUpdateStream,
    LiquidationStream,
    LatestCandlestickStream,
    FundingPaymentStream,
    FundingRateStream,
    AllBboStream,
]
