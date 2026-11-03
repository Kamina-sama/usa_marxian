"""Tests for Shaikh benchmarks and the Moseley-Shaikh comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.analysis.compare import compare_benchmarks
from usa_marxian.model.shaikh import labour_values, prices_of_production


def _matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [[0.20, 0.10], [0.30, 0.40]],
        index=["A", "B"],
        columns=["A", "B"],
    )


def _labour() -> pd.Series:
    return pd.Series({"A": 0.10, "B": 0.20})


def test_labour_values_solve_leontief_inverse():
    matrix = _matrix()
    expected = np.linalg.solve((np.eye(2) - matrix.to_numpy()).T, _labour().to_numpy())
    actual = labour_values(matrix, _labour())
    assert np.allclose(actual.to_numpy(), expected)


def test_prices_of_production_are_positive_and_normalisable():
    matrix = _matrix()
    prices = prices_of_production(matrix, _labour(), 0.20)
    assert (prices > 0).all()
    output = pd.Series({"A": 100.0, "B": 80.0})
    total = float((prices * output).sum())
    normalised = prices * (float(output.sum()) / total)
    assert np.isclose(float((normalised * output).sum()), float(output.sum()))


def test_compare_benchmarks_prefers_closer_benchmark():
    panel = pd.DataFrame(
        {
            "year": [2020] * 5,
            "industry_code": list("ABCDE"),
            "is_market": [True] * 5,
            "GO": [100.0, 120.0, 80.0, 60.0, 200.0],
            "PP_market": [102.0, 118.0, 82.0, 59.0, 198.0],
            "PP_S": [90.0, 110.0, 70.0, 80.0, 230.0],
            "P_V": [80.0, 100.0, 60.0, 90.0, 250.0],
        }
    )
    comparison = compare_benchmarks(panel)
    assert len(comparison) == 3
    moseley = comparison.loc[
        comparison["benchmark"].str.startswith("Moseley"), "mae_pct"
    ].iloc[0]
    shaikh = comparison.loc[
        comparison["benchmark"].str.startswith("Shaikh prices"), "mae_pct"
    ].iloc[0]
    assert moseley < shaikh
