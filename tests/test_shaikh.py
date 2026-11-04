"""Tests for Shaikh benchmarks and the Moseley-Shaikh comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.analysis.compare import compare_benchmarks
from usa_marxian.model.shaikh import (
    cross_dual_gravitation,
    iterative_prices_endogenous,
)
from usa_marxian.model.sraffa import (
    build_technical_matrices,
    build_technical_matrix,
    iterative_prices,
    labour_values,
    prices_of_production,
)


def _matrix() -> pd.DataFrame:
    return pd.DataFrame(
        [[0.20, 0.10], [0.30, 0.40]],
        index=["A", "B"],
        columns=["A", "B"],
    )


def _labour() -> pd.Series:
    return pd.Series({"A": 0.10, "B": 0.20})


def test_technical_matrix_uses_requested_year():
    panel = pd.DataFrame(
        {
            "year": [2017, 2017, 2018, 2018],
            "industry_code": ["A", "B", "A", "B"],
            "GO": [100.0, 100.0, 200.0, 100.0],
        }
    )
    use = pd.DataFrame(
        {
            "year": [2017, 2017, 2017, 2017, 2018, 2018, 2018, 2018],
            "commodity_code": ["A", "A", "B", "B", "A", "A", "B", "B"],
            "industry_code": ["A", "B", "A", "B", "A", "B", "A", "B"],
            "value": [20.0, 10.0, 30.0, 40.0, 80.0, 20.0, 60.0, 40.0],
        }
    )

    matrix_2017 = build_technical_matrix(use, panel, year=2017)
    matrix_2018 = build_technical_matrix(use, panel, year=2018)
    matrices = build_technical_matrices(use, panel)

    assert np.isclose(matrix_2017.loc["A", "A"], 0.20)
    assert np.isclose(matrix_2018.loc["A", "A"], 0.40)
    assert set(matrices) == {2017, 2018}


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


def test_iterative_prices_converges_to_direct_solution():
    matrix = _matrix()
    direct = prices_of_production(matrix, _labour(), 0.20)
    iterative = iterative_prices(matrix, _labour(), 0.20)
    assert iterative.converged
    assert iterative.iterations > 1
    direct = direct / direct.sum()
    assert np.allclose(iterative.prices, direct, atol=1e-8)


def test_endogenous_iteration_converges():
    matrix = _matrix()
    output = pd.Series({"A": 100.0, "B": 80.0})
    result = iterative_prices_endogenous(matrix, _labour(), output)
    assert result.converged
    assert np.isfinite(result.profit_rate)
    assert result.profit_rate > -1
    assert (result.prices > 0).all()


def test_cross_dual_produces_a_history():
    matrix = _matrix()
    output = pd.Series({"A": 100.0, "B": 80.0})
    result = cross_dual_gravitation(matrix, _labour(), output, steps=50)
    assert len(result.history) == 50
    assert np.isfinite(result.r_dispersion_start)
    assert np.isfinite(result.r_dispersion_end)


def test_compare_benchmarks_prefers_closer_benchmark():
    panel = pd.DataFrame(
        {
            "year": [2020] * 5,
            "industry_code": list("ABCDE"),
            "is_market": [True] * 5,
            "GO": [100.0, 120.0, 80.0, 60.0, 200.0],
            "PP_market": [102.0, 118.0, 82.0, 59.0, 198.0],
            "PP_Sraffa": [90.0, 110.0, 70.0, 80.0, 230.0],
            "PP_Shaikh": [88.0, 108.0, 72.0, 78.0, 228.0],
            "P_V": [80.0, 100.0, 60.0, 90.0, 250.0],
        }
    )
    comparison = compare_benchmarks(panel)
    assert len(comparison) == 4
    moseley = comparison.loc[
        comparison["benchmark"].str.startswith("Moseley"), "mae_pct"
    ].iloc[0]
    sraffa = comparison.loc[
        comparison["benchmark"].str.startswith("Sraffa prices"), "mae_pct"
    ].iloc[0]
    assert moseley < sraffa
