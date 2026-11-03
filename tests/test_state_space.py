"""Tests for the Shaikh state-space dataset."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.model.state_space import build_state_space


def _panel() -> pd.DataFrame:
    rows = []
    for year in (2017, 2018):
        for code, go, wage in (("A", 100.0, 40.0), ("B", 200.0, 80.0)):
            rows.append(
                {
                    "year": year,
                    "industry_code": code,
                    "industry_name": f"Industry {code}",
                    "GO": go,
                    "V": wage,
                    "go_price": 100.0,
                    "is_market": True,
                }
            )
    return pd.DataFrame(rows)


def _capital() -> pd.DataFrame:
    rows = []
    for year in (2017, 2018):
        for code, current, real in (("A", 500.0, 400.0), ("B", 800.0, 640.0)):
            rows.append(
                {
                    "year": year,
                    "industry_code": code,
                    "M_current": current,
                    "M_real": real,
                    "I_current": 50.0,
                    "D_current": 10.0,
                }
            )
    return pd.DataFrame(rows)


def _accounts() -> pd.DataFrame:
    return pd.DataFrame(
        {"L": [10.0, 12.0], "V": [120.0, 144.0], "N": [200.0, 220.0], "S": [80.0, 76.0]},
        index=pd.Index([2017, 2018], name="year"),
    )


def _use() -> pd.DataFrame:
    rows = []
    for year in (2017, 2018):
        for commodity in ("A", "B"):
            for industry in ("A", "B"):
                rows.append(
                    {
                        "year": year,
                        "commodity_code": commodity,
                        "industry_code": industry,
                        "value": 20.0,
                    }
                )
    return pd.DataFrame(rows)


def test_state_space_has_required_variables():
    result = build_state_space(
        _panel(), _use(), _accounts(), _capital(), base_year=2017
    )
    state = result.state
    required = {
        "price",
        "quantity",
        "capital",
        "investment",
        "depreciation",
        "utilization",
        "wage_rate",
        "labour_hours",
        "labour_coefficient",
        "labour_coefficient_real",
    }
    assert required.issubset(state.columns)
    assert len(state) == 4
    assert result.summary["n_matrices"] == 2


def test_state_space_arithmetic_and_base_year_normalisation():
    result = build_state_space(
        _panel(), _use(), _accounts(), _capital(), base_year=2017
    )
    state = result.state.set_index(["year", "industry_code"])

    row = state.loc[(2018, "A")]
    assert np.isclose(row["price"], 1.0)
    assert np.isclose(row["quantity"], 100.0)
    assert np.isclose(row["capital"], 400.0)
    assert np.isclose(row["investment"], 40.0)  # 50 / (500/400)
    assert np.isclose(row["depreciation"], 8.0)  # 10 / 1.25
    assert np.isclose(row["wage_rate"], 12.0)  # 144 / 12

    base = state.xs(2017, level="year")
    assert np.allclose(base["utilization"], 1.0)
