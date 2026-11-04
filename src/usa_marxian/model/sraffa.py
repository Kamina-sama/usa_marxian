"""Sraffa's technical matrices, labour values and prices of production.

This module contains the Sraffian fixed-point code. Shaikh's adjustment process
lives in ``model.shaikh``.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .industries import NON_MARKET_CODES


def build_technical_matrix(
    use_matrices: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    year: int | None = None,
    base_year: int = 2017,
) -> pd.DataFrame:
    """Build the 71x71 input-output matrix ``A`` for one year.

    ``A[c, j] = U[c, j] / GO[j]`` in current prices. If ``year`` is omitted,
    the matrix for ``base_year`` is returned.
    """
    selected_year = int(year if year is not None else base_year)
    codes = sorted(
        panel.loc[~panel["industry_code"].isin(NON_MARKET_CODES), "industry_code"]
        .astype(str)
        .unique()
    )
    base = use_matrices.loc[use_matrices["year"] == selected_year]
    if base.empty:
        raise ValueError(f"No Use matrix for {selected_year}")

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
        panel.loc[panel["year"] == selected_year]
        .set_index("industry_code")["GO"]
        .reindex(codes)
    )
    if base_output.isna().any() or (base_output <= 0).any():
        raise ValueError(f"Gross output missing or non-positive for {selected_year}")

    return matrix.div(base_output, axis=1)


def build_technical_matrices(
    use_matrices: pd.DataFrame,
    panel: pd.DataFrame,
    *,
    base_year: int = 2017,
) -> dict[int, pd.DataFrame]:
    """Build annual input-output matrices for every year present in both."""
    years = sorted(
        set(use_matrices["year"].astype(int)).intersection(
            set(panel["year"].astype(int))
        )
    )
    if not years:
        raise ValueError("No overlapping Use-table and panel years")

    matrices: dict[int, pd.DataFrame] = {}
    for year in years:
        try:
            matrices[int(year)] = build_technical_matrix(
                use_matrices, panel, year=year
            )
        except ValueError:
            continue
    if not matrices:
        raise ValueError("No annual technical matrices could be built")
    if base_year not in matrices:
        base_year = min(matrices)
    return matrices


def build_real_technical_matrices(
    current_matrices: dict[int, pd.DataFrame],
    panel: pd.DataFrame,
) -> dict[int, pd.DataFrame]:
    """Deflate current-price matrices to 2017-dollar coefficients.

    ``A_real[c, j] = A_current[c, j] * p_j / p_c`` using the broad-sector
    gross-output deflators in the panel.
    """
    prices = (
        panel.loc[:, ["year", "industry_code", "go_price"]]
        .assign(price=lambda frame: frame["go_price"] / 100.0)
        .set_index(["year", "industry_code"])["price"]
    )
    real: dict[int, pd.DataFrame] = {}
    for year, matrix in current_matrices.items():
        price = prices.loc[int(year)].reindex(matrix.columns)
        if price.isna().any() or (price <= 0).any():
            continue
        real[int(year)] = matrix.mul(price, axis=1).div(price, axis=0)
    if not real:
        raise ValueError("No real technical matrices could be built")
    return real


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


def sraffa_prices_of_production(
    matrix: pd.DataFrame,
    labour: pd.Series,
    profit_rate: float,
    *,
    capital_cost: pd.Series | None = None,
) -> pd.Series:
    """Return Sraffian prices ``p = l [I - (1+r)A]^-1``.

    ``capital_cost`` is an optional per-unit fixed-capital charge (current
    dollars per 2017 dollar of output). When supplied it is added to the
    primary-input term before solving. This is a diagnostic for the absence of
    fixed capital in the basic Sraffian system, not a full joint-product model.
    """
    identity = np.eye(matrix.shape[0])
    coefficients = matrix.to_numpy(dtype=float)
    direct = labour.reindex(matrix.index).to_numpy(dtype=float)
    rhs = direct
    if capital_cost is not None:
        rhs = rhs + capital_cost.reindex(matrix.index).fillna(0.0).to_numpy(
            dtype=float
        )
    try:
        prices = np.linalg.solve(
            (identity - (1.0 + profit_rate) * coefficients).T, rhs
        )
    except np.linalg.LinAlgError as exc:
        raise ValueError(f"Price system singular at r={profit_rate:.3f}") from exc
    return pd.Series(prices, index=matrix.index, name="price")


def prices_of_production(
    matrix: pd.DataFrame,
    labour: pd.Series,
    profit_rate: float,
    **kwargs,
) -> pd.Series:
    """Backward-compatible alias for :func:`sraffa_prices_of_production`."""
    return sraffa_prices_of_production(
        matrix, labour, profit_rate, **kwargs
    )


@dataclass
class IterationResult:
    prices: pd.Series
    profit_rate: float
    iterations: int
    converged: bool
    residual: float
    history: list[float]


def iterative_prices(
    matrix: pd.DataFrame,
    labour: pd.Series,
    profit_rate: float,
    *,
    max_iter: int = 1000,
    tol: float = 1e-10,
    initial: pd.Series | None = None,
) -> IterationResult:
    """Fixed-``r`` cost-plus iteration.

    ``p_{k+1} = (1+r)(p_k A + w l)`` with ``w=1``. The iterates are
    normalised to sum to one. This converges to the same ray as the direct
    Sraffian solve when ``(1+r) * lambda_max(A) < 1``.
    """
    index = matrix.index
    coefficients = matrix.to_numpy(dtype=float)
    direct = labour.reindex(index).to_numpy(dtype=float)
    start = (initial if initial is not None else labour).reindex(index)
    p = start.to_numpy(dtype=float)
    if not np.isfinite(p).all() or (p <= 0).any():
        p = direct.copy()

    history: list[float] = []
    for iteration in range(1, max_iter + 1):
        new = (1.0 + profit_rate) * (coefficients.T @ p + direct)
        if not np.isfinite(new).all() or (new <= 0).any():
            return IterationResult(
                prices=pd.Series(p / p.sum(), index=index, name="price"),
                profit_rate=float(profit_rate),
                iterations=iteration,
                converged=False,
                residual=float("inf"),
                history=history,
            )
        scale = max(float(np.max(np.abs(p))), 1e-12)
        residual = float(np.max(np.abs(new - p)) / scale)
        history.append(residual)
        p = new
        if residual < tol:
            return IterationResult(
                prices=pd.Series(p / p.sum(), index=index, name="price"),
                profit_rate=float(profit_rate),
                iterations=iteration,
                converged=True,
                residual=residual,
                history=history,
            )
    return IterationResult(
        prices=pd.Series(p / p.sum(), index=index, name="price"),
        profit_rate=float(profit_rate),
        iterations=max_iter,
        converged=False,
        residual=float(history[-1]) if history else float("inf"),
        history=history,
    )


