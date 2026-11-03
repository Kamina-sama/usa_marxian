"""Aggregate tests of the labour theory of value.

The central testable implication of the macro-monetary reading is that new
value is proportional to labour time:

    N_t = m * L_t

Taking logs, ``log N = log m + log L``. With a constant MELT the slope on
``log L`` is one. A slope greater than one means the MELT rises with the
scale of employment; a slope below one means it falls. The level of the slope
is therefore informative either way, and the unit-slope restriction is a
sharp test of the simple LTV.

These are time-series tests on aggregate data. They cannot identify
*individual* labour values; that requires input-output data and is left to
the industry-level module on the roadmap.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.tsa.stattools import coint


@dataclass
class LTVResult:
    """Estimates from ``log N = a + b log L``."""

    value_column: str
    slope: float
    std_error: float
    ci_low: float
    ci_high: float
    t_stat_slope_one: float
    p_value_slope_one: float
    r_squared: float
    nobs: int
    sample_start: int
    sample_end: int
    coint_t: float
    coint_p: float
    coint_critical_5pct: float

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_ltv(
    accounts: pd.DataFrame,
    *,
    start: int | None = None,
    end: int | None = None,
    maxlags: int | None = None,
    value_column: str = "auto",
) -> LTVResult:
    """Estimate the aggregate value-labour relation with HAC standard errors.

    By default the dependent variable is real new value (``new_value_real``)
    when available. Using nominal new value would conflate the labour theory
    of value with inflation: the nominal MELT rises with the price level, so
    the slope would be far above one for monetary reasons alone.

    ``coint`` is the Engle-Granger statistic for the null of no cointegration
    between ``log N`` and ``log L``. Rejecting the null supports a stable
    long-run relation; it does not by itself prove the LTV.
    """
    if value_column == "auto":
        value_column = "new_value_real" if "new_value_real" in accounts.columns else "N"
    frame = accounts.loc[:, [value_column, "L"]]
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if start is not None:
        frame = frame.loc[frame.index >= start]
    if end is not None:
        frame = frame.loc[frame.index <= end]
    if len(frame) < 10:
        raise ValueError("Need at least 10 annual observations")

    y = np.log(frame[value_column].to_numpy(dtype=float))
    x = np.log(frame["L"].to_numpy(dtype=float))
    exog = pd.DataFrame({"log_L": x}, index=frame.index)
    exog = sm.add_constant(exog)

    lags = maxlags if maxlags is not None else max(1, int(np.floor(len(frame) ** 0.5)))
    model = sm.OLS(y, exog).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    contrast = model.t_test("log_L = 1")

    ci = model.conf_int().loc["log_L"]
    coint_t, coint_p, coint_crit = coint(y, x, trend="c", maxlag=lags)
    # statsmodels <0.14 returns a dict keyed by "1%", "5%", "10%"; newer
    # versions return a three-element array in the same order.
    if isinstance(coint_crit, dict):
        coint_crit_5 = float(coint_crit["5%"])
    else:
        coint_crit_5 = float(np.ravel(np.asarray(coint_crit))[1])

    return LTVResult(
        value_column=value_column,
        slope=float(model.params["log_L"]),
        std_error=float(model.bse["log_L"]),
        ci_low=float(ci.iloc[0]),
        ci_high=float(ci.iloc[1]),
        t_stat_slope_one=float(np.ravel(contrast.tvalue)[0]),
        p_value_slope_one=float(np.ravel(contrast.pvalue)[0]),
        r_squared=float(model.rsquared),
        nobs=int(model.nobs),
        sample_start=int(frame.index.min()),
        sample_end=int(frame.index.max()),
        coint_t=float(coint_t),
        coint_p=float(coint_p),
        coint_critical_5pct=coint_crit_5,
    )
