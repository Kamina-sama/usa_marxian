"""Shaikh's classical benchmarks: labour values and prices of production.

Two Shaikh-style benchmarks are built from the BEA summary Use table:

1. **Direct prices / labour values.** With ``A`` the input-output matrix and
   ``l`` the direct labour coefficients,

       lambda = l (I - A)^-1

   ``lambda_i`` is the total labour required per dollar of output of industry
   ``i``. Multiplying by the monetary expression of labour time and normalising
   to total gross output gives a value-price benchmark.

2. **Prices of production.** With a uniform profit rate ``r`` on flow capital
   and a wage rate ``w``,

       p = (1 + r)(p A + w l)

   or, solving for ``p``,

       p = w (1 + r) l [I - (1 + r) A]^-1

   The relative prices are independent of ``w``; the scale is fixed by
   normalising ``p . GO`` to total gross output. ``r`` is the observed
   aggregate surplus-value rate on cost, ``sum(S) / sum(K)``.

Differences from Moseley's benchmark
------------------------------------
Moseley's ``PP_i = K_i + R M_i`` uses the *stock* of advanced capital and the
aggregate rate ``R = S/M``. Shaikh's prices use the *flow* cost matrix and a
uniform profit rate on cost. The two are not nested; comparing them is the
point.

The Use table has 73 commodity rows but 71 industry columns. ``Used`` and
``Other`` are non-produced commodities (scrap and noncomparable imports, about
1.35% of intermediate use); they are excluded from ``A``. The matrix is
therefore square and invertible, at the cost of a small understatement of
intermediate inputs.
"""

from __future__ import annotations

import warnings
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .industries import NON_MARKET_CODES


@dataclass
class ShaikhResult:
    panel: pd.DataFrame
    matrix: pd.DataFrame
    technical_coefficients: pd.DataFrame
    summary: dict


def build_technical_matrix(
    use_matrices: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    base_year: int = 2017,
) -> pd.DataFrame:
    """Build the 71x71 input-output matrix ``A`` for the base year."""
    codes = sorted(
        panel.loc[~panel["industry_code"].isin(NON_MARKET_CODES), "industry_code"]
        .astype(str)
        .unique()
    )
    base = use_matrices.loc[use_matrices["year"] == base_year]
    if base.empty:
        raise ValueError(f"No Use matrix for base year {base_year}")

    base = base.loc[base["commodity_code"].astype(str).isin(codes)]
    matrix = (
        base.pivot_table(
            index="commodity_code",
            columns="industry_code",
            values="value",
            aggfunc="sum",
        )
        .reindex(index=codes, columns=codes)
        .fillna(0.0)
    )

    base_output = (
        panel.loc[panel["year"] == base_year]
        .set_index("industry_code")["GO"]
        .reindex(codes)
    )
    if base_output.isna().any() or (base_output <= 0).any():
        raise ValueError("Base-year gross output missing or non-positive")

    return matrix.div(base_output, axis=1)


def _normalise(values: pd.Series, output: pd.Series) -> pd.Series:
    total = float((values * output).sum())
    if total <= 0 or not np.isfinite(total):
        raise ValueError("Benchmark cannot be normalised to total output")
    return values * (float(output.sum()) / total)


def labour_values(
    matrix: pd.DataFrame,
    labour: pd.Series,
) -> pd.Series:
    """Return ``lambda = l (I - A)^-1``."""
    identity = np.eye(matrix.shape[0])
    coefficients = matrix.to_numpy(dtype=float)
    direct = labour.reindex(matrix.index).to_numpy(dtype=float)
    try:
        values = np.linalg.solve((identity - coefficients).T, direct)
    except np.linalg.LinAlgError as exc:
        raise ValueError("Input-output matrix is singular") from exc
    return pd.Series(values, index=matrix.index, name="labour_value")


def prices_of_production(
    matrix: pd.DataFrame,
    labour: pd.Series,
    profit_rate: float,
) -> pd.Series:
    """Return relative prices ``p = l [I - (1+r)A]^-1``."""
    identity = np.eye(matrix.shape[0])
    coefficients = matrix.to_numpy(dtype=float)
    direct = labour.reindex(matrix.index).to_numpy(dtype=float)
    try:
        prices = np.linalg.solve(
            (identity - (1.0 + profit_rate) * coefficients).T, direct
        )
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"Price system singular at r={profit_rate:.3f}") from exc
    return pd.Series(prices, index=matrix.index, name="price")


def build_shaikh_benchmarks(
    panel: pd.DataFrame,
    use_matrices: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    base_year: int = 2017,
) -> ShaikhResult:
    """Build Shaikh's value-price and price-of-production benchmarks."""
    matrix = build_technical_matrix(use_matrices, panel, base_year=base_year)
    hours = accounts["L"].dropna()

    records = []
    for year, group in panel.groupby("year", sort=True):
        if year not in hours.index:
            continue
        group = group.set_index("industry_code").reindex(matrix.index)
        if group["GO"].isna().any() or (group["GO"] <= 0).any():
            continue

        output = group["GO"].astype(float)
        wage_bill = group["V"].astype(float)
        total_hours = float(hours.loc[year]) * 1e9
        if total_hours <= 0:
            continue
        wage_rate = float(wage_bill.sum() * 1e6 / total_hours)
        if wage_rate <= 0:
            continue

        direct_labour = wage_bill / (output * wage_rate)
        surplus = (group["T"] + group["GOS"]).astype(float).sum()
        cost = (group["C"] + group["V"]).astype(float).sum()
        if cost <= 0:
            continue
        profit_rate = float(surplus / cost)

        try:
            values = labour_values(matrix, direct_labour)
            prices = prices_of_production(matrix, direct_labour, profit_rate)
        except ValueError as exc:
            warnings.warn(f"Shaikh benchmark skipped for {year}: {exc}", stacklevel=2)
            continue

        if (values <= 0).any() or (prices <= 0).any():
            warnings.warn(
                f"Shaikh benchmark has non-positive values or prices in {year}",
                stacklevel=2,
            )
            continue

        value_price = _normalise(values, output)
        production_price = _normalise(prices, output)

        for code in matrix.index:
            records.append(
                {
                    "year": int(year),
                    "industry_code": code,
                    "P_V": float(value_price.loc[code] * output.loc[code]),
                    "PP_S": float(production_price.loc[code] * output.loc[code]),
                }
            )

    if not records:
        raise ValueError("Shaikh benchmarks produced no observations")

    benchmarks = pd.DataFrame(records)
    merged = panel.merge(
        benchmarks, on=["year", "industry_code"], how="left", validate="many_to_one"
    )
    return ShaikhResult(
        panel=merged,
        matrix=matrix,
        technical_coefficients=matrix,
        summary={
            "base_year": int(base_year),
            "n_industries": int(matrix.shape[0]),
            "profit_rate": "sum(S)/sum(K), current year",
        },
    )
