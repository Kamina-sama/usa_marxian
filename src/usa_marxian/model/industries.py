"""Industry-level Marxian accounts and tests.

The BEA Use table gives, for each industry:

    C_i, V_i, T_i, GOS_i, N_i, GO_i

from which we build

    S_i = T_i + GOS_i                 surplus-value (gross of CFC)
    K_i = C_i + V_i                   cost price
    r_i = S_i / K_i                   industry surplus-value rate

The aggregate rate is ``R = sum(S_i) / sum(K_i)``. Two price benchmarks are
compared with observed gross output:

* ``PP_K_i = K_i (1 + R)``: prices of production with ``M_i`` proxied by the
  cost price. This is the equalised-profit-rate benchmark.
* ``PP_V_i = V_i (1 + S_total / V_total)``: a labour-only markup benchmark.

Because the Use table is an accounting identity, ``C_i + N_i = GO_i`` exactly;
a "value price" test at this level would be vacuous. The informative tests are
the dispersion of ``r_i`` and the distance between ``PP_i`` and observed gross
output.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# Housing is mostly imputed rent with almost no measured intermediate cost, and
# the government units are not capitalist enterprises. They are kept in the
# full sample but excluded from the market-industry robustness subset.
NON_MARKET_CODES = {"HS", "GFGD", "GFGN", "GFE", "GSLG", "GSLE"}


def _weighted_cv(values: np.ndarray, weights: np.ndarray) -> float:
    mean = np.average(values, weights=weights)
    variance = np.average((values - mean) ** 2, weights=weights)
    return float(np.sqrt(variance) / mean) if mean else float("nan")


def _weighted_quantile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    values = values[order]
    weights = weights[order]
    cumulative = np.cumsum(weights) / weights.sum()
    return float(np.interp(q, cumulative, values))


def add_industry_ratios(panel: pd.DataFrame) -> pd.DataFrame:
    """Add year-specific aggregate rates and price benchmarks."""
    required = {"year", "C", "V", "T", "GOS", "N", "GO", "S", "K"}
    missing = required.difference(panel.columns)
    if missing:
        raise KeyError(f"Missing industry columns: {sorted(missing)}")

    out = panel.copy()
    out["is_market"] = ~out["industry_code"].isin(NON_MARKET_CODES)
    totals = out.groupby("year")[["S", "K", "V", "GO"]].transform("sum")
    out["R_cost"] = totals["S"] / totals["K"]
    out["PP_K"] = out["K"] * (1.0 + out["R_cost"])
    out["PP_V"] = out["V"] * (1.0 + totals["S"] / totals["V"])
    out["r"] = out["S"] / out["K"]
    out["gap_K"] = out["GO"] - out["PP_K"]
    out["abs_gap_pct_K"] = (out["gap_K"].abs() / out["GO"]).replace([np.inf, -np.inf], np.nan)
    out["gap_V"] = out["GO"] - out["PP_V"]
    out["abs_gap_pct_V"] = (out["gap_V"].abs() / out["GO"]).replace([np.inf, -np.inf], np.nan)
    return out


def _fit_log_slope(observed: pd.Series, benchmark: pd.Series) -> float:
    frame = pd.DataFrame({"observed": observed, "benchmark": benchmark}).replace(
        [np.inf, -np.inf], np.nan
    )
    frame = frame.loc[(frame > 0).all(axis=1)].dropna()
    if len(frame) < 3:
        return float("nan")
    x = np.log(frame["benchmark"].to_numpy())
    y = np.log(frame["observed"].to_numpy())
    design = np.column_stack([np.ones(len(x)), x])
    return float(np.linalg.lstsq(design, y, rcond=None)[0][1])


def year_summary(panel: pd.DataFrame) -> pd.DataFrame:
    """One row per year with dispersion and price-fit statistics."""
    enriched = add_industry_ratios(panel)
    rows = []
    for year, group in enriched.groupby("year", sort=True):
        group = group.loc[(group["K"] > 0) & (group["GO"] > 0)].copy()
        if group.empty:
            continue
        weights = group["K"].to_numpy(dtype=float)
        rates = group["r"].to_numpy(dtype=float)
        aggregate_rate = float(group["S"].sum() / group["K"].sum())

        p10 = _weighted_quantile(rates, weights, 0.10)
        p90 = _weighted_quantile(rates, weights, 0.90)

        market = group.loc[group["is_market"]]
        market_n = int(len(market))
        if market_n >= 3:
            market_weights = market["K"].to_numpy(dtype=float)
            market_rates = market["r"].to_numpy(dtype=float)
            market_cv = _weighted_cv(market_rates, market_weights)
            market_mae = 100.0 * float(market["abs_gap_pct_K"].mean())
            market_share = float((market["abs_gap_pct_K"] <= 0.25).mean())
        else:
            market_cv = market_mae = market_share = float("nan")

        rows.append(
            {
                "year": int(year),
                "n_industries": int(len(group)),
                "R_cost": aggregate_rate,
                "rate_weighted_cv": _weighted_cv(rates, weights),
                "rate_p10": p10,
                "rate_p90": p90,
                "rate_p90_p10": p90 / p10 if p10 else float("nan"),
                "mae_pct_K": 100.0 * float(group["abs_gap_pct_K"].mean()),
                "rmse_pct_K": 100.0
                * float(np.sqrt(np.mean(group["abs_gap_pct_K"].dropna() ** 2))),
                "corr_K": float(group["GO"].corr(group["PP_K"])),
                "slope_K": _fit_log_slope(group["GO"], group["PP_K"]),
                "mae_pct_V": 100.0 * float(group["abs_gap_pct_V"].mean()),
                "rmse_pct_V": 100.0
                * float(np.sqrt(np.mean(group["abs_gap_pct_V"].dropna() ** 2))),
                "corr_V": float(group["GO"].corr(group["PP_V"])),
                "slope_V": _fit_log_slope(group["GO"], group["PP_V"]),
                "share_within_25pct_K": float((group["abs_gap_pct_K"] <= 0.25).mean()),
                "n_market": market_n,
                "rate_weighted_cv_market": market_cv,
                "mae_pct_K_market": market_mae,
                "share_within_25pct_K_market": market_share,
                "total_GO": float(group["GO"].sum()),
                "total_S": float(group["S"].sum()),
                "total_K": float(group["K"].sum()),
            }
        )
    return pd.DataFrame(rows)


def industry_report(panel: pd.DataFrame) -> dict:
    """Headline industry results, including the latest year and sample means."""
    summary = year_summary(panel)
    if summary.empty:
        raise ValueError("No industry observations")
    latest = summary.iloc[-1].to_dict()
    numeric = summary.select_dtypes(include="number")
    return {
        "n_years": int(summary.shape[0]),
        "n_industries": int(panel["industry_code"].nunique()),
        "sample_start": int(summary["year"].min()),
        "sample_end": int(summary["year"].max()),
        "latest_year": int(latest["year"]),
        "latest": latest,
        "sample_means": {
            "rate_weighted_cv": float(numeric["rate_weighted_cv"].mean()),
            "mae_pct_K": float(numeric["mae_pct_K"].mean()),
            "mae_pct_V": float(numeric["mae_pct_V"].mean()),
            "corr_K": float(numeric["corr_K"].mean()),
            "slope_K": float(numeric["slope_K"].mean()),
            "share_within_25pct_K": float(numeric["share_within_25pct_K"].mean()),
            "rate_weighted_cv_market": float(numeric["rate_weighted_cv_market"].mean()),
            "mae_pct_K_market": float(numeric["mae_pct_K_market"].mean()),
            "share_within_25pct_K_market": float(
                numeric["share_within_25pct_K_market"].mean()
            ),
        },
    }


def latest_dispersion(panel: pd.DataFrame) -> pd.DataFrame:
    """Industry rows for the latest year, with the price benchmarks attached."""
    enriched = add_industry_ratios(panel)
    latest_year = int(enriched["year"].max())
    latest = enriched.loc[enriched["year"] == latest_year].copy()
    latest = latest.sort_values("r", ascending=False)
    return latest.loc[
        :,
        [
            "year",
            "industry_code",
            "industry_name",
            "C",
            "V",
            "S",
            "K",
            "GO",
            "r",
            "PP_K",
            "PP_V",
            "abs_gap_pct_K",
            "is_market",
        ],
    ]
