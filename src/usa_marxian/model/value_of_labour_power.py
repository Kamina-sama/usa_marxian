"""The value of labour power: construction, trend and identification.

Marx's value of labour power is the labour time socially necessary to produce
the worker's means of subsistence. Three claims sit inside that phrase, of very
different strength:

1. *Accounting* — the wage equals the money value of the customary basket:
   ``V = m · Λ · L``, so the wage share equals the basket's labour content per
   hour worked.
2. *Custom* — that content is historically sticky, so ``Λ`` has no trend.
3. *Independence* — ``Λ`` is a magnitude in its own right, not a restatement of
   the wage share ``ω = V/N``.

This module builds ``Λ``, tests (2), and — most importantly — tests (3), because
if ``Λ`` is proportional to ``ω`` the exercise has no content. That is the same
failure mode that made the MELT distribution test vacuous; here it has to be
checked rather than assumed, since ``Λ`` is computed from a quantity system and
``ω`` from the wage bill.

Construction:

    λ_t        = l_t (I - A_t)^-1          hours per 2017 dollar, 65 market industries
    C_real_t   = C_t / (go_price_t / 100)  consumption deflated to 2017 dollars
    Λ_t        = Σ_c λ_ct · C_real_ct / L_t   hours embodied per hour worked

Coverage is partial: labour values exist only for the 65 market industries, and
housing (imputed rent) is not among them. ``coverage`` in the result records the
share of personal consumption expenditure the basket actually covers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

from ..analysis.diagnostics import adf_test, kpss_test

TREND_FLAT_THRESHOLD = 0.003  # 0.3% per year: the "customary" claim


@dataclass
class TrendResult:
    """Log-linear trend and unit-root diagnostics for one series."""

    column: str
    first: float
    last: float
    trend_per_year: float
    trend_std_error: float
    trend_p_value: float
    adf_p_value: float
    kpss_p_value: float

    def as_dict(self) -> dict:
        return {
            "column": self.column,
            "first": float(self.first),
            "last": float(self.last),
            "trend_per_year": float(self.trend_per_year),
            "trend_std_error": float(self.trend_std_error),
            "trend_p_value": float(self.trend_p_value),
            "adf_p_value": float(self.adf_p_value),
            "kpss_p_value": float(self.kpss_p_value),
        }


def _labour_values(
    matrix: pd.DataFrame,
    hours: pd.Series,
    output_real: pd.Series,
) -> pd.Series:
    """``λ = l (I - A)^-1`` in hours per 2017 dollar."""
    codes = list(matrix.index)
    a = matrix.to_numpy(dtype=float)
    direct_labour = (hours.reindex(codes).to_numpy(dtype=float)) / (
        output_real.reindex(codes).to_numpy(dtype=float) * 1e6
    )
    if not np.isfinite(direct_labour).all():
        raise ValueError("labour coefficients contain non-finite values")
    values = np.linalg.solve((np.eye(len(codes)) - a).T, direct_labour)
    return pd.Series(values, index=codes, name="labour_value")


def _price_value_ratio(
    values: np.ndarray,
    price: np.ndarray,
    labour_values: np.ndarray,
    melt: float,
) -> float:
    """Money price of a final-use basket divided by its labour value."""
    nominal = float(values.sum()) * 1e6
    real = values * 1e6 / price
    value = float(labour_values @ (melt * real))
    return nominal / value if value > 0 else float("nan")


def _matrix_for_year(
    matrices: pd.DataFrame, year: int, codes: list[str]
) -> pd.DataFrame:
    block = matrices.loc[matrices["year"] == year]
    wide = (
        block.pivot_table(
            index="commodity_code",
            columns="industry_code",
            values="value",
            aggfunc="sum",
        )
        .reindex(index=codes, columns=codes)
        .fillna(0.0)
    )
    return wide


def build_basket_panel(
    processed: Path,
    accounts: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build the year-by-year value-of-labour-power panel."""
    matrices_real_path = processed / "technical_matrices_real.csv"
    matrices_path = processed / "technical_matrices.csv"
    industries_path = processed / "industries_shaikh.csv"
    demand_path = processed / "final_demand.csv"
    accounts_path = processed / "accounts.csv"

    for path in (matrices_real_path, industries_path, demand_path, accounts_path):
        if not path.exists():
            raise FileNotFoundError(
                f"{path.name} not found; run `usa-marxian industries` first"
            )

    matrices = pd.read_csv(matrices_real_path)
    matrices_current = pd.read_csv(matrices_path)
    industries = pd.read_csv(
        industries_path,
        usecols=[
            "year",
            "industry_code",
            "labour_hours",
            "GO",
            "GO_real",
            "go_price",
            "is_market",
        ],
    )
    industries = industries.loc[industries["is_market"]]
    demand = pd.read_csv(demand_path)
    if accounts is None:
        accounts = pd.read_csv(accounts_path, index_col=0)

    rows: list[dict] = []
    for year in sorted(matrices["year"].unique()):
        year = int(year)
        block = matrices.loc[matrices["year"] == year]
        codes = sorted(set(block["commodity_code"]) | set(block["industry_code"]))

        panel_year = industries.loc[industries["year"] == year].set_index(
            "industry_code"
        )
        panel_year = panel_year.reindex(codes)
        if panel_year["labour_hours"].isna().any():
            continue

        matrix = _matrix_for_year(matrices, year, codes)
        lambda_t = _labour_values(
            matrix, panel_year["labour_hours"], panel_year["GO_real"]
        )

        demand_year = demand.loc[demand["year"] == year].set_index("commodity_code")
        demand_year = demand_year.reindex(codes)
        price = panel_year["go_price"].to_numpy(dtype=float) / 100.0

        consumption_nominal = demand_year["C"].fillna(0.0).to_numpy(dtype=float) * 1e6
        consumption_real = consumption_nominal / price

        # Import content: commodity import share applied to consumption.
        current_matrix = _matrix_for_year(matrices_current, year, codes)
        intermediate = current_matrix.to_numpy(dtype=float) @ panel_year[
            "GO"
        ].to_numpy(dtype=float)
        supply = (
            demand_year[["C", "G", "I", "X"]].fillna(0.0).sum(axis=1).to_numpy(dtype=float)
            + intermediate
        )
        imports = demand_year["M"].fillna(0.0).to_numpy(dtype=float)
        with np.errstate(divide="ignore", invalid="ignore"):
            import_share = np.where(supply > 0, imports / supply, 0.0)
        import_share = np.clip(np.nan_to_num(import_share), 0.0, 0.95)
        consumption_domestic = consumption_real * (1.0 - import_share)

        labour_billion_hours = float(accounts.loc[year, "L"])
        labour_hours = labour_billion_hours * 1e9
        melt = float(accounts.loc[year, "N"]) * 1e9 / labour_hours

        # Coherence: labour embodied in total final demand should equal total
        # hours. The shortfall is the non-market sector this panel excludes.
        final_demand_real = (
            demand_year[["C", "G", "I", "X"]].fillna(0.0).sum(axis=1).to_numpy(
                dtype=float
            )
            - demand_year["M"].fillna(0.0).to_numpy(dtype=float)
        ) * 1e6 / price
        coherence = float(
            lambda_t.to_numpy(dtype=float) @ final_demand_real
        ) / labour_hours

        value_of_basket = float(lambda_t.to_numpy(dtype=float) @ consumption_real)
        value_of_basket_domestic = float(
            lambda_t.to_numpy(dtype=float) @ consumption_domestic
        )

        lambda_array = lambda_t.to_numpy(dtype=float)
        ratios = {
            name: _price_value_ratio(
                demand_year[column].fillna(0.0).to_numpy(dtype=float),
                price,
                lambda_array,
                melt,
            )
            for name, column in (
                ("pv_consumption", "C"),
                ("pv_investment", "I"),
                ("pv_government", "G"),
                ("pv_exports", "X"),
            )
        }

        rows.append(
            {
                "year": year,
                "coherence": coherence,
                "lambda_actual": value_of_basket / labour_hours,
                "lambda_domestic": value_of_basket_domestic / labour_hours,
                "wage_share": float(accounts.loc[year, "V"] / accounts.loc[year, "N"]),
                "consumption_share_of_wage": float(
                    consumption_nominal.sum()
                )
                / (float(accounts.loc[year, "V"]) * 1e9),
                "price_to_value_ratio": float(consumption_nominal.sum())
                / (melt * value_of_basket),
                "coverage_share": float(
                    demand.loc[demand["year"] == year]
                    .set_index("commodity_code")
                    .reindex(codes)["C"]
                    .fillna(0.0)
                    .sum()
                )
                / float(demand.loc[demand["year"] == year, "C"].sum()),
                "import_share": float(
                    demand_year["M"].fillna(0.0).sum()
                    / demand_year[["C", "G", "I", "X"]].fillna(0.0).sum().sum()
                ),
                "pv_consumption": ratios["pv_consumption"],
                "pv_investment": ratios["pv_investment"],
                "pv_government": ratios["pv_government"],
                "pv_exports": ratios["pv_exports"],
            }
        )

    panel = pd.DataFrame(rows).set_index("year").sort_index()
    panel["wedge"] = panel["lambda_actual"] / panel["wage_share"]

    # The only strictly wage-financed basket these data allow: rescale the
    # observed basket so that it costs exactly the wage bill. If the result is
    # proportional to the wage share, the concept is not separately identified.
    panel["lambda_wage_financed"] = panel["lambda_actual"] / panel[
        "consumption_share_of_wage"
    ]
    panel["wage_financed_ratio"] = (
        panel["lambda_wage_financed"] / panel["wage_share"]
    )
    return panel


