"""Gravitation and predictive tests for prices of production.

What "center of gravitation" means empirically
----------------------------------------------
Moseley's prices of production are gross annual industry revenues. The observed
counterpart is BEA gross output. Define the deviation

    d_it = log(GO_it / PP_it)

If PP is a center of gravitation, three things should hold:

1. deviations are temporary, not a permanent industry characteristic;
2. when GO is above PP (d > 0), future GO growth is lower, and when GO is
   below PP (d < 0), future GO growth is higher;
3. PP contains information about future GO beyond a naive random-walk forecast.

The tests below correspond to those three claims. They are deliberately
separate: a stationary deviation is necessary but not sufficient for
gravitation, and a good contemporaneous fit says nothing about forecasting.

Panel error correction
----------------------
    Δ log GO_it = α_i + γ_t + β d_i,t-1 + ε_it

β < 0 means GO moves toward PP. The mirror regression on Δ log PP shows whether
PP moves toward GO instead. A negative β on Δd alone is not enough; it can be
driven entirely by PP adjusting to GO.

Forecasts
---------
One-, three- and five-year-ahead forecasts of GO are compared with:

* naive: GO_t
* PP: PP_t
* AR(1): industry fixed effect + log GO_t
* ECM: industry fixed effect + log GO_t + d_t

Out-of-sample windows are expanding. Lower log RMSE is better.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from linearmodels.panel import PanelOLS
from scipy import stats
from statsmodels.tsa.stattools import adfuller, coint

from ..model.industries import CapitalProxy, SurplusBasis, add_industry_ratios


@dataclass
class AdjustmentResult:
    dependent: str
    beta: float
    std_error: float
    t_stat: float
    p_value: float
    half_life_years: float | None
    nobs: int
    r_squared_within: float

    def to_dict(self) -> dict:
        return asdict(self)


def prepare_gravitation_panel(
    panel: pd.DataFrame,
    *,
    capital_proxy: CapitalProxy = "fixed_assets",
    surplus: SurplusBasis = "auto",
    market_only: bool = True,
) -> pd.DataFrame:
    """Build the industry deviation panel used by all tests.

    Government units and housing are excluded by default: their "prices" are
    not market prices, and their capital stocks fall back to the cost proxy.
    """
    frame = add_industry_ratios(panel, capital_proxy=capital_proxy, surplus=surplus)
    if market_only and "is_market" in frame.columns:
        frame = frame.loc[frame["is_market"]].copy()
    frame = frame.loc[(frame["GO"] > 0) & (frame["PP"] > 0)].copy()
    frame = frame.sort_values(["industry_code", "year"])

    frame["d"] = np.log(frame["GO"] / frame["PP"])
    frame["profit_gap"] = frame["r"] - frame["R_benchmark"]
    frame["log_GO"] = np.log(frame["GO"])
    frame["log_PP"] = np.log(frame["PP"])

    grouped = frame.groupby("industry_code", group_keys=False)
    frame["d_lag"] = grouped["d"].shift(1)
    frame["log_GO_lag"] = grouped["log_GO"].shift(1)
    frame["log_PP_lag"] = grouped["log_PP"].shift(1)
    frame["delta_log_GO"] = grouped["log_GO"].diff()
    frame["delta_log_PP"] = grouped["log_PP"].diff()
    frame["delta_d"] = grouped["d"].diff()

    for horizon in (1, 3, 5):
        frame[f"target_GO_{horizon}"] = grouped["GO"].shift(-horizon)

    return frame


def _half_life(beta: float) -> float | None:
    """Half-life for an error-correction coefficient (beta < 0)."""
    if beta is None or not np.isfinite(beta) or beta >= 0 or beta <= -1:
        return None
    return float(np.log(0.5) / np.log(1.0 + beta))


def _persistence_half_life(beta: float) -> float | None:
    """Half-life for an AR(1) persistence coefficient (0 < beta < 1)."""
    if beta is None or not np.isfinite(beta) or beta <= 0 or beta >= 1:
        return None
    return float(np.log(0.5) / np.log(beta))


def _panel_fit(
    frame: pd.DataFrame,
    dependent: str,
    regressors: list[str],
) -> AdjustmentResult:
    subset = frame.dropna(subset=[dependent, *regressors]).set_index(
        ["industry_code", "year"]
    )
    model = PanelOLS(
        subset[dependent],
        subset[regressors],
        entity_effects=True,
        time_effects=True,
    )
    result = model.fit(cov_type="clustered", cluster_entity=True)
    beta = float(result.params[regressors[0]])
    return AdjustmentResult(
        dependent=dependent,
        beta=beta,
        std_error=float(result.std_errors[regressors[0]]),
        t_stat=float(result.tstats[regressors[0]]),
        p_value=float(result.pvalues[regressors[0]]),
        half_life_years=_half_life(beta),
        nobs=int(result.nobs),
        r_squared_within=float(result.rsquared_within),
    )


def deviation_summary(frame: pd.DataFrame) -> dict:
    """Level, dispersion and persistence of the deviation series."""
    data = frame.dropna(subset=["d"]).copy()
    by_year = (
        data.groupby("year")
        .agg(
            n=("d", "size"),
            mean_d=("d", "mean"),
            mean_abs_d=("d", lambda s: float(s.abs().mean())),
            share_within_10pct=("d", lambda s: float((s.abs() <= 0.10).mean())),
            share_within_25pct=("d", lambda s: float((s.abs() <= 0.25).mean())),
        )
        .reset_index()
    )

    # Mean absolute deviation weighted by gross output.
    weights = data["GO"].to_numpy(dtype=float)
    abs_d = data["d"].abs().to_numpy(dtype=float)
    weighted_mean_abs = float(np.average(abs_d, weights=weights))

    ar1 = _panel_fit(frame, "d", ["d_lag"])
    trend = sm.OLS(
        by_year["mean_abs_d"].to_numpy(),
        sm.add_constant(by_year["year"].to_numpy(dtype=float)),
    ).fit()

    return {
        "n_obs": int(data["d"].size),
        "n_industries": int(data["industry_code"].nunique()),
        "mean_d": float(data["d"].mean()),
        "std_d": float(data["d"].std(ddof=1)),
        "mean_abs_d": float(abs_d.mean()),
        "weighted_mean_abs_d": weighted_mean_abs,
        "median_abs_d": float(np.median(abs_d)),
        "p90_abs_d": float(np.percentile(abs_d, 90)),
        "share_within_10pct": float((abs_d <= 0.10).mean()),
        "share_within_25pct": float((abs_d <= 0.25).mean()),
        "autocorrelation_lag1": float(data["d"].corr(data["d_lag"])),
        "ar1_beta": ar1.beta,
        "ar1_half_life_years": _persistence_half_life(ar1.beta),
        "trend_mean_abs_per_year": float(trend.params[1]),
        "trend_p_value": float(trend.pvalues[1]),
        "by_year": by_year,
    }


def panel_unit_root(frame: pd.DataFrame, *, min_obs: int = 12) -> dict:
    """Fisher-type panel ADF test on the deviation series."""
    p_values = []
    rejected = 0
    used = 0
    for _, group in frame.groupby("industry_code"):
        series = group["d"].dropna()
        if len(series) < min_obs:
            continue
        used += 1
        try:
            p_value = adfuller(
                series.to_numpy(dtype=float),
                maxlag=1,
                regression="c",
                autolag=None,
                result_object=False,
            )[1]
        except (ValueError, np.linalg.LinAlgError):
            continue
        p_values.append(float(p_value))
        rejected += int(p_value < 0.05)

    p_values = np.clip(np.asarray(p_values, dtype=float), 1e-12, 1.0)
    if p_values.size == 0:
        return {
            "n_industries": 0,
            "share_rejecting_5pct": float("nan"),
            "median_p_value": float("nan"),
            "fisher_stat": float("nan"),
            "fisher_p_value": float("nan"),
        }

    fisher_stat = float(-2.0 * np.log(p_values).sum())
    return {
        "n_industries": int(p_values.size),
        "n_series_used": int(used),
        "share_rejecting_5pct": float(rejected / p_values.size),
        "median_p_value": float(np.median(p_values)),
        "fisher_stat": fisher_stat,
        "fisher_p_value": float(stats.chi2.sf(fisher_stat, 2 * p_values.size)),
    }


def cointegration_test(frame: pd.DataFrame, *, min_obs: int = 15) -> dict:
    """Per-industry Engle-Granger test between log GO and log PP."""
    p_values = []
    for _, group in frame.groupby("industry_code"):
        data = group[["log_GO", "log_PP"]].dropna()
        if len(data) < min_obs:
            continue
        try:
            _, p_value, _ = coint(
                data["log_GO"].to_numpy(dtype=float),
                data["log_PP"].to_numpy(dtype=float),
                trend="c",
                maxlag=1,
            )
        except (ValueError, np.linalg.LinAlgError):
            continue
        p_values.append(float(p_value))

    p_values = np.clip(np.asarray(p_values, dtype=float), 1e-12, 1.0)
    if p_values.size == 0:
        return {
            "n_industries": 0,
            "share_rejecting_5pct": float("nan"),
            "median_p_value": float("nan"),
            "fisher_stat": float("nan"),
            "fisher_p_value": float("nan"),
        }
    fisher_stat = float(-2.0 * np.log(p_values).sum())
    return {
        "n_industries": int(p_values.size),
        "share_rejecting_5pct": float((p_values < 0.05).mean()),
        "median_p_value": float(np.median(p_values)),
        "fisher_stat": fisher_stat,
        "fisher_p_value": float(stats.chi2.sf(fisher_stat, 2 * p_values.size)),
    }


def error_correction(frame: pd.DataFrame) -> dict:
    """Panel error-correction models in both directions."""
    models = {
        "delta_log_GO": _panel_fit(frame, "delta_log_GO", ["d_lag"]),
        "delta_log_PP": _panel_fit(frame, "delta_log_PP", ["d_lag"]),
        "delta_d": _panel_fit(frame, "delta_d", ["d_lag"]),
    }
    return {name: result.to_dict() for name, result in models.items()}


def _fit_forecast_model(
    train: pd.DataFrame,
    test: pd.DataFrame,
    predictors: list[str],
    target_column: str,
) -> np.ndarray:
    """Fit a pooled panel model with industry dummies and predict levels."""
    dummy_columns = sorted(train["industry_code"].unique())[1:]
    train_dummies = pd.get_dummies(
        train["industry_code"], drop_first=True, dtype=float
    ).reindex(columns=dummy_columns, fill_value=0.0)
    test_dummies = pd.get_dummies(
        test["industry_code"], drop_first=True, dtype=float
    ).reindex(columns=dummy_columns, fill_value=0.0)

    x_train = pd.concat(
        [train[predictors].reset_index(drop=True), train_dummies.reset_index(drop=True)],
        axis=1,
    )
    x_train = sm.add_constant(x_train, has_constant="add")
    y_train = np.log(train[target_column].to_numpy(dtype=float))
    model = sm.OLS(y_train, x_train).fit()

    x_test = pd.concat(
        [test[predictors].reset_index(drop=True), test_dummies.reset_index(drop=True)],
        axis=1,
    )
    x_test = sm.add_constant(x_test, has_constant="add").reindex(
        columns=x_train.columns, fill_value=0.0
    )
    return np.exp(model.predict(x_test))


def _forecast_metrics(actual: np.ndarray, predicted: np.ndarray, model: str, horizon: int) -> dict:
    valid = (actual > 0) & (predicted > 0) & np.isfinite(actual) & np.isfinite(predicted)
    actual = actual[valid]
    predicted = predicted[valid]
    log_error = np.log(actual) - np.log(predicted)
    return {
        "horizon": horizon,
        "model": model,
        "n": int(actual.size),
        "rmse_log": float(np.sqrt(np.mean(log_error**2))),
        "mae_log": float(np.mean(np.abs(log_error))),
        "mape_pct": float(100.0 * np.mean(np.abs(actual - predicted) / actual)),
        "bias_log": float(np.mean(log_error)),
    }


def _bootstrap_rmse_difference(
    errors_a: np.ndarray,
    errors_b: np.ndarray,
    *,
    n_boot: int = 1000,
    seed: int = 20261103,
) -> dict:
    rng = np.random.default_rng(seed)
    n = len(errors_a)
    differences = np.empty(n_boot, dtype=float)
    for index in range(n_boot):
        draw = rng.integers(0, n, n)
        rmse_a = np.sqrt(np.mean(errors_a[draw] ** 2))
        rmse_b = np.sqrt(np.mean(errors_b[draw] ** 2))
        differences[index] = rmse_a - rmse_b
    return {
        "delta_rmse": float(
            np.sqrt(np.mean(errors_a**2)) - np.sqrt(np.mean(errors_b**2))
        ),
        "ci_low": float(np.percentile(differences, 2.5)),
        "ci_high": float(np.percentile(differences, 97.5)),
        "share_a_better": float((differences < 0).mean()),
        "n_boot": int(n_boot),
    }


def forecast_evaluation(
    frame: pd.DataFrame,
    *,
    start_year: int = 2008,
    horizons: Iterable[int] = (1, 3, 5),
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Expanding-window out-of-sample forecasts of gross output."""
    forecast_rows: list[pd.DataFrame] = []
    comparison_rows: list[dict] = []

    for horizon in horizons:
        target = f"target_GO_{horizon}"
        data = frame.dropna(subset=[target, "log_GO", "d"]).copy()
        years = sorted(data["year"].unique())
        if len(years) <= 2:
            continue

        for origin_year in range(start_year, max(years) + 1):
            train = data.loc[data["year"] < origin_year]
            test = data.loc[data["year"] == origin_year]
            if train.empty or test.empty or train[target].notna().sum() < 50:
                continue

            actual = test[target].to_numpy(dtype=float)
            predictions = {
                "naive": test["GO"].to_numpy(dtype=float),
                "pp": test["PP"].to_numpy(dtype=float),
            }
            predictions["ar1"] = _fit_forecast_model(
                train, test, ["log_GO"], target
            )
            predictions["ecm"] = _fit_forecast_model(
                train, test, ["log_GO", "d"], target
            )

            block = pd.DataFrame(
                {
                    "horizon": horizon,
                    "origin_year": int(origin_year),
                    "target_year": int(origin_year + horizon),
                    "industry_code": test["industry_code"].to_numpy(),
                    "actual": actual,
                    **{f"pred_{name}": values for name, values in predictions.items()},
                }
            )
            forecast_rows.append(block)

    if not forecast_rows:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    forecasts = pd.concat(forecast_rows, ignore_index=True)

    # Metrics are computed on the pooled out-of-sample errors, not averaged
    # across yearly RMSEs.
    metric_rows = []
    for horizon, group in forecasts.groupby("horizon"):
        for model in ("naive", "pp", "ar1", "ecm"):
            metric_rows.append(
                _forecast_metrics(
                    group["actual"].to_numpy(dtype=float),
                    group[f"pred_{model}"].to_numpy(dtype=float),
                    model,
                    int(horizon),
                )
            )
    metrics = pd.DataFrame(metric_rows).sort_values(["horizon", "rmse_log"])

    for horizon, group in forecasts.groupby("horizon"):
        actual = group["actual"].to_numpy(dtype=float)
        valid = actual > 0
        for model in ("naive", "pp", "ar1", "ecm"):
            valid &= (
                group[f"pred_{model}"].to_numpy(dtype=float) > 0
            ) & np.isfinite(group[f"pred_{model}"].to_numpy(dtype=float))
        valid &= np.isfinite(actual)
        if valid.sum() < 10:
            continue

        errors = {
            model: np.log(actual[valid])
            - np.log(group[f"pred_{model}"].to_numpy(dtype=float)[valid])
            for model in ("naive", "pp", "ar1", "ecm")
        }
        for first, second in (("pp", "naive"), ("ecm", "ar1"), ("pp", "ar1")):
            comparison = _bootstrap_rmse_difference(errors[first], errors[second])
            comparison.update(
                {"horizon": int(horizon), "model_a": first, "model_b": second}
            )
            comparison_rows.append(comparison)

    comparisons = pd.DataFrame(comparison_rows)
    return forecasts, metrics, comparisons


