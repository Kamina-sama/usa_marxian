"""State-space dataset for Shaikh-style real competition.

The table is one row per market industry-year plus a long annual input-output
matrix. It contains the minimum state needed for a stock-flow cross-dual model:

    price_i        gross-output price index, 2017 = 1
    quantity_i     real gross output, millions of 2017 dollars
    capital_i      real net fixed capital stock, millions of 2017 dollars
    investment_i   real gross investment, millions of 2017 dollars
    depreciation_i real depreciation, millions of 2017 dollars
    utilization_i  output-capital ratio, normalised to 1 in the base year
    wage_rate      aggregate money wage, dollars per hour
    labour_i       labour hours, millions
    l_i            direct labour coefficient, hours per current dollar
    l_real_i       direct labour coefficient, hours per 2017 dollar
    A_t            annual commodity-by-industry input matrix

Prices and quantities are based on broad-sector gross-output deflators. The
capital deflator is the implicit deflator from the current-cost and fixed-cost
net stock files. This is a measurement dataset, not yet a behavioural model.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..data.bea_final_demand import attach_final_demand
from .sraffa import build_real_technical_matrices, build_technical_matrices

STATE_COLUMNS = [
    "year",
    "industry_code",
    "industry_name",
    "price",
    "quantity",
    "capital",
    "investment",
    "depreciation",
    "utilization",
    "wage_rate",
    "wage_rate_i",
    "fte",
    "labour_hours",
    "labour_coefficient",
    "labour_coefficient_real",
    "hours_source",
    "consumption_demand",
    "government_demand",
    "exports_demand",
    "imports_demand",
    "GO",
    "V",
    "capital_current",
    "capital_real",
]


@dataclass
class StateSpaceResult:
    state: pd.DataFrame
    matrices: pd.DataFrame
    matrices_real: pd.DataFrame
    macro: pd.DataFrame
    summary: dict


def _matrix_long(matrices: dict[int, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    for year, matrix in sorted(matrices.items()):
        for commodity, row in matrix.iterrows():
            for industry, value in row.items():
                if value:
                    rows.append(
                        {
                            "year": int(year),
                            "commodity_code": str(commodity),
                            "industry_code": str(industry),
                            "value": float(value),
                        }
                    )
    return pd.DataFrame(rows)


def build_state_space(
    panel: pd.DataFrame,
    use_matrices: pd.DataFrame,
    accounts: pd.DataFrame,
    capital_detail: pd.DataFrame,
    *,
    base_year: int = 2017,
    market_only: bool = True,
    final_demand: pd.DataFrame | None = None,
) -> StateSpaceResult:
    """Build the industry-year state table and annual matrices."""
    data = panel.copy()
    if market_only:
        if "is_market" not in data.columns:
            raise KeyError("Panel has no is_market column")
        data = data.loc[data["is_market"]].copy()

    required = {"year", "industry_code", "GO", "V", "go_price"}
    missing = required.difference(data.columns)
    if missing:
        raise KeyError(f"Panel missing state-space columns: {sorted(missing)}")

    detail = capital_detail.rename(
        columns={
            "M_current": "capital_current",
            "M_real": "capital_real",
            "I_current": "investment_current",
            "D_current": "depreciation_current",
        }
    )
    data = data.merge(
        detail,
        on=["year", "industry_code"],
        how="left",
        validate="many_to_one",
    )
    capital_columns = [
        "capital_current",
        "capital_real",
        "investment_current",
        "depreciation_current",
    ]
    if data.loc[:, capital_columns].isna().any().any():
        missing_rows = data.loc[
            data.loc[:, capital_columns].isna().any(axis=1),
            ["year", "industry_code"],
        ]
        raise ValueError(
            "Capital detail missing for state-space rows: "
            f"{missing_rows.head().to_dict(orient='records')}"
        )

    data["price"] = data["go_price"] / 100.0
    data["quantity"] = data["GO"] / data["price"]
    data["capital"] = data["capital_real"]
    data["capital_deflator"] = data["capital_current"] / data["capital_real"]
    data["investment"] = data["investment_current"] / data["capital_deflator"]
    data["depreciation"] = data["depreciation_current"] / data["capital_deflator"]

    output_capital = data["quantity"] / data["capital"]
    base = data.loc[data["year"] == base_year]
    base_ratio = (
        base.assign(ratio=base["quantity"] / base["capital"])
        .groupby("industry_code")["ratio"]
        .mean()
    )
    data["utilization"] = output_capital / data["industry_code"].map(base_ratio)

    macro = accounts.loc[:, [column for column in ("L", "V", "N", "S") if column in accounts]].copy()
    macro["wage_rate"] = macro["V"] / macro["L"]
    data["wage_rate"] = data["year"].map(macro["wage_rate"])
    if "labour_hours" not in data.columns:
        data["labour_hours"] = data["V"] * 1e6 / data["wage_rate"]
        data["hours_source"] = "compensation"
    if "wage_rate_i" not in data.columns:
        data["wage_rate_i"] = data["V"] / data["labour_hours"]
    data["labour_coefficient"] = data["labour_hours"] / (data["GO"] * 1e6)
    data["labour_coefficient_real"] = data["labour_hours"] / (
        data["quantity"] * 1e6
    )
    if final_demand is not None:
        data = attach_final_demand(data, final_demand)

    state = data.loc[
        :, [column for column in STATE_COLUMNS if column in data.columns]
    ].sort_values(["year", "industry_code"])
    complete = [
        "price",
        "quantity",
        "capital",
        "investment",
        "depreciation",
        "utilization",
        "wage_rate",
        "labour_hours",
        "labour_coefficient",
        "labour_coefficient_real",
    ]
    state = state.dropna(subset=complete).reset_index(drop=True)
    if state.empty:
        raise ValueError("State space has no complete industry-year rows")

    matrices = build_technical_matrices(use_matrices, panel, base_year=base_year)
    matrices_real = build_real_technical_matrices(matrices, panel)
    matrix_long = _matrix_long(matrices)
    matrix_real_long = _matrix_long(matrices_real)

    summary = {
        "start_year": int(state["year"].min()),
        "end_year": int(state["year"].max()),
        "n_years": int(state["year"].nunique()),
        "n_industries": int(state["industry_code"].nunique()),
        "n_matrices": int(len(matrices)),
        "n_matrices_real": int(len(matrices_real)),
        "base_year": int(base_year),
        "market_only": bool(market_only),
        "n_observations": int(state.shape[0]),
        "price_start_year": int(state["year"].min()),
        "state_columns": list(state.columns),
        "matrix_rows": int(matrix_long.shape[0]),
        "matrix_real_rows": int(matrix_real_long.shape[0]),
    }
    return StateSpaceResult(
        state=state.reset_index(drop=True),
        matrices=matrix_long,
        matrices_real=matrix_real_long,
        macro=macro.reset_index(),
        summary=summary,
    )
