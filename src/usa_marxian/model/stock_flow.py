"""Stock-flow cross-dual simulation for Shaikh-style real competition.

The simulation uses the state-space dataset:

    p_i, q_i, k_i, I_i, u_i, w, l_i, A_t

Final demand is reconstructed from observed output and the real input matrix:

    F_t = q_t - A_t q_t

and is treated as exogenous. The behavioural block is:

    cost_i   = (p A)_i + w l_i
    r_i      = (p_i - cost_i) / cost_i
    r_bar    = (p q - cost q) / (cost q)

    p_i' = p_i exp(-alpha (r_i - r_bar))
    q_i' = q_i + beta (D_i - q_i),    D_i = (A q)_i + F_i
    I_i  = k_i [gamma0 + gamma1 (r_i - r_bar) + gamma2 (u_i - 1)]
    k_i' = (1 - delta_i) k_i + I_i
    w'   = w [1 + phi (U - 1)]

This is a deliberately small structural model. It is estimated by matching
simulated and observed price, output and capital paths.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution

PARAMETER_BOUNDS = {
    "alpha": (0.0, 0.30),
    "beta": (0.0, 0.80),
    "gamma0": (0.0, 0.15),
    "gamma1": (0.0, 0.50),
    "gamma2": (0.0, 0.50),
    "phi": (0.0, 0.30),
    "kappa": (0.0, 1.0),
}


@dataclass
class StockFlowParams:
    # Calibrated on 2005-2023 with exogenous final demand. The price block
    # remains weak; output and capital are the well-fitting dimensions.
    alpha: float = 0.0185
    beta: float = 0.80
    gamma0: float = 0.125
    gamma1: float = 0.04
    gamma2: float = 0.50
    phi: float = 0.0
    kappa: float = 0.0

    def to_array(self) -> np.ndarray:
        return np.array(
            [
                self.alpha,
                self.beta,
                self.gamma0,
                self.gamma1,
                self.gamma2,
                self.phi,
                self.kappa,
            ]
        )

    @classmethod
    def from_array(cls, values: np.ndarray) -> StockFlowParams:
        return cls(*[float(value) for value in values])

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class StockFlowResult:
    trajectories: pd.DataFrame
    metrics: pd.DataFrame
    params: StockFlowParams
    summary: dict


def _matrix_dict(long: pd.DataFrame) -> dict[int, pd.DataFrame]:
    matrices = {}
    for year, group in long.groupby("year"):
        matrices[int(year)] = group.pivot_table(
            index="commodity_code",
            columns="industry_code",
            values="value",
            aggfunc="sum",
        ).fillna(0.0)
    return matrices


def _wide(state: pd.DataFrame, column: str) -> pd.DataFrame:
    return state.pivot(index="year", columns="industry_code", values=column).sort_index()


def _base_ratios(state: pd.DataFrame, base_year: int) -> pd.Series:
    base = state.loc[state["year"] == base_year].set_index("industry_code")
    return (base["quantity"] / base["capital"]).astype(float)


def _final_demand(
    output: pd.Series,
    matrix: pd.DataFrame,
) -> pd.Series:
    aligned = output.reindex(matrix.index).astype(float)
    intermediate = matrix.dot(output.reindex(matrix.columns).astype(float))
    return aligned - intermediate


def _metrics(observed: np.ndarray, simulated: np.ndarray, label: str) -> dict:
    mask = (
        np.isfinite(observed)
        & np.isfinite(simulated)
        & (observed > 0)
        & (simulated > 0)
    )
    observed = observed[mask]
    simulated = simulated[mask]
    if observed.size < 3:
        return {"variable": label, "n": 0}
    error = np.log(observed) - np.log(simulated)
    return {
        "variable": label,
        "n": int(observed.size),
        "rmse_log": float(np.sqrt(np.mean(error**2))),
        "mae_log": float(np.mean(np.abs(error))),
        "corr": float(np.corrcoef(observed, simulated)[0, 1]),
        "mape_pct": float(100.0 * np.mean(np.abs(observed - simulated) / observed)),
    }


def simulate(
    state: pd.DataFrame,
    matrices_real: pd.DataFrame,
    params: StockFlowParams,
    *,
    start_year: int | None = None,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Simulate the cross-dual system from the first available year."""
    matrices = _matrix_dict(matrices_real)
    years = sorted(set(state["year"].astype(int)) & set(matrices))
    if start_year is not None:
        years = [year for year in years if year >= start_year]
    if end_year is not None:
        years = [year for year in years if year <= end_year]
    if len(years) < 3:
        raise ValueError("Need at least three years for a simulation")

    base_year = 2017 if 2017 in state["year"].unique() else years[0]
    base_ratio = _base_ratios(state, base_year)
    codes = sorted(base_ratio.index)
    for matrix in matrices.values():
        codes = [code for code in codes if code in matrix.index and code in matrix.columns]

    p_wide = _wide(state, "price").reindex(columns=codes)
    q_wide = _wide(state, "quantity").reindex(columns=codes)
    k_wide = _wide(state, "capital").reindex(columns=codes)
    l_wide = _wide(state, "labour_coefficient_real").reindex(columns=codes)
    w_series = state.groupby("year")["wage_rate"].first()
    dep_wide = _wide(state, "depreciation").reindex(columns=codes)
    investment_wide = _wide(state, "investment").reindex(columns=codes)

    p = p_wide.loc[years[0]].to_numpy(dtype=float)
    q = q_wide.loc[years[0]].to_numpy(dtype=float)
    k = k_wide.loc[years[0]].to_numpy(dtype=float)
    w = float(w_series.loc[years[0]])
    base = base_ratio.reindex(codes).to_numpy(dtype=float)

    rows = []
    for index in range(len(years) - 1):
        year = years[index]
        next_year = years[index + 1]
        matrix = matrices[year].reindex(index=codes, columns=codes).to_numpy(dtype=float)
        labour = l_wide.loc[year].reindex(codes).to_numpy(dtype=float)
        final_demand = _final_demand(
            q_wide.loc[year].reindex(codes),
            matrices[year].reindex(index=codes, columns=codes),
        ).to_numpy(dtype=float)

        cost = matrix.T @ p + w * labour
        cost = np.clip(cost, 1e-12, None)
        rates = np.clip((p - cost) / cost, -0.99, 2.0)
        denominator = float(cost @ q)
        average = float((p @ q - denominator) / denominator) if denominator > 0 else 0.0

        intermediate = matrix @ q
        demand = intermediate + final_demand
        q_new = q + params.beta * (demand - q)
        q_new = np.clip(q_new, 1e-6, None)

        cost_ratio = np.clip(cost / np.clip(p, 1e-12, None), 0.0, 3.0)
        p_new = p * (1.0 + params.kappa * (cost_ratio - 1.0))
        p_new = p_new * np.exp(
            np.clip(-params.alpha * (rates - average), -1.0, 1.0)
        )
        denominator_price = float(p_new @ q_new)
        if denominator_price > 0:
            p_new = p_new * (float(q_new.sum()) / denominator_price)
        p_new = np.clip(p_new, 1e-6, None)

        utilization = (q_new / k) / np.clip(base, 1e-12, None)
        aggregate_utilization = float(
            (q_new @ utilization) / max(q_new.sum(), 1e-12)
        )
        w_new = w * (1.0 + params.phi * (aggregate_utilization - 1.0))
        w_new = max(w_new, 1e-6)

        investment = k * (
            params.gamma0
            + params.gamma1 * (rates - average)
            + params.gamma2 * (utilization - 1.0)
        )
        investment = np.clip(investment, 0.0, None)
        depreciation = dep_wide.loc[year].reindex(codes).to_numpy(dtype=float)
        depreciation = np.clip(depreciation, 0.0, None)
        k_new = k - depreciation + investment
        k_new = np.clip(k_new, 1e-6, None)

        for position, code in enumerate(codes):
            rows.append(
                {
                    "year": int(next_year),
                    "industry_code": code,
                    "p_sim": float(p_new[position]),
                    "q_sim": float(q_new[position]),
                    "k_sim": float(k_new[position]),
                    "I_sim": float(investment[position]),
                    "p_obs": float(p_wide.loc[next_year, code]),
                    "q_obs": float(q_wide.loc[next_year, code]),
                    "k_obs": float(k_wide.loc[next_year, code]),
                    "I_obs": float(investment_wide.loc[next_year, code]),
                }
            )

        p, q, k, w = p_new, q_new, k_new, w_new

    return pd.DataFrame(rows)


