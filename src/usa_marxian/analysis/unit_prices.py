"""Unit-price comparison: model relative prices vs observed gross-output prices.

The revenue comparison in ``benchmark_comparison.csv`` asks whether
``PP_i`` tracks ``GO_i``. Both are gross revenues, so industry size can dominate.
This module compares **unit prices** instead:

* observed: ``price_obs_i = GOPI_i / 100``;
* Moseley: ``p_moseley_i = PP_i / quantity_i``;
* Sraffa, Shaikh, regulating, labour values from the benchmark panel.

All price series are normalised per year to a quantity-weighted geometric mean
of one, so the comparison is about relative prices. Levels are arbitrary;
relative prices are the economically meaningful object.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .gravitation import (
    deviation_summary,
    error_correction,
    forecast_evaluation,
)

UNIT_PRICE_MODELS = {
    "Moseley PP (stock capital)": "p_moseley",
    "Sraffa prices of production": "p_sraffa",
    "Shaikh iterated prices": "p_shaikh",
    "Regulating capital": "p_reg",
    "Direct prices (labour values)": "p_v",
}


def _weighted_geometric_mean(values: pd.Series, weights: pd.Series) -> float:
    mask = values.notna() & (values > 0) & weights.notna() & (weights > 0)
    if not mask.any():
        return float("nan")
    return float(
        np.exp(np.average(np.log(values[mask]), weights=weights[mask]))
    )


def build_unit_price_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Build a normalised unit-price panel from the benchmark panel."""
    data = panel.copy()
    if "go_price" not in data.columns:
        raise KeyError("Panel has no go_price column")
    data["price_obs"] = data["go_price"] / 100.0
    data["quantity"] = data["GO"] / data["price_obs"]

    moseley_column = "PP_market" if "PP_market" in data.columns else "PP"
    data["p_moseley"] = data[moseley_column] / data["quantity"]
    if "regulating_factor" in data.columns and "p_sraffa" in data.columns:
        data["p_reg"] = data["p_sraffa"] * data["regulating_factor"]

    model_columns = [
        column
        for column in UNIT_PRICE_MODELS.values()
        if column in data.columns
    ]
    for column in ["price_obs", *model_columns]:
        data[f"{column}_n"] = np.nan

    for _, group in data.groupby("year"):
        weights = group["quantity"]
        for column in ["price_obs", *model_columns]:
            values = group[column]
            geo = _weighted_geometric_mean(values, weights)
            if np.isfinite(geo) and geo > 0:
                data.loc[group.index, f"{column}_n"] = values / geo

    return data


def _metrics(frame: pd.DataFrame, column: str, label: str) -> dict:
    data = frame.loc[:, ["year", "industry_code", "price_obs_n", column]].replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    data = data.loc[(data["price_obs_n"] > 0) & (data[column] > 0)]
    if len(data) < 3:
        return {"benchmark": label, "n": 0}
    error = np.log(data["price_obs_n"]) - np.log(data[column])
    slope = float(
        np.polyfit(np.log(data[column]), np.log(data["price_obs_n"]), 1)[0]
    )
    return {
        "benchmark": label,
        "n": int(len(data)),
        "log_mae": float(np.mean(np.abs(error))),
        "log_rmse": float(np.sqrt(np.mean(error**2))),
        "corr": float(data["price_obs_n"].corr(data[column])),
        "slope": slope,
        "within_10pct": float((error.abs() <= np.log(1.10)).mean()),
        "within_25pct": float((error.abs() <= np.log(1.25)).mean()),
        "bias_log": float(np.mean(error)),
    }


def _by_year(frame: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    rows = []
    for year, group in frame.groupby("year"):
        row = _metrics(group, column, label)
        row["year"] = int(year)
        rows.append(row)
    return pd.DataFrame(rows)


def _gravitation_frame(frame: pd.DataFrame, column: str) -> pd.DataFrame:
    data = frame.loc[:, ["year", "industry_code", "price_obs_n", column]].dropna()
    data = data.rename(columns={column: "benchmark"})
    data = data.loc[(data["price_obs_n"] > 0) & (data["benchmark"] > 0)]
    data = data.sort_values(["industry_code", "year"]).copy()
    data["GO"] = data["price_obs_n"]
    data["log_GO"] = np.log(data["price_obs_n"])
    data["log_PP"] = np.log(data["benchmark"])
    data["d"] = data["log_GO"] - data["log_PP"]
    grouped = data.groupby("industry_code", group_keys=False)
    data["d_lag"] = grouped["d"].shift(1)
    data["delta_log_GO"] = grouped["log_GO"].diff()
    data["delta_log_PP"] = grouped["log_PP"].diff()
    data["delta_d"] = grouped["d"].diff()
    data["target_GO_1"] = grouped["price_obs_n"].shift(-1)
    return data


def _unit_price_gravitation(frame: pd.DataFrame, column: str, label: str) -> dict:
    data = _gravitation_frame(frame, column)
    summary = deviation_summary(data)
    adjustment = error_correction(data)
    _, metrics, _ = forecast_evaluation(
        data, pp="benchmark", start_year=2008, horizons=(1,)
    )
    metrics = metrics.loc[metrics["horizon"] == 1].set_index("model")
    return {
        "benchmark": label,
        "n_obs": summary["n_obs"],
        "mean_abs_d": summary["mean_abs_d"],
        "half_life_years": summary["ar1_half_life_years"],
        "autocorrelation": summary["autocorrelation_lag1"],
        "beta_go": adjustment["delta_log_GO"]["beta"],
        "p_go": adjustment["delta_log_GO"]["p_value"],
        "beta_pp": adjustment["delta_log_PP"]["beta"],
        "p_pp": adjustment["delta_log_PP"]["p_value"],
        "forecast_pp_1y": float(metrics.loc["pp", "rmse_log"]),
        "forecast_naive_1y": float(metrics.loc["naive", "rmse_log"]),
    }


def compare_unit_prices(panel: pd.DataFrame) -> dict:
    """Return unit-price comparison, by-year metrics and gravitation tests."""
    data = build_unit_price_panel(panel)
    common_columns = [
        f"{column}_n"
        for column in UNIT_PRICE_MODELS.values()
        if f"{column}_n" in data.columns
    ]
    data = data.dropna(subset=["price_obs_n", *common_columns])
    comparison_rows = []
    year_rows = []
    gravitation_rows = []
    for label, column in UNIT_PRICE_MODELS.items():
        normalized = f"{column}_n"
        if normalized not in data.columns or data[normalized].notna().sum() < 3:
            continue
        comparison_rows.append(_metrics(data, normalized, label))
        year_rows.append(_by_year(data, normalized, label))
        try:
            gravitation_rows.append(
                _unit_price_gravitation(data, normalized, label)
            )
        except Exception:
            # Tiny synthetic panels do not support the ECM/forecast block.
            continue

    comparison = pd.DataFrame(comparison_rows)
    by_year = (
        pd.concat(year_rows, ignore_index=True)
        if year_rows
        else pd.DataFrame()
    )
    gravitation = pd.DataFrame(gravitation_rows)
    latest_year = int(data["year"].max())
    latest = comparison.copy()
    latest["year"] = latest_year
    return {
        "panel": data,
        "comparison": comparison,
        "by_year": by_year,
        "gravitation": gravitation,
        "latest": latest,
        "latest_year": latest_year,
        "summary": {
            "latest_year": latest_year,
            "n_industries": int(data["industry_code"].nunique()),
            "models": list(comparison["benchmark"]) if not comparison.empty else [],
        },
    }