def _verdict(summary: dict, unit_root: dict, adjustment: dict) -> str:
    go = adjustment["delta_log_GO"]
    pp = adjustment["delta_log_PP"]
    parts = []

    if summary["autocorrelation_lag1"] > 0.9:
        parts.append(
            "Deviations are highly persistent "
            f"(autocorrelation {summary['autocorrelation_lag1']:.2f})."
        )
    else:
        parts.append(
            "Deviations show moderate persistence "
            f"(autocorrelation {summary['autocorrelation_lag1']:.2f})."
        )

    if go["beta"] < 0 and go["p_value"] < 0.05:
        parts.append(
            "Market gross output adjusts toward prices of production "
            f"(beta = {go['beta']:.3f}, p = {go['p_value']:.3f})."
        )
    else:
        parts.append(
            "Market gross output does not adjust toward prices of production "
            f"(beta = {go['beta']:.3f}, p = {go['p_value']:.3f})."
        )

    if pp["beta"] > 0 and pp["p_value"] < 0.05:
        parts.append(
            "Prices of production instead adjust toward market gross output "
            f"(beta = {pp['beta']:.3f}, p = {pp['p_value']:.3f})."
        )

    if unit_root["fisher_p_value"] < 0.05:
        parts.append(
            "The panel ADF rejects a unit root "
            f"(Fisher p = {unit_root['fisher_p_value']:.4f}), although only "
            f"{unit_root['share_rejecting_5pct']:.0%} of industries reject "
            "individually."
        )
    else:
        parts.append(
            "The panel ADF does not reject a unit root in the deviations "
            f"(Fisher p = {unit_root['fisher_p_value']:.4f})."
        )

    return " ".join(parts)


def run_gravitation(
    panel: pd.DataFrame,
    *,
    capital_proxy: CapitalProxy = "fixed_assets",
    market_only: bool = True,
    start_year: int = 2008,
    horizons: Iterable[int] = (1, 3, 5),
) -> dict:
    """Run the full gravitation battery and return tables plus a verdict."""
    frame = prepare_gravitation_panel(
        panel, capital_proxy=capital_proxy, market_only=market_only
    )
    summary = deviation_summary(frame)
    unit_root = panel_unit_root(frame)
    cointegration = cointegration_test(frame)
    adjustment = error_correction(frame)
    forecasts, metrics, comparisons = forecast_evaluation(
        frame, start_year=start_year, horizons=horizons
    )

    return {
        "sample": {
            "start_year": int(frame["year"].min()),
            "end_year": int(frame["year"].max()),
            "n_industries": int(frame["industry_code"].nunique()),
            "n_obs": int(frame["d"].notna().sum()),
        },
        "deviation": summary,
        "unit_root": unit_root,
        "cointegration": cointegration,
        "error_correction": adjustment,
        "forecast_metrics": metrics,
        "forecast_comparisons": comparisons,
        "forecasts": forecasts,
        "verdict": _verdict(summary, unit_root, adjustment),
    }
