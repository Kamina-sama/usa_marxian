"""End-to-end pipelines: macro accounts, robustness, diagnostics, industries."""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .analysis.compare import (
    benchmark_gravitation,
    compare_benchmarks,
    run_shaikh_comparison,
)
from .analysis.descriptives import summary_table
from .analysis.diagnostics import diagnostics_table
from .analysis.gravitation import run_gravitation
from .analysis.ltv import LTVResult, estimate_ltv
from .analysis.price_diagnostics import run_price_diagnostics
from .analysis.profit_check import property_income_check, property_income_summary
from .analysis.unit_prices import compare_unit_prices
from .config import ProjectConfig
from .data.bea_assets import (
    attach_capital_stock,
    capital_coverage,
    load_government_housing_capital,
    load_industry_capital,
    load_industry_capital_detail,
)
from .data.bea_employment import (
    attach_employment,
    employment_coverage,
    load_industry_employment,
)
from .data.bea_final_demand import categorise_final_demand, load_final_demand
from .data.bea_industry_prices import attach_industry_prices, load_industry_prices
from .data.bea_inventory_detail import load_industry_inventories_detail
from .data.bea_io import build_industry_panel, load_use_matrices
from .data.bls_industry import fetch_manufacturing_hours
from .data.build import build_accounts, build_raw_panel, validate_accounts
from .data.census_ecn import load_regulating_data
from .data.quality import write_quality
from .data.sectors import (
    attach_input_deflator,
    attach_sector_data,
    fetch_sector_prices,
    load_sector_config,
)
from .model.equalities import profit_rate_decomposition, profit_rate_summary
from .model.industries import (
    add_industry_ratios,
    industry_reconciliation,
    industry_report,
    latest_dispersion,
    proxy_sensitivity,
    year_summary,
)
from .model.melt import MeltSummary, melt_summary
from .model.regulating import build_regulating_benchmark
from .model.robustness import run_specifications, specification_ranges
from .model.state_space import build_state_space
from .model.stock_flow import fit_stock_flow
from .viz.plots import (
    plot_composition,
    plot_distribution,
    plot_gravitation_deviation,
    plot_gravitation_forecast,
    plot_industry_dispersion,
    plot_melt,
    plot_pp_vs_go,
    plot_profit_rate,
    plot_robustness,
)


@dataclass
class PipelineResult:
    raw: pd.DataFrame
    accounts: pd.DataFrame
    report: dict[str, Any] = field(default_factory=dict)
    robustness: pd.DataFrame | None = None
    diagnostics: pd.DataFrame | None = None
    quality: dict[str, Any] | None = None


@dataclass
class IndustryResult:
    panel: pd.DataFrame
    summary: pd.DataFrame
    latest: pd.DataFrame
    report: dict[str, Any] = field(default_factory=dict)


def _json_safe(value):
    """Convert numpy scalars and NaN to JSON-serialisable values."""
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float):
        return None if math.isnan(value) or math.isinf(value) else value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


def _identity_errors(accounts: pd.DataFrame) -> dict[str, float]:
    return {
        "P_minus_C_plus_N": float((accounts["P"] - (accounts["C"] + accounts["N"])).abs().max()),
        "K_minus_C_plus_V": float((accounts["K"] - (accounts["C"] + accounts["V"])).abs().max()),
        "S_minus_N_minus_V": float((accounts["S"] - (accounts["N"] - accounts["V"])).abs().max()),
        "R_minus_identity": float(
            (accounts["rate_profit"] - accounts["rate_profit_identity"]).abs().max()
        ),
    }


