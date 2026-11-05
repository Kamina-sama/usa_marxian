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

from .sraffa import (
    IterationResult,
    _normalise,
    aligned_costs,
    build_real_technical_matrices,
    build_technical_matrices,
    iterative_prices,
    labour_values,
    sraffa_prices_fixed_capital,
    sraffa_prices_of_production,
)


@dataclass
class ShaikhResult:
    panel: pd.DataFrame
    matrix: pd.DataFrame
    matrices: dict[int, pd.DataFrame]
    technical_coefficients: pd.DataFrame
    summary: dict


def iterative_prices_fixed_capital(
    matrix: pd.DataFrame,
    capital_matrix: pd.DataFrame,
    depreciation: pd.DataFrame,
    labour: pd.Series,
    output: pd.Series,
    *,
    max_iter: int = 1000,
    tol: float = 1e-10,
    damping: float = 1.0,
    initial: pd.Series | None = None,
) -> IterationResult:
    """Shaikh cost-plus iteration with fixed capital and endogenous ``r``.

    The price equation is

        p = (1+r)(pA + w l) + p (B o (r + Delta))

    and ``r`` is the aggregate surplus divided by capital advanced.
    """
    index = matrix.index
    coefficients = matrix.reindex(index=index, columns=index).fillna(0.0).to_numpy(
        dtype=float
    )
    capital = capital_matrix.reindex(index=index, columns=index).fillna(0.0).to_numpy(
        dtype=float
    )
    delta = depreciation.reindex(index=index, columns=index).fillna(0.0).to_numpy(
        dtype=float
    )
    direct = labour.reindex(index).to_numpy(dtype=float)
    quantities = output.reindex(index).to_numpy(dtype=float)
    if (quantities <= 0).any() or not np.isfinite(quantities).all():
        raise ValueError("Output quantities must be positive and finite")

    start = (initial if initial is not None else labour).reindex(index)
    p = start.to_numpy(dtype=float)
    if not np.isfinite(p).all() or (p <= 0).any():
        p = direct.copy()
    p = p * (quantities.sum() / (p @ quantities))

    history: list[float] = []
    profit_rate = float("nan")
    capital_advanced = float("nan")
    depreciation_value = float("nan")
    for iteration in range(1, max_iter + 1):
        intermediate = coefficients @ quantities
        fixed_capital = capital @ quantities
        depreciation_flow = (capital * delta) @ quantities
        intermediate_value = float(p @ intermediate)
        fixed_value = float(p @ fixed_capital)
        depreciation_value = float(p @ depreciation_flow)
        labour_value = float(direct @ quantities)
        surplus = float(
            p @ quantities
            - intermediate_value
            - labour_value
            - depreciation_value
        )
        capital_advanced = intermediate_value + labour_value + fixed_value
        if capital_advanced <= 0 or not np.isfinite(capital_advanced):
            break
        profit_rate = surplus / capital_advanced
        if not np.isfinite(profit_rate) or profit_rate <= -1.0:
            break

        base = coefficients.T @ p + direct
        capital_charge = (capital * (profit_rate + delta)).T @ p
        new = (1.0 + profit_rate) * base + capital_charge
        if not np.isfinite(new).all() or (new <= 0).any():
            break
        new = new * (quantities.sum() / (new @ quantities))
        if damping < 1.0:
            new = damping * new + (1.0 - damping) * p
            new = new * (quantities.sum() / (new @ quantities))
        residual = float(np.max(np.abs(new - p)))
        history.append(residual)
        p = new
        if residual < tol:
            return IterationResult(
                prices=pd.Series(p, index=index, name="price"),
                profit_rate=profit_rate,
                iterations=iteration,
                converged=True,
                residual=residual,
                history=history,
                capital_advanced=capital_advanced,
                depreciation_value=depreciation_value,
            )
    return IterationResult(
        prices=pd.Series(p, index=index, name="price"),
        profit_rate=profit_rate,
        iterations=len(history),
        converged=False,
        residual=float(history[-1]) if history else float("inf"),
        history=history,
        capital_advanced=capital_advanced,
        depreciation_value=depreciation_value,
    )


