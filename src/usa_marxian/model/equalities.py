"""Aggregate equalities and the rate-of-profit decomposition.

Moseley's two aggregate equalities are

    total price of production = total value-price
    total profit              = total surplus-value

Under his sequential, single-system method both hold by construction for the
economy as a whole, because the general rate of profit is defined as
``R = S / M`` and the same money capital magnitudes are used at both levels of
abstraction. The functions here check the algebra on real or synthetic data
and decompose movements in the rate of profit.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class EqualityCheck:
    """Comparison of two aggregate magnitudes."""

    total_price: float
    total_value: float
    price_value_gap: float
    price_value_gap_pct: float
    total_profit: float
    total_surplus_value: float
    profit_surplus_gap: float
    profit_surplus_gap_pct: float


def check_two_equalities(
    *,
    total_price: float,
    total_value: float,
    total_profit: float,
    total_surplus_value: float,
) -> EqualityCheck:
    """Compute both aggregate gaps in levels and percentages."""
    price_gap = total_price - total_value
    profit_gap = total_profit - total_surplus_value
    return EqualityCheck(
        total_price=float(total_price),
        total_value=float(total_value),
        price_value_gap=float(price_gap),
        price_value_gap_pct=float(100.0 * price_gap / total_value) if total_value else float("nan"),
        total_profit=float(total_profit),
        total_surplus_value=float(total_surplus_value),
        profit_surplus_gap=float(profit_gap),
        profit_surplus_gap_pct=(
            float(100.0 * profit_gap / total_surplus_value) if total_surplus_value else float("nan")
        ),
    )


def check_industry_equalities(frame: pd.DataFrame) -> EqualityCheck:
    """Check the two equalities from an industry-level frame.

    Required columns: ``price_of_production``, ``value_price``, ``profit``,
    ``surplus_value``. Rows are industries. Sums, not unit values, are
    compared, because Marx's prices of production are gross annual industry
    revenues rather than unit prices.
    """
    required = {"price_of_production", "value_price", "profit", "surplus_value"}
    missing = required.difference(frame.columns)
    if missing:
        raise KeyError(f"Missing columns: {sorted(missing)}")
    return check_two_equalities(
        total_price=frame["price_of_production"].sum(),
        total_value=frame["value_price"].sum(),
        total_profit=frame["profit"].sum(),
        total_surplus_value=frame["surplus_value"].sum(),
    )


def profit_rate_decomposition(accounts: pd.DataFrame) -> pd.DataFrame:
    """Decompose ``R = S/M`` into the rate of surplus-value and composition.

    ``R = (S/V) / (M/V)``. The output reports log changes and their
    contributions, so that

        dlog R = dlog(S/V) - dlog(M/V)
    """
    out = pd.DataFrame(index=accounts.index)
    out["rate_profit"] = accounts["S"] / accounts["M"]
    out["rate_surplus_value"] = accounts["S"] / accounts["V"]
    out["composition"] = accounts["M"] / accounts["V"]

    out["dlog_rate_profit"] = np.log(out["rate_profit"]).diff()
    out["dlog_rate_surplus_value"] = np.log(out["rate_surplus_value"]).diff()
    out["dlog_composition"] = np.log(out["composition"]).diff()
    out["contribution_surplus_value"] = out["dlog_rate_surplus_value"]
    out["contribution_composition"] = -out["dlog_composition"]
    out["decomposition_residual"] = (
        out["dlog_rate_profit"]
        - out["contribution_surplus_value"]
        - out["contribution_composition"]
    )
    return out


def profit_rate_summary(accounts: pd.DataFrame) -> dict[str, float]:
    """Headline values for the rate of profit over the sample."""
    rate = (accounts["S"] / accounts["M"]).dropna()
    if rate.empty:
        raise ValueError("No rate-of-profit observations")
    first_year, last_year = int(rate.index.min()), int(rate.index.max())
    return {
        "first_year": first_year,
        "last_year": last_year,
        "first_value": float(rate.loc[first_year]),
        "last_value": float(rate.loc[last_year]),
        "mean": float(rate.mean()),
        "min": float(rate.min()),
        "max": float(rate.max()),
        "change_pp": float(100.0 * (rate.loc[last_year] - rate.loc[first_year])),
    }


def implied_rate_of_profit(*, s_over_v: float, m_over_v: float) -> float:
    """Analytic helper: R = (S/V) / (M/V)."""
    return s_over_v / m_over_v


def decomposition_frame(accounts: pd.DataFrame) -> pd.DataFrame:
    """Return the decomposition columns without the identity residual check."""
    frame = profit_rate_decomposition(accounts)
    return frame.loc[:, ["rate_profit", "rate_surplus_value", "composition"]]
