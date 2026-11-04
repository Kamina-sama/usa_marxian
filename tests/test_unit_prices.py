"""Tests for the unit-price comparison."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.analysis.unit_prices import (
    build_unit_price_panel,
    compare_unit_prices,
)


def _panel() -> pd.DataFrame:
    rows = []
    for year in (2017, 2018):
        for code, go, price in (("A", 100.0, 1.0), ("B", 200.0, 1.2), ("C", 50.0, 0.8)):
            quantity = go / price
            rows.append(
                {
                    "year": year,
                    "industry_code": code,
                    "GO": go,
                    "go_price": price * 100.0,
                    "quantity": quantity,
                    "PP_market": go,
                    "p_sraffa": price,
                    "p_shaikh": price,
                    "p_v": price,
                }
            )
    return pd.DataFrame(rows)


def test_unit_price_panel_normalises_geometric_mean():
    panel = _panel()
    data = build_unit_price_panel(panel)
    for _year, group in data.groupby("year"):
        weights = group["quantity"]
        geo = np.exp(
            np.average(np.log(group["price_obs_n"]), weights=weights)
        )
        assert np.isclose(geo, 1.0)


def test_perfect_model_has_zero_error():
    panel = _panel()
    panel["p_sraffa"] = panel["price_obs"] if "price_obs" in panel else panel["go_price"] / 100.0
    result = compare_unit_prices(panel)
    sraffa = result["comparison"].loc[
        result["comparison"]["benchmark"] == "Sraffa prices of production"
    ].iloc[0]
    assert sraffa["log_mae"] < 1e-10
    assert np.isclose(sraffa["corr"], 1.0)