def iterative_prices_endogenous(
    matrix: pd.DataFrame,
    labour: pd.Series,
    output: pd.Series,
    *,
    depreciation_cost: pd.Series | None = None,
    max_iter: int = 1000,
    tol: float = 1e-10,
    initial: pd.Series | None = None,
) -> IterationResult:
    """Shaikh-style cost-plus iteration with an endogenous profit rate.

    ``labour`` must be the wage cost per unit of output (``w l``), not hours
    per dollar. ``depreciation_cost`` is consumption of fixed capital per unit
    of output; it enters the cost base, so the surplus is net of CFC and the
    iteration converges to the same centre as the direct solve at its own rate.
    Each round computes the aggregate profit rate implied by the current price
    vector, then reprices with that rate:

    ``r_k = (p_k y - (p_k A + v + d) y) / ((p_k A + v + d) y)``
    ``p_{k+1} = (1+r_k)(p_k A + v + d)``

    Prices are normalised so that ``p . y`` equals total output. The fixed
    point is a Sraffian price system with the model-implied rate, not the
    directly imposed observed rate.
    """
    index = matrix.index
    coefficients = matrix.to_numpy(dtype=float)
    direct = aligned_costs(labour, index, "labour cost")
    primary = direct.copy()
    if depreciation_cost is not None:
        primary = primary + aligned_costs(
            depreciation_cost, index, "depreciation cost"
        )
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
        cost = coefficients.T @ p + primary
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
    capital_matrices: dict[int, tuple[pd.DataFrame, pd.DataFrame]] | None = None,
) -> ShaikhResult:
    """Build Sraffa/Shaikh value-price and price-of-production benchmarks."""
    matrices_current = build_technical_matrices(
        use_matrices, panel, base_year=base_year
    )
    matrices = build_real_technical_matrices(matrices_current, panel)
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
        if (
            "go_price" not in group.columns
            or group["go_price"].isna().any()
            or (group["go_price"] <= 0).any()
        ):
            continue

        output = group["GO"].astype(float)
        if "quantity" in group.columns and group["quantity"].notna().all():
            output_real = group["quantity"].astype(float)
            price = output / output_real
        else:
            price = group["go_price"].astype(float) / 100.0
            output_real = output / price
        wage_bill = group["V"].astype(float)
        total_hours = float(hours.loc[year]) * 1e9
        if total_hours <= 0:
            continue
        wage_rate = float(wage_bill.sum() * 1e6 / total_hours)
        if wage_rate <= 0:
            continue

        if "labour_hours" in group.columns and group["labour_hours"].notna().all():
            labour_hours = group["labour_hours"].astype(float)
        else:
            labour_hours = wage_bill * 1e6 / wage_rate
        direct_labour = labour_hours / (output_real * 1e6)
        # Wage cost per unit of real output. Industry-specific wage rates are
        # used deliberately: V_j / q_j embeds each industry's own wage level,
        # which is an empirical choice rather than Sraffa's uniform wage.
        labour_cost = wage_bill / output_real
        # Consumption of fixed capital per unit of real output. Depreciation is
        # a cost of production and enters the price system; without it
        # capital-intensive industries are systematically underpriced relative
        # to observed gross output, which also includes CFC.
        if "CFC" in group.columns:
            depreciation_cost = (
                group["CFC"].astype(float)
                / (group["go_price"].astype(float) / 100.0)
            ) / output_real
        else:
            depreciation_cost = None

        if {"S_real", "K_real"}.issubset(group.columns):
            surplus = group["S_real"].astype(float).sum()
            cost = group["K_real"].astype(float).sum()
            if "T" in group.columns and "va_price" in group.columns:
                taxes_real = float(
                    (group["T"].astype(float) / (group["va_price"] / 100.0)).sum()
                )
            else:
                taxes_real = 0.0
            gross_profit = surplus - taxes_real
        else:
            gross_profit = float(group["GOS"].astype(float).sum())
            cost = float((group["C"] + group["V"]).astype(float).sum())
        if cost <= 0:
            continue
        profit_rate = float(gross_profit / cost)

        try:
            values = labour_values(matrix, direct_labour)
            value_price = _normalise(values, output_real)
            prices = sraffa_prices_of_production(
                matrix,
                labour_cost,
                profit_rate,
                depreciation_cost=depreciation_cost,
            )
            fixed_iteration = iterative_prices(
                matrix,
                labour_cost,
                profit_rate,
                depreciation_cost=depreciation_cost,
                initial=value_price,
            )
            endogenous_iteration = iterative_prices_endogenous(
                matrix,
                labour_cost,
                output_real,
                depreciation_cost=depreciation_cost,
                initial=value_price,
            )
            cross_dual = cross_dual_gravitation(
                matrix,
                labour_cost,
                output_real,
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

        production_price = _normalise(prices, output_real)
        iterated_price = _normalise(iterated_price, output_real)

        fixed_price = None
        fixed_rate = None
        fixed_shaikh = None
        if capital_matrices is not None and int(year) in capital_matrices:
            capital_matrix, depreciation = capital_matrices[int(year)]
            fixed_rate = float(
                gross_profit / (group["M"].astype(float).sum() + cost)
            )
            try:
                fixed_prices = sraffa_prices_fixed_capital(
                    matrix,
                    capital_matrix,
                    depreciation,
                    labour_cost,
                    fixed_rate,
                )
                if (fixed_prices > 0).all():
                    fixed_price = _normalise(fixed_prices, output_real)
                fixed_shaikh = iterative_prices_fixed_capital(
                    matrix,
                    capital_matrix,
                    depreciation,
                    labour_cost,
                    output_real,
                    initial=value_price,
                )
                if not (fixed_shaikh.prices > 0).all():
                    fixed_shaikh = None
            except ValueError as exc:
                warnings.warn(
                    f"Fixed-capital Sraffa skipped for {year}: {exc}",
                    stacklevel=2,
                )

        for code in matrix.index:
            records.append(
                {
                    "year": int(year),
                    "industry_code": code,
                    "P_V": float(value_price.loc[code] * output_real.loc[code] * price.loc[code]),
                    "PP_Sraffa": float(
                        production_price.loc[code] * output_real.loc[code] * price.loc[code]
                    ),
                    "PP_Shaikh": float(
                        iterated_price.loc[code] * output_real.loc[code] * price.loc[code]
                    ),
                    "p_sraffa": float(production_price.loc[code]),
                    "p_shaikh": float(iterated_price.loc[code]),
                    "p_v": float(value_price.loc[code]),
                    "PP_Sraffa_fixed": float(
                        fixed_price.loc[code] * output_real.loc[code] * price.loc[code]
                    )
                    if fixed_price is not None
                    else float("nan"),
                    "p_sraffa_fixed": float(fixed_price.loc[code])
                    if fixed_price is not None
                    else float("nan"),
                    "r_fixed": float(fixed_rate) if fixed_rate is not None else float("nan"),
                    "PP_Shaikh_fixed": float(
                        _normalise(fixed_shaikh.prices, output_real).loc[code]
                        * output_real.loc[code]
                        * price.loc[code]
                    )
                    if fixed_shaikh is not None
                    else float("nan"),
                    "p_shaikh_fixed": float(
                        _normalise(fixed_shaikh.prices, output_real).loc[code]
                    )
                    if fixed_shaikh is not None
                    else float("nan"),
                    "r_shaikh_fixed": float(fixed_shaikh.profit_rate)
                    if fixed_shaikh is not None
                    else float("nan"),
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
            "matrix_prices": "deflated 2017-dollar Use tables, annual",
            "profit_rate": "sum(S_real)/sum(K_real), current year",
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
