"""Industry-level Marxian accounts and tests.

The BEA Use table gives, for each industry:

    C_i, V_i, T_i, GOS_i, N_i, GO_i

from which we build **gross** and, when CFC data are available, **net**
accounts:

    S_gross_i = T_i + GOS_i
    K_gross_i = C_i + V_i
    S_net_i   = T_i + GOS_i - CFC_i
    K_net_i   = C_i + CFC_i + V_i
    N_net_i   = N_i - CFC_i

Both satisfy ``K + S = GO``. The gross split is what the Use table alone
supports; the net split moves depreciation from surplus-value into constant
capital, which is the correct Marxian treatment.

Prices of production follow Moseley exactly:

    PP_i = K_i + R M_i,        R = sum(S_i) / sum(M_i)

The industry capital stock ``M_i`` is not in the Use table. The module makes
the proxy explicit and supports several:

* ``cost``: M_i = K_i (the default, and the source of the earlier K_i(1+R)
  shortcut);
* ``output``: M_i = GO_i;
* ``value_added``: M_i = N_i;
* ``fixed_assets``: an actual M_i column, if supplied.

Because ``R`` is defined from the chosen ``M`` aggregate, ``sum(PP_i) =
sum(GO_i)`` holds for every proxy. The informative comparison is the distance
between ``PP_i`` and observed gross output, not the aggregate identity.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

CapitalProxy = Literal["cost", "output", "value_added", "fixed_assets"]
SurplusBasis = Literal["gross", "net", "auto"]

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


def _resolve_basis(panel: pd.DataFrame, surplus: SurplusBasis) -> str:
    if surplus != "auto":
        return surplus
    if "CFC" in panel.columns and panel["CFC"].notna().any():
        return "net"
    return "gross"


def _capital_proxy(
    frame: pd.DataFrame,
    proxy: CapitalProxy,
    *,
    cost_column: str,
    value_column: str,
) -> pd.Series:
    if proxy == "cost":
        return frame[cost_column]
    if proxy == "output":
        return frame["GO"]
    if proxy == "value_added":
        return frame[value_column]
    if proxy == "fixed_assets":
        if "M" not in frame.columns:
            raise KeyError("capital_proxy='fixed_assets' requires an M column")
        return frame["M"]
    raise ValueError(f"Unknown capital proxy: {proxy}")


def add_industry_ratios(
    panel: pd.DataFrame,
    *,
    capital_proxy: CapitalProxy = "cost",
    surplus: SurplusBasis = "auto",
) -> pd.DataFrame:
    """Add gross/net accounts, industry rates and price benchmarks."""
    required = {"year", "C", "V", "T", "GOS", "N", "GO"}
    missing = required.difference(panel.columns)
    if missing:
        raise KeyError(f"Missing industry columns: {sorted(missing)}")

    basis = _resolve_basis(panel, surplus)
    out = panel.copy()
    out["is_market"] = ~out["industry_code"].astype(str).isin(NON_MARKET_CODES)
    out["surplus_basis"] = basis
    out["capital_proxy"] = (
        "fixed_assets+inventories" if capital_proxy == "fixed_assets" else capital_proxy
    )

    out["S_gross"] = out["T"] + out["GOS"]
    out["K_gross"] = out["C"] + out["V"]
    out["r_gross"] = out["S_gross"] / out["K_gross"]

    if "CFC" in out.columns:
        if basis == "net":
            # Drop only years with no CFC data at all (1997 in the current
            # vintage). Industries outside the private CFC groups, such as
            # government and used goods, have structurally zero CFC and must
            # remain in the panel.
            has_cfc = out.groupby("year")["CFC"].transform("count") > 0
            out = out.loc[has_cfc].copy()
        out["CFC"] = out["CFC"].fillna(0.0)
    else:
        out["CFC"] = 0.0
    out["C_total"] = out["C"] + out["CFC"]
    out["S_net"] = out["S_gross"] - out["CFC"]
    out["K_net"] = out["C_total"] + out["V"]
    out["N_net"] = out["N"] - out["CFC"]
    out["r_net"] = out["S_net"] / out["K_net"]

    value_column = "S_net" if basis == "net" else "S_gross"
    cost_column = "K_net" if basis == "net" else "K_gross"
    new_value_column = "N_net" if basis == "net" else "N"

    out["M_proxy"] = _capital_proxy(
        out, capital_proxy, cost_column=cost_column, value_column=new_value_column
    )
    totals = out.groupby("year")[
        [value_column, "M_proxy", "V", "GO", cost_column]
    ].transform("sum")

    out["R_benchmark"] = totals[value_column] / totals["M_proxy"]
    out["PP"] = out[cost_column] + out["R_benchmark"] * out["M_proxy"]

    # Market-only benchmark: the full sample includes government and housing,
    # whose capital stocks fall back to K. Using the full-sample R for the
    # market comparison would contaminate it with those proxies.
    market = out.loc[out["is_market"]]
    market_totals = market.groupby("year")[[value_column, "M_proxy"]].sum()
    market_rate = market_totals[value_column] / market_totals["M_proxy"]
    out["R_benchmark_market"] = out["year"].map(market_rate)
    out["PP_market"] = (
        out[cost_column] + out["R_benchmark_market"] * out["M_proxy"]
    )

    out["PP_V"] = out["V"] * (1.0 + totals[value_column] / totals["V"])
    out["r"] = out[value_column] / out[cost_column]
    out["gap_PP"] = out["GO"] - out["PP"]
    out["abs_gap_pct_PP"] = (out["gap_PP"].abs() / out["GO"]).replace(
        [np.inf, -np.inf], np.nan
    )
    out["gap_PP_market"] = out["GO"] - out["PP_market"]
    out["abs_gap_pct_PP_market"] = (out["gap_PP_market"].abs() / out["GO"]).replace(
        [np.inf, -np.inf], np.nan
    )
    out["gap_PP_V"] = out["GO"] - out["PP_V"]
    out["abs_gap_pct_PP_V"] = (out["gap_PP_V"].abs() / out["GO"]).replace(
        [np.inf, -np.inf], np.nan
    )

    # Long-run centre of gravitation: trailing five-year averages of cost and
    # capital, and a trailing five-year average general profit rate. This is a
    # deliberately slow-moving benchmark, not a current-year accounting price.
    out = out.sort_values(["industry_code", "year"]).copy()
    aggregate_rate = out.groupby("year")["R_benchmark"].first().sort_index()
    out["R_long"] = out["year"].map(
        aggregate_rate.rolling(window=5, min_periods=1).mean()
    )
    grouped_industry = out.groupby("industry_code", group_keys=False)
    out["K_trend"] = grouped_industry[cost_column].transform(
        lambda s: s.rolling(window=5, min_periods=1).mean()
    )
    out["M_trend"] = grouped_industry["M_proxy"].transform(
        lambda s: s.rolling(window=5, min_periods=1).mean()
    )
    out["PP_long"] = out["K_trend"] + out["R_long"] * out["M_trend"]
    out["gap_PP_long"] = out["GO"] - out["PP_long"]
    out["abs_gap_pct_PP_long"] = (out["gap_PP_long"].abs() / out["GO"]).replace(
        [np.inf, -np.inf], np.nan
    )

    market_aggregate_rate = (
        out.groupby("year")["R_benchmark_market"].first().sort_index()
    )
    out["R_long_market"] = out["year"].map(
        market_aggregate_rate.rolling(window=5, min_periods=1).mean()
    )
    out["PP_long_market"] = out["K_trend"] + out["R_long_market"] * out["M_trend"]
    out["gap_PP_long_market"] = out["GO"] - out["PP_long_market"]
    out["abs_gap_pct_PP_long_market"] = (
        out["gap_PP_long_market"].abs() / out["GO"]
    ).replace([np.inf, -np.inf], np.nan)
    out = out.sort_values(["year", "industry_code"]).reset_index(drop=True)

    # Real accounts use sector-specific price indexes when available.
    #
    # Value added, compensation and gross output can each be deflated by their
    # own sector index. We deliberately do NOT construct real intermediate
    # consumption as GO_real - N_real: with different deflators that residual
    # is not a valid volume and can even be negative. A real profit rate would
    # need a sector intermediate-input deflator, which the summary Use table
    # does not provide.
    if {"va_price", "go_price"}.issubset(out.columns):
        va_deflator = out["va_price"] / 100.0
        go_deflator = out["go_price"] / 100.0
        out["N_real"] = out[new_value_column] / va_deflator
        out["GO_real"] = out["GO"] / go_deflator
        out["V_real"] = out["V"] / va_deflator
        out["S_real"] = out["N_real"] - out["V_real"]
        out["va_deflator"] = out["va_price"]
        out["go_deflator"] = out["go_price"]

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


def year_summary(
    panel: pd.DataFrame,
    *,
    capital_proxy: CapitalProxy = "cost",
    surplus: SurplusBasis = "auto",
) -> pd.DataFrame:
    """One row per year with dispersion and price-fit statistics."""
    enriched = add_industry_ratios(panel, capital_proxy=capital_proxy, surplus=surplus)
    rows = []
    for year, group in enriched.groupby("year", sort=True):
        group = group.loc[
            (group["K_net"] > 0) & (group["GO"] > 0) & (group["PP"].notna())
        ].copy()
        if group.empty:
            continue
        basis = str(group["surplus_basis"].iloc[0])
        cost_column = "K_net" if basis == "net" else "K_gross"
        value_column = "S_net" if basis == "net" else "S_gross"
        weights = group[cost_column].to_numpy(dtype=float)
        rates = group["r"].to_numpy(dtype=float)
        aggregate_rate = float(group[value_column].sum() / group["M_proxy"].sum())
        aggregate_markup = float(
            group[value_column].sum() / group[cost_column].sum()
        )

        p10 = _weighted_quantile(rates, weights, 0.10)
        p90 = _weighted_quantile(rates, weights, 0.90)

        market = group.loc[group["is_market"]]
        market_n = int(len(market))
        if market_n >= 3:
            market_weights = market[cost_column].to_numpy(dtype=float)
            market_rates = market["r"].to_numpy(dtype=float)
            market_cv = _weighted_cv(market_rates, market_weights)
            market_mae = 100.0 * float(market["abs_gap_pct_PP_market"].mean())
            market_share = float((market["abs_gap_pct_PP_market"] <= 0.25).mean())
            market_rate = float(
                market[value_column].sum() / market["M_proxy"].sum()
            )
            market_corr = float(market["GO"].corr(market["PP_market"]))
            market_slope = _fit_log_slope(market["GO"], market["PP_market"])
            market_p10 = _weighted_quantile(market_rates, market_weights, 0.10)
            market_p90 = _weighted_quantile(market_rates, market_weights, 0.90)
        else:
            market_cv = market_mae = market_share = market_rate = float("nan")
            market_corr = market_slope = float("nan")
            market_p10 = market_p90 = float("nan")

        row = {
            "year": int(year),
            "n_industries": int(len(group)),
            "surplus_basis": str(group["surplus_basis"].iloc[0]),
            "capital_proxy": str(group["capital_proxy"].iloc[0]),
            "R_benchmark": aggregate_rate,
            "markup_cost": aggregate_markup,
            "rate_weighted_cv": _weighted_cv(rates, weights),
            "rate_p10": p10,
            "rate_p90": p90,
            "rate_p90_p10": p90 / p10 if p10 else float("nan"),
            "mae_pct_PP": 100.0 * float(group["abs_gap_pct_PP"].mean()),
            "rmse_pct_PP": 100.0
            * float(np.sqrt(np.mean(group["abs_gap_pct_PP"].dropna() ** 2))),
            "corr_PP": float(group["GO"].corr(group["PP"])),
            "slope_PP": _fit_log_slope(group["GO"], group["PP"]),
            "mae_pct_PP_V": 100.0 * float(group["abs_gap_pct_PP_V"].mean()),
            "rmse_pct_PP_V": 100.0
            * float(np.sqrt(np.mean(group["abs_gap_pct_PP_V"].dropna() ** 2))),
            "corr_PP_V": float(group["GO"].corr(group["PP_V"])),
            "slope_PP_V": _fit_log_slope(group["GO"], group["PP_V"]),
            "share_within_25pct_PP": float((group["abs_gap_pct_PP"] <= 0.25).mean()),
            "n_market": market_n,
            "R_benchmark_market": market_rate,
            "rate_p10_market": market_p10,
            "rate_p90_market": market_p90,
            "rate_p90_p10_market": (
                market_p90 / market_p10 if market_p10 else float("nan")
            ),
            "rate_weighted_cv_market": market_cv,
            "mae_pct_PP_long": 100.0 * float(group["abs_gap_pct_PP_long"].mean()),
            "corr_PP_long": float(group["GO"].corr(group["PP_long"])),
            "share_within_25pct_PP_long": float(
                (group["abs_gap_pct_PP_long"] <= 0.25).mean()
            ),
            "mae_pct_PP_long_market": (
                100.0 * float(market["abs_gap_pct_PP_long_market"].mean())
                if market_n >= 3
                else float("nan")
            ),
            "corr_PP_long_market": (
                float(market["GO"].corr(market["PP_long_market"]))
                if market_n >= 3
                else float("nan")
            ),
            "share_within_25pct_PP_long_market": (
                float((market["abs_gap_pct_PP_long_market"] <= 0.25).mean())
                if market_n >= 3
                else float("nan")
            ),
            "mae_pct_PP_market": market_mae,
            "corr_PP_market": market_corr,
            "slope_PP_market": market_slope,
            "share_within_25pct_PP_market": market_share,
            "total_GO": float(group["GO"].sum()),
            "total_N": float(group["N"].sum()),
            "total_N_net": float(group["N_net"].sum()),
            "total_S": float(group[value_column].sum()),
            "total_K": float(group[cost_column].sum()),
            "total_M": float(group["M_proxy"].sum()),
            "total_M_assets": (
                float(group["M_assets"].sum()) if "M_assets" in group.columns else np.nan
            ),
            "total_CFC": float(group["CFC"].sum()),
        }
        if "N_real" in group.columns:
            row["total_N_real"] = (
                float(group["N_real"].sum()) if group["N_real"].notna().any() else np.nan
            )
            row["total_GO_real"] = (
                float(group["GO_real"].sum()) if group["GO_real"].notna().any() else np.nan
            )
            row["total_S_real"] = (
                float(group["S_real"].sum()) if group["S_real"].notna().any() else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def industry_report(
    panel: pd.DataFrame,
    *,
    capital_proxy: CapitalProxy = "cost",
    surplus: SurplusBasis = "auto",
) -> dict:
    """Headline industry results, including the latest year and sample means."""
    summary = year_summary(panel, capital_proxy=capital_proxy, surplus=surplus)
    if summary.empty:
        raise ValueError("No industry observations")
    latest = summary.iloc[-1].to_dict()
    numeric = summary.select_dtypes(include="number")

    real_growth = {}
    if "total_N_real" in summary.columns:
        real = summary.dropna(subset=["total_N_real", "total_GO_real"])
        if len(real) > 1:
            years = real["year"].to_numpy(dtype=float)
            for column, label in (("total_N_real", "real_N"), ("total_GO_real", "real_GO")):
                first, last = float(real[column].iloc[0]), float(real[column].iloc[-1])
                n_years = max(1, int(years[-1] - years[0]))
                real_growth[f"{label}_growth"] = (last / first) ** (1.0 / n_years) - 1.0
            real_growth["real_start_year"] = int(years[0])
            real_growth["real_end_year"] = int(years[-1])
            real_growth["sector_deflator_last"] = (
                float(real["total_N_net"].iloc[-1]) / float(real["total_N_real"].iloc[-1])
            )

    return {
        "n_years": int(summary.shape[0]),
        "n_industries": int(panel["industry_code"].nunique()),
        "sample_start": int(summary["year"].min()),
        "sample_end": int(summary["year"].max()),
        "latest_year": int(latest["year"]),
        "surplus_basis": str(latest["surplus_basis"]),
        "capital_proxy": str(latest["capital_proxy"]),
        "latest": latest,
        "sample_means": {
            "rate_weighted_cv": float(numeric["rate_weighted_cv"].mean()),
            "mae_pct_PP": float(numeric["mae_pct_PP"].mean()),
            "mae_pct_PP_V": float(numeric["mae_pct_PP_V"].mean()),
            "mae_pct_PP_long": float(numeric["mae_pct_PP_long"].mean()),
            "corr_PP": float(numeric["corr_PP"].mean()),
            "corr_PP_market": float(numeric["corr_PP_market"].mean()),
            "corr_PP_long": float(numeric["corr_PP_long"].mean()),
            "corr_PP_long_market": float(numeric["corr_PP_long_market"].mean()),
            "slope_PP": float(numeric["slope_PP"].mean()),
            "share_within_25pct_PP": float(numeric["share_within_25pct_PP"].mean()),
            "share_within_25pct_PP_long": float(
                numeric["share_within_25pct_PP_long"].mean()
            ),
            "share_within_25pct_PP_long_market": float(
                numeric["share_within_25pct_PP_long_market"].mean()
            ),
            "rate_weighted_cv_market": float(numeric["rate_weighted_cv_market"].mean()),
            "rate_p90_p10_market": float(numeric["rate_p90_p10_market"].mean()),
            "mae_pct_PP_market": float(numeric["mae_pct_PP_market"].mean()),
            "mae_pct_PP_long_market": float(
                numeric["mae_pct_PP_long_market"].mean()
            ),
            "share_within_25pct_PP_market": float(
                numeric["share_within_25pct_PP_market"].mean()
            ),
            **real_growth,
        },
    }


def industry_reconciliation(
    panel: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    surplus: SurplusBasis = "auto",
) -> pd.DataFrame:
    """Reconcile industry totals with the macro accounts by year.

    ``accounts`` is the macro accounts frame indexed by year with columns
    ``P`` (GDP), ``C`` (CFC), ``N`` (NDP) and ``S`` (surplus-value).
    """
    enriched = add_industry_ratios(panel, surplus=surplus)
    # Industry tables are in millions of dollars; the macro accounts are in
    # billions. Convert before comparing.
    industry = (
        enriched.groupby("year")
        .agg(
            industry_N=("N", "sum"),
            industry_CFC=("CFC", "sum"),
            industry_N_net=("N_net", "sum"),
            industry_S_net=("S_net", "sum"),
        )
        .rename_axis("year")
        / 1000.0
    )
    macro = accounts.loc[:, ["P", "C", "N", "S"]].rename(
        columns={"P": "gdp", "C": "macro_CFC", "N": "ndp", "S": "macro_S"}
    )
    out = industry.join(macro, how="inner")
    out["gap_N"] = out["industry_N"] - out["gdp"]
    out["gap_CFC"] = out["industry_CFC"] - out["macro_CFC"]
    out["gap_N_net"] = out["industry_N_net"] - out["ndp"]
    out["gap_S_net"] = out["industry_S_net"] - out["macro_S"]
    return out.reset_index()


def proxy_sensitivity(
    panel: pd.DataFrame,
    *,
    surplus: SurplusBasis = "auto",
) -> pd.DataFrame:
    """Compare price-of-production fit across capital-stock proxies."""
    rows = []
    proxies = []
    if "M" in panel.columns:
        proxies.append("fixed_assets")
    proxies += ["cost", "output", "value_added"]
    for proxy in proxies:
        summary = year_summary(panel, capital_proxy=proxy, surplus=surplus)
        rows.append(
            {
                "capital_proxy": (
                    "fixed_assets+inventories" if proxy == "fixed_assets" else proxy
                ),
                "surplus_basis": str(summary["surplus_basis"].iloc[0]),
                "mae_pct_PP": float(summary["mae_pct_PP"].mean()),
                "mae_pct_PP_market": float(summary["mae_pct_PP_market"].mean()),
                "corr_PP": float(summary["corr_PP"].mean()),
                "corr_PP_market": float(summary["corr_PP_market"].mean()),
                "slope_PP": float(summary["slope_PP"].mean()),
                "share_within_25pct_PP": float(summary["share_within_25pct_PP"].mean()),
            }
        )
    return pd.DataFrame(rows)


def latest_dispersion(
    panel: pd.DataFrame,
    *,
    capital_proxy: CapitalProxy = "cost",
    surplus: SurplusBasis = "auto",
) -> pd.DataFrame:
    """Industry rows for the latest year, with benchmarks attached."""
    enriched = add_industry_ratios(panel, capital_proxy=capital_proxy, surplus=surplus)
    latest_year = int(enriched["year"].max())
    latest = enriched.loc[enriched["year"] == latest_year].copy()
    latest = latest.sort_values("r", ascending=False)
    columns = [
        "year",
        "industry_code",
        "industry_name",
        "C",
        "CFC",
        "V",
        "S_net",
        "K_net",
        "GO",
        "r",
        "M_proxy",
        "M_assets",
        "capital_source",
        "R_benchmark_market",
        "PP",
        "PP_market",
        "PP_long",
        "PP_long_market",
        "PP_V",
        "abs_gap_pct_PP",
        "abs_gap_pct_PP_market",
        "abs_gap_pct_PP_long",
        "abs_gap_pct_PP_long_market",
        "is_market",
    ]
    if "N_real" in latest.columns:
        columns += ["N_real", "GO_real", "r_real"]
    return latest.loc[:, [column for column in columns if column in latest.columns]]
