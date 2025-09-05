from nado_protocol.engine_client.types.execute import (
    BurnNlpParams,
    CancelAndPlaceParams,
    CancelOrdersParams,
    CancelProductOrdersParams,
    ExecuteResponse,
    MintNlpParams,
    PlaceMarketOrderParams,
    PlaceOrderParams,
)
from nado_protocol.client.apis.base import NadoBaseAPI
from nado_protocol.trigger_client.types.execute import (
    PlaceTriggerOrderParams,
    CancelTriggerOrdersParams,
    CancelProductTriggerOrdersParams,
)
from nado_protocol.utils.exceptions import MissingTriggerClient
from nado_protocol.utils.subaccount import Subaccount


class MarketExecuteAPI(NadoBaseAPI):
    """
    Provides functionality to interact with the Nado's market execution APIs.
    This class contains methods that allow clients to execute operations such as minting LP tokens, burning LP tokens,
    placing and cancelling orders on the Nado market.

    Attributes:
        context (NadoClientContext): The context that provides connectivity configuration for NadoClient.

    Note:
        This class should not be instantiated directly, it is designed to be used through a NadoClient instance.
    """

    def mint_nlp(self, params: MintNlpParams) -> ExecuteResponse:
        """
        Mint NLP tokens through the engine.

        Args:
            params (MintNlpParams): Parameters required to mint NLP tokens.

        Returns:
            ExecuteResponse: The response from the engine execution.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.mint_nlp(params)

    def burn_nlp(self, params: BurnNlpParams) -> ExecuteResponse:
        """
        Burn NLP tokens through the engine.

        Args:
            params (BurnNlpParams): Parameters required to burn NLP tokens.

        Returns:
            ExecuteResponse: The response from the engine execution.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.burn_nlp(params)

    def place_order(self, params: PlaceOrderParams) -> ExecuteResponse:
        """
        Places an order through the engine.

        Args:
            params (PlaceOrderParams): Parameters required to place an order.

        Returns:
            ExecuteResponse: The response from the engine execution.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.place_order(params)

    def place_market_order(self, params: PlaceMarketOrderParams) -> ExecuteResponse:
        """
        Places a market order through the engine.

        Args:
            params (PlaceMarketOrderParams): Parameters required to place a market order.

        Returns:
            ExecuteResponse: The response from the engine execution.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.place_market_order(params)

    def cancel_orders(self, params: CancelOrdersParams) -> ExecuteResponse:
        """
        Cancels orders through the engine.

        Args:
            params (CancelOrdersParams): Parameters required to cancel orders.

        Returns:
            ExecuteResponse: The response from the engine execution containing information about the canceled product orders.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.cancel_orders(params)

    def cancel_product_orders(
        self, params: CancelProductOrdersParams
    ) -> ExecuteResponse:
        """
        Cancels all orders for provided products through the engine.

        Args:
            params (CancelProductOrdersParams): Parameters required to cancel product orders.

        Returns:
            ExecuteResponse: The response from the engine execution containing information about the canceled product orders.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.cancel_product_orders(params)

    def cancel_and_place(self, params: CancelAndPlaceParams) -> ExecuteResponse:
        """
        Cancels orders and places a new one through the engine on the same request.

        Args:
            params (CancelAndPlaceParams): Parameters required to cancel orders and place a new one.

        Returns:
            ExecuteResponse: The response from the engine execution.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.cancel_and_place(params)

    def close_position(
        self, subaccount: Subaccount, product_id: int
    ) -> ExecuteResponse:
        """
        Places an order through the engine to close a position for the provided `product_id`.

        Attributes:
            subaccount (Subaccount): The subaccount to close position for.
            product_id (int): The ID of the product to close position for.

         Returns:
            ExecuteResponse: The response from the engine execution.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.close_position(subaccount, product_id)

    def place_trigger_order(self, params: PlaceTriggerOrderParams) -> ExecuteResponse:
        if self.context.trigger_client is None:
            raise MissingTriggerClient()
        return self.context.trigger_client.place_trigger_order(params)

    def cancel_trigger_orders(
        self, params: CancelTriggerOrdersParams
    ) -> ExecuteResponse:
        if self.context.trigger_client is None:
            raise MissingTriggerClient()
        return self.context.trigger_client.cancel_trigger_orders(params)

    def cancel_trigger_product_orders(
        self, params: CancelProductTriggerOrdersParams
    ) -> ExecuteResponse:
        if self.context.trigger_client is None:
            raise MissingTriggerClient()
        return self.context.trigger_client.cancel_product_trigger_orders(params)
