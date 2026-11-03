"""Tests for the gravitation and forecast tests."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.analysis.gravitation import (
    cointegration_test,
    deviation_summary,
    error_correction,
    forecast_evaluation,
    panel_unit_root,
    prepare_gravitation_panel,
)


@pytest.fixture
def gravitation_frame() -> pd.DataFrame:
    rng = np.random.default_rng(11)
    rows = []
    for industry in range(12):
        log_go = 5.0 + np.cumsum(rng.normal(0.02, 0.03, 20))
        d = np.zeros(20)
        for year in range(1, 20):
            d[year] = 0.5 * d[year - 1] + rng.normal(0.0, 0.05)
        log_pp = log_go - d
        for year in range(20):
            rows.append(
                {
                    "industry_code": f"I{industry:02d}",
                    "year": 2000 + year,
                    "GO": float(np.exp(log_go[year])),
                    "PP": float(np.exp(log_pp[year])),
                    "d": float(d[year]),
                    "log_GO": float(log_go[year]),
                    "log_PP": float(log_pp[year]),
                    "r": 0.2,
                    "R_benchmark": 0.2,
                }
            )
    frame = pd.DataFrame(rows).sort_values(["industry_code", "year"])
    grouped = frame.groupby("industry_code", group_keys=False)
    frame["d_lag"] = grouped["d"].shift(1)
    frame["log_GO_lag"] = grouped["log_GO"].shift(1)
    frame["delta_log_GO"] = grouped["log_GO"].diff()
    frame["delta_log_PP"] = grouped["log_PP"].diff()
    frame["delta_d"] = grouped["d"].diff()
    for horizon in (1, 3, 5):
        frame[f"target_GO_{horizon}"] = grouped["GO"].shift(-horizon)

    # Make the adjustment direction explicit for the ECM test.
    noise = rng.normal(0.0, 0.01, len(frame))
    frame["delta_log_GO"] = -0.4 * frame["d_lag"] + noise
    frame["delta_log_PP"] = 0.05 * frame["d_lag"] + noise
    frame["delta_d"] = frame["delta_log_GO"] - frame["delta_log_PP"]
    return frame


def test_deviation_summary(gravitation_frame):
    summary = deviation_summary(gravitation_frame)
    assert summary["n_obs"] > 100
    assert 0 <= summary["share_within_25pct"] <= 1
    assert summary["autocorrelation_lag1"] > 0.5
    assert "by_year" in summary


def test_error_correction_detects_go_adjustment(gravitation_frame):
    result = error_correction(gravitation_frame)
    assert result["delta_log_GO"]["beta"] < 0
    assert result["delta_log_GO"]["p_value"] < 0.05
    assert result["delta_log_GO"]["half_life_years"] is not None
    assert result["delta_log_PP"]["beta"] > 0


def test_unit_root_and_cointegration_run(gravitation_frame):
    unit_root = panel_unit_root(gravitation_frame, min_obs=10)
    assert unit_root["n_industries"] == 12
    assert 0 <= unit_root["share_rejecting_5pct"] <= 1

    cointegration = cointegration_test(gravitation_frame, min_obs=10)
    assert cointegration["n_industries"] == 12
    assert 0 <= cointegration["fisher_p_value"] <= 1


def test_prepare_builds_long_run_columns():
    rows = []
    base = {
        "A": dict(C=100.0, V=40.0, T=5.0, GOS=55.0, N=100.0, GO=200.0),
        "B": dict(C=50.0, V=30.0, T=5.0, GOS=15.0, N=50.0, GO=100.0),
        "C": dict(C=200.0, V=20.0, T=10.0, GOS=20.0, N=50.0, GO=250.0),
    }
    for year in (2019, 2020):
        for code, values in base.items():
            row = {"year": year, "industry_code": code, "industry_name": f"Industry {code}"}
            row.update(values)
            rows.append(row)
    frame = prepare_gravitation_panel(pd.DataFrame(rows), capital_proxy="cost")
    assert {"PP_long", "d_long", "d_long_lag", "delta_log_PP_long"}.issubset(
        frame.columns
    )
    assert frame["d_long"].notna().any()


def test_forecast_evaluation_returns_metrics(gravitation_frame):
    forecasts, metrics, comparisons = forecast_evaluation(
        gravitation_frame, start_year=2008, horizons=(1, 3)
    )
    assert not forecasts.empty
    assert set(metrics["model"]) == {"naive", "pp", "ar1", "ecm"}
    assert set(metrics["horizon"]) == {1, 3}
    assert (metrics["rmse_log"] > 0).all()
    assert not comparisons.empty
    assert {"model_a", "model_b", "delta_rmse", "ci_low", "ci_high"}.issubset(
        comparisons.columns
    )
