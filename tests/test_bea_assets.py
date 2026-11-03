"""Tests for the BEA fixed-asset capital stock mapping."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.bea_assets import (
    attach_capital_stock,
    capital_coverage,
    load_capital_config,
)


def test_mapping_covers_private_industries():
    config = load_capital_config()
    assert len(config["fa_to_io"]) == 74
    assert len(set(config["fa_to_io"].values())) == 65


def test_attach_uses_actual_then_fallback():
    panel = pd.DataFrame(
        {
            "year": [2020, 2020, 2020],
            "industry_code": ["A", "B", "C"],
            "C": [100.0, 200.0, 300.0],
            "V": [50.0, 60.0, 70.0],
        }
    )
    capital = pd.DataFrame({"year": [2020], "industry_code": ["A"], "M": [1_000_000.0]})

    attached = attach_capital_stock(panel, capital, fallback="cost")

    assert attached.loc[attached["industry_code"] == "A", "capital_source"].iloc[0] == "fixed_assets"
    assert attached.loc[attached["industry_code"] == "B", "capital_source"].iloc[0] == "cost_proxy"
    assert np.isclose(attached.loc[attached["industry_code"] == "A", "M"].iloc[0], 1_000_000.0)
    assert np.isclose(attached.loc[attached["industry_code"] == "B", "M"].iloc[0], 260.0)


def test_capital_coverage():
    panel = pd.DataFrame(
        {
            "year": [2020, 2020, 2020],
            "industry_code": ["A", "B", "C"],
            "capital_source": ["fixed_assets", "cost_proxy", "cost_proxy"],
            "M_assets": [1_000_000.0, np.nan, np.nan],
            "M": [1_000_000.0, 260.0, 370.0],
        }
    )
    coverage = capital_coverage(panel, pd.Series({2020: 1000.0}))
    row = coverage.iloc[0]
    assert row["n_actual"] == 1
    assert row["n_proxy"] == 2
    assert np.isclose(row["total_M_assets_bn"], 1000.0)
    assert np.isclose(row["gap_pct"], 0.0)