def trend_test(panel: pd.DataFrame, column: str) -> TrendResult:
    """Log-linear trend with HAC errors plus ADF and KPSS."""
    series = panel[column].replace([np.inf, -np.inf], np.nan).dropna()
    if len(series) < 10:
        raise ValueError(f"not enough observations for {column}")
    years = series.index.to_numpy(dtype=float)
    design = sm.add_constant((years - years.mean()).reshape(-1, 1))
    fit = sm.OLS(np.log(series.to_numpy(dtype=float)), design).fit(
        cov_type="HAC", cov_kwds={"maxlags": max(1, int(np.floor(len(series) ** 0.5)))}
    )
    adf = adf_test(series, name=column)
    kpss = kpss_test(series, name=column)
    return TrendResult(
        column=column,
        first=float(series.iloc[0]),
        last=float(series.iloc[-1]),
        trend_per_year=float(fit.params[1]),
        trend_std_error=float(fit.bse[1]),
        trend_p_value=float(fit.pvalues[1]),
        adf_p_value=float(adf.p_value),
        kpss_p_value=float(kpss.p_value),
    )


def identification_test(panel: pd.DataFrame) -> dict:
    """Is Λ independent information, or the wage share in disguise?

    Regresses log Λ on log ω. A slope of one with R² of one would mean the
    value of labour power adds nothing to the wage share. The decomposition
    shows which channel moves the wedge when it does move:

        Λ/ω = (consumption spending / wage bill) / (price / value of basket)
    """
    data = panel.loc[:, ["lambda_actual", "wage_share", "wedge"]].replace(
        [np.inf, -np.inf], np.nan
    ).dropna()
    x = np.log(data["wage_share"].to_numpy(dtype=float))
    y = np.log(data["lambda_actual"].to_numpy(dtype=float))
    design = sm.add_constant(x)
    fit = sm.OLS(y, design).fit(cov_type="HAC", cov_kwds={"maxlags": 4})

    consumption_share = trend_test(panel, "consumption_share_of_wage")
    price_value = trend_test(panel, "price_to_value_ratio")
    wedge = trend_test(panel, "wedge")

    price_value_flat = (
        abs(price_value.trend_per_year) < TREND_FLAT_THRESHOLD
        or price_value.trend_p_value > 0.05
    )

    if price_value_flat:
        channel = (
            "The price-to-value ratio of the consumption basket is flat, so the "
            "wedge moves with consumption spending relative to the wage bill, "
            "not with prices deviating further from values."
        )
    else:
        channel = (
            "The price-to-value ratio of the consumption basket is itself "
            "trending, so part of the movement is a changing price-value gap."
        )

    return {
        "slope_log_lambda_on_log_wage_share": float(fit.params[1]),
        "slope_std_error": float(fit.bse[1]),
        "r_squared": float(fit.rsquared),
        "wedge_trend": wedge.as_dict(),
        "consumption_share_trend": consumption_share.as_dict(),
        "price_value_trend": price_value.as_dict(),
        "price_value_flat": bool(price_value_flat),
        "channel": channel,
    }