def build_report(accounts: pd.DataFrame, config: ProjectConfig) -> dict[str, Any]:
    melt: MeltSummary = melt_summary(accounts, base_year=config.settings.base_year)
    melt_real = melt_summary(accounts, column="melt_real", base_year=config.settings.base_year)
    ltv: LTVResult = estimate_ltv(accounts)
    ltv_nominal: LTVResult = estimate_ltv(accounts, value_column="N")
    profit = profit_rate_summary(accounts)

    return {
        "sample": {
            "start_year": int(accounts.index.min()),
            "end_year": int(accounts.index.max()),
            "n_years": int(accounts.shape[0]),
            "hours_method": config.settings.hours_method,
            "include_inventories": config.settings.include_inventories,
        },
        "melt": melt.to_dict(),
        "melt_real": melt_real.to_dict(),
        "ltv": ltv.to_dict(),
        "ltv_nominal": ltv_nominal.to_dict(),
        "profit_rate": profit,
        "property_income": property_income_summary(accounts),
        "identity_max_abs_error": _identity_errors(accounts),
        "summary": summary_table(accounts).to_dict(orient="records"),
    }


def run(
    config: ProjectConfig | None = None,
    *,
    save: bool = True,
    make_plots: bool = True,
    with_robustness: bool = True,
    with_diagnostics: bool = True,
    refresh: bool = False,
) -> PipelineResult:
    """Run the full macro pipeline and optionally persist artifacts."""
    config = config or ProjectConfig.load()
    config.settings.ensure_directories()

    raw = build_raw_panel(config, refresh=refresh)
    accounts = build_accounts(raw, config.settings)
    validate_accounts(accounts)
    report = build_report(accounts, config)

    robustness = None
    diagnostics = None
    quality = None

    if with_robustness:
        robustness = run_specifications(raw, config.settings)
        report["robustness"] = robustness.to_dict(orient="records")
        report["robustness_ranges"] = specification_ranges(robustness).to_dict(orient="records")

    if with_diagnostics:
        diagnostics = diagnostics_table(accounts)
        report["diagnostics"] = diagnostics.to_dict(orient="records")

    if save:
        processed = config.settings.processed_dir
        raw.to_csv(processed / "raw_panel.csv", index_label="year")
        accounts.to_csv(processed / "accounts.csv", index_label="year")

        quality = write_quality(
            raw,
            csv_path=processed / "data_quality.csv",
            json_path=processed / "data_quality.json",
            core_columns=[
                "gdp",
                "cfc",
                "gdp_deflator",
                "compensation",
                "capital_stock",
                "hours_index",
            ],
        )
        report["quality"] = quality

        tables = config.settings.output_dir / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        summary_table(accounts).to_csv(tables / "summary.csv", index=False)
        pd.DataFrame([report["ltv"]]).to_csv(tables / "ltv_test.csv", index=False)
        pd.DataFrame([report["ltv_nominal"]]).to_csv(
            tables / "ltv_test_nominal.csv", index=False
        )
        pd.DataFrame([report["melt"]]).to_csv(tables / "melt_summary.csv", index=False)
        pd.DataFrame([report["melt_real"]]).to_csv(
            tables / "melt_summary_real.csv", index=False
        )
        pd.DataFrame([report["profit_rate"]]).to_csv(
            tables / "profit_rate_summary.csv", index=False
        )
        profit_rate_decomposition(accounts).to_csv(
            tables / "profit_rate_decomposition.csv", index_label="year"
        )
        property_income_check(accounts).to_csv(
            tables / "property_income_check.csv", index_label="year"
        )
        if robustness is not None:
            robustness.to_csv(tables / "robustness.csv", index=False)
            specification_ranges(robustness).to_csv(tables / "robustness_ranges.csv", index=False)
        if diagnostics is not None:
            diagnostics.to_csv(tables / "diagnostics.csv", index=False)

        with (config.settings.output_dir / "report.json").open("w", encoding="utf-8") as handle:
            json.dump(_json_safe(report), handle, indent=2)

    if make_plots:
        figures = config.settings.output_dir / "figures"
        plot_melt(accounts, figures / "melt.png")
        plot_melt(accounts, figures / "melt_real.png", real=True)
        plot_distribution(accounts, figures / "distribution.png")
        plot_profit_rate(accounts, figures / "rate_of_profit.png")
        plot_composition(accounts, figures / "composition.png")
        if robustness is not None:
            plot_robustness(robustness, figures / "robustness.png")

    return PipelineResult(
        raw=raw,
        accounts=accounts,
        report=report,
        robustness=robustness,
        diagnostics=diagnostics,
        quality=quality,
    )


