"""Assemble the raw panel and derive the Marxian accounts.

Accounting layers
-----------------
The default empirical mapping is the **net value-added layer**:

    P = GDP                    total value-price
    C = CFC                    consumed constant capital (depreciation only)
    N = GDP - CFC = NDP        new value produced in the year
    V = compensation           variable capital (annual wage bill)
    S = N - V                  surplus-value
    K = C + V                  cost price

This mapping reproduces Moseley's identities exactly:

    P = C + N                  (his eq. 3)
    S = P - K = N - V          (his eqs. 1, 6, 7)

A gross-output layer would replace ``P`` with gross output and ``C`` with
intermediate consumption plus CFC. The surplus-value ``S = N - V`` is the same
either way, because constant capital cancels; that is Moseley's "dual
significance of constant capital".
"""

from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from ..config import ProjectConfig, SeriesSpec
from .cache import load_raw_series

CORE_ROLES = [
    "gdp",
    "cfc",
    "gdp_deflator",
    "compensation",
    "net_operating_surplus",
    "capital_stock",
]


def roles_for_settings(settings) -> list[str]:
    roles = list(CORE_ROLES)
    if settings.include_inventories:
        roles.append("inventories")
    if settings.hours_method == "ces":
        roles += ["employment", "weekly_hours"]
    elif settings.hours_method == "nipa":
        roles.append("hours_nipa")
    elif settings.hours_method == "indexed":
        roles += ["hours_index", "hours_nipa"]
    return roles


def annualize(frame: pd.DataFrame, spec: SeriesSpec) -> pd.Series:
    """Collapse a raw series to an annual series indexed by year."""
    series = frame.set_index("date")["value"].astype(float) * spec.scale
    series = series.dropna()
    if series.empty:
        raise ValueError(f"Empty series after scaling: {spec.series_id}")

    if spec.frequency == "annual":
        annual = series.groupby(series.index.year).last()
    else:
        resampled = series.resample("YE").agg(spec.agg)
        annual = pd.Series(resampled.to_numpy(), index=resampled.index.year)

    annual.index.name = "year"
    return annual


def _load_role(
    config: ProjectConfig,
    role: str,
    *,
    start_year: int,
    end_year: int | None,
) -> pd.Series | None:
    spec = config.catalog.get(role)
    if spec is None:
        if role in CORE_ROLES:
            raise KeyError(f"Required series role missing from catalog: {role}")
        return None
    try:
        frame = load_raw_series(
            spec,
            config.settings.raw_dir,
            max_age_days=config.settings.cache_max_age_days,
            start_year=start_year,
            end_year=end_year,
            fred_api_key=config.api.fred_api_key,
            bls_api_key=config.api.bls_api_key,
            bea_api_key=config.api.bea_api_key,
        )
    except Exception:
        if spec.optional:
            import warnings

            warnings.warn(
                f"Optional series unavailable, skipping: {role} ({spec.series_id})",
                stacklevel=2,
            )
            return None
        raise
    return annualize(frame, spec)


def build_raw_panel(config: ProjectConfig, *, start_year: int | None = None) -> pd.DataFrame:
    """Download (or load cached) raw series and align them by year."""
    settings = config.settings
    start = start_year or settings.start_year
    end = settings.end_year

    series: dict[str, pd.Series] = {}
    for role in roles_for_settings(settings):
        values = _load_role(config, role, start_year=start, end_year=end)
        if values is not None:
            values.name = role
            series[role] = values

    panel = pd.concat(series.values(), axis=1).sort_index()
    panel = panel.loc[(panel.index >= start)]
    if end is not None:
        panel = panel.loc[panel.index <= end]
    return panel


def compute_hours(raw: pd.DataFrame, method: str, base_year: int = 2017) -> pd.Series:
    """Return total annual labour hours in billions of hours."""
    if method == "ces":
        # employment is in thousands of persons, weekly_hours in hours/week.
        return raw["employment"] * raw["weekly_hours"] * 52.0 / 1e6
    if method == "nipa":
        return raw["hours_nipa"]
    if method == "indexed":
        if "hours_nipa" not in raw or "hours_index" not in raw:
            raise ValueError(
                "hours_method='indexed' requires both hours_index and hours_nipa "
                "(the NIPA benchmark series)"
            )
        benchmark = raw["hours_nipa"].dropna()
        if benchmark.empty:
            raise ValueError("hours_method='indexed': NIPA hours benchmark is empty")
        if base_year not in benchmark.index:
            base_year = int(benchmark.index.min())
        return raw["hours_index"] * benchmark.loc[base_year] / 100.0
    raise ValueError(f"Unknown hours method: {method}")


