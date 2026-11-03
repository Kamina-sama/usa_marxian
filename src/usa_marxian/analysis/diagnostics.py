"""Formal diagnostics for the aggregate time-series claims.

The descriptive statistics in the main report are not enough to distinguish a
stable long-run relation from two unrelated trends. This module adds:

* unit-root tests (ADF, KPSS, Zivot-Andrews with a break);
* first-difference and trend-augmented LTV regressions;
* a pairs bootstrap for the LTV slope;
* Chow tests and a scan for the most likely break year.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.tsa.stattools import adfuller, kpss, zivot_andrews


def _clean(series: pd.Series) -> pd.Series:
    return series.replace([np.inf, -np.inf], np.nan).dropna()


def _value_column(accounts: pd.DataFrame, value_column: str) -> str:
    if value_column == "auto":
        return "new_value_real" if "new_value_real" in accounts.columns else "N"
    return value_column


def _ols_hac(y: np.ndarray, x: pd.DataFrame, lags: int | None = None):
    lags = lags if lags is not None else max(1, int(np.floor(len(y) ** 0.5)))
    return sm.OLS(y, x).fit(cov_type="HAC", cov_kwds={"maxlags": lags})


@dataclass
class UnitRootResult:
    test: str
    statistic: float
    p_value: float
    stationary_5pct: bool | None
    detail: str = ""


def _failed(test: str, exc: Exception) -> UnitRootResult:
    return UnitRootResult(
        test=test,
        statistic=float("nan"),
        p_value=float("nan"),
        stationary_5pct=None,
        detail=f"test failed: {type(exc).__name__}: {exc}",
    )


def adf_test(series: pd.Series, *, name: str = "series") -> UnitRootResult:
    values = _clean(series).to_numpy(dtype=float)
    try:
        statistic, p_value, *_ = adfuller(values, autolag="AIC", result_object=False)
    except (np.linalg.LinAlgError, ValueError) as exc:
        return _failed(f"ADF ({name})", exc)
    return UnitRootResult(
        test=f"ADF ({name})",
        statistic=float(statistic),
        p_value=float(p_value),
        stationary_5pct=bool(p_value < 0.05),
        detail="null: unit root; rejection means stationarity",
    )


def kpss_test(series: pd.Series, *, name: str = "series") -> UnitRootResult:
    values = _clean(series).to_numpy(dtype=float)
    try:
        statistic, p_value, lags, _crit = kpss(
            values, regression="c", nlags="auto", result_object=False
        )
    except (np.linalg.LinAlgError, ValueError) as exc:
        return _failed(f"KPSS ({name})", exc)
    return UnitRootResult(
        test=f"KPSS ({name})",
        statistic=float(statistic),
        p_value=float(p_value),
        stationary_5pct=bool(p_value > 0.05),
        detail=f"null: stationarity; lags={lags}",
    )


def zivot_andrews_test(series: pd.Series, *, name: str = "series") -> UnitRootResult:
    values = _clean(series).to_numpy(dtype=float)
    try:
        result = zivot_andrews(values, trim=0.15, autolag="AIC", regression="c")
    except (np.linalg.LinAlgError, ValueError):
        # Strongly trending series can make automatic lag selection singular.
        try:
            result = zivot_andrews(
                values, trim=0.15, maxlag=4, regression="c", autolag=None
            )
        except (np.linalg.LinAlgError, ValueError) as exc:
            return _failed(f"Zivot-Andrews ({name})", exc)
    statistic, p_value = float(result[0]), float(result[1])
    return UnitRootResult(
        test=f"Zivot-Andrews ({name})",
        statistic=statistic,
        p_value=p_value,
        stationary_5pct=bool(p_value < 0.05),
        detail="null: unit root with one endogenous break",
    )


def chow_test(
    accounts: pd.DataFrame,
    break_year: int,
    *,
    value_column: str = "auto",
) -> tuple[float, float]:
    """Chow test for a break in ``log N = a + b log L`` at ``break_year``."""
    column = _value_column(accounts, value_column)
    frame = accounts.loc[:, [column, "L"]].replace([np.inf, -np.inf], np.nan).dropna()
    y = np.log(frame[column].to_numpy(dtype=float))
    x = sm.add_constant(np.log(frame["L"].to_numpy(dtype=float)))
    n, k = x.shape

    pre = frame.index < break_year
    post = frame.index >= break_year
    if pre.sum() < k + 2 or post.sum() < k + 2:
        return float("nan"), float("nan")

    rss_full = sm.OLS(y, x).fit().ssr
    rss_pre = sm.OLS(y[pre], x[pre]).fit().ssr
    rss_post = sm.OLS(y[post], x[post]).fit().ssr
    denominator_df = n - 2 * k
    if denominator_df <= 0 or (rss_pre + rss_post) <= 0:
        return float("nan"), float("nan")

    f_stat = ((rss_full - (rss_pre + rss_post)) / k) / ((rss_pre + rss_post) / denominator_df)
    p_value = float(stats.f.sf(f_stat, k, denominator_df))
    return float(f_stat), p_value


def scan_break(
    accounts: pd.DataFrame,
    *,
    min_segment: int = 8,
    value_column: str = "auto",
) -> dict:
    """Scan candidate break years and return the largest Chow statistic."""
    column = _value_column(accounts, value_column)
    frame = accounts.loc[:, [column, "L"]].dropna()
    if len(frame) < 2 * min_segment + 2:
        return {"break_year": None, "f_stat": float("nan"), "p_value": float("nan")}
    candidates = frame.index[min_segment : len(frame) - min_segment]
    best = {"break_year": None, "f_stat": -np.inf, "p_value": float("nan")}
    for year in candidates:
        f_stat, p_value = chow_test(accounts, int(year), value_column=column)
        if np.isfinite(f_stat) and f_stat > best["f_stat"]:
            best = {"break_year": int(year), "f_stat": float(f_stat), "p_value": p_value}
    return best


def first_difference_ltv(accounts: pd.DataFrame, *, value_column: str = "auto") -> dict:
    """Regress ``d log N`` on ``d log L``; robust to stochastic trends."""
    column = _value_column(accounts, value_column)
    frame = accounts.loc[:, [column, "L"]].replace([np.inf, -np.inf], np.nan).dropna()
    y = np.log(frame[column]).diff().dropna()
    x = np.log(frame["L"]).diff().loc[y.index]
    exog = sm.add_constant(pd.DataFrame({"dlog_L": x.to_numpy()}, index=y.index))
    model = _ols_hac(y.to_numpy(dtype=float), exog)
    contrast = model.t_test("dlog_L = 1")
    return {
        "slope": float(model.params["dlog_L"]),
        "std_error": float(model.bse["dlog_L"]),
        "p_value_slope_one": float(np.ravel(contrast.pvalue)[0]),
        "r_squared": float(model.rsquared),
        "nobs": int(model.nobs),
    }


def trend_augmented_ltv(accounts: pd.DataFrame, *, value_column: str = "auto") -> dict:
    """Regress ``log N`` on ``log L`` and a linear trend."""
    column = _value_column(accounts, value_column)
    frame = accounts.loc[:, [column, "L"]].replace([np.inf, -np.inf], np.nan).dropna()
    y = np.log(frame[column].to_numpy(dtype=float))
    years = frame.index.to_numpy(dtype=float) - float(frame.index.min())
    exog = pd.DataFrame(
        {"log_L": np.log(frame["L"].to_numpy(dtype=float)), "trend": years},
        index=frame.index,
    )
    exog = sm.add_constant(exog)
    model = _ols_hac(y, exog)
    contrast = model.t_test("log_L = 1")
    return {
        "slope": float(model.params["log_L"]),
        "std_error": float(model.bse["log_L"]),
        "p_value_slope_one": float(np.ravel(contrast.pvalue)[0]),
        "trend_coefficient": float(model.params["trend"]),
        "r_squared": float(model.rsquared),
        "nobs": int(model.nobs),
    }


def bootstrap_ltv_slope(
    accounts: pd.DataFrame,
    *,
    n_boot: int = 2000,
    seed: int = 20261103,
    value_column: str = "auto",
) -> dict:
    """Pairs bootstrap for the log-log slope."""
    column = _value_column(accounts, value_column)
    frame = accounts.loc[:, [column, "L"]].replace([np.inf, -np.inf], np.nan).dropna()
    log_y = np.log(frame[column].to_numpy(dtype=float))
    log_x = np.log(frame["L"].to_numpy(dtype=float))
    n = len(frame)
    rng = np.random.default_rng(seed)
    slopes = np.empty(n_boot, dtype=float)

    for index in range(n_boot):
        draw = rng.integers(0, n, n)
        x = log_x[draw]
        if np.ptp(x) == 0:
            slopes[index] = np.nan
            continue
        design = np.column_stack([np.ones(n), x])
        slopes[index] = np.linalg.lstsq(design, log_y[draw], rcond=None)[0][1]

    slopes = slopes[np.isfinite(slopes)]
    return {
        "mean": float(slopes.mean()),
        "ci_low": float(np.percentile(slopes, 2.5)),
        "ci_high": float(np.percentile(slopes, 97.5)),
        "share_above_one": float((slopes > 1).mean()),
        "n_boot": int(slopes.size),
    }


def run_diagnostics(accounts: pd.DataFrame) -> dict:
    """Run the full diagnostic battery and return a nested dictionary."""
    melt_column = "melt_real" if "melt_real" in accounts.columns else "melt"
    melt = accounts[melt_column]
    profit = accounts["S"] / accounts["M"]
    rate_sv = accounts["S"] / accounts["V"]

    return {
        "melt": {
            "adf": asdict(adf_test(melt, name=melt_column)),
            "kpss": asdict(kpss_test(melt, name=melt_column)),
            "zivot_andrews": asdict(zivot_andrews_test(melt, name=melt_column)),
        },
        "rate_profit": {
            "adf": asdict(adf_test(profit, name="rate_profit")),
            "kpss": asdict(kpss_test(profit, name="rate_profit")),
            "zivot_andrews": asdict(zivot_andrews_test(profit, name="rate_profit")),
        },
        "rate_surplus_value": {
            "adf": asdict(adf_test(rate_sv, name="rate_surplus_value")),
            "kpss": asdict(kpss_test(rate_sv, name="rate_surplus_value")),
        },
        "ltv_first_difference": first_difference_ltv(accounts),
        "ltv_trend_augmented": trend_augmented_ltv(accounts),
        "ltv_bootstrap": bootstrap_ltv_slope(accounts),
        "ltv_chow_1973": dict(
            zip(("f_stat", "p_value"), chow_test(accounts, 1973), strict=True)
        ),
        "ltv_chow_2008": dict(
            zip(("f_stat", "p_value"), chow_test(accounts, 2008), strict=True)
        ),
        "ltv_break_scan": scan_break(accounts),
    }


def diagnostics_table(accounts: pd.DataFrame) -> pd.DataFrame:
    """Flatten ``run_diagnostics`` into a tidy table."""
    result = run_diagnostics(accounts)
    rows: list[dict] = []

    for series_name in ("melt", "rate_profit", "rate_surplus_value"):
        for test in result[series_name].values():
            rows.append(
                {
                    "block": series_name,
                    "test": test["test"],
                    "statistic": test["statistic"],
                    "p_value": test["p_value"],
                    "stationary_5pct": test["stationary_5pct"],
                    "detail": test["detail"],
                }
            )

    for block in ("ltv_first_difference", "ltv_trend_augmented"):
        values = result[block]
        rows.append(
            {
                "block": block,
                "test": "slope on log L",
                "statistic": values["slope"],
                "p_value": values["p_value_slope_one"],
                "stationary_5pct": None,
                "detail": f"n={values['nobs']}, R2={values['r_squared']:.3f}",
            }
        )

    bootstrap = result["ltv_bootstrap"]
    rows.append(
        {
            "block": "ltv_bootstrap",
            "test": "95% CI for slope",
            "statistic": bootstrap["mean"],
            "p_value": None,
            "stationary_5pct": None,
            "detail": (
                f"[{bootstrap['ci_low']:.3f}, {bootstrap['ci_high']:.3f}]; "
                f"share>1={bootstrap['share_above_one']:.3f}"
            ),
        }
    )

    for block in ("ltv_chow_1973", "ltv_chow_2008"):
        values = result[block]
        rows.append(
            {
                "block": block,
                "test": "Chow F",
                "statistic": values["f_stat"],
                "p_value": values["p_value"],
                "stationary_5pct": None,
                "detail": "break in log N = a + b log L",
            }
        )

    scan = result["ltv_break_scan"]
    rows.append(
        {
            "block": "ltv_break_scan",
            "test": "largest Chow F",
            "statistic": scan["f_stat"],
            "p_value": scan["p_value"],
            "stationary_5pct": None,
            "detail": f"candidate break year={scan['break_year']}",
        }
    )
    return pd.DataFrame(rows)
