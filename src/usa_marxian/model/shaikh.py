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
    matrices: dict[int, pd.DataFrame]
    technical_coefficients: pd.DataFrame
    summary: dict


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


def iterative_prices_endogenous(
    matrix: pd.DataFrame,
    labour: pd.Series,
    output: pd.Series,
    *,
    max_iter: int = 1000,
    tol: float = 1e-10,
    initial: pd.Series | None = None,
) -> IterationResult:
    """Shaikh-style cost-plus iteration with an endogenous profit rate.

    ``labour`` must be the wage cost per unit of output (``w l``), not hours
    per dollar. Each round computes the aggregate profit rate implied by the
    current price vector, then reprices with that rate:

    ``r_k = (p_k y - w L) / ((p_k A + w l) y)``
    ``p_{k+1} = (1+r_k)(p_k A + w l)``

    Prices are normalised so that ``p . y`` equals total output. The fixed
    point is a Sraffian price system with the model-implied rate, not the
    directly imposed observed rate.
    """
    index = matrix.index
    coefficients = matrix.to_numpy(dtype=float)
    direct = labour.reindex(index).to_numpy(dtype=float)
    quantities = output.reindex(index).to_numpy(dtype=float)
    if (quantities <= 0).any() or not np.isfinite(quantities).all():
        raise ValueError("Output quantities must be positive and finite")

    start = (initial if initial is not None else labour).reindex(index)
    p = start.to_numpy(dtype=float)
    if not np.isfinite(p).all() or (p <= 0).any():
        p = direct.copy()

    history: list[float] = []
    profit_rate = float("nan")
    for iteration in range(1, max_iter + 1):
        cost = coefficients.T @ p + direct
        denominator = float(cost @ quantities)
        if denominator <= 0 or not np.isfinite(denominator):
            break
        surplus = float(p @ quantities - denominator)
        profit_rate = surplus / denominator
        if not np.isfinite(profit_rate) or profit_rate <= -1.0:
            break
        new = (1.0 + profit_rate) * cost
        if not np.isfinite(new).all() or (new <= 0).any():
            break
        scale = max(float(np.max(np.abs(p))), 1e-12)
        residual = float(np.max(np.abs(new - p)) / scale)
        history.append(residual)
        p = new
        if residual < tol:
            return IterationResult(
                prices=pd.Series(p / p.sum(), index=index, name="price"),
                profit_rate=profit_rate,
                iterations=iteration,
                converged=True,
                residual=residual,
                history=history,
            )
    return IterationResult(
        prices=pd.Series(p / p.sum(), index=index, name="price"),
        profit_rate=profit_rate,
        iterations=len(history),
        converged=False,
        residual=float(history[-1]) if history else float("inf"),
        history=history,
    )


@dataclass
class CrossDualResult:
    prices: pd.Series
    output: pd.Series
    history: pd.DataFrame
    converged: bool
    iterations: int
    r_dispersion_start: float
    r_dispersion_end: float


def cross_dual_gravitation(
    matrix: pd.DataFrame,
    labour: pd.Series,
    output: pd.Series,
    *,
    steps: int = 300,
    price_speed: float = 0.05,
    output_speed: float = 0.02,
    tol: float = 1e-8,
    initial: pd.Series | None = None,
) -> CrossDualResult:
    """Minimal cross-dual price/output adjustment.

    Prices rise where the industry profit rate exceeds the average, and output
    shares rise where profitability is above average:

    ``p_i' = p_i exp(-alpha (r_i - r_bar))``
    ``q_i' = q_i exp( beta  (r_i - r_bar))``

    This is a transparent toy version of "real competition", not a fully
    specified Shaikh model. It is used only to check whether the adjustment
    tends to reduce profit-rate dispersion.
    """
    index = matrix.index
    coefficients = matrix.to_numpy(dtype=float)
    direct = labour.reindex(index).to_numpy(dtype=float)
    q = output.reindex(index).to_numpy(dtype=float)
    if (q <= 0).any() or not np.isfinite(q).all():
        raise ValueError("Output quantities must be positive and finite")
    q = q / q.sum()

    p = (
        (initial if initial is not None else labour)
        .reindex(index)
        .to_numpy(dtype=float)
    )
    if not np.isfinite(p).all() or (p <= 0).any():
        p = np.ones_like(direct)
    p = p * (1.0 / (p @ q))

    history = []
    dispersion = float("nan")

    for step in range(1, steps + 1):
        cost = coefficients.T @ p + direct
        if (cost <= 0).any() or not np.isfinite(cost).all():
            break
        rates = np.clip((p - cost) / cost, -0.99, 2.0)
        denominator = float(cost @ q)
        if denominator <= 0:
            break
        average = float((p @ q - denominator) / denominator)
        weights = cost * q
        weights = weights / weights.sum()
        dispersion = float(np.sqrt(np.sum(weights * (rates - average) ** 2)))

        with np.errstate(over="ignore"):
            p_new = p * np.exp(np.clip(-price_speed * (rates - average), -1.0, 1.0))
            q_new = q * np.exp(np.clip(output_speed * (rates - average), -1.0, 1.0))
        p_new = p_new * (1.0 / (p_new @ q_new))
        q_new = q_new / q_new.sum()

        price_change = float(np.max(np.abs(p_new - p)))
        output_change = float(np.max(np.abs(q_new - q)))
        history.append(
            {
                "step": step,
                "average_rate": average,
                "rate_dispersion": dispersion,
                "price_change": price_change,
                "output_change": output_change,
            }
        )
        p, q = p_new, q_new
        if price_change < tol and output_change < tol:
            break

    return CrossDualResult(
        prices=pd.Series(p, index=index, name="price"),
        output=pd.Series(q, index=index, name="output_share"),
        history=pd.DataFrame(history),
        converged=bool(
            len(history) > 0
            and history[-1]["price_change"] < tol
            and history[-1]["output_change"] < tol
        ),
        iterations=len(history),
        r_dispersion_start=float(history[0]["rate_dispersion"]) if history else float("nan"),
        r_dispersion_end=dispersion,
    )


