"""Regression tests for seconds/minutes conversion."""

import pytest

from custom_components.robotail.settings import delay_minutes


@pytest.mark.parametrize(
    "seconds,minutes", [(60, 1), (300, 5), (3600, 60), ("120", 2), (1, 1 / 60), (0, 0)]
)
def test_delay_minutes(seconds, minutes):
    assert delay_minutes(seconds) == minutes


@pytest.mark.parametrize(
    "value", [None, True, "bad", -1, 3601, float("nan"), float("inf")]
)
def test_invalid_delay(value):
    assert delay_minutes(value) is None
