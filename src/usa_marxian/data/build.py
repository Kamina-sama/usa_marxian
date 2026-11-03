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

Alternative specifications
--------------------------
``build_accounts`` accepts four switches, used by the robustness module:

* ``value_added``: ``ndp`` (default), ``nnp``, or ``nnp_factor``.
* ``capital_stock``: ``nonresidential`` (default) or ``private_total``.
* ``include_inventories``: whether inventory stock is added to ``M``.
* ``melt_numerator``: which money new-value concept divides by hours.

The switches change the measured magnitudes but not the accounting identities.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Literal

import numpy as np
import pandas as pd

from ..config import ProjectConfig, SeriesSpec
from .cache import load_raw_series

ValueAdded = Literal["ndp", "nnp", "nnp_factor"]
CapitalStock = Literal["nonresidential", "private_total"]
MeltNumerator = Literal["ndp", "nnp", "nnp_factor", "gdp"]

CORE_ROLES = [
    "gdp",
    "gnp",
    "cfc",
    "gdp_deflator",
    "compensation",
    "net_operating_surplus",
    "taxes_on_production",
    "corporate_profits",
    "proprietors_income",
    "net_interest",
    "rental_income",
    "capital_stock",
    "capital_stock_private",
    "net_national_factor_income",
]

PROPERTY_INCOME_COMPONENTS = [
    "corporate_profits",
    "proprietors_income",
    "net_interest",
    "rental_income",
]


def roles_for_settings(settings) -> list[str]:
    """Roles needed for the accounts *and* for every robustness specification.

    All hours ingredients are loaded even when the baseline uses only one of
    them, because the robustness module switches hours methods on the same raw
    panel. Inventories are also always loaded; the accounting switch decides
    whether they enter M.
    """
    return list(CORE_ROLES) + [
        "inventories",
        "employment",
        "weekly_hours",
        "hours_index",
        "hours_nipa",
    ]


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
    refresh: bool = False,
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
            force=refresh,
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


def build_raw_panel(
    config: ProjectConfig,
    *,
    start_year: int | None = None,
    refresh: bool = False,
) -> pd.DataFrame:
    """Download (or load cached) raw series and align them by year."""
    settings = config.settings
    start = start_year or settings.start_year
    end = settings.end_year

    series: dict[str, pd.Series] = {}
    for role in roles_for_settings(settings):
        values = _load_role(config, role, start_year=start, end_year=end, refresh=refresh)
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


def _require(raw: pd.DataFrame, column: str, label: str) -> pd.Series:
    if column not in raw.columns:
        raise KeyError(f"{label} requires raw series {column!r}")
    return raw[column]