def metrics_table(trajectories: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for simulated, observed, label in (
        ("p_sim", "p_obs", "price"),
        ("q_sim", "q_obs", "quantity"),
        ("k_sim", "k_obs", "capital"),
        ("I_sim", "I_obs", "investment"),
    ):
        rows.append(
            _metrics(
                trajectories[observed].to_numpy(dtype=float),
                trajectories[simulated].to_numpy(dtype=float),
                label,
            )
        )
    return pd.DataFrame(rows)


def _objective(
    values: np.ndarray,
    state: pd.DataFrame,
    matrices_real: pd.DataFrame,
) -> float:
    params = StockFlowParams.from_array(values)
    try:
        trajectories = simulate(state, matrices_real, params)
        metrics = metrics_table(trajectories).set_index("variable")
        if "rmse_log" not in metrics.columns or metrics["rmse_log"].isna().any():
            return 1e6
        return float(
            metrics.loc["price", "rmse_log"]
            + metrics.loc["quantity", "rmse_log"]
            + 0.5 * metrics.loc["capital", "rmse_log"]
        )
    except Exception:
        return 1e6


def fit_stock_flow(
    state: pd.DataFrame,
    matrices_real: pd.DataFrame,
    *,
    calibrate: bool = True,
    seed: int = 20261103,
    max_iter: int = 20,
) -> StockFlowResult:
    """Calibrate the adjustment parameters and return simulated trajectories."""
    params = StockFlowParams()
    if calibrate:
        bounds = [PARAMETER_BOUNDS[name] for name in (
            "alpha",
            "beta",
            "gamma0",
            "gamma1",
            "gamma2",
            "phi",
            "kappa",
        )]
        result = differential_evolution(
            lambda values: _objective(values, state, matrices_real),
            bounds,
            seed=seed,
            maxiter=max_iter,
            popsize=8,
            polish=True,
            workers=1,
        )
        params = StockFlowParams.from_array(result.x)

    trajectories = simulate(state, matrices_real, params)
    metrics = metrics_table(trajectories)
    summary = {
        "params": params.to_dict(),
        "start_year": int(trajectories["year"].min()),
        "end_year": int(trajectories["year"].max()),
        "n_observations": int(trajectories.shape[0]),
        "metrics": metrics.to_dict(orient="records"),
        "calibrated": bool(calibrate),
    }
    return StockFlowResult(
        trajectories=trajectories,
        metrics=metrics,
        params=params,
        summary=summary,
    )
