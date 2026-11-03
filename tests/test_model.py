"""Tests for the model layer: MELT, equalities, LTV and profit rate."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.analysis.descriptives import summary_table
from usa_marxian.analysis.ltv import estimate_ltv
from usa_marxian.model.equalities import (
    check_industry_equalities,
    check_two_equalities,
    implied_rate_of_profit,
    profit_rate_decomposition,
    profit_rate_summary,
)
from usa_marxian.model.melt import melt_index, melt_summary, melt_trend


def test_two_equalities_zero_when_aggregates_match():
    check = check_two_equalities(
        total_price=1000.0,
        total_value=1000.0,
        total_profit=250.0,
        total_surplus_value=250.0,
    )
    assert check.price_value_gap == pytest.approx(0.0)
    assert check.price_value_gap_pct == pytest.approx(0.0)
    assert check.profit_surplus_gap == pytest.approx(0.0)


def test_industry_equalities_use_sums():
    frame = pd.DataFrame(
        {
            "price_of_production": [600.0, 400.0],
            "value_price": [550.0, 450.0],
            "profit": [150.0, 100.0],
            "surplus_value": [175.0, 75.0],
        }
    )
    check = check_industry_equalities(frame)
    assert check.total_price == pytest.approx(1000.0)
    assert check.total_value == pytest.approx(1000.0)
    assert check.total_profit == pytest.approx(250.0)
    assert check.total_surplus_value == pytest.approx(250.0)


def test_profit_rate_decomposition_is_exact(accounts):
    frame = profit_rate_decomposition(accounts)
    assert np.allclose(frame["decomposition_residual"].dropna(), 0.0, atol=1e-12)
    assert implied_rate_of_profit(s_over_v=2.0, m_over_v=8.0) == pytest.approx(0.25)


def test_profit_rate_summary(accounts):
    summary = profit_rate_summary(accounts)
    assert summary["first_year"] == int(accounts.index.min())
    assert summary["last_year"] == int(accounts.index.max())


def test_melt_summary_and_index(accounts):
    summary = melt_summary(accounts, base_year=2017)
    assert summary.nobs == len(accounts)
    assert summary.mean > 0
    assert summary.base_value == pytest.approx(accounts.loc[2017, "melt"])

    index = melt_index(accounts, base_year=2017)
    assert index.loc[2017] == pytest.approx(100.0)


def test_melt_trend_on_rising_series(accounts):
    trend = melt_trend(accounts)
    assert trend.slope_per_year > 0
    assert trend.r_squared > 0.5


def test_ltv_recovers_unit_slope(ltv_accounts):
    result = estimate_ltv(ltv_accounts)
    assert result.nobs == len(ltv_accounts)
    assert result.slope == pytest.approx(1.0, abs=0.05)
    assert result.r_squared > 0.95


def test_ltv_requires_enough_observations(accounts):
    with pytest.raises(ValueError):
        estimate_ltv(accounts.iloc[:5])


def test_summary_table_covers_accounts(accounts):
    table = summary_table(accounts)
    assert "variable" in table.columns
    assert len(table) >= 8
    assert table["n"].gt(0).all()
