"""Independent check of surplus-value against measured property income.

``S = N - V`` is an accounting residual, so comparing it with itself proves
nothing. The informative comparison uses NIPA property income:

    property income = corporate profits + proprietors' income
                      + net interest + rental income

Adding taxes on production gives a measure that should be close to ``S``.
Proprietors' income is mixed income, so the property-income total is an upper
bound on pure profit; the gap is a measurement diagnostic, not a refutation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def property_income_check(accounts: pd.DataFrame) -> pd.DataFrame:
    """Annual comparison table."""
    columns = [
        "S",
        "taxes_on_production",
        "property_income",
        "property_income_plus_taxes",
        "profit_check_gap",
        "profit_check_ratio",
        "gross_operating_surplus_implied",
        "property_income_vs_gos",
    ]
    present = [column for column in columns if column in accounts.columns]
    return accounts.loc[:, present].copy()


def property_income_summary(accounts: pd.DataFrame) -> dict:
    """Headline statistics for the independent profit check."""
    ratio = accounts.get("profit_check_ratio", pd.Series(dtype=float))
    ratio = pd.to_numeric(ratio, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    gap = accounts.get("profit_check_gap", pd.Series(dtype=float))
    gap = pd.to_numeric(gap, errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()

    surplus = accounts["S"].dropna()
    property_income = accounts.get("property_income", pd.Series(dtype=float)).dropna()
    aligned = pd.concat([surplus, property_income], axis=1, join="inner").dropna()

    return {
        "n_years": int(ratio.size),
        "mean_ratio": float(ratio.mean()) if not ratio.empty else float("nan"),
        "min_ratio": float(ratio.min()) if not ratio.empty else float("nan"),
        "max_ratio": float(ratio.max()) if not ratio.empty else float("nan"),
        "mean_gap_bn": float(gap.mean()) if not gap.empty else float("nan"),
        "mean_gap_pct_of_S": (
            float(100.0 * gap.mean() / surplus.mean()) if not gap.empty and surplus.mean() else float("nan")
        ),
        "corr_S_property_income": (
            float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1])) if len(aligned) >= 3 else float("nan")
        ),
    }