def _gravitation_report(gravitation: dict) -> dict[str, Any]:
    deviation = {
        key: value
        for key, value in gravitation["deviation"].items()
        if not isinstance(value, pd.DataFrame)
    }
    report = {
        "sample": gravitation["sample"],
        "deviation": deviation,
        "unit_root": gravitation["unit_root"],
        "cointegration": gravitation["cointegration"],
        "error_correction": gravitation["error_correction"],
        "forecast_metrics": gravitation["forecast_metrics"].to_dict(orient="records"),
        "forecast_comparisons": gravitation["forecast_comparisons"].to_dict(orient="records"),
        "verdict": gravitation["verdict"],
    }
    long_run = gravitation.get("long_run")
    if long_run is not None:
        long_deviation = {
            key: value
            for key, value in long_run["deviation"].items()
            if not isinstance(value, pd.DataFrame)
        }
        report["long_run"] = {
            "label": long_run.get("label"),
            "deviation": long_deviation,
            "unit_root": long_run["unit_root"],
            "cointegration": long_run["cointegration"],
            "error_correction": long_run["error_correction"],
            "forecast_metrics": long_run["forecast_metrics"].to_dict(orient="records"),
            "forecast_comparisons": long_run["forecast_comparisons"].to_dict(
                orient="records"
            ),
        }
    return report


