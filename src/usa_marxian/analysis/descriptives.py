"""Descriptive tables for the Marxian accounts."""

from __future__ import annotations

import numpy as np
import pandas as pd

LABELS = {
    "P": "Total value-price P (GDP)",
    "C": "Consumed constant capital C (CFC)",
    "N": "New value N (NDP)",
    "V": "Variable capital V (compensation)",
    "S": "Surplus-value S",
    "K": "Cost price K = C + V",
    "L": "Total hours worked L (billions)",
    "melt": "MELT m = N/L (USD per hour)",
    "melt_real": "MELT, constant 2017 USD per hour",
    "rate_surplus_value": "Rate of surplus-value S/V",
    "profit_share": "Profit share S/N",
    "wage_share": "Wage share V/N",
    "M": "Advanced capital stock M",
    "rate_profit": "General rate of profit R = S/M",
    "composition": "Composition of capital M/V",
    "capital_output_ratio": "Capital-output ratio M/N",
}


def summary_table(accounts: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Summary statistics for the main series."""
    columns = columns or [column for column in LABELS if column in accounts.columns]
    rows = []
    for column in columns:
        series = accounts[column].replace([np.inf, -np.inf], np.nan).dropna()
        if series.empty:
            continue
        rows.append(
            {
                "variable": column,
                "label": LABELS.get(column, column),
                "n": int(series.size),
                "first_year": int(series.index.min()),
                "last_year": int(series.index.max()),
                "first": float(series.iloc[0]),
                "last": float(series.iloc[-1]),
                "mean": float(series.mean()),
                "median": float(series.median()),
                "std": float(series.std(ddof=1)),
                "min": float(series.min()),
                "max": float(series.max()),
            }
        )
    return pd.DataFrame(rows)


def annual_table(accounts: pd.DataFrame, columns: list[str] | None = None) -> pd.DataFrame:
    """Annual values of selected variables, rounded for readability."""
    columns = columns or [
        column
        for column in ("N", "V", "S", "L", "melt", "rate_surplus_value", "rate_profit")
        if column in accounts.columns
    ]
    return accounts.loc[:, columns].round(4)
