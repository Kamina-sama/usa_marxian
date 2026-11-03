"""End-to-end pipeline: fetch -> accounts -> analysis -> artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from .analysis.descriptives import summary_table
from .analysis.ltv import LTVResult, estimate_ltv
from .config import ProjectConfig
from .data.build import build_accounts, build_raw_panel, validate_accounts
from .model.equalities import profit_rate_decomposition, profit_rate_summary
from .model.melt import MeltSummary, melt_summary
from .viz.plots import plot_composition, plot_distribution, plot_melt, plot_profit_rate


@dataclass
class PipelineResult:
    raw: pd.DataFrame
    accounts: pd.DataFrame
    report: dict[str, Any] = field(default_factory=dict)


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
        "summary": summary_table(accounts).to_dict(orient="records"),
    }


def run(
    config: ProjectConfig | None = None,
    *,
    save: bool = True,
    make_plots: bool = True,
) -> PipelineResult:
    """Run the full pipeline and optionally persist artifacts."""
    config = config or ProjectConfig.load()
    config.settings.ensure_directories()

    raw = build_raw_panel(config)
    accounts = build_accounts(raw, config.settings)
    validate_accounts(accounts)
    report = build_report(accounts, config)

    if save:
        processed = config.settings.processed_dir
        raw.to_csv(processed / "raw_panel.csv", index_label="year")
        accounts.to_csv(processed / "accounts.csv", index_label="year")

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
        with (config.settings.output_dir / "report.json").open("w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, default=str)

    if make_plots:
        figures = config.settings.output_dir / "figures"
        plot_melt(accounts, figures / "melt.png")
        plot_melt(accounts, figures / "melt_real.png", real=True)
        plot_distribution(accounts, figures / "distribution.png")
        plot_profit_rate(accounts, figures / "rate_of_profit.png")
        plot_composition(accounts, figures / "composition.png")

    return PipelineResult(raw=raw, accounts=accounts, report=report)


def load_accounts(config: ProjectConfig | None = None) -> pd.DataFrame:
    """Load the processed accounts, building them if the file is absent."""
    config = config or ProjectConfig.load()
    path: Path = config.settings.processed_dir / "accounts.csv"
    if path.exists():
        return pd.read_csv(path, index_col="year")
    return run(config=config, save=True, make_plots=False).accounts
