"""Client for the gateway edge/cached query endpoint (`/edge/query`).

These read pre-cached gateway state (prices, symbols, products, health groups,
BBO history) and offer lightweight `ping`/`time` control calls. Responses reuse
the same data models as the engine `/query` endpoint where shapes match.
"""

from typing import Optional

import requests

from nado_protocol.engine_client.types import EngineClientOpts
from nado_protocol.engine_client.types.query import (
    AllProductsData,
    ContractsData,
    HealthGroupsData,
    MarketPricesData,
    NlpPoolInfoData,
    StatusData,
    SymbolsData,
)
from nado_protocol.utils.exceptions import (
    BadStatusCodeException,
    QueryFailedException,
)
from nado_protocol.utils.model import NadoBaseModel, ensure_data_type


class BboHistorySample(NadoBaseModel):
    """A single best-bid/offer sample in a cached BBO history series."""

    product_id: int
    timestamp: str
    bid: str
    ask: str


class BboHistoryData(NadoBaseModel):
    """Cached rolling best-bid/offer history (up to ~30 minutes)."""

    interval_ms: int
    limit: int
    history: list[BboHistorySample]


class EngineEdgeQueryClient:
    """Client for the `/edge/query` cached-read endpoint."""

    def __init__(self, opts: EngineClientOpts):
        self._opts = EngineClientOpts.model_validate(opts)
        self.url = f"{self._opts.url}/edge/query"
        self.session = requests.Session()
        self.session.headers.update({"Accept-Encoding": "gzip"})

    def _edge_query(self, request: dict, data_type):
        res = self.session.post(self.url, json=request)
        if res.status_code != 200:
            raise BadStatusCodeException(res.text)
        body = res.json()
        if body.get("status") != "success":
            raise QueryFailedException(res.text)
        return ensure_data_type(data_type.model_validate(body["data"]), data_type)

    def get_cached_market_prices(
        self, product_ids: Optional[list[int]] = None
    ) -> MarketPricesData:
        """Cached best bid/ask prices, optionally filtered to `product_ids`."""
        request: dict = {"type": "cached_prices"}
        if product_ids is not None:
            request["product_ids"] = product_ids
        return self._edge_query(request, MarketPricesData)

    def get_cached_symbols(
        self,
        product_ids: Optional[list[int]] = None,
        product_type: Optional[str] = None,
    ) -> SymbolsData:
        """Cached symbol/product configuration."""
        request: dict = {"type": "cached_symbols"}
        if product_ids is not None:
            request["product_ids"] = product_ids
        if product_type is not None:
            request["product_type"] = product_type
        return self._edge_query(request, SymbolsData)

    def get_cached_contracts(self) -> ContractsData:
        """Cached chain id and endpoint address."""
        return self._edge_query({"type": "cached_contracts"}, ContractsData)

    def get_cached_status(self) -> StatusData:
        """Cached engine status."""
        return self._edge_query({"type": "cached_status"}, StatusData)

    def get_cached_all_products(self) -> AllProductsData:
        """Cached spot + perp product list."""
        return self._edge_query({"type": "cached_all_products"}, AllProductsData)

    def get_cached_edge_all_products(self) -> dict:
        """Cached spot + perp products across chains, keyed by chain id."""
        res = self.session.post(self.url, json={"type": "cached_edge_all_products"})
        if res.status_code != 200:
            raise BadStatusCodeException(res.text)
        body = res.json()
        if body.get("status") != "success":
            raise QueryFailedException(res.text)
        return body["data"]

    def get_cached_health_groups(self) -> HealthGroupsData:
        """Cached spot/perp health group pairs."""
        return self._edge_query({"type": "cached_health_groups"}, HealthGroupsData)

    def get_cached_nlp_pool_info(self) -> NlpPoolInfoData:
        """Cached NLP pool info."""
        return self._edge_query({"type": "cached_nlp_pool_info"}, NlpPoolInfoData)

    def get_cached_bbo_history(
        self,
        product_ids: Optional[list[int]] = None,
        interval_ms: Optional[int] = None,
        max_time_ms: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> BboHistoryData:
        """Cached rolling best-bid/offer history per product."""
        request: dict = {"type": "cached_bbo_history"}
        if product_ids is not None:
            request["product_ids"] = product_ids
        if interval_ms is not None:
            request["interval_ms"] = interval_ms
        if max_time_ms is not None:
            request["max_time_ms"] = max_time_ms
        if limit is not None:
            request["limit"] = limit
        return self._edge_query(request, BboHistoryData)

    def ping(self, client_time: Optional[str] = None, id: Optional[int] = None) -> dict:
        """Edge-control ping; returns the raw `pong` control response."""
        request: dict = {"type": "ping"}
        if id is not None:
            request["id"] = id
        if client_time is not None:
            request["client_time"] = client_time
        res = self.session.post(self.url, json=request)
        if res.status_code != 200:
            raise BadStatusCodeException(res.text)
        return res.json()

    def time(self, id: Optional[int] = None) -> dict:
        """Edge-control server time; returns the raw control response."""
        request: dict = {"type": "time"}
        if id is not None:
            request["id"] = id
        res = self.session.post(self.url, json=request)
        if res.status_code != 200:
            raise BadStatusCodeException(res.text)
        return res.json()