def run_industries(
    config: ProjectConfig | None = None,
    *,
    save: bool = True,
    make_plots: bool = True,
    refresh: bool = False,
    with_gravitation: bool = True,
) -> IndustryResult:
    """Build and analyse the BEA summary-level industry accounts."""
    config = config or ProjectConfig.load()
    config.settings.ensure_directories()

    panel = build_industry_panel(
        config.settings.raw_dir,
        max_age_days=max(365, config.settings.cache_max_age_days),
        force=refresh,
    )
    try:
        panel = attach_sector_data(
            panel,
            raw_dir=config.settings.raw_dir,
            max_age_days=config.settings.cache_max_age_days,
            force=refresh,
        )
    except Exception as exc:  # keep the gross accounts usable if a proxy is absent
        warnings.warn(
            f"Sector deflators/CFC unavailable, using gross accounts: {exc}",
            stacklevel=2,
        )

    use_matrices = None
    try:
        sector_config = load_sector_config()
        use_matrices = load_use_matrices(
            config.settings.raw_dir,
            max_age_days=max(365, config.settings.cache_max_age_days),
            force=refresh,
        )
        sector_prices = fetch_sector_prices(
            sector_config,
            config.settings.raw_dir,
            max_age_days=config.settings.cache_max_age_days,
            force=refresh,
        )
        panel = attach_input_deflator(
            panel, use_matrices, sector_prices, sector_config, base_year=2017
        )
    except Exception as exc:
        warnings.warn(
            f"Intermediate-input deflator unavailable, real profit rates skipped: {exc}",
            stacklevel=2,
        )

    final_demand = None
    final_demand_summary = None
    if use_matrices is not None:
        try:
            final_demand = categorise_final_demand(
                load_final_demand(
                    config.settings.raw_dir,
                    force=refresh,
                )
            )
            final_demand_summary = {
                "rows": int(final_demand.shape[0]),
                "years": int(final_demand["year"].nunique()),
                "categories": sorted(
                    column
                    for column in ("C", "I", "G", "X", "M")
                    if column in final_demand.columns
                ),
            }
        except Exception as exc:
            warnings.warn(
                f"Final-demand columns unavailable: {exc}",
                stacklevel=2,
            )

    industry_prices = None
    price_coverage = None
    if config.api.bea_api_key:
        try:
            industry_prices = load_industry_prices(
                config.settings.raw_dir,
                config.api.bea_api_key,
                force=refresh,
            )
            panel = attach_industry_prices(panel, industry_prices)
            price_coverage = {
                "source": "bea_gdpbyindustry",
                "rows": int(industry_prices.shape[0]),
                "coverage": panel["price_source"].value_counts().to_dict(),
            }
        except Exception as exc:
            warnings.warn(
                f"Industry-level BEA prices unavailable, using sector proxies: {exc}",
                stacklevel=2,
            )

    capital = load_industry_capital(
        config.settings.raw_dir,
        max_age_days=max(365, config.settings.cache_max_age_days),
        force=refresh,
    )
    special_capital = load_government_housing_capital(
        config.settings.raw_dir,
        max_age_days=max(365, config.settings.cache_max_age_days),
        force=refresh,
    )
    inventories = load_industry_inventories_detail(
        config.settings.raw_dir,
        panel,
        max_age_days=max(365, config.settings.cache_max_age_days),
        force=refresh,
    )
    panel = attach_capital_stock(
        panel,
        capital,
        inventories=inventories,
        special=special_capital,
        fallback="cost",
    )

    # Measured industry employment and wage rates (Table 6.5D FTE).
    accounts_path = config.settings.processed_dir / "accounts.csv"
    if accounts_path.exists():
        try:
            macro_hours = pd.read_csv(accounts_path, index_col="year")["L"]
            employment = load_industry_employment(
                config.settings.raw_dir, force=refresh
            )
            manufacturing_hours = None
            if config.api.bls_api_key:
                try:
                    manufacturing_hours = fetch_manufacturing_hours(
                        config.api.bls_api_key,
                        start_year=max(2005, int(macro_hours.index.min())),
                        end_year=int(macro_hours.index.max()),
                    )
                except Exception as exc:
                    warnings.warn(
                        f"BLS manufacturing hours unavailable: {exc}",
                        stacklevel=2,
                    )
            panel = attach_employment(
                panel,
                employment,
                macro_hours,
                manufacturing_hours=manufacturing_hours,
            )
        except Exception as exc:
            warnings.warn(
                f"Industry employment unavailable, hours stay compensation-allocated: {exc}",
                stacklevel=2,
            )

    capital_table = panel.loc[
        :,
        [
            "year",
            "industry_code",
            "M_assets",
            "M_inv",
            "M",
            "capital_source",
            "inventory_category",
            "inventory_source",
        ],
    ].copy()

    employment_table = None
    employment_cov = None
    if "labour_hours" in panel.columns:
        employment_table = panel.loc[
            :,
            [
                "year",
                "industry_code",
                "fte",
                "hours_per_fte",
                "labour_hours",
                "wage_rate_i",
                "hours_source",
            ],
        ].copy()
        accounts_path_for_hours = config.settings.processed_dir / "accounts.csv"
        hours_series = (
            pd.read_csv(accounts_path_for_hours, index_col="year")["L"]
            if accounts_path_for_hours.exists()
            else None
        )
        employment_cov = employment_coverage(panel, hours_series)
        latest_emp = employment_cov.iloc[-1]
        employment_summary = {
            "hours_source": "fte",
            "n_industries": int(latest_emp["n_industries"]),
            "n_fte": int(latest_emp["n_fte"]),
            "total_hours_bn": float(latest_emp["hours_bn"]),
            "macro_hours_bn": float(latest_emp.get("macro_hours_bn", float("nan"))),
            "gap_pct": float(latest_emp.get("gap_pct", float("nan"))),
        }
        employment_coverage_records = employment_cov.to_dict(orient="records")

    enriched = add_industry_ratios(panel, capital_proxy="fixed_assets")
    summary = year_summary(panel, capital_proxy="fixed_assets")
    latest_table = latest_dispersion(panel, capital_proxy="fixed_assets")
    report = industry_report(panel, capital_proxy="fixed_assets")
    if price_coverage is not None:
        report["prices"] = price_coverage
    if final_demand_summary is not None:
        report["final_demand"] = final_demand_summary
    if employment_table is not None:
        report["employment"] = employment_summary
        report["employment_coverage"] = employment_coverage_records
    proxies = proxy_sensitivity(panel)
    report["proxy_sensitivity"] = proxies.to_dict(orient="records")

    latest_summary = report["latest"]
    if "R_real_market" in latest_summary:
        report["real"] = {
            "R_real": float(latest_summary["R_real"]),
            "R_real_market": float(latest_summary["R_real_market"]),
            "r_real_weighted_cv": float(latest_summary["r_real_weighted_cv"]),
            "r_real_weighted_cv_market": float(
                latest_summary["r_real_weighted_cv_market"]
            ),
            "input_deflator_base_year": 2017,
        }

    reconciliation = None
    coverage = None
    macro_accounts = None
    accounts_path = config.settings.processed_dir / "accounts.csv"
    try:
        if accounts_path.exists():
            macro_accounts = pd.read_csv(accounts_path, index_col="year")
        else:
            macro_accounts = build_accounts(build_raw_panel(config), config.settings)
        reconciliation = industry_reconciliation(panel, macro_accounts)
        report["reconciliation"] = reconciliation.to_dict(orient="records")

        coverage = capital_coverage(panel, macro_accounts)
        latest_coverage = coverage.iloc[-1]
        report["capital"] = {
            "capital_proxy": "fixed_assets+inventories",
            "fallback": "cost",
            "n_actual": int(latest_coverage["n_actual"]),
            "n_proxy": int(latest_coverage["n_proxy"]),
            "total_M_assets_bn": float(latest_coverage["total_M_assets_bn"]),
            "private_M_assets_bn": float(latest_coverage["private_M_assets_bn"]),
            "special_M_assets_bn": float(latest_coverage["special_M_assets_bn"]),
            "total_M_inv_bn": float(latest_coverage["total_M_inv_bn"]),
            "total_M_actual_bn": float(latest_coverage["total_M_actual_bn"]),
            "macro_fixed_bn": float(latest_coverage["macro_fixed_bn"]),
            "macro_inv_bn": float(latest_coverage["macro_inv_bn"]),
            "macro_M_bn": float(latest_coverage["macro_M_bn"]),
            "gap_fixed_pct": float(latest_coverage["gap_fixed_pct"]),
            "gap_inv_pct": float(latest_coverage["gap_inv_pct"]),
            "gap_total_pct": float(latest_coverage["gap_total_pct"]),
            "inventory_detail_share": float(
                panel.loc[panel["inventory_source"] == "BEA 1BUC detail", "M_inv"].sum()
                / panel["M_inv"].sum()
            ),
            "inventory_detail_codes": int(
                panel.loc[
                    panel["inventory_source"] == "BEA 1BUC detail", "industry_code"
                ].nunique()
            ),
        }
        report["capital_coverage"] = coverage.to_dict(orient="records")
    except Exception as exc:  # reconciliation is a check, not a prerequisite
        warnings.warn(
            f"Industry/macro reconciliation unavailable: {exc}",
            stacklevel=2,
        )

    state_space = None
    if use_matrices is not None and macro_accounts is not None:
        try:
            capital_detail = load_industry_capital_detail(
                config.settings.raw_dir,
                max_age_days=max(365, config.settings.cache_max_age_days),
                force=refresh,
            )
            state_space = build_state_space(
                enriched,
                use_matrices,
                macro_accounts,
                capital_detail,
                base_year=2017,
                final_demand=final_demand,
            )
            report["state_space"] = state_space.summary
        except Exception as exc:
            warnings.warn(
                f"State-space dataset unavailable: {exc}",
                stacklevel=2,
            )

    stock_flow = None
    if state_space is not None:
        try:
            stock_flow = fit_stock_flow(
                state_space.state,
                state_space.matrices_real,
                calibrate=False,
            )
            report["stock_flow"] = stock_flow.summary
        except Exception as exc:
            warnings.warn(
                f"Stock-flow simulation unavailable: {exc}",
                stacklevel=2,
            )

    shaikh = None
    if use_matrices is not None and macro_accounts is not None:
        try:
            shaikh = run_shaikh_comparison(
                enriched, use_matrices, macro_accounts, base_year=2017
            )
            report["shaikh"] = shaikh.summary
            report["benchmark_comparison"] = shaikh.comparison.to_dict(orient="records")
            if config.api.census_api_key:
                try:
                    regulating_data = load_regulating_data(
                        config.settings.raw_dir,
                        config.api.census_api_key,
                        force=refresh,
                    )
                    if regulating_data is not None:
                        regulating = build_regulating_benchmark(
                            shaikh.shaikh.panel,
                            regulating_data,
                        )
                        shaikh.shaikh.panel = regulating.panel
                        shaikh.comparison = compare_benchmarks(regulating.panel)
                        reg_grav = benchmark_gravitation(
                            regulating.panel,
                            "PP_reg",
                            "Regulating capital (low-cost firms)",
                        )
                        shaikh.gravitation = pd.concat(
                            [shaikh.gravitation, pd.DataFrame([reg_grav])],
                            ignore_index=True,
                        )
                        shaikh.summary["gravitation"] = shaikh.gravitation.to_dict(
                            orient="records"
                        )
                        report["regulating"] = regulating.summary
                        report["benchmark_comparison"] = shaikh.comparison.to_dict(
                            orient="records"
                        )
                except Exception as exc:
                    warnings.warn(
                        f"Regulating-capital benchmark unavailable: {exc}",
                        stacklevel=2,
                    )
        except Exception as exc:
            warnings.warn(
                f"Shaikh comparison unavailable: {exc}",
                stacklevel=2,
            )

    unit_prices = None
    if shaikh is not None:
        try:
            unit_prices = compare_unit_prices(shaikh.shaikh.panel)
            price_diagnostics = run_price_diagnostics(unit_prices["panel"])
            report["unit_prices"] = {
                "latest_year": unit_prices["latest_year"],
                "comparison": unit_prices["comparison"].to_dict(orient="records"),
                "gravitation": unit_prices["gravitation"].to_dict(orient="records"),
                "diagnostics": {
                    "revenue_ratio": price_diagnostics["revenue_ratio"]["summary"],
                    "within_sector_identified": price_diagnostics[
                        "within_sector_identified"
                    ],
                    "measurement_identified": price_diagnostics[
                        "measurement_identified"
                    ],
                },
            }
        except Exception as exc:
            warnings.warn(
                f"Unit-price comparison unavailable: {exc}",
                stacklevel=2,
            )

    gravitation = None
    gravitation_report = None
    if with_gravitation:
        try:
            gravitation = run_gravitation(panel, capital_proxy="fixed_assets")
            gravitation_report = _gravitation_report(gravitation)
            report["gravitation"] = gravitation_report
        except Exception as exc:
            warnings.warn(
                f"Gravitation tests unavailable: {exc}",
                stacklevel=2,
            )

    if save:
        processed = config.settings.processed_dir
        enriched.to_csv(processed / "industries.csv", index=False)
        capital.to_csv(processed / "industry_fixed_assets.csv", index=False)
        special_capital.to_csv(processed / "industry_government_housing.csv", index=False)
        inventories.to_csv(processed / "industry_inventories.csv", index=False)
        tables = config.settings.output_dir / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        capital_table.to_csv(processed / "industry_capital.csv", index=False)
        if industry_prices is not None:
            industry_prices.to_csv(processed / "industry_prices.csv", index=False)
        if final_demand is not None:
            final_demand.to_csv(processed / "final_demand.csv", index=False)
        if employment_table is not None:
            employment_table.to_csv(
                processed / "industry_employment.csv", index=False
            )
            if employment_cov is not None:
                employment_cov.to_csv(
                    tables / "industry_employment_coverage.csv", index=False
                )
        summary.to_csv(tables / "industry_summary.csv", index=False)
        latest_table.to_csv(tables / "industry_latest.csv", index=False)
        proxies.to_csv(tables / "industry_proxy_sensitivity.csv", index=False)
        if reconciliation is not None:
            reconciliation.to_csv(tables / "industry_reconciliation.csv", index=False)
        if coverage is not None:
            coverage.to_csv(tables / "industry_capital_coverage.csv", index=False)
        if state_space is not None:
            state_space.state.to_csv(processed / "state_space.csv", index=False)
            state_space.matrices.to_csv(
                processed / "technical_matrices.csv", index=False
            )
            state_space.matrices_real.to_csv(
                processed / "technical_matrices_real.csv", index=False
            )
            state_space.macro.to_csv(
                processed / "state_space_macro.csv", index=False
            )
            with (processed / "state_space.json").open(
                "w", encoding="utf-8"
            ) as handle:
                json.dump(_json_safe(state_space.summary), handle, indent=2)
        if stock_flow is not None:
            stock_flow.metrics.to_csv(
                tables / "stock_flow_metrics.csv", index=False
            )
            stock_flow.trajectories.to_csv(
                tables / "stock_flow_trajectories.csv", index=False
            )
            with (config.settings.output_dir / "stock_flow.json").open(
                "w", encoding="utf-8"
            ) as handle:
                json.dump(_json_safe(stock_flow.summary), handle, indent=2)
        if shaikh is not None:
            shaikh.shaikh.panel.to_csv(
                processed / "industries_shaikh.csv", index=False
            )
            shaikh.comparison.to_csv(
                tables / "benchmark_comparison.csv", index=False
            )
            shaikh.gravitation.to_csv(
                tables / "benchmark_gravitation.csv", index=False
            )
            iteration_columns = [
                "year",
                "r_observed",
                "r_model",
                "iterations",
                "iteration_residual",
                "iteration_converged",
                "cross_dual_converged",
                "cross_dual_steps",
                "cross_dual_dispersion_start",
                "cross_dual_dispersion_end",
            ]
            available = [
                column
                for column in iteration_columns
                if column in shaikh.shaikh.panel.columns
            ]
            shaikh.shaikh.panel.loc[:, available].drop_duplicates(
                subset=["year"]
            ).to_csv(processed / "shaikh_iterations.csv", index=False)
            with (config.settings.output_dir / "shaikh.json").open(
                "w", encoding="utf-8"
            ) as handle:
                json.dump(_json_safe(shaikh.summary), handle, indent=2)
            if unit_prices is not None:
                unit_prices["panel"].to_csv(
                    processed / "unit_prices.csv", index=False
                )
                unit_prices["comparison"].to_csv(
                    tables / "unit_price_comparison.csv", index=False
                )
                unit_prices["by_year"].to_csv(
                    tables / "unit_price_by_year.csv", index=False
                )
                unit_prices["gravitation"].to_csv(
                    tables / "unit_price_gravitation.csv", index=False
                )
                pd.DataFrame(
                    [price_diagnostics["revenue_ratio"]["summary"]]
                ).to_csv(tables / "price_revenue_ratio.csv", index=False)
                price_diagnostics["revenue_ratio"]["by_year"].to_csv(
                    tables / "price_revenue_ratio_by_year.csv", index=False
                )
                price_diagnostics["within_sector"].to_csv(
                    tables / "price_within_sector.csv", index=False
                )
                with (config.settings.output_dir / "price_diagnostics.json").open(
                    "w", encoding="utf-8"
                ) as handle:
                    json.dump(
                        _json_safe(
                            {
                                "revenue_ratio": price_diagnostics["revenue_ratio"][
                                    "summary"
                                ],
                                "within_sector": price_diagnostics[
                                    "within_sector"
                                ].to_dict(orient="records"),
                                "measurement": price_diagnostics["measurement"],
                                "within_sector_identified": price_diagnostics[
                                    "within_sector_identified"
                                ],
                                "measurement_identified": price_diagnostics[
                                    "measurement_identified"
                                ],
                            }
                        ),
                        handle,
                        indent=2,
                    )
                with (config.settings.output_dir / "unit_prices.json").open(
                    "w", encoding="utf-8"
                ) as handle:
                    json.dump(
                        _json_safe(
                            {
                                "summary": unit_prices["summary"],
                                "latest": unit_prices["latest"].to_dict(
                                    orient="records"
                                ),
                            }
                        ),
                        handle,
                        indent=2,
                    )
        if gravitation is not None:
            deviation = gravitation["deviation"]
            pd.DataFrame(
                [
                    {"metric": key, "value": value}
                    for key, value in deviation.items()
                    if not isinstance(value, pd.DataFrame)
                ]
            ).to_csv(tables / "gravitation_summary.csv", index=False)
            deviation["by_year"].to_csv(tables / "gravitation_by_year.csv", index=False)
            pd.DataFrame(
                [
                    {"model": name, **values}
                    for name, values in gravitation["error_correction"].items()
                ]
            ).to_csv(tables / "gravitation_ecm.csv", index=False)
            gravitation["forecast_metrics"].to_csv(
                tables / "gravitation_forecast_metrics.csv", index=False
            )
            gravitation["forecast_comparisons"].to_csv(
                tables / "gravitation_forecast_comparisons.csv", index=False
            )
            long_run = gravitation.get("long_run")
            if long_run is not None:
                pd.DataFrame(
                    [
                        {"metric": key, "value": value}
                        for key, value in long_run["deviation"].items()
                        if not isinstance(value, pd.DataFrame)
                    ]
                ).to_csv(tables / "gravitation_long_run_summary.csv", index=False)
                pd.DataFrame(
                    [
                        {"model": name, **values}
                        for name, values in long_run["error_correction"].items()
                    ]
                ).to_csv(tables / "gravitation_long_run_ecm.csv", index=False)
                long_run["forecast_metrics"].to_csv(
                    tables / "gravitation_long_run_forecast_metrics.csv", index=False
                )
                long_run["forecast_comparisons"].to_csv(
                    tables / "gravitation_long_run_forecast_comparisons.csv", index=False
                )
            with (config.settings.output_dir / "gravitation.json").open(
                "w", encoding="utf-8"
            ) as handle:
                json.dump(_json_safe(gravitation_report), handle, indent=2)
        with (config.settings.output_dir / "industries.json").open("w", encoding="utf-8") as handle:
            json.dump(_json_safe(report), handle, indent=2)

    if make_plots:
        figures = config.settings.output_dir / "figures"
        plot_industry_dispersion(summary, figures / "industry_dispersion.png")
        plot_pp_vs_go(latest_table, figures / "pp_vs_go.png")
        if gravitation is not None:
            plot_gravitation_deviation(
                gravitation["deviation"]["by_year"],
                figures / "gravitation_deviation.png",
            )
            plot_gravitation_forecast(
                gravitation["forecast_metrics"],
                figures / "gravitation_forecast.png",
            )

    return IndustryResult(panel=panel, summary=summary, latest=latest_table, report=report)


def load_accounts(config: ProjectConfig | None = None) -> pd.DataFrame:
    """Load the processed accounts, building them if the file is absent."""
    config = config or ProjectConfig.load()
    path: Path = config.settings.processed_dir / "accounts.csv"
    if path.exists():
        return pd.read_csv(path, index_col="year")
    return run(config=config, save=True, make_plots=False).accounts
