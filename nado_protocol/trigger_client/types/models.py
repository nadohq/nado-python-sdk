from typing import Optional, Union
from nado_protocol.utils.model import NadoBaseModel


class PriceAboveTrigger(NadoBaseModel):
    price_above: str


class PriceBelowTrigger(NadoBaseModel):
    price_below: str


class LastPriceAboveTrigger(NadoBaseModel):
    last_price_above: str


class LastPriceBelowTrigger(NadoBaseModel):
    last_price_below: str


TriggerCriteria = Union[
    PriceAboveTrigger, PriceBelowTrigger, LastPriceAboveTrigger, LastPriceBelowTrigger
]


class OrderData(NadoBaseModel):
    sender: str
    priceX18: str
    amount: str
    expiration: str
    nonce: str


class TriggerOrderData(NadoBaseModel):
    """
    Data model for details of a trigger order.
    """

    product_id: int
    order: OrderData
    signature: str
    spot_leverage: Optional[bool]
    digest: Optional[str]
    trigger: TriggerCriteria
