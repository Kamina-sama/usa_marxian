"""Smoke tests for the findings figures.

These only check that each plot renders and writes a non-trivial PNG, plus the
guard that stops the coefficient plot from silently degrading to one benchmark.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import numpy as np
import pandas as pd
import pytest

from usa_marxian.viz import findings


def _comparison() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "benchmark": [
                "Moseley PP (stock capital) | market",
                "Sraffa prices of production (flow capital) | market",
                "Direct prices (labour values) | market",
            ],
            "n": [1560, 1560, 1560],
            "mae_pct": [12.4, 18.7, 36.5],
            "rmse_pct": [19.4, 28.2, 47.9],
            "corr": [0.983, 0.957, 0.888],
            "slope": [1.043, 0.941, 0.872],
            "share_within_25pct": [0.895, 0.760, 0.433],
            "mean_gap_pct": [-5.7, -2.9, -8.7],
        }
    )


def _unit_panel() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    model = rng.normal(size=200)
    return pd.DataFrame(
        {
            "price_obs_n": np.exp(0.6 * model + rng.normal(scale=0.1, size=200)),
            "p_moseley_working_n": np.exp(model),
            "p_sraffa_n": np.exp(0.3 * model + rng.normal(scale=0.3, size=200)),
            "p_v_n": np.exp(rng.normal(size=200)),
        }
    )


def _forecast_metrics() -> pd.DataFrame:
    rows = []
    values = {"naive": 0.12, "ar1": 0.12, "ecm": 0.12, "pp": 0.21}
    for model, base in values.items():
        for index, horizon in enumerate((1, 3, 5)):
            rows.append({"horizon": horizon, "model": model, "rmse_log": base * (1 + index)})
    return pd.DataFrame(rows)


def _summary() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": list(range(2010, 2024)),
            "rate_weighted_cv": np.linspace(2.4, 2.1, 14),
            "rate_weighted_cv_market": np.linspace(0.78, 0.61, 14),
            "R_benchmark_market": np.linspace(0.18, 0.20, 14),
            "R_real_market": np.linspace(0.18, 0.20, 14),
        }
    )


def test_benchmark_fit_writes_png(tmp_path):
    path = findings.plot_benchmark_fit(_comparison(), tmp_path / "fit.png")
    assert path.exists()
    assert path.stat().st_size > 1_000


def test_unit_price_fit_writes_png(tmp_path):
    path = findings.plot_unit_price_fit(_unit_panel(), tmp_path / "unit.png")
    assert path.exists()
    assert path.stat().st_size > 1_000


def test_forecast_plot_handles_missing_long_run(tmp_path):
    path = findings.plot_forecast_horizons(_forecast_metrics(), None, tmp_path / "f.png")
    assert path.exists()
    assert path.stat().st_size > 1_000


def test_dispersion_plot_writes_png(tmp_path):
    path = findings.plot_dispersion_and_deflator(_summary(), tmp_path / "d.png")
    assert path.exists()
    assert path.stat().st_size > 1_000


def test_capital_composition_writes_png(tmp_path):
    coverage = pd.DataFrame(
        {
            "year": [2023],
            "private_M_assets_bn": [34_948.0],
            "special_M_assets_bn": [47_797.0],
            "total_M_inv_bn": [3_805.0],
        }
    )
    inventories = pd.DataFrame(
        {
            "year": [2023, 2023],
            "industry_code": ["a", "b"],
            "M_inv": [2_043_000.0, 1_762_000.0],
            "inventory_source": [
                "BEA 1BUC detail",
                "BEA 5.8.5B broad allocation",
            ],
        }
    )
    path = findings.plot_capital_composition(coverage, inventories, tmp_path / "c.png")
    assert path.exists()
    assert path.stat().st_size > 1_000


def test_coefficient_plot_rejects_single_benchmark(tmp_path):
    panel = pd.DataFrame(
        {
            "is_market": [True, True],
            "industry_code": ["a", "a"],
            "year": [2000, 2001],
            "GO": [100.0, 110.0],
            "PP_market": [90.0, 100.0],
        }
    )
    with pytest.raises(ValueError, match="at least two"):
        findings.plot_gravitation_coefficients(panel, tmp_path / "g.png")


def test_build_reports_missing_artifacts(tmp_path):
    class _Settings:
        output_dir = tmp_path / "output"
        processed_dir = tmp_path / "processed"

    class _Config:
        settings = _Settings()

    with pytest.raises(FileNotFoundError, match="run `usa-marxian all` first"):
        findings.build_findings_figures(_Config())
