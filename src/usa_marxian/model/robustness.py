"""Alternative specifications and robustness tables.

Each specification changes one measurement assumption at a time, rebuilds the
accounts, and reports the same headline statistics. The point is not to find
the "right" number but to see which conclusions survive reasonable changes in
the proxies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace

import numpy as np
import pandas as pd

from ..analysis.ltv import estimate_ltv
from ..data.build import (
    CapitalStock,
    MeltNumerator,
    ValueAdded,
    build_accounts,
    validate_accounts,
)
from .equalities import profit_rate_summary
from .melt import melt_summary


@dataclass(frozen=True)
class Spec:
    """One combination of measurement choices."""

    name: str
    value_added: ValueAdded = "ndp"
    capital_stock: CapitalStock = "nonresidential"
    include_inventories: bool = True
    hours_method: str = "indexed"
    melt_numerator: MeltNumerator = "ndp"


DEFAULT_SPECS: tuple[Spec, ...] = (
    Spec("baseline"),
    Spec("no_inventories", include_inventories=False),
    Spec("private_capital", capital_stock="private_total"),
    Spec("nnp", value_added="nnp", melt_numerator="nnp"),
    Spec("nnp_factor", value_added="nnp_factor", melt_numerator="nnp_factor"),
    Spec("hours_nipa", hours_method="nipa"),
    Spec("hours_ces", hours_method="ces"),
    Spec("melt_gdp", melt_numerator="gdp"),
)


def _property_ratio(accounts: pd.DataFrame) -> float:
    series = accounts["profit_check_ratio"].replace([np.inf, -np.inf], np.nan).dropna()
    return float(series.mean()) if not series.empty else float("nan")


def run_specification(
    raw: pd.DataFrame,
    settings,
    spec: Spec,
) -> dict:
    """Build one specification and return its headline statistics."""
    accounts = build_accounts(
        raw,
        settings,
        value_added=spec.value_added,
        capital_stock=spec.capital_stock,
        include_inventories=spec.include_inventories,
        melt_numerator=spec.melt_numerator,
        hours_method=spec.hours_method,
    )
    validate_accounts(accounts)

    melt = melt_summary(accounts, base_year=settings.base_year)
    ltv = estimate_ltv(accounts)
    profit = profit_rate_summary(accounts)

    record = asdict(spec)
    record.update(
        {
            "n_years": int(accounts.shape[0]),
            "sample_start": int(accounts.index.min()),
            "sample_end": int(accounts.index.max()),
            "melt_mean": melt.mean,
            "melt_cv": melt.coefficient_of_variation,
            "melt_trend": melt.trend_per_year,
            "melt_trend_p": melt.trend_p_value,
            "ltv_slope": ltv.slope,
            "ltv_ci_low": ltv.ci_low,
            "ltv_ci_high": ltv.ci_high,
            "ltv_p_unit": ltv.p_value_slope_one,
            "rate_profit_first": profit["first_value"],
            "rate_profit_last": profit["last_value"],
            "rate_profit_mean": profit["mean"],
            "rate_surplus_value_last": float(
                accounts["rate_surplus_value"].dropna().iloc[-1]
            ),
            "composition_last": float(accounts["composition"].dropna().iloc[-1]),
            "property_check_mean_ratio": _property_ratio(accounts),
            "error": None,
        }
    )
    return record


def run_specifications(
    raw: pd.DataFrame,
    settings,
    specs: tuple[Spec, ...] | list[Spec] | None = None,
) -> pd.DataFrame:
    """Run every specification; failures are recorded rather than raised."""
    specs = specs or DEFAULT_SPECS
    records = []
    for spec in specs:
        try:
            records.append(run_specification(raw, settings, spec))
        except Exception as exc:  # keep the table usable when one proxy is absent
            record = asdict(spec)
            record.update({"error": f"{type(exc).__name__}: {exc}"})
            records.append(record)
    return pd.DataFrame(records)


def specification_ranges(table: pd.DataFrame) -> pd.DataFrame:
    """Min/max of each headline metric across successful specifications."""
    metrics = [
        "melt_mean",
        "melt_trend",
        "ltv_slope",
        "rate_profit_first",
        "rate_profit_last",
        "rate_profit_mean",
        "rate_surplus_value_last",
        "composition_last",
        "property_check_mean_ratio",
    ]
    rows = []
    valid = table.loc[table["error"].isna()] if "error" in table else table
    for metric in metrics:
        if metric not in valid.columns:
            continue
        series = pd.to_numeric(valid[metric], errors="coerce").dropna()
        if series.empty:
            continue
        rows.append(
            {
                "metric": metric,
                "min": float(series.min()),
                "max": float(series.max()),
                "mean": float(series.mean()),
                "n_specs": int(series.size),
            }
        )
    return pd.DataFrame(rows)


def with_spec(base: Spec, **changes) -> Spec:
    """Convenience for interactive work: ``with_spec(DEFAULT_SPECS[0], value_added='nnp')``."""
    return replace(base, **changes)
