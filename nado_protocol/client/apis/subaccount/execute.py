from nado_protocol.client.apis.base import NadoBaseAPI
from nado_protocol.engine_client.types.execute import (
    AddOrderSignerParams,
    DeleteOrderSignerParams,
    ExecuteResponse,
    LinkSignerParams,
    LiquidateSubaccountParams,
)


class SubaccountExecuteAPI(NadoBaseAPI):
    """
    Provides functionalities for executing operations related to subaccounts in the Nado Protocol.

    Inherits from NadoBaseAPI, which provides a basic context setup for accessing Nado.
    This class extends the base class to provide specific functionalities for executing actions related to subaccounts.

    The provided methods include:
    - `liquidate_subaccount`: Performs the liquidation of a subaccount.
    - `link_signer`: Links a signer to a subaccount, granting them transaction signing permissions.
    - `add_order_signer`: Authorises an order signer that can only place and cancel orders.
    - `delete_order_signer`: Removes an order signer and cancels the orders it placed.

    Attributes:
        context (NadoClientContext): Provides connectivity details for accessing Nado APIs.
    """

    def liquidate_subaccount(
        self, params: LiquidateSubaccountParams
    ) -> ExecuteResponse:
        """
        Liquidates a subaccount through the engine.

        Args:
            params (LiquidateSubaccountParams): Parameters for liquidating the subaccount.

        Returns:
            ExecuteResponse: Execution response from the engine.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.liquidate_subaccount(params)

    def link_signer(self, params: LinkSignerParams) -> ExecuteResponse:
        """
        Links a signer to a subaccount to allow them to sign transactions on behalf of the subaccount.

        Args:
            params (LinkSignerParams): Parameters for linking a signer to a subaccount.

        Returns:
            ExecuteResponse: Execution response from the engine.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.link_signer(params)

    def add_order_signer(self, params: AddOrderSignerParams) -> ExecuteResponse:
        """
        Authorises an order signer on a subaccount (max 15). Order signers can place and cancel
        orders, including trigger and TWAP orders, but cannot withdraw, transfer or manage signers.

        Args:
            params (AddOrderSignerParams): Parameters including the order signer to add.

        Returns:
            ExecuteResponse: Execution response from the engine.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.add_order_signer(params)

    def delete_order_signer(self, params: DeleteOrderSignerParams) -> ExecuteResponse:
        """
        Removes an order signer from a subaccount and cancels the open orders it placed.

        Args:
            params (DeleteOrderSignerParams): Parameters including the order signer to remove.

        Returns:
            ExecuteResponse: Execution response from the engine.

        Raises:
            Exception: If there is an error during the execution or the response status is not "success".
        """
        return self.context.engine_client.delete_order_signer(params)
