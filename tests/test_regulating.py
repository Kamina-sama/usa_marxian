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
    regulating = pd.DataFrame(
        {
            "industry_code": ["A", "B"],
            "unit_cost": [0.5, 0.5],
            "unit_cost_min": [0.4, 0.45],
            "cost_cv": [0.2, 0.1],
        }
    )

    result = build_regulating_benchmark(panel, regulating, theta=0.5)

    a = result.panel.loc[result.panel["industry_code"] == "A"].iloc[0]
    b = result.panel.loc[result.panel["industry_code"] == "B"].iloc[0]
    # factor = 1 - theta * (1 - min/avg)
    assert np.isclose(a["regulating_factor"], 1 - 0.5 * 0.2)
    assert np.isclose(b["regulating_factor"], 1 - 0.5 * 0.1)
    assert np.isclose(a["cost_dispersion"], 0.2)

    assert np.isclose(
        result.panel.loc[result.panel["industry_code"] == "A", "PP_reg"].iloc[0],
        90.0 * (1 - 0.5 * 0.2),
    )
    assert result.summary["n_mapped"] == 2
