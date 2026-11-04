"""Diagnostics for the unit-price result.

Three tests:

1. Revenue-ratio composition — how far is ``PP/GO`` from one, and does it
   explain the unit-price variance?
2. Within-sector relative prices — remove the broad-sector deflator and compare
   model vs observed relative prices within sectors.
3. Measurement error — use the value-added and gross-output deflators as two
   proxies to bound attenuation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

MODELS = {
    "Moseley": "p_moseley_n",
    "Sraffa": "p_sraffa_n",
    "Shaikh": "p_shaikh_n",
    "Regulating": "p_reg_n",
    "Direct prices": "p_v_n",
}


def revenue_ratio_diagnostics(panel: pd.DataFrame) -> dict:
    data = panel.loc[panel["is_market"]].copy()
    data = data.loc[(data["GO"] > 0) & (data["PP_market"] > 0)]
    data["ratio"] = data["PP_market"] / data["GO"]
    data["log_ratio"] = np.log(data["ratio"])
    data["log_price"] = np.log(data["price_obs_n"])
    data["log_p_moseley"] = np.log(data["p_moseley_n"])

    summary = {
        "n": int(len(data)),
        "mean_ratio": float(data["ratio"].mean()),
        "std_ratio": float(data["ratio"].std()),
        "p05_ratio": float(data["ratio"].quantile(0.05)),
        "p95_ratio": float(data["ratio"].quantile(0.95)),
        "mean_abs_log_ratio": float(data["log_ratio"].abs().mean()),
        "share_within_5pct": float((data["ratio"].sub(1).abs() <= 0.05).mean()),
        "share_within_10pct": float((data["ratio"].sub(1).abs() <= 0.10).mean()),
        "share_within_20pct": float((data["ratio"].sub(1).abs() <= 0.20).mean()),
        "corr_log_ratio_price": float(data["log_ratio"].corr(data["log_price"])),
        "var_log_ratio": float(data["log_ratio"].var()),
        "var_log_price": float(data["log_price"].var()),
        "var_log_p_moseley": float(data["log_p_moseley"].var()),
        "cov_ratio_price": float(np.cov(data["log_ratio"], data["log_price"])[0, 1]),
    }
    if summary["var_log_p_moseley"] > 0:
        summary["ratio_variance_share"] = float(
            (summary["var_log_ratio"] + summary["cov_ratio_price"])
            / summary["var_log_p_moseley"]
        )
    else:
        summary["ratio_variance_share"] = float("nan")

    by_year = (
        data.groupby("year")
        .agg(
            n=("ratio", "size"),
            std_ratio=("ratio", "std"),
            mean_abs_log_ratio=("log_ratio", lambda s: float(s.abs().mean())),
            corr_ratio_price=("ratio", lambda s: float("nan")),
        )
        .reset_index()
    )
    for index, row in by_year.iterrows():
        group = data.loc[data["year"] == row["year"]]
        by_year.loc[index, "corr_ratio_price"] = group["log_ratio"].corr(
            group["log_price"]
        )

    latest = data.loc[data["year"] == data["year"].max()].copy()
    latest_table = (
        latest.loc[:, ["industry_code", "ratio", "log_price", "log_p_moseley"]]
        .sort_values("ratio")
        .reset_index(drop=True)
    )
    return {
        "summary": summary,
        "by_year": by_year,
        "latest": latest_table,
    }


def _demean(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    data = frame.copy()
    grouped = data.groupby(["year", "sector"])
    for column in columns:
        data[f"{column}_dm"] = data[column] - grouped[column].transform("mean")
    return data


def within_sector_diagnostics(panel: pd.DataFrame) -> pd.DataFrame:
    data = panel.loc[panel["is_market"]].copy()
    data = data.dropna(subset=["price_obs_n", "sector"])
    data = data.loc[(data["price_obs_n"] > 0)]
    data["log_price_obs"] = np.log(data["price_obs_n"])
    for label, column in MODELS.items():
        if column not in data.columns:
            continue
        valid = data.loc[(data[column] > 0)].copy()
        valid[f"log_{column}"] = np.log(valid[column])
        valid = _demean(valid, ["log_price_obs", f"log_{column}"])
        x = valid[f"log_{column}_dm"]
        y = valid["log_price_obs_dm"]
        mask = x.notna() & y.notna()
        if mask.sum() < 5:
            continue
        identified = bool(float(np.var(y[mask])) > 1e-12)
        slope = (
            float(np.polyfit(x[mask], y[mask], 1)[0]) if identified else float("nan")
        )
        corr = float(x[mask].corr(y[mask])) if identified else float("nan")
        if "results" not in data.attrs:
            data.attrs["results"] = []
        data.attrs["results"].append(
            {
                "benchmark": label,
                "n": int(mask.sum()),
                "identified": identified,
                "corr_within": corr,
                "slope_within": slope,
                "rmse_within": float(np.sqrt(np.mean((y[mask] - x[mask]) ** 2))),
            }
        )
    return pd.DataFrame(data.attrs.get("results", []))


def measurement_error_diagnostics(panel: pd.DataFrame) -> dict:
    data = panel.loc[panel["is_market"]].copy()
    data = data.dropna(subset=["va_price", "go_price", "sector"])
    data = data.loc[(data["va_price"] > 0) & (data["go_price"] > 0)].copy()
    data["log_va"] = np.log(data["va_price"])
    data["log_go"] = np.log(data["go_price"])
    data = _demean(data, ["log_va", "log_go"])
    x = data["log_go_dm"]
    y = data["log_va_dm"]
    mask = x.notna() & y.notna()
    x, y = x[mask], y[mask]
    if len(x) < 5:
        return {}
    var_x = float(np.var(x, ddof=1))
    var_y = float(np.var(y, ddof=1))
    cov = float(np.cov(x, y)[0, 1])
    if var_x <= 1e-12 or var_y <= 1e-12:
        return {
            "n": int(len(x)),
            "identified": False,
            "var_log_go": var_x,
            "var_log_va": var_y,
        }
    reliability_go = cov / var_x
    reliability_va = cov / var_y
    return {
        "n": int(len(x)),
        "identified": True,
        "corr_va_go": float(np.corrcoef(x, y)[0, 1]),
        "var_log_go": var_x,
        "var_log_va": var_y,
        "cov": cov,
        "reliability_go_as_proxy": float(reliability_go),
        "reliability_va_as_proxy": float(reliability_va),
        "slope_va_on_go": float(cov / var_x) if var_x > 0 else float("nan"),
        "slope_go_on_va": float(cov / var_y) if var_y > 0 else float("nan"),
    }


def run_price_diagnostics(panel: pd.DataFrame) -> dict:
    within = within_sector_diagnostics(panel)
    measurement = measurement_error_diagnostics(panel)
    return {
        "revenue_ratio": revenue_ratio_diagnostics(panel),
        "within_sector": within,
        "measurement": measurement,
        "within_sector_identified": bool(
            not within.empty and within["identified"].any()
        ),
        "measurement_identified": bool(measurement.get("identified", False)),
    }