def build_accounts(
    raw: pd.DataFrame,
    settings,
    *,
    value_added: ValueAdded = "ndp",
    capital_stock: CapitalStock = "nonresidential",
    include_inventories: bool | None = None,
    melt_numerator: MeltNumerator | None = None,
    hours_method: str | None = None,
) -> pd.DataFrame:
    """Derive Moseley's aggregate variables from the raw panel.

    Parameters are explicit so the robustness module can vary one assumption
    at a time without mutating the settings object.
    """
    if include_inventories is None:
        include_inventories = settings.include_inventories
    if hours_method is None:
        hours_method = settings.hours_method
    if melt_numerator is None:
        melt_numerator = "ndp" if value_added == "ndp" else value_added

    out = pd.DataFrame(index=raw.index)
    out.index.name = "year"

    out["C"] = raw["cfc"]                       # consumed constant capital
    if value_added == "ndp":
        out["N"] = raw["gdp"] - raw["cfc"]
    elif value_added == "nnp":
        out["N"] = _require(raw, "gnp", "value_added='nnp'") - raw["cfc"]
    elif value_added == "nnp_factor":
        out["N"] = _require(raw, "net_national_factor_income", "value_added='nnp_factor'")
    else:  # pragma: no cover - guarded by the Literal
        raise ValueError(f"Unknown value_added specification: {value_added}")

    out["P"] = out["C"] + out["N"]              # total value-price
    out["V"] = raw["compensation"]              # variable capital
    out["S"] = out["N"] - out["V"]              # surplus-value
    out["K"] = out["C"] + out["V"]              # cost price
    out["net_operating_surplus"] = raw.get("net_operating_surplus")

    if "taxes_on_production" in raw:
        out["taxes_on_production"] = raw["taxes_on_production"]
    else:
        out["taxes_on_production"] = (
            out["N"] - out["V"] - out["net_operating_surplus"]
        )

    # Independent property-income check. All four components are required for
    # the sum to be meaningful; otherwise the column is left missing.
    if all(component in raw.columns for component in PROPERTY_INCOME_COMPONENTS):
        out["property_income"] = raw.loc[:, PROPERTY_INCOME_COMPONENTS].sum(axis=1)
    else:
        out["property_income"] = np.nan
    out["property_income_plus_taxes"] = out["property_income"] + out["taxes_on_production"]
    out["profit_check_gap"] = out["property_income_plus_taxes"] - out["S"]
    out["profit_check_ratio"] = out["property_income_plus_taxes"] / out["S"]
    out["gross_operating_surplus_implied"] = out["S"] - out["taxes_on_production"]
    out["property_income_vs_gos"] = (
        out["property_income"] / out["gross_operating_surplus_implied"]
    )

    out["L"] = compute_hours(raw, hours_method, settings.base_year)

    # Alternative MELT numerators. The default follows the value-added choice.
    ndp = raw["gdp"] - raw["cfc"]
    out["melt_ndp"] = ndp / out["L"]
    out["melt_gdp"] = raw["gdp"] / out["L"]
    if "gnp" in raw:
        out["melt_nnp"] = (raw["gnp"] - raw["cfc"]) / out["L"]
    if "net_national_factor_income" in raw:
        out["melt_nnp_factor"] = raw["net_national_factor_income"] / out["L"]

    melt_columns = {
        "ndp": "melt_ndp",
        "nnp": "melt_nnp",
        "nnp_factor": "melt_nnp_factor",
        "gdp": "melt_gdp",
    }
    try:
        out["melt"] = out[melt_columns[melt_numerator]]
    except KeyError as exc:
        raise KeyError(f"MELT numerator unavailable: {melt_numerator}") from exc

    deflator = raw["gdp_deflator"] / 100.0
    out["melt_real"] = out["melt"] / deflator
    out["new_value_real"] = out["N"] / deflator
    out["gdp_real"] = raw["gdp"] / deflator

    # Distribution.
    out["rate_surplus_value"] = out["S"] / out["V"]
    out["profit_share"] = out["S"] / out["N"]
    out["wage_share"] = out["V"] / out["N"]

    # Advanced capital stock and the general rate of profit.
    # Inventories are optional and treated as zero when missing, but the fixed
    # asset stock is required: if it is absent, M must be missing rather than
    # silently reduced to inventories alone.
    if capital_stock == "nonresidential":
        fixed = raw["capital_stock"]
    elif capital_stock == "private_total":
        fixed = _require(raw, "capital_stock_private", "capital_stock='private_total'")
    else:  # pragma: no cover
        raise ValueError(f"Unknown capital_stock specification: {capital_stock}")

    # K100071A027NBEA is an *opening* balance: the value for year t is the
    # stock at the start of t, i.e. the end of t-1. Shift it forward so the
    # inventory stock is measured at the end of the year, like the fixed-asset
    # stock. The last year falls back to its opening value.
    if "inventories" in raw:
        inventories = raw["inventories"].shift(-1).fillna(raw["inventories"])
    else:
        inventories = 0.0
    out["M_fixed_only"] = fixed
    out["M"] = fixed + inventories if include_inventories else fixed
    out["M_private_total"] = (
        _require(raw, "capital_stock_private", "M_private_total") + inventories
    )

    out["rate_profit"] = out["S"] / out["M"]
    out["rate_profit_fixed_only"] = out["S"] / out["M_fixed_only"]
    out["rate_profit_private_total"] = out["S"] / out["M_private_total"]
    out["composition"] = out["M"] / out["V"]
    out["composition_fixed_only"] = out["M_fixed_only"] / out["V"]
    out["composition_private_total"] = out["M_private_total"] / out["V"]
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
        "S = P - K": (accounts["S"], accounts["P"] - accounts["K"]),
        "R = (S/V) / (M/V)": (accounts["rate_profit"], accounts["rate_profit_identity"]),
    }
    for label, (left, right) in checks.items():
        if not close(left, right):
            raise AssertionError(f"Accounting identity failed: {label}")

    if (accounts["L"] <= 0).any():
        raise AssertionError("Labour hours must be positive")
    if (accounts["M"] <= 0).any():
        raise AssertionError("Advanced capital must be positive")


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
