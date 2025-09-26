import requests
from functools import singledispatchmethod
from typing import Union, Optional, List
from nado_protocol.contracts.types import NadoExecuteType
from nado_protocol.trigger_client.types.execute import (
    TriggerExecuteParams,
    TriggerExecuteRequest,
    PlaceTriggerOrderParams,
    CancelTriggerOrdersParams,
    CancelProductTriggerOrdersParams,
    to_trigger_execute_request,
)
from nado_protocol.engine_client.types.execute import ExecuteResponse
from nado_protocol.trigger_client.types import TriggerClientOpts
from nado_protocol.utils.exceptions import (
    BadStatusCodeException,
    ExecuteFailedException,
)
from nado_protocol.utils.execute import NadoBaseExecute
from nado_protocol.utils.model import NadoBaseModel, is_instance_of_union
from nado_protocol.utils.twap import create_twap_order
from nado_protocol.trigger_client.types.models import (
    PriceTrigger, 
    LastPriceAbove, 
    LastPriceBelow,
    OraclePriceAbove,
    OraclePriceBelow,
    MidPriceAbove,
    MidPriceBelow
)


class TriggerExecuteClient(NadoBaseExecute):
    def __init__(self, opts: TriggerClientOpts):
        super().__init__(opts)
        self._opts: TriggerClientOpts = TriggerClientOpts.parse_obj(opts)
        self.url: str = self._opts.url
        self.session = requests.Session()

    def tx_nonce(self, _: str) -> int:
        raise NotImplementedError

    @singledispatchmethod
    def execute(
        self, params: Union[TriggerExecuteParams, TriggerExecuteRequest]
    ) -> ExecuteResponse:
        """
        Executes the operation defined by the provided parameters.

        Args:
            params (ExecuteParams): The parameters for the operation to execute. This can represent a variety of operations, such as placing orders, cancelling orders, and more.

        Returns:
            ExecuteResponse: The response from the executed operation.
        """
        req: TriggerExecuteRequest = (
            params if is_instance_of_union(params, TriggerExecuteRequest) else to_trigger_execute_request(params)  # type: ignore
        )
        return self._execute(req)

    @execute.register
    def _(self, req: dict) -> ExecuteResponse:
        """
        Overloaded method to execute the operation defined by the provided request.

        Args:
            req (dict): The request data for the operation to execute. Can be a dictionary or an instance of ExecuteRequest.

        Returns:
            ExecuteResponse: The response from the executed operation.
        """
        parsed_req: TriggerExecuteRequest = NadoBaseModel.parse_obj(req)  # type: ignore
        return self._execute(parsed_req)

    def _execute(self, req: TriggerExecuteRequest) -> ExecuteResponse:
        """
        Internal method to execute the operation. Sends request to the server.

        Args:
            req (TriggerExecuteRequest): The request data for the operation to execute.

        Returns:
            ExecuteResponse: The response from the executed operation.

        Raises:
            BadStatusCodeException: If the server response status code is not 200.
            ExecuteFailedException: If there's an error in the execution or the response status is not "success".
        """
        res = self.session.post(f"{self.url}/execute", json=req.dict())
        if res.status_code != 200:
            raise BadStatusCodeException(res.text)
        try:
            execute_res = ExecuteResponse(**res.json(), req=req.dict())
        except Exception:
            raise ExecuteFailedException(res.text)
        if execute_res.status != "success":
            raise ExecuteFailedException(res.text)
        return execute_res

    def place_trigger_order(self, params: PlaceTriggerOrderParams) -> ExecuteResponse:
        params = PlaceTriggerOrderParams.parse_obj(params)
        params.order = self.prepare_execute_params(params.order, True)
        params.signature = params.signature or self._sign(
            NadoExecuteType.PLACE_ORDER, params.order.dict(), params.product_id
        )
        return self.execute(params)

    def place_twap_order(
        self,
        product_id: int,
        sender: str,
        price_x18: str,
        total_amount_x18: str,
        expiration: int,
        nonce: int,
        times: int,
        slippage_frac: float,
        interval_seconds: int,
        custom_amounts_x18: Optional[List[str]] = None,
        reduce_only: bool = False,
        spot_leverage: Optional[bool] = None,
        id: Optional[int] = None,
    ) -> ExecuteResponse:
        """
        Place a TWAP (Time-Weighted Average Price) order.
        
        This is a convenience method that creates a TWAP trigger order with the specified parameters.
        
        Args:
            product_id (int): The product ID for the order.
            sender (str): The sender address (32 bytes hex).
            price_x18 (str): The limit price multiplied by 1e18.
            total_amount_x18 (str): The total amount to trade multiplied by 1e18 (signed, negative for sell).
            expiration (int): Order expiration timestamp.
            nonce (int): Order nonce.
            times (int): Number of TWAP executions (1-500).
            slippage_frac (float): Slippage tolerance as a fraction (e.g., 0.01 for 1%).
            interval_seconds (int): Time interval between executions in seconds.
            custom_amounts_x18 (Optional[List[str]]): Custom amounts for each execution multiplied by 1e18.
            reduce_only (bool): Whether this is a reduce-only order.
            spot_leverage (Optional[bool]): Whether to use spot leverage.
            id (Optional[int]): Optional order ID.
        
        Returns:
            ExecuteResponse: The response from placing the TWAP order.
        """
        params = create_twap_order(
            product_id=product_id,
            sender=sender,
            price_x18=price_x18,
            total_amount_x18=total_amount_x18,
            expiration=expiration,
            nonce=nonce,
            times=times,
            slippage_frac=slippage_frac,
            interval_seconds=interval_seconds,
            custom_amounts_x18=custom_amounts_x18,
            reduce_only=reduce_only,
            spot_leverage=spot_leverage,
            id=id,
        )
        return self.place_trigger_order(params)

    def place_price_trigger_order(
        self,
        product_id: int,
        sender: str,
        price_x18: str,
        amount_x18: str,
        expiration: int,
        nonce: int,
        trigger_price_x18: str,
        trigger_type: str = "last_price_above",
        reduce_only: bool = False,
        spot_leverage: Optional[bool] = None,
        id: Optional[int] = None,
    ) -> ExecuteResponse:
        """
        Place a price trigger order.
        
        This is a convenience method that creates a price trigger order with the specified parameters.
        
        Args:
            product_id (int): The product ID for the order.
            sender (str): The sender address (32 bytes hex).
            price_x18 (str): The limit price multiplied by 1e18.
            amount_x18 (str): The amount to trade multiplied by 1e18 (signed, negative for sell).
            expiration (int): Order expiration timestamp.
            nonce (int): Order nonce.
            trigger_price_x18 (str): The trigger price multiplied by 1e18.
            trigger_type (str): Type of price trigger - one of:
                "last_price_above", "last_price_below", 
                "oracle_price_above", "oracle_price_below",
                "mid_price_above", "mid_price_below"
            reduce_only (bool): Whether this is a reduce-only order.
            spot_leverage (Optional[bool]): Whether to use spot leverage.
            id (Optional[int]): Optional order ID.
        
        Returns:
            ExecuteResponse: The response from placing the price trigger order.
        
        Raises:
            ValueError: If trigger_type is not supported.
        """
        # Create the appropriate price requirement based on trigger type
        price_requirement_mapping = {
            "last_price_above": LastPriceAbove(last_price_above=trigger_price_x18),
            "last_price_below": LastPriceBelow(last_price_below=trigger_price_x18),
            "oracle_price_above": OraclePriceAbove(oracle_price_above=trigger_price_x18),
            "oracle_price_below": OraclePriceBelow(oracle_price_below=trigger_price_x18),
            "mid_price_above": MidPriceAbove(mid_price_above=trigger_price_x18),
            "mid_price_below": MidPriceBelow(mid_price_below=trigger_price_x18),
        }
        
        if trigger_type not in price_requirement_mapping:
            raise ValueError(
                f"Unsupported trigger_type: {trigger_type}. "
                f"Supported types: {list(price_requirement_mapping.keys())}"
            )
        
        price_requirement = price_requirement_mapping[trigger_type]
        trigger = PriceTrigger(price_requirement=price_requirement)
        
        params = PlaceTriggerOrderParams(
            product_id=product_id,
            order={
                "sender": sender,
                "priceX18": price_x18,
                "amount": amount_x18,
                "expiration": expiration,
                "nonce": nonce,
                "appendix": 0,  # Will be built by the order preparation
            },
            trigger=trigger,
            spot_leverage=spot_leverage,
            id=id,
        )
        
        return self.place_trigger_order(params)

    def cancel_trigger_orders(
        self, params: CancelTriggerOrdersParams
    ) -> ExecuteResponse:
        params = self.prepare_execute_params(
            CancelTriggerOrdersParams.parse_obj(params), True
        )
        params.signature = params.signature or self._sign(
            NadoExecuteType.CANCEL_ORDERS, params.dict()
        )
        return self.execute(params)

    def cancel_product_trigger_orders(
        self, params: CancelProductTriggerOrdersParams
    ) -> ExecuteResponse:
        params = self.prepare_execute_params(
            CancelProductTriggerOrdersParams.parse_obj(params), True
        )
        params.signature = params.signature or self._sign(
            NadoExecuteType.CANCEL_PRODUCT_ORDERS, params.dict()
        )
        return self.execute(params)
