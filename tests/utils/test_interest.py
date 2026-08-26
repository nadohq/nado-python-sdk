"""Tests that the interest helpers match `SpotEngine._updateState`."""

import pytest

from nado_protocol.engine_client.types.models import (
    SpotProduct,
    SpotProductConfig,
    SpotProductState,
)
from nado_protocol.utils.interest import (
    calc_borrow_rate_in_period,
    calc_borrow_rate_per_second,
    calc_deposit_rate_in_period,
)
from nado_protocol.utils.math import to_x18
from nado_protocol.utils.time import TimeInSeconds

MIN_DEPOSIT_RATE = 0.05
INTEREST_FEE_FRACTION = 0.2

PERIODS = [
    TimeInSeconds.HOUR,
    TimeInSeconds.DAY,
    TimeInSeconds.DAY * 30,
    TimeInSeconds.YEAR,
]


def spot_product(total_borrows: float = 500_000) -> SpotProduct:
    config = SpotProductConfig(
        token="0x",
        interest_inflection_util_x18=str(to_x18(0.8)),
        interest_floor_x18=str(to_x18(0.01)),
        interest_small_cap_x18=str(to_x18(0.04)),
        interest_large_cap_x18=str(to_x18(0.4)),
        withdraw_fee_x18=str(to_x18(0)),
        min_deposit_rate_x18=str(to_x18(MIN_DEPOSIT_RATE)),
    )
    state = SpotProductState(
        cumulative_deposits_multiplier_x18=str(to_x18(1)),
        cumulative_borrows_multiplier_x18=str(to_x18(1)),
        total_deposits_normalized=str(to_x18(1_000_000)),
        total_borrows_normalized=str(to_x18(total_borrows)),
    )
    return SpotProduct.model_construct(product_id=0, config=config, state=state)


def on_chain_borrow_rate(product: SpotProduct, period: int) -> float:
    """`borrowRateMultiplier * minDepositRateMultiplier - 1`, as the engine computes it."""
    borrow_rate_per_second = calc_borrow_rate_per_second(product)
    min_deposit_rate_per_second = MIN_DEPOSIT_RATE / TimeInSeconds.YEAR
    return (1 + borrow_rate_per_second) ** period * (
        1 + min_deposit_rate_per_second
    ) ** period - 1


@pytest.mark.parametrize("period", PERIODS)
def test_borrow_rate_applies_min_deposit_rate(period):
    product = spot_product()
    assert calc_borrow_rate_in_period(product, period) == pytest.approx(
        on_chain_borrow_rate(product, period), rel=1e-12
    )


def test_borrow_rate_stays_under_the_annual_floor_for_an_hour():
    # The min deposit rate was not applied at all, so an hour of borrowing
    # reported only the borrow curve.
    product = spot_product()
    hour = calc_borrow_rate_in_period(product, TimeInSeconds.HOUR)
    assert hour > on_chain_borrow_rate(product, TimeInSeconds.HOUR) / 2
    assert hour < MIN_DEPOSIT_RATE / 100


def test_deposit_rate_pays_the_floor_when_nothing_is_borrowed():
    product = spot_product(total_borrows=0)
    expected = (1 + MIN_DEPOSIT_RATE / TimeInSeconds.YEAR) ** TimeInSeconds.DAY - 1
    assert calc_deposit_rate_in_period(
        product, TimeInSeconds.DAY, INTEREST_FEE_FRACTION
    ) == pytest.approx(expected, rel=1e-12)


def test_deposit_rate_compounds_the_floor_on_top_of_the_realized_rate():
    product = spot_product()
    period = TimeInSeconds.DAY
    utilization = 0.5
    borrow_multiplier = (1 + calc_borrow_rate_per_second(product)) ** period
    realized = utilization * (borrow_multiplier - 1) * (1 - INTEREST_FEE_FRACTION)
    expected = (1 + realized) * (
        1 + MIN_DEPOSIT_RATE / TimeInSeconds.YEAR
    ) ** period - 1
    assert calc_deposit_rate_in_period(
        product, period, INTEREST_FEE_FRACTION
    ) == pytest.approx(expected, rel=1e-12)
