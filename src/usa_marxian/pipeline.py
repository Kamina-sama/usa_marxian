"""End-to-end pipelines: macro accounts, robustness, diagnostics, industries."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from .analysis.descriptives import summary_table
from .analysis.diagnostics import diagnostics_table
from .analysis.ltv import LTVResult, estimate_ltv
from .analysis.profit_check import property_income_check, property_income_summary
from .config import ProjectConfig
from .data.bea_io import build_industry_panel
from .data.build import build_accounts, build_raw_panel, validate_accounts
from .data.quality import write_quality
from .model.equalities import profit_rate_decomposition, profit_rate_summary
from .model.industries import (
    add_industry_ratios,
    industry_report,
    latest_dispersion,
    year_summary,
)
from .model.melt import MeltSummary, melt_summary
from .model.robustness import run_specifications, specification_ranges
from .viz.plots import (
    plot_composition,
    plot_distribution,
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


def run_industries(
    config: ProjectConfig | None = None,
    *,
    save: bool = True,
    make_plots: bool = True,
    refresh: bool = False,
) -> IndustryResult:
    """Build and analyse the BEA summary-level industry accounts."""
    config = config or ProjectConfig.load()
    config.settings.ensure_directories()

    panel = build_industry_panel(
        config.settings.raw_dir,
        max_age_days=max(365, config.settings.cache_max_age_days),
        force=refresh,
    )
    enriched = add_industry_ratios(panel)
    summary = year_summary(panel)
    latest = latest_dispersion(panel)
    report = industry_report(panel)

    if save:
        processed = config.settings.processed_dir
        enriched.to_csv(processed / "industries.csv", index=False)
        tables = config.settings.output_dir / "tables"
        tables.mkdir(parents=True, exist_ok=True)
        summary.to_csv(tables / "industry_summary.csv", index=False)
        latest.to_csv(tables / "industry_latest.csv", index=False)
        with (config.settings.output_dir / "industries.json").open("w", encoding="utf-8") as handle:
            json.dump(_json_safe(report), handle, indent=2)

    if make_plots:
        figures = config.settings.output_dir / "figures"
        plot_industry_dispersion(summary, figures / "industry_dispersion.png")
        plot_pp_vs_go(latest, figures / "pp_vs_go.png")

    return IndustryResult(panel=panel, summary=summary, latest=latest, report=report)


def load_accounts(config: ProjectConfig | None = None) -> pd.DataFrame:
    """Load the processed accounts, building them if the file is absent."""
    config = config or ProjectConfig.load()
    path: Path = config.settings.processed_dir / "accounts.csv"
    if path.exists():
        return pd.read_csv(path, index_col="year")
    return run(config=config, save=True, make_plots=False).accounts
