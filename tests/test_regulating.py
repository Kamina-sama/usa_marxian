"""Tests for the regulating-capital benchmark and NAICS mapping."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.census_ecn import map_naics_to_io
from usa_marxian.model.regulating import build_regulating_benchmark


def test_map_naics_to_io_uses_longest_prefix():
    config = {"32": "32X", "321": "321", "3219": "321"}
    codes = pd.Series(["3219", "3211", "322", "33"])
    mapped = map_naics_to_io(codes, config)
    assert mapped.iloc[0] == "321"
    assert mapped.iloc[1] == "321"
    assert mapped.iloc[2] == "32X"
    assert pd.isna(mapped.iloc[3])


def test_build_regulating_benchmark_reduces_low_concentration_prices():
    panel = pd.DataFrame(
        {
            "industry_code": ["A", "B"],
            "GO": [100.0, 100.0],
            "PP_Sraffa": [90.0, 110.0],
        }
    )
    unit_cost = pd.DataFrame(
        {"industry_code": ["A", "B"], "unit_cost": [0.5, 0.5]}
    )
    concentration = pd.DataFrame(
        {"industry_code": ["A", "B"], "concentration": [0.8, 0.2]}
    )

    result = build_regulating_benchmark(
        panel, unit_cost, concentration, theta=0.5
    )

    # A is concentrated (dispersion 0.2), B is not (dispersion 0.8).
    a = result.panel.loc[result.panel["industry_code"] == "A"].iloc[0]
    b = result.panel.loc[result.panel["industry_code"] == "B"].iloc[0]
    assert np.isclose(a["cost_dispersion"], 0.2)
    assert np.isclose(b["cost_dispersion"], 0.8)
    assert np.isclose(a["regulating_factor"], 0.9)
    assert np.isclose(b["regulating_factor"], 0.6)

    # Normalised to total GO.
    assert np.isclose(result.panel["PP_reg"].sum(), 200.0, atol=1e-9)
    assert result.summary["n_mapped"] == 2
