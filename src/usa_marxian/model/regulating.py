"""Regulating-capital benchmark from Census cost and concentration data.

Shaikh's "real competition" prices are set by the lowest-cost producers in each
industry. Without plant-level data, this module uses two Census proxies:

* ``unit_cost_i = (payroll + materials) / receipts`` — the average prime cost;
* ``concentration_i`` — the share of receipts of the top firms.

The regulating cost is modelled as a fraction below average cost, where the
fraction is larger when the industry is less concentrated:

    cost_dispersion_i = 1 - concentration_i
    regulating_cost_i = unit_cost_i * (1 - theta * cost_dispersion_i)
    PP_reg_i = PP_Sraffa_i * (1 - theta * cost_dispersion_i)

``theta`` is a calibration parameter; the benchmark is then normalised to total
gross output. Industries without Census coverage fall back to the Sraffa price.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class RegulatingResult:
    panel: pd.DataFrame
    summary: dict


def build_regulating_benchmark(
    panel: pd.DataFrame,
    unit_cost: pd.DataFrame,
    concentration: pd.DataFrame,
    *,
    theta: float = 0.5,
    base_column: str = "PP_Sraffa",
) -> RegulatingResult:
    """Attach ``PP_reg`` and cost-heterogeneity columns to the panel."""
    if base_column not in panel.columns:
        raise KeyError(f"Missing base benchmark column {base_column!r}")

    out = panel.merge(
        unit_cost.loc[:, ["industry_code", "unit_cost"]],
        on="industry_code",
        how="left",
        validate="many_to_one",
    )
    out = out.merge(
        concentration.loc[:, ["industry_code", "concentration"]],
        on="industry_code",
        how="left",
        validate="many_to_one",
    )

    out["cost_dispersion"] = 1.0 - out["concentration"]
    mapped = out["cost_dispersion"].notna()
    out["regulating_factor"] = np.where(
        mapped, 1.0 - theta * out["cost_dispersion"], 1.0
    )
    out["regulating_cost"] = out["unit_cost"] * out["regulating_factor"]
    out["PP_reg"] = out[base_column] * out["regulating_factor"]

    total_go = float(out["GO"].sum())
    total_reg = float(out["PP_reg"].sum())
    if total_reg > 0:
        out["PP_reg"] = out["PP_reg"] * (total_go / total_reg)

    summary = {
        "theta": float(theta),
        "n_mapped": int(mapped.sum()),
        "n_total": int(out.shape[0]),
        "mean_cost_dispersion": float(
            out.loc[mapped, "cost_dispersion"].mean()
        ),
        "coverage_share": float(mapped.mean()),
        "base_column": base_column,
        "source": "Census ecnbasic unit cost + ecnsize concentration",
    }
    return RegulatingResult(panel=out, summary=summary)
