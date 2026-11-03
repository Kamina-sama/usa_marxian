"""Shared fixtures."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.config import SeriesSpec, Settings
from usa_marxian.data.build import build_accounts


@pytest.fixture
def settings() -> Settings:
    return Settings(
        start_year=1990,
        end_year=2020,
        base_year=2017,
        hours_method="ces",
        include_inventories=True,
    )


@pytest.fixture
def raw_panel() -> pd.DataFrame:
    years = pd.RangeIndex(1990, 2021, name="year")
    n = len(years)
    trend = np.linspace(0, 1, n)

    gdp = pd.Series(6000 + 14000 * trend, index=years)
    cfc = pd.Series(600 + 2600 * trend, index=years)
    compensation = pd.Series(3400 + 7600 * trend, index=years)
    nos = pd.Series(1200 + 2400 * trend, index=years)
    capital_stock = pd.Series(9000 + 26000 * trend, index=years)
    inventories = pd.Series(1200 + 2200 * trend, index=years)
    deflator = pd.Series(60 + 45 * trend, index=years)
    employment = pd.Series(110_000 + 30_000 * trend, index=years)
    weekly_hours = pd.Series(34.5 - 0.5 * trend, index=years)

    return pd.DataFrame(
        {
            "gdp": gdp,
            "cfc": cfc,
            "gdp_deflator": deflator,
            "compensation": compensation,
            "net_operating_surplus": nos,
            "capital_stock": capital_stock,
            "inventories": inventories,
            "employment": employment,
            "weekly_hours": weekly_hours,
        }
    )


@pytest.fixture
def accounts(raw_panel, settings) -> pd.DataFrame:
    return build_accounts(raw_panel, settings)


@pytest.fixture
def ltv_accounts() -> pd.DataFrame:
    """Data generated under the null N = m L with a constant m."""
    years = pd.RangeIndex(1980, 2021, name="year")
    rng = np.random.default_rng(42)
    hours = pd.Series(np.linspace(180.0, 260.0, len(years)), index=years)
    noise = np.exp(rng.normal(0.0, 0.01, len(years)))
    new_value = 35.0 * hours * noise
    variable = 0.6 * new_value
    return pd.DataFrame(
        {
            "N": new_value,
            "V": variable,
            "S": new_value - variable,
            "M": 6.0 * new_value,
            "L": hours,
        },
        index=years,
    )


@pytest.fixture
def fred_spec() -> SeriesSpec:
    return SeriesSpec(
        label="Test series",
        provider="fred",
        series_id="TEST",
        units="billions_usd",
        frequency="quarterly",
        agg="mean",
        scale=1.0,
    )