def build_accounts(raw: pd.DataFrame, settings) -> pd.DataFrame:
    """Derive Moseley's aggregate variables from the raw panel."""
    out = pd.DataFrame(index=raw.index)
    out.index.name = "year"

    out["P"] = raw["gdp"]                       # total value-price
    out["C"] = raw["cfc"]                       # consumed constant capital
    out["N"] = out["P"] - out["C"]              # new value (NDP)
    out["V"] = raw["compensation"]              # variable capital
    out["S"] = out["N"] - out["V"]              # surplus-value
    out["K"] = out["C"] + out["V"]              # cost price
    out["net_operating_surplus"] = raw.get("net_operating_surplus")
    if "net_operating_surplus" in raw:
        out["taxes_on_production"] = out["N"] - out["V"] - raw["net_operating_surplus"]

    out["L"] = compute_hours(raw, settings.hours_method, settings.base_year)

    # Monetary expression of labour time: dollars of new value per hour.
    out["melt"] = out["N"] / out["L"]
    deflator = raw["gdp_deflator"] / 100.0
    out["melt_real"] = out["melt"] / deflator
    out["new_value_real"] = out["N"] / deflator

    # Distribution.
    out["rate_surplus_value"] = out["S"] / out["V"]
    out["profit_share"] = out["S"] / out["N"]
    out["wage_share"] = out["V"] / out["N"]

    # Advanced capital stock and the general rate of profit.
    # Inventories are optional and treated as zero when missing, but the fixed
    # asset stock is required: if it is absent, M must be missing rather than
    # silently reduced to inventories alone.
    out["M"] = raw["capital_stock"]
    if "inventories" in raw and settings.include_inventories:
        out["M"] = out["M"] + raw["inventories"].fillna(0.0)
    out["rate_profit"] = out["S"] / out["M"]
    out["composition"] = out["M"] / out["V"]
    out["rate_profit_identity"] = out["rate_surplus_value"] / out["composition"]
    out["capital_output_ratio"] = out["M"] / out["N"]

    # Drop years in which a core variable is missing. This matters at the end
    # of the sample: BEA fixed-asset stocks lag one year behind NIPA flows, so
    # the latest year would otherwise show a profit rate computed with an
    # inventory-only capital stock.
    core = ["P", "C", "N", "V", "S", "L", "M"]
    out = out.loc[out[core].notna().all(axis=1)]

    return out


def validate_accounts(accounts: pd.DataFrame, tolerance: float = 1e-6) -> None:
    """Check that the accounting identities hold to numerical tolerance."""
    def close(left: pd.Series, right: pd.Series) -> bool:
        return bool(np.allclose(left.dropna(), right.dropna(), rtol=tolerance, atol=1e-6))

    checks = {
        "P = C + N": (accounts["P"], accounts["C"] + accounts["N"]),
        "K = C + V": (accounts["K"], accounts["C"] + accounts["V"]),
        "S = N - V": (accounts["S"], accounts["N"] - accounts["V"]),
        "R = (S/V) / (M/V)": (accounts["rate_profit"], accounts["rate_profit_identity"]),
    }
    for label, (left, right) in checks.items():
        if not close(left, right):
            raise AssertionError(f"Accounting identity failed: {label}")


def report_series_map(config: ProjectConfig, roles: Iterable[str] | None = None) -> pd.DataFrame:
    """Human-readable table of the role -> series mapping."""
    roles = roles or roles_for_settings(config.settings)
    rows = []
    for role in roles:
        spec = config.catalog.get(role)
        if spec is None:
            continue
        rows.append(
            {
                "role": role,
                "label": spec.label,
                "provider": spec.provider,
                "series_id": spec.series_id,
                "units": spec.units,
                "frequency": spec.frequency,
                "optional": spec.optional,
            }
        )
    return pd.DataFrame(rows)