def build_shaikh_benchmarks(
    panel: pd.DataFrame,
    use_matrices: pd.DataFrame,
    accounts: pd.DataFrame,
    *,
    base_year: int = 2017,
) -> ShaikhResult:
    """Build Shaikh's value-price and price-of-production benchmarks."""
    matrices = build_technical_matrices(use_matrices, panel, base_year=base_year)
    matrix = matrices.get(base_year, next(iter(matrices.values())))
    hours = accounts["L"].dropna()

    records = []
    for year, group in panel.groupby("year", sort=True):
        if year not in hours.index:
            continue
        matrix = matrices.get(int(year))
        if matrix is None:
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
        labour_cost = wage_bill / output
        surplus = (group["T"] + group["GOS"]).astype(float).sum()
        cost = (group["C"] + group["V"]).astype(float).sum()
        if cost <= 0:
            continue
        profit_rate = float(surplus / cost)

        try:
            values = labour_values(matrix, direct_labour)
            value_price = _normalise(values, output)
            prices = prices_of_production(matrix, labour_cost, profit_rate)
            fixed_iteration = iterative_prices(
                matrix, labour_cost, profit_rate, initial=value_price
            )
            endogenous_iteration = iterative_prices_endogenous(
                matrix, labour_cost, output, initial=value_price
            )
            cross_dual = cross_dual_gravitation(
                matrix,
                labour_cost,
                output,
                steps=400,
                tol=1e-5,
                initial=value_price,
            )
        except ValueError as exc:
            warnings.warn(f"Shaikh benchmark skipped for {year}: {exc}", stacklevel=2)
            continue

        if (values <= 0).any() or (prices <= 0).any():
            warnings.warn(
                f"Shaikh benchmark has non-positive values or prices in {year}",
                stacklevel=2,
            )
            continue

        iterated_price = (
            endogenous_iteration.prices
            if endogenous_iteration.converged
            and (endogenous_iteration.prices > 0).all()
            else fixed_iteration.prices
        )

        production_price = _normalise(prices, output)
        iterated_price = _normalise(iterated_price, output)

        for code in matrix.index:
            records.append(
                {
                    "year": int(year),
                    "industry_code": code,
                    "P_V": float(value_price.loc[code] * output.loc[code]),
                    "PP_S": float(production_price.loc[code] * output.loc[code]),
                    "PP_S_iter": float(iterated_price.loc[code] * output.loc[code]),
                    "r_observed": float(profit_rate),
                    "r_model": float(endogenous_iteration.profit_rate),
                    "iterations": int(endogenous_iteration.iterations),
                    "iteration_residual": float(endogenous_iteration.residual),
                    "iteration_converged": bool(endogenous_iteration.converged),
                    "cross_dual_converged": bool(cross_dual.converged),
                    "cross_dual_steps": int(cross_dual.iterations),
                    "cross_dual_dispersion_start": float(
                        cross_dual.r_dispersion_start
                    ),
                    "cross_dual_dispersion_end": float(cross_dual.r_dispersion_end),
                }
            )

    if not records:
        raise ValueError("Shaikh benchmarks produced no observations")

    benchmarks = pd.DataFrame(records)
    merged = panel.merge(
        benchmarks, on=["year", "industry_code"], how="left", validate="many_to_one"
    )
    iteration_summary = (
        benchmarks.groupby("year")
        .agg(
            iterations=("iterations", "max"),
            residual=("iteration_residual", "max"),
            converged=("iteration_converged", "all"),
            r_model=("r_model", "mean"),
            r_observed=("r_observed", "mean"),
            cross_dual_converged=("cross_dual_converged", "all"),
            cross_dual_steps=("cross_dual_steps", "max"),
            dispersion_start=("cross_dual_dispersion_start", "mean"),
            dispersion_end=("cross_dual_dispersion_end", "mean"),
        )
        .reset_index()
    )

    return ShaikhResult(
        panel=merged,
        matrix=matrix,
        matrices=matrices,
        technical_coefficients=matrix,
        summary={
            "base_year": int(base_year),
            "n_industries": int(matrix.shape[0]),
            "n_matrices": int(len(matrices)),
            "matrix_years": [min(matrices), max(matrices)],
            "matrix_prices": "current-price Use tables, annual",
            "profit_rate": "sum(S)/sum(K), current year",
            "solver": "Sraffian direct solve + fixed-r iteration + endogenous-r iteration + cross-dual simulation",
            "iterations_mean": float(iteration_summary["iterations"].mean()),
            "iterations_max": int(iteration_summary["iterations"].max()),
            "converged_share": float(iteration_summary["converged"].mean()),
            "r_model_mean": float(iteration_summary["r_model"].mean()),
            "r_observed_mean": float(iteration_summary["r_observed"].mean()),
            "cross_dual_converged_share": float(
                iteration_summary["cross_dual_converged"].mean()
            ),
            "cross_dual_steps_mean": float(
                iteration_summary["cross_dual_steps"].mean()
            ),
            "dispersion_start_mean": float(iteration_summary["dispersion_start"].mean()),
            "dispersion_end_mean": float(iteration_summary["dispersion_end"].mean()),
        },
    )
