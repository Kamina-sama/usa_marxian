"""The monetary expression of labour time (MELT).

Moseley's ``m`` in ``N = m L`` is the money value of one hour of abstract
labour. Empirically it is recovered residually as

    m_t = N_t / L_t

where ``N`` is net value added (net domestic product) and ``L`` is total hours
worked. This is an accounting identity for any given year, so the substantive
questions are about its *behaviour over time*:

* Is ``m`` stable, or does it trend? A stable ``m`` supports the simple
  labour theory of value at the aggregate level.
* Is ``N`` proportional to ``L``? A log-log slope of one is the LTV
  prediction. A slope below one implies labour productivity growth.
* Is ``m`` cointegrated with the price level? Under a commodity-money reading
  it should track the monetary base; under credit money it is an index.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import adfuller


@dataclass
class MeltSummary:
    """Descriptive statistics for the MELT over the sample."""

    nobs: int
    mean: float
    median: float
    std: float
    coefficient_of_variation: float
    minimum: float
    maximum: float
    trend_per_year: float
    trend_p_value: float
    adf_stat: float
    adf_p_value: float
    base_year: int | None = None
    base_value: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class MeltTrend:
    """OLS trend of the (log) MELT."""

    slope_per_year: float
    std_error: float
    p_value: float
    r_squared: float
    nobs: int


def melt_trend(accounts: pd.DataFrame, *, column: str = "melt") -> MeltTrend:
    series = accounts[column].replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 3:
        raise ValueError("Need at least three observations to estimate a trend")
    years = series.index.to_numpy(dtype=float)
    y = np.log(series.to_numpy(dtype=float))
    model = sm.OLS(y, sm.add_constant(years)).fit(
        cov_type="HAC", cov_kwds={"maxlags": max(1, int(len(y) ** 0.5))}
    )
    return MeltTrend(
        slope_per_year=float(model.params[1]),
        std_error=float(model.bse[1]),
        p_value=float(model.pvalues[1]),
        r_squared=float(model.rsquared),
        nobs=int(model.nobs),
    )


def melt_summary(
    accounts: pd.DataFrame,
    *,
    column: str = "melt",
    base_year: int | None = None,
) -> MeltSummary:
    """Summarise the level and stability of the MELT."""
    series = accounts[column].replace([np.inf, -np.inf], np.nan).dropna()
    if series.empty:
        raise ValueError(f"No observations in column {column!r}")

    trend = melt_trend(accounts, column=column)
    adf_stat, adf_p, *_ = adfuller(series.to_numpy(), autolag="AIC", result_object=False)

    base_value = None
    if base_year is not None and base_year in series.index:
        base_value = float(series.loc[base_year])

    return MeltSummary(
        nobs=int(series.size),
        mean=float(series.mean()),
        median=float(series.median()),
        std=float(series.std(ddof=1)),
        coefficient_of_variation=float(series.std(ddof=1) / series.mean()),
        minimum=float(series.min()),
        maximum=float(series.max()),
        trend_per_year=trend.slope_per_year,
        trend_p_value=trend.p_value,
        adf_stat=float(adf_stat),
        adf_p_value=float(adf_p),
        base_year=base_year,
        base_value=base_value,
    )


def melt_index(accounts: pd.DataFrame, base_year: int, *, column: str = "melt") -> pd.Series:
    """Re-base the MELT to 100 in ``base_year``."""
    series = accounts[column].dropna()
    if base_year not in series.index:
        raise KeyError(f"Base year {base_year} not in sample")
    return 100.0 * series / series.loc[base_year]
