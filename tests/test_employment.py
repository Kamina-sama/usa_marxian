"""Tests for industry employment and wage-rate construction."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.bea_employment import (
    attach_employment,
    employment_coverage,
    map_fte_to_io,
)


def test_map_fte_to_io_aggregates():
    fte = pd.DataFrame(
        {
            "year": [2020, 2020, 2020],
            "fte_code": ["N1", "N2", "N3"],
            "fte_name": ["Wood products", "Farms", "Wood products"],
            "fte": [100.0, 200.0, 50.0],
        }
    )
    config = {"Wood products": "321", "Farms": "111CA"}
    mapped = map_fte_to_io(fte, config)
    assert mapped.loc[mapped["industry_code"] == "321", "fte"].iloc[0] == 150.0
    assert mapped.loc[mapped["industry_code"] == "111CA", "fte"].iloc[0] == 200.0


def test_attach_employment_uses_market_fte_only():
    panel = pd.DataFrame(
        {
            "year": [2020, 2020],
            "industry_code": ["A", "HS"],
            "V": [100.0, 0.0],
        }
    )
    employment = pd.DataFrame(
        {
            "year": [2020, 2020],
            "industry_code": ["A", "HS"],
            "fte": [1000.0, 5000.0],
        }
    )
    hours = pd.Series({2020: 0.2})  # billions of hours

    attached = attach_employment(panel, employment, hours)

    # Only the market industry A enters the hours-per-FTE calibration.
    # hours_per_fte = 0.2e9 / (1000e3) = 200 hours; labour_hours = 1000*1000*200.
    a = attached.loc[attached["industry_code"] == "A"].iloc[0]
    assert np.isclose(a["fte"], 1000.0)
    assert np.isclose(a["labour_hours"], 200_000_000.0)
    assert np.isclose(a["wage_rate_i"], 100.0 * 1e6 / 200_000_000.0)


def test_employment_coverage_reconciles_to_macro_hours():
    panel = pd.DataFrame(
        {
            "year": [2020, 2020],
            "industry_code": ["A", "B"],
            "fte": [500.0, 500.0],
            "labour_hours": [100_000_000_000.0, 100_000_000_000.0],
        }
    )
    hours = pd.Series({2020: 200.0})
    coverage = employment_coverage(panel, hours)
    row = coverage.iloc[0]
    assert np.isclose(row["hours_bn"], 200.0)
    assert np.isclose(row["gap_pct"], 0.0, atol=1e-6)
