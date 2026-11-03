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

import pandas as pd


@dataclass
class RegulatingResult:
    panel: pd.DataFrame
    summary: dict


def build_regulating_benchmark(
    panel: pd.DataFrame,
    regulating: pd.DataFrame,
    *,
    base_column: str = "PP_Sraffa",
    theta: float = 0.10,
) -> RegulatingResult:
    """Attach ``PP_reg`` and cost-heterogeneity columns to the panel.

    ``regulating`` must contain ``industry_code, unit_cost, unit_cost_min,
    cost_cv``. The low-cost sub-industry's relative cost gap is applied only
    partially: ``factor = 1 - theta * (1 - unit_cost_min / unit_cost)``.
    """
    if base_column not in panel.columns:
        raise KeyError(f"Missing base benchmark column {base_column!r}")

    out = panel.merge(
        regulating.loc[
            :, ["industry_code", "unit_cost", "unit_cost_min", "cost_cv"]
        ],
        on="industry_code",
        how="left",
        validate="many_to_one",
    )

    raw_gap = 1.0 - (out["unit_cost_min"] / out["unit_cost"])
    raw_gap = raw_gap.clip(lower=0.0, upper=0.5)
    out["regulating_factor"] = 1.0 - theta * raw_gap
    out["cost_dispersion"] = out["cost_cv"]
    out["regulating_cost"] = out["unit_cost"] * out["regulating_factor"]
    out["PP_reg"] = out[base_column] * out["regulating_factor"]

    mapped = out["regulating_factor"].notna()
    summary = {
        "theta": float(theta),
        "n_mapped": int(mapped.sum()),
        "n_total": int(out.shape[0]),
        "mean_regulating_factor": float(out.loc[mapped, "regulating_factor"].mean()),
        "mean_cost_dispersion": float(out.loc[mapped, "cost_dispersion"].mean()),
        "coverage_share": float(mapped.mean()),
        "base_column": base_column,
        "source": "Census ecnbasic 6-digit sub-industry unit costs",
    }
    return RegulatingResult(panel=out, summary=summary)
