"""Tests for the Sraffian price system after depreciation was added.

The point of these tests is that the price equation is easy to get subtly wrong
in ways that still return plausible numbers, so each one pins an exact quantity
rather than a qualitative direction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.model.shaikh import iterative_prices_endogenous
from usa_marxian.model.sraffa import (
    iterative_prices,
    sraffa_prices_of_production,
)


def _one_sector(technical: float = 0.2) -> pd.DataFrame:
    return pd.DataFrame([[technical]], index=["X"], columns=["X"])


def test_price_equation_marks_up_cost_and_depreciation() -> None:
    """p = (1+r)(v + d) / (1 - (1+r)a) for a one-sector economy."""
    profit_rate = 0.25
    prices = sraffa_prices_of_production(
        _one_sector(0.2),
        pd.Series({"X": 1.0}),
        profit_rate,
        depreciation_cost=pd.Series({"X": 0.5}),
    )
    expected = (1.0 + profit_rate) * (1.0 + 0.5) / (1.0 - (1.0 + profit_rate) * 0.2)
    assert prices["X"] == pytest.approx(expected, rel=1e-12)


def test_wage_markup_is_applied() -> None:
    """Dropping the (1+r) on the wage term would give 1.2 rather than 1.5."""
    prices = sraffa_prices_of_production(
        _one_sector(0.0), pd.Series({"X": 1.0}), 0.5
    )
    assert prices["X"] == pytest.approx(1.5, rel=1e-12)


def test_depreciation_raises_relative_prices_of_capital_intensive_sectors() -> None:
    """A sector with depreciation must be dearer than one without."""
    matrix = pd.DataFrame(
        [[0.1, 0.0], [0.0, 0.1]], index=["A", "B"], columns=["A", "B"]
    )
    labour = pd.Series({"A": 1.0, "B": 1.0})
    base = sraffa_prices_of_production(matrix, labour, 0.2)
    with_dep = sraffa_prices_of_production(
        matrix,
        labour,
        0.2,
        depreciation_cost=pd.Series({"A": 0.4, "B": 0.0}),
    )
    ratio = (with_dep / base).loc[["A", "B"]]
    assert ratio["A"] > 1.0
    assert ratio["B"] == pytest.approx(1.0, rel=1e-12)


def test_missing_industry_raises_instead_of_filling_zero() -> None:
    matrix = pd.DataFrame(
        [[0.1, 0.0], [0.0, 0.1]], index=["A", "B"], columns=["A", "B"]
    )
    with pytest.raises(ValueError, match="missing"):
        sraffa_prices_of_production(matrix, pd.Series({"A": 1.0}), 0.1)


def test_nan_coefficient_raises() -> None:
    matrix = pd.DataFrame([[0.1]], index=["A"], columns=["A"])
    with pytest.raises(ValueError, match="non-finite"):
        sraffa_prices_of_production(
            matrix, pd.Series({"A": np.nan}), 0.1
        )


def test_iteration_agrees_with_direct_solve_on_the_same_cost_base() -> None:
    """Both must include depreciation, or they converge to different rays."""
    matrix = pd.DataFrame(
        [[0.2, 0.1], [0.15, 0.25]], index=["A", "B"], columns=["A", "B"]
    )
    labour = pd.Series({"A": 1.0, "B": 0.8})
    depreciation = pd.Series({"A": 0.3, "B": 0.2})
    direct = sraffa_prices_of_production(
        matrix, labour, 0.15, depreciation_cost=depreciation
    )
    iterated = iterative_prices(
        matrix, labour, 0.15, depreciation_cost=depreciation
    ).prices
    assert iterated.sum() == pytest.approx(1.0, rel=1e-9)
    direct_normalised = direct / direct.sum()
    np.testing.assert_allclose(
        direct_normalised.to_numpy(), iterated.to_numpy(), rtol=1e-6
    )


def _two_sector():
    matrix = pd.DataFrame(
        [[0.2, 0.1], [0.15, 0.25]], index=["A", "B"], columns=["A", "B"]
    )
    labour = pd.Series({"A": 1.0, "B": 0.8})
    output = pd.Series({"A": 1.0, "B": 1.0})
    depreciation = pd.Series({"A": 0.3, "B": 0.2})
    return matrix, labour, output, depreciation


def test_endogenous_iteration_matches_direct_solve_at_its_own_rate() -> None:
    """The iteration's fixed point must be the Sraffian system at its own r.

    This is the property that broke when Sraffa gained a depreciation term and
    Shaikh did not: the two converged to different centres.
    """
    matrix, labour, output, depreciation = _two_sector()
    result = iterative_prices_endogenous(
        matrix, labour, output, depreciation_cost=depreciation
    )
    assert result.converged
    direct = sraffa_prices_of_production(
        matrix, labour, result.profit_rate, depreciation_cost=depreciation
    )
    direct_ray = (direct / direct.sum()).to_numpy()
    np.testing.assert_allclose(
        direct_ray, result.prices.to_numpy(), rtol=1e-8, atol=1e-10
    )


def test_endogenous_iteration_prices_depreciation_into_the_sector() -> None:
    """A sector carrying depreciation must become dearer relative to the other."""
    matrix, labour, output, depreciation = _two_sector()
    without = iterative_prices_endogenous(matrix, labour, output)
    with_depreciation = iterative_prices_endogenous(
        matrix, labour, output, depreciation_cost=depreciation
    )
    assert (
        with_depreciation.prices["A"] / with_depreciation.prices["B"]
        > without.prices["A"] / without.prices["B"]
    )
