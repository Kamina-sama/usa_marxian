"""Compare Moseley and Shaikh price benchmarks against observed gross output."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..model.shaikh import ShaikhResult, build_shaikh_benchmarks
from .gravitation import deviation_summary, error_correction, forecast_evaluation

BENCHMARK_LABELS = {
    "PP": "Moseley PP (stock capital)",
    "PP_S": "Shaikh prices of production (flow capital)",
    "PP_S_iter": "Shaikh iterated prices (endogenous r)",
    "P_V": "Shaikh direct prices (labour values)",
}


@dataclass
class ComparisonResult:
    shaikh: ShaikhResult
    comparison: pd.DataFrame
    gravitation: pd.DataFrame
    summary: dict


def _fit_log_slope(observed: pd.Series, benchmark: pd.Series) -> float:
    if len(observed) < 3:
        return float("nan")
    return float(np.polyfit(np.log(benchmark), np.log(observed), 1)[0])


def _metrics(frame: pd.DataFrame, column: str, *, label: str) -> dict:
    data = frame.loc[:, [column, "GO"]].replace([np.inf, -np.inf], np.nan).dropna()
    data = data.loc[(data[column] > 0) & (data["GO"] > 0)]
    if data.empty:
        return {"benchmark": label, "n": 0}
    error = (data["GO"] - data[column]) / data["GO"]
    return {
        "benchmark": label,
        "n": int(data.shape[0]),
        "mae_pct": float(100.0 * error.abs().mean()),
        "rmse_pct": float(100.0 * np.sqrt((error**2).mean())),
        "corr": float(data["GO"].corr(data[column])),
        "slope": _fit_log_slope(data["GO"], data[column]),
        "share_within_25pct": float((error.abs() <= 0.25).mean()),
        "mean_gap_pct": float(100.0 * error.mean()),
    }


def compare_benchmarks(panel: pd.DataFrame) -> pd.DataFrame:
    """Compare all benchmarks on the same market-industry sample.

    Moseley's benchmark uses ``PP_market`` here, which applies the market-only
    profit rate. Using the full-sample ``PP`` on market industries would embed
    the government/housing capital stock in the benchmark rate and exaggerate
    Moseley's fit.
    """
    frame = panel.loc[panel["is_market"]].copy() if "is_market" in panel.columns else panel
    common = [
        column
        for column in ("PP_market", "PP_S", "PP_S_iter", "P_V", "GO")
        if column in frame.columns
    ]
    if common:
        frame = frame.dropna(subset=common)
    rows = []
    for column, label in BENCHMARK_LABELS.items():
        use_column = column
        if column == "PP" and "PP_market" in frame.columns:
            use_column = "PP_market"
        if use_column not in frame.columns:
            continue
        rows.append(_metrics(frame, use_column, label=f"{label} | market"))
    return pd.DataFrame(rows)


def _benchmark_frame(panel: pd.DataFrame, column: str) -> pd.DataFrame:
    frame = panel.loc[panel["is_market"], ["year", "industry_code", "GO", column]].copy()
    frame = frame.rename(columns={column: "benchmark"})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame.loc[(frame["GO"] > 0) & (frame["benchmark"] > 0)]
    frame = frame.sort_values(["industry_code", "year"])
    frame["log_GO"] = np.log(frame["GO"])
    frame["log_PP"] = np.log(frame["benchmark"])
    frame["d"] = frame["log_GO"] - frame["log_PP"]

    grouped = frame.groupby("industry_code", group_keys=False)
    frame["d_lag"] = grouped["d"].shift(1)
    frame["delta_log_GO"] = grouped["log_GO"].diff()
    frame["delta_log_PP"] = grouped["log_PP"].diff()
    frame["delta_d"] = grouped["d"].diff()
    frame["target_GO_1"] = grouped["GO"].shift(-1)
    return frame


def _benchmark_gravitation(panel: pd.DataFrame, column: str, label: str) -> dict:
    frame = _benchmark_frame(panel, column)
    summary = deviation_summary(frame)
    adjustment = error_correction(frame)
    _, metrics, _ = forecast_evaluation(
        frame, pp="benchmark", start_year=2008, horizons=(1,)
    )
    metrics = metrics.loc[metrics["horizon"] == 1].set_index("model")
    return {
        "benchmark": label,
        "n_obs": summary["n_obs"],
        "mean_abs_d": summary["mean_abs_d"],
        "share_within_25pct": summary["share_within_25pct"],
        "autocorrelation": summary["autocorrelation_lag1"],
        "half_life_years": summary["ar1_half_life_years"],
        "beta_go": adjustment["delta_log_GO"]["beta"],
        "p_go": adjustment["delta_log_GO"]["p_value"],
        "beta_pp": adjustment["delta_log_PP"]["beta"],
        "p_pp": adjustment["delta_log_PP"]["p_value"],
        "forecast_pp_1y": float(metrics.loc["pp", "rmse_log"]),
        "forecast_naive_1y": float(metrics.loc["naive", "rmse_log"]),
    }


def run_shaikh_comparison(
    panel: pd.DataFrame,
    use_matrices: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    base_year: int = 2017,
) -> ComparisonResult:
    """Build Shaikh benchmarks and compare them with Moseley's PP."""
    shaikh = build_shaikh_benchmarks(
        panel, use_matrices, accounts, base_year=base_year
    )
    comparison = compare_benchmarks(shaikh.panel)
    gravitation = pd.DataFrame(
        [
            _benchmark_gravitation(
                shaikh.panel, "PP_market", "Moseley PP (stock capital)"
            ),
            _benchmark_gravitation(
                shaikh.panel, "PP_S", "Shaikh prices of production (flow capital)"
            ),
            _benchmark_gravitation(
                shaikh.panel, "PP_S_iter", "Shaikh iterated prices (endogenous r)"
            ),
            _benchmark_gravitation(
                shaikh.panel, "P_V", "Shaikh direct prices (labour values)"
            ),
        ]
    )

    latest_year = int(shaikh.panel["year"].max())
    latest_frame = shaikh.panel.loc[
        (shaikh.panel["year"] == latest_year) & (shaikh.panel["is_market"])
    ]
    latest_rows = []
    for column, label in BENCHMARK_LABELS.items():
        use_column = column
        if column == "PP" and "PP_market" in latest_frame.columns:
            use_column = "PP_market"
        if use_column in latest_frame.columns:
            latest_rows.append(
                {**_metrics(latest_frame, use_column, label=label), "year": latest_year}
            )

    return ComparisonResult(
        shaikh=shaikh,
        comparison=comparison,
        gravitation=gravitation,
        summary={
            **shaikh.summary,
            "latest_year": latest_year,
            "latest_market": latest_rows,
            "gravitation": gravitation.to_dict(orient="records"),
        },
    )