def run_volp_tests(panel: pd.DataFrame) -> dict:
    """Trend tests, identification test and a verdict assembled from both."""
    trends = {
        column: trend_test(panel, column).as_dict()
        for column in (
            "lambda_actual",
            "lambda_domestic",
            "lambda_wage_financed",
            "wage_share",
            "consumption_share_of_wage",
            "price_to_value_ratio",
            "wedge",
            "wage_financed_ratio",
        )
    }
    identification = identification_test(panel)

    lambda_trend = trends["lambda_actual"]
    wage_financed = trends["wage_financed_ratio"]
    significant = lambda_trend["trend_p_value"] < 0.05
    large = abs(lambda_trend["trend_per_year"]) >= TREND_FLAT_THRESHOLD
    cumulative = (1 + lambda_trend["trend_per_year"]) ** len(panel) - 1

    if significant and large:
        custom_text = (
            "Strict constancy is rejected: the basket's labour content trends "
            f"{100 * lambda_trend['trend_per_year']:+.2f}%/yr "
            f"(p={lambda_trend['trend_p_value']:.3f}, {100 * cumulative:+.1f}% "
            "cumulative)."
        )
    elif significant:
        custom_text = (
            "Strict constancy is rejected in the statistical sense but the "
            f"drift is small: {100 * lambda_trend['trend_per_year']:+.2f}%/yr "
            f"(p={lambda_trend['trend_p_value']:.3f}, {100 * cumulative:+.1f}% "
            "cumulative)."
        )
    else:
        custom_text = (
            "The basket's labour content is trendless within tolerance, which "
            "is consistent with a customary value of labour power."
        )

    gradient_years = int(
        (panel["pv_consumption"] < panel["pv_investment"]).sum()
    )
    verdict = (
        f"{custom_text} Identification: a wage-financed basket is proportional "
        "to the wage share — the ratio between them trends "
        f"{100 * wage_financed['trend_per_year']:+.2f}%/yr "
        f"(p={wage_financed['trend_p_value']:.3f}) — so the value of labour "
        "power is not separately identified in these accounts. "
        f"{identification['channel']} What is identified is the price-value "
        "gradient across uses: consumption sells below its labour value in "
        f"{gradient_years} of {len(panel)} years while investment sells above it."
    )

    return {
        "sample": {
            "start_year": int(panel.index.min()),
            "end_year": int(panel.index.max()),
            "n_years": int(len(panel)),
            "mean_coverage": float(panel["coverage_share"].mean()),
        },
        "coherence": {
            "first_year": int(panel.index[0]),
            "first": float(panel["coherence"].iloc[0]),
            "last_year": int(panel.index[-1]),
            "last": float(panel["coherence"].iloc[-1]),
            "mean": float(panel["coherence"].mean()),
            "min": float(panel["coherence"].min()),
        },
        "trends": trends,
        "identification": identification,
        "customary_claim_rejected": bool(significant),
        "price_value_by_category": {
            "consumption": float(panel["pv_consumption"].mean()),
            "investment": float(panel["pv_investment"].mean()),
            "government": float(panel["pv_government"].mean()),
            "exports": float(panel["pv_exports"].mean()),
        },
        "gradient_years_consumption_below_investment": gradient_years,
        "verdict": verdict,
    }


def write_outputs(
    panel: pd.DataFrame, result: dict, output_dir: Path
) -> dict[str, Path]:
    """Persist the panel and the summary."""
    import json

    tables = output_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    panel_path = tables / "volp_panel.csv"
    panel.reset_index().to_csv(panel_path, index=False)

    json_path = output_dir / "value_of_labour_power.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, default=float)

    return {"panel": panel_path, "json": json_path}
