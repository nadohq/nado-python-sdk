from typing import List, Optional
from nado_protocol.utils.order import (
    build_appendix,
    OrderAppendixTriggerType,
)
from nado_protocol.utils.expiration import OrderType
from nado_protocol.trigger_client.types.models import TimeTrigger
from nado_protocol.engine_client.types.execute import PlaceOrderParams
from nado_protocol.trigger_client.types.execute import PlaceTriggerOrderParams


def create_twap_order(
    product_id: int,
    sender: str,
    price_x18: str,
    total_amount: str,
    expiration: int,
    nonce: int,
    times: int,
    slippage_frac: float,
    interval_seconds: int,
    custom_amounts: Optional[List[str]] = None,
    reduce_only: bool = False,
    spot_leverage: Optional[bool] = None,
    id: Optional[int] = None,
) -> PlaceTriggerOrderParams:
    """
    Create a TWAP (Time-Weighted Average Price) order.
    
    Args:
        product_id (int): The product ID for the order.
        sender (str): The sender address (32 bytes hex).
        price_x18 (str): The limit price multiplied by 1e18.
        total_amount (str): The total amount to trade (signed, negative for sell).
        expiration (int): Order expiration timestamp.
        nonce (int): Order nonce.
        times (int): Number of TWAP executions (1-500).
        slippage_frac (float): Slippage tolerance as a fraction (e.g., 0.01 for 1%).
        interval_seconds (int): Time interval between executions in seconds.
        custom_amounts (Optional[List[str]]): Custom amounts for each execution. If provided,
                                           uses TWAP_CUSTOM_AMOUNTS trigger type.
        reduce_only (bool): Whether this is a reduce-only order.
        spot_leverage (Optional[bool]): Whether to use spot leverage.
        id (Optional[int]): Optional order ID.
    
    Returns:
        PlaceTriggerOrderParams: Parameters for placing the TWAP order.
    
    Raises:
        ValueError: If parameters are invalid.
    """
    if times < 1 or times > 500:
        raise ValueError(f"TWAP times must be between 1 and 500, got {times}")
    
    if slippage_frac < 0 or slippage_frac > 1:
        raise ValueError(f"Slippage fraction must be between 0 and 1, got {slippage_frac}")
    
    if interval_seconds <= 0:
        raise ValueError(f"Interval must be positive, got {interval_seconds}")
    
    # Determine trigger type
    trigger_type = (
        OrderAppendixTriggerType.TWAP_CUSTOM_AMOUNTS
        if custom_amounts is not None
        else OrderAppendixTriggerType.TWAP
    )
    
    # Build appendix - TWAP orders must use IOC execution type
    appendix = build_appendix(
        order_type=OrderType.IMMEDIATE_OR_CANCEL,
        reduce_only=reduce_only,
        trigger_type=trigger_type,
        twap_times=times,
        twap_slippage_frac=slippage_frac,
    )
    
    # Create the base order
    order = PlaceOrderParams(
        product_id=product_id,
        order={
            "sender": sender,
            "priceX18": price_x18,
            "amount": total_amount,
            "expiration": expiration,
            "nonce": nonce,
            "appendix": appendix,
        },
        spot_leverage=spot_leverage,
        id=id,
    )
    
    # Create trigger criteria
    trigger = TimeTrigger(
        interval=interval_seconds,
        amounts=custom_amounts,
    )
    
    return PlaceTriggerOrderParams(
        **order.dict(),
        trigger=trigger,
    )


def validate_twap_order(
    total_amount: str,
    times: int,
    custom_amounts: Optional[List[str]] = None,
) -> None:
    """
    Validate TWAP order parameters.
    
    Args:
        total_amount (str): The total amount to trade.
        times (int): Number of TWAP executions.
        custom_amounts (Optional[List[str]]): Custom amounts for each execution.
    
    Raises:
        ValueError: If validation fails.
    """
    total_amount_int = int(total_amount)
    
    if custom_amounts is None:
        # For equal distribution, total amount must be divisible by times
        if total_amount_int % times != 0:
            raise ValueError(
                f"Total amount {total_amount} must be divisible by times {times} "
                f"for equal distribution TWAP orders"
            )
    else:
        # For custom amounts, verify the list length and sum
        if len(custom_amounts) != times:
            raise ValueError(
                f"Custom amounts list length ({len(custom_amounts)}) must equal "
                f"times ({times})"
            )
        
        custom_sum = sum(int(amount) for amount in custom_amounts)
        if custom_sum != total_amount_int:
            raise ValueError(
                f"Sum of custom amounts ({custom_sum}) must equal "
                f"total amount ({total_amount_int})"
            )


def estimate_twap_completion_time(times: int, interval_seconds: int) -> int:
    """
    Estimate the total time for TWAP order completion.
    
    Args:
        times (int): Number of TWAP executions.
        interval_seconds (int): Time interval between executions.
    
    Returns:
        int: Estimated completion time in seconds.
    """
    return (times - 1) * interval_seconds


def calculate_equal_amounts(total_amount: str, times: int) -> List[str]:
    """
    Calculate equal amounts for TWAP executions.
    
    Args:
        total_amount (str): The total amount to distribute.
        times (int): Number of executions.
    
    Returns:
        List[str]: List of equal amounts for each execution.
    
    Raises:
        ValueError: If total amount is not divisible by times.
    """
    total_amount_int = int(total_amount)
    
    if total_amount_int % times != 0:
        raise ValueError(
            f"Total amount {total_amount} is not divisible by times {times}"
        )
    
    amount_per_execution = total_amount_int // times
    return [str(amount_per_execution)] * times