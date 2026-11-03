"""Tests for the stock-flow cross-dual simulation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.model.stock_flow import (
    StockFlowParams,
    fit_stock_flow,
    metrics_table,
    simulate,
)


def _state() -> pd.DataFrame:
    rows = []
    for year in (2017, 2018, 2019):
        for code, price, quantity, capital in (
            ("A", 1.0, 100.0, 500.0),
            ("B", 1.0, 200.0, 800.0),
        ):
            rows.append(
                {
                    "year": year,
                    "industry_code": code,
                    "price": price,
                    "quantity": quantity,
                    "capital": capital,
                    "depreciation": 10.0,
                    "investment": 20.0,
                    "labour_coefficient_real": 0.01,
                    "wage_rate": 10.0,
                }
            )
    return pd.DataFrame(rows)


def _matrices() -> pd.DataFrame:
    rows = []
    for year in (2017, 2018, 2019):
        for commodity in ("A", "B"):
            for industry in ("A", "B"):
                rows.append(
                    {
                        "year": year,
                        "commodity_code": commodity,
                        "industry_code": industry,
                        "value": 0.1,
                    }
                )
    return pd.DataFrame(rows)


def test_simulate_returns_trajectories_and_metrics():
    result = simulate(
        _state(), _matrices(), StockFlowParams(), start_year=2017
    )
    assert not result.empty
    assert {
        "p_sim",
        "q_sim",
        "k_sim",
        "I_sim",
        "p_obs",
        "q_obs",
        "k_obs",
        "I_obs",
    }.issubset(result.columns)
    metrics = metrics_table(result)
    assert set(metrics["variable"]) == {"price", "quantity", "capital", "investment"}


def test_fit_stock_flow_without_calibration_runs():
    result = fit_stock_flow(
        _state(), _matrices(), calibrate=False
    )
    assert result.params.alpha >= 0
    assert result.summary["n_observations"] > 0
    assert np.isfinite(result.metrics["rmse_log"]).all()
