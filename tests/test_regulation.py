"""Tests for the profit-rate regulation module."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from usa_marxian.analysis import regulation as reg


def _panel(n_industries: int = 20, n_years: int = 12, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for index in range(n_industries):
        level = rng.normal(0.2, 0.05)
        capital = 1000.0
        for step in range(n_years):
            rate = float(level + rng.normal(0.0, 0.02))
            rows.append(
                {
                    "year": 2000 + step,
                    "industry_code": f"i{index:02d}",
                    "M": capital,
                    "S_net": rate * capital,
                    "is_market": True,
                }
            )
    return pd.DataFrame(rows)


def _state(panel: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(1)
    frame = panel.loc[:, ["year", "industry_code"]].copy()
    frame["capital"] = 1000.0
    frame["investment"] = rng.normal(60.0, 5.0, len(frame))
    return frame


def test_regulation_panel_computes_rates_and_gap():
    panel = _panel(n_industries=3, n_years=2)
    regulation = reg.build_regulation_panel(panel)
    assert len(regulation) == 6
    assert "r" in regulation.columns and "R" in regulation.columns
    year = 2000
    block = regulation.loc[regulation["year"] == year]
    expected = block["S_net"].sum() / block["M"].sum()
    assert block["R"].iloc[0] == pytest.approx(expected)
    assert block["gap"].iloc[0] == pytest.approx(block["r"].iloc[0] - expected)


def test_dispersion_table_has_one_row_per_year():
    regulation = reg.build_regulation_panel(_panel())
    table = reg.dispersion_by_year(regulation)
    assert len(table) == regulation["year"].nunique()
    for column in ("R", "cv", "iqr", "p90_p10", "mean_abs_gap"):
        assert column in table.columns
    assert (table["iqr"] >= 0).all()


def test_convergence_is_never_identified_with_two_way_effects():
    """The collinearity is structural, so this must hold on any data."""
    result = reg.convergence_test(reg.build_regulation_panel(_panel()))
    assert result["identified"] is False
    assert result["beta_toward_R"] == pytest.approx(
        result["beta_toward_own_mean"], abs=1e-10
    )
    assert "mean reversion" in result["note"]


def test_verdict_says_dispersion_is_not_narrowing():
    regulation = reg.build_regulation_panel(_panel())
    result = reg.run_regulation_tests(regulation, _state(regulation))
    assert "do not converge" in result["verdict"]
    assert result["capital_mobility"]["supported"] in (True, False)
    assert result["dispersion_trend"]["cv"] != 0


def test_capital_mobility_reports_a_coefficient():
    regulation = reg.build_regulation_panel(_panel())
    result = reg.capital_mobility_test(regulation, _state(regulation))
    assert set(result) >= {"beta", "p_value", "supported", "nobs"}
    assert np.isfinite(result["beta"])


def test_write_outputs_creates_both_artifacts(tmp_path):
    regulation = reg.build_regulation_panel(_panel())
    result = reg.run_regulation_tests(regulation, _state(regulation))
    paths = reg.write_outputs(regulation, result, tmp_path)
    assert paths["json"].exists() and paths["dispersion"].exists()
    payload = json.loads(paths["json"].read_text())
    assert "verdict" in payload
    table = pd.read_csv(paths["dispersion"])
    assert "mean_abs_gap" in table.columns


def test_missing_columns_raise():
    with pytest.raises(KeyError, match="missing columns"):
        reg.build_regulation_panel(pd.DataFrame({"year": [2000]}))
