"""Figures for the headline findings.

Every plot here reads artifacts that ``usa-marxian analyze`` and
``usa-marxian industries`` already write. Nothing is refetched, so the whole
set rebuilds in a couple of seconds with ``usa-marxian figures`` or
``make figures``.

The guiding rule: one picture per claim the project actually makes, and the
picture must be readable without a regression table next to it.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..analysis.gravitation import error_correction
from ..config import ProjectConfig
from .plots import _finish

# Palette shared with plots.py so the whole figure set looks like one document.
BLUE = "#1f4e79"
GREEN = "#4a6b3a"
OCHRE = "#7a5c1e"
ORANGE = "#a15c1e"
RED = "#8b1a1a"
GREY = "#444444"

FAMILY_COLORS = {
    "moseley": BLUE,
    "sraffa": GREEN,
    "shaikh": OCHRE,
    "regulating": ORANGE,
    "direct": RED,
}


def _family_color(label: str) -> str:
    low = label.lower()
    for key, color in FAMILY_COLORS.items():
        if low.startswith(key):
            return color
    return GREY


def _clean_label(label: str) -> str:
    return str(label).replace(" | market", "").strip()


def plot_benchmark_fit(comparison: pd.DataFrame, path: Path) -> Path:
    """Revenue fit: typical error and rank agreement per benchmark."""
    data = comparison.copy()
    data["label"] = data["benchmark"].map(_clean_label)
    data = data.sort_values("mae_pct", ascending=True).reset_index(drop=True)
    colors = [_family_color(label) for label in data["label"]]

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.4), sharey=True)

    axes[0].barh(data["label"], data["mae_pct"], color=colors)
    axes[0].set_xlabel("Mean absolute error vs observed gross output (%)")
    axes[0].set_title("Typical revenue error — lower is better")
    for y, value in enumerate(data["mae_pct"]):
        axes[0].text(value + 0.3, y, f"{value:.1f}%", va="center", fontsize=8.5)
    axes[0].set_xlim(0, data["mae_pct"].max() * 1.18)

    axes[1].barh(data["label"], data["corr"], color=colors)
    axes[1].set_xlabel("Correlation with observed gross output")
    axes[1].set_title("Rank agreement — higher is better")
    axes[1].set_xlim(0, 1.02)
    for y, corr in enumerate(data["corr"]):
        axes[1].text(
            corr - 0.012,
            y,
            f"{corr:.3f}",
            va="center",
            ha="right",
            fontsize=8.5,
            color="white",
        )

    observations = int(comparison["n"].max()) if "n" in comparison else 0
    fig.suptitle(
        "Prices of production vs observed industry revenue, "
        f"{observations:,} market industry-years",
        fontsize=11.5,
    )
    return _finish(fig, path)


def plot_unit_price_fit(panel: pd.DataFrame, path: Path) -> Path:
    """Relative unit prices: model against data for three benchmarks."""
    columns = [
        ("p_moseley_working_n", "Moseley, working capital"),
        ("p_sraffa_n", "Sraffa prices of production"),
        ("p_v_n", "Direct prices (labour values)"),
    ]
    columns = [(c, t) for c, t in columns if c in panel.columns]
    if not columns:
        raise ValueError("unit-price panel has no model price columns")

    fig, axes = plt.subplots(1, len(columns), figsize=(4.6 * len(columns), 4.8))
    axes = np.atleast_1d(axes)

    for ax, (column, title) in zip(axes, columns, strict=True):
        data = panel.loc[:, ["price_obs_n", column]].replace([np.inf, -np.inf], np.nan)
        data = data.dropna()
        data = data.loc[(data["price_obs_n"] > 0) & (data[column] > 0)]
        x = np.log(data[column].to_numpy(dtype=float))
        y = np.log(data["price_obs_n"].to_numpy(dtype=float))
        slope, intercept = np.polyfit(x, y, 1)
        corr = float(np.corrcoef(x, y)[0, 1])
        color = _family_color(title)

        ax.scatter(x, y, s=7, alpha=0.30, color=color, linewidths=0)
        low = float(min(x.min(), y.min()))
        high = float(max(x.max(), y.max()))
        ax.plot([low, high], [low, high], "--", color=GREY, linewidth=1.1)
        grid = np.linspace(low, high, 50)
        ax.plot(grid, intercept + slope * grid, color=color, linewidth=2.2)
        ax.text(
            0.04,
            0.96,
            f"corr {corr:.3f}\nslope {slope:.2f}",
            transform=ax.transAxes,
            va="top",
            fontsize=9.5,
            bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.85, edgecolor="none"),
        )
        ax.set_title(title, fontsize=10.5)
        ax.set_xlabel("log model relative price")
    axes[0].set_ylabel("log observed relative price")

    fig.suptitle(
        "Relative unit prices: dashed line is perfect agreement, solid line is the fitted slope",
        fontsize=11,
    )
    return _finish(fig, path)


def _ecm_for(panel: pd.DataFrame, column: str) -> dict:
    """Panel error correction of gross output and one benchmark price."""
    frame = panel.loc[panel["is_market"], ["industry_code", "year", "GO", column]].copy()
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    frame = frame.loc[(frame["GO"] > 0) & (frame[column] > 0)]
    frame = frame.sort_values(["industry_code", "year"])
    frame["log_GO"] = np.log(frame["GO"].to_numpy(dtype=float))
    frame["log_PP"] = np.log(frame[column].to_numpy(dtype=float))
    frame["d"] = frame["log_GO"] - frame["log_PP"]
    grouped = frame.groupby("industry_code")
    frame["d_lag"] = grouped["d"].shift(1)
    frame["delta_log_GO"] = grouped["log_GO"].diff()
    frame["delta_log_PP"] = grouped["log_PP"].diff()
    frame["delta_d"] = grouped["d"].diff()
    return error_correction(frame)


def plot_gravitation_coefficients(
    panel: pd.DataFrame,
    path: Path,
    *,
    columns: list[tuple[str, str]] | None = None,
) -> Path:
    """Error-correction coefficients with 95% confidence intervals."""
    columns = columns or [
        ("PP_market", "Moseley PP"),
        ("PP_Sraffa", "Sraffa"),
        ("PP_Shaikh", "Shaikh"),
        ("P_V", "Direct prices"),
    ]
    columns = [(c, t) for c, t in columns if c in panel.columns]
    if len(columns) < 2:
        raise ValueError(
            "the coefficient plot needs at least two benchmark columns; "
            f"found {[c for c, _ in columns]} in {list(panel.columns)[:6]}..."
        )

    rows = []
    for column, label in columns:
        models = _ecm_for(panel, column)
        go = models["delta_log_GO"]
        pp = models["delta_log_PP"]
        rows.append(
            {
                "label": label,
                "beta_go": go["beta"],
                "se_go": go["std_error"],
                "p_go": go["p_value"],
                "beta_pp": pp["beta"],
                "se_pp": pp["std_error"],
                "p_pp": pp["p_value"],
            }
        )
    table = pd.DataFrame(rows)

    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6), sharey=True)
    panels = [
        (axes[0], "beta_go", "se_go", "p_go", "Market output response, beta_GO"),
        (axes[1], "beta_pp", "se_pp", "p_pp", "Price-of-production response, beta_PP"),
    ]
    for ax, beta, se, pvalue, title in panels:
        order = table.sort_values(beta)
        colors = [_family_color(label) for label in order["label"]]
        lower = 1.96 * order[se]
        ax.errorbar(
            order[beta],
            order["label"],
            xerr=lower,
            fmt="o",
            color=GREY,
            ecolor=GREY,
            elinewidth=1.3,
            capsize=3,
        )
        ax.scatter(order[beta], order["label"], color=colors, s=55, zorder=3)
        ax.axvline(0.0, color=RED, linestyle="--", linewidth=1.2)
        ax.set_title(title, fontsize=10.5)
        ax.set_xlabel("Coefficient on the lagged log gap (bars = 95% CI)")
        for y, (value, pval) in enumerate(zip(order[beta], order[pvalue], strict=True)):
            marker = "significant" if pval < 0.05 else "not significant"
            offset = (-8, 6) if value > 0 else (8, 6)
            align = "right" if value > 0 else "left"
            ax.annotate(
                f"p={pval:.3f}  {marker}",
                (value, y),
                textcoords="offset points",
                xytext=offset,
                ha=align,
                fontsize=8,
            )

    axes[0].text(
        0.02,
        0.02,
        "Negative = the gap closes (gravitation)\nPositive = the gap widens (divergence)",
        transform=axes[0].transAxes,
        fontsize=8.5,
        va="bottom",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="white", alpha=0.9, edgecolor="none"),
    )
    market = panel.loc[panel["is_market"]] if "is_market" in panel.columns else panel
    n_industries = int(market["industry_code"].nunique())
    first, last = int(market["year"].min()), int(market["year"].max())
    fig.suptitle(
        "Does market output move toward prices of production? "
        f"{n_industries} industries, {first}-{last}",
        fontsize=11.5,
    )
    return _finish(fig, path)


def plot_forecast_horizons(
    current: pd.DataFrame,
    long_run: pd.DataFrame | None,
    path: Path,
) -> Path:
    """Out-of-sample log RMSE by horizon, current and long-run centres."""
    panels = [("Current prices of production", current)]
    if long_run is not None and not long_run.empty:
        panels.append(("Long-run centre (5-year trailing average)", long_run))

    fig, axes = plt.subplots(1, len(panels), figsize=(6.2 * len(panels), 4.6), sharey=True)
    axes = np.atleast_1d(axes)
    styles = {
        "naive": dict(color=GREY, linestyle="--", marker="s"),
        "ar1": dict(color=GREEN, linestyle="-", marker="o"),
        "ecm": dict(color=BLUE, linestyle="-", marker="^"),
        "pp": dict(color=RED, linestyle="-", marker="D"),
    }
    for ax, (title, metrics) in zip(axes, panels, strict=True):
        for model, group in metrics.groupby("model"):
            group = group.sort_values("horizon")
            style = styles.get(str(model).lower(), dict(color=GREY, marker="o"))
            ax.plot(
                group["horizon"],
                group["rmse_log"],
                linewidth=2.4 if str(model).lower() == "pp" else 1.8,
                label=str(model).upper() if str(model).lower() == "ecm" else str(model),
                **style,
            )
        ax.set_xticks(sorted(metrics["horizon"].unique()))
        ax.set_xlabel("Forecast horizon (years)")
        ax.set_title(title, fontsize=10.5)
    axes[0].set_ylabel("Pooled log RMSE (lower is better)")
    axes[0].legend(frameon=False, fontsize=9)

    fig.suptitle(
        "Forecasting gross output: the price benchmark is worse than a random walk",
        fontsize=11.5,
    )
    return _finish(fig, path)


def plot_dispersion_and_deflator(summary: pd.DataFrame, path: Path) -> Path:
    """Profit-rate dispersion, and how much the deflator actually changes."""
    fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.6))

    axes[0].plot(
        summary["year"],
        summary["rate_weighted_cv"],
        color=RED,
        linewidth=1.9,
        label="Full sample (incl. government, housing)",
    )
    axes[0].plot(
        summary["year"],
        summary["rate_weighted_cv_market"],
        color=BLUE,
        linewidth=2.1,
        label="Market industries",
    )
    axes[0].set_yscale("log")
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Weighted coefficient of variation of r_i (log scale)")
    axes[0].set_title("Profit-rate dispersion: outliers drive the full sample")
    axes[0].legend(frameon=False, fontsize=9)

    axes[1].plot(
        summary["year"],
        100 * summary["R_benchmark_market"],
        color=BLUE,
        linewidth=2.1,
        label="Nominal",
    )
    axes[1].plot(
        summary["year"],
        100 * summary["R_real_market"],
        color=GREEN,
        linewidth=1.9,
        linestyle="--",
        label="Real, 2017 dollars",
    )
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Percent")
    axes[1].set_title("Market rate of profit: deflating barely moves it")
    axes[1].legend(frameon=False, fontsize=9)

    return _finish(fig, path)


def plot_capital_composition(
    coverage: pd.DataFrame,
    inventories: pd.DataFrame,
    path: Path,
) -> Path:
    """What the advanced capital stock is made of, and inventory data quality."""
    latest = coverage.loc[coverage["year"] == coverage["year"].max()].iloc[0]
    year = int(latest["year"])
    parts = [
        ("Government and housing", float(latest["special_M_assets_bn"]), GREEN),
        ("Private fixed assets", float(latest["private_M_assets_bn"]), BLUE),
        ("Private inventories", float(latest["total_M_inv_bn"]), ORANGE),
    ]
    total = sum(value for _, value, _ in parts)

    inv = inventories.loc[inventories["year"] == inventories["year"].max()]
    by_source = inv.groupby("inventory_source")["M_inv"].sum()
    detail = float(by_source.get("BEA 1BUC detail", 0.0))
    broad = float(by_source.get("BEA 5.8.5B broad allocation", 0.0))
    inv_total = detail + broad

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.0))

    names = [name for name, _, _ in parts]
    values = [value for _, value, _ in parts]
    colors = [color for _, _, color in parts]
    axes[0].barh(names, values, color=colors)
    for y, value in enumerate(values):
        axes[0].text(value + total * 0.015, y, f"{value:,.0f} bn", va="center", fontsize=9)
    axes[0].set_xlim(0, max(values) * 1.30)
    axes[0].set_xlabel(f"Billion dollars, {year}")
    axes[0].set_title(f"Capital advanced M = {total:,.0f} bn, three sources")

    split = [
        ("Table 5.8.5B broad allocation", broad, ORANGE),
        ("BEA Table 1BUC detail", detail, BLUE),
    ]
    names = [name for name, _, _ in split]
    values = [value for _, value, _ in split]
    colors = [color for _, _, color in split]
    axes[1].barh(names, values, color=colors)
    for y, value in enumerate(values):
        share = 100 * value / inv_total if inv_total else float("nan")
        axes[1].text(
            value + inv_total * 0.015,
            y,
            f"{value / 1000:,.0f} bn  ({share:.1f}%)",
            va="center",
            fontsize=9,
        )
    axes[1].set_xlim(0, max(values) * 1.30)
    axes[1].set_xlabel(f"Million dollars, {year}")
    axes[1].set_title(f"Inventories = {inv_total / 1000:,.0f} bn, split by data source")

    return _finish(fig, path)


def _benchmark_panel(processed: Path) -> Path:
    """Panel that carries all benchmark price columns.

    ``industries.csv`` only has the Moseley columns; the Sraffa, Shaikh and
    labour-value benchmarks live in ``industries_shaikh.csv``.
    """
    for name in ("industries_shaikh.csv", "industries.csv"):
        candidate = processed / name
        if candidate.exists():
            return candidate
    return processed / "industries_shaikh.csv"


def build_findings_figures(config: ProjectConfig) -> dict[str, Path]:
    """Render every findings figure from existing artifacts."""
    settings = config.settings
    tables = settings.output_dir / "tables"
    processed = settings.processed_dir
    figures = settings.output_dir / "figures"
    figures.mkdir(parents=True, exist_ok=True)

    required = {
        "benchmark comparison": tables / "benchmark_comparison.csv",
        "unit-price panel": processed / "unit_prices.csv",
        "benchmark panel": _benchmark_panel(processed),
        "forecast metrics": tables / "gravitation_forecast_metrics.csv",
        "industry summary": tables / "industry_summary.csv",
        "capital coverage": tables / "industry_capital_coverage.csv",
        "inventory stocks": processed / "industry_inventories.csv",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    if missing:
        names = ", ".join(missing)
        raise FileNotFoundError(
            f"missing artifacts ({names}); run `usa-marxian all` first"
        )

    written: dict[str, Path] = {}

    comparison = pd.read_csv(required["benchmark comparison"])
    written["benchmark_fit"] = plot_benchmark_fit(comparison, figures / "findings_benchmark_fit.png")

    unit_panel = pd.read_csv(required["unit-price panel"])
    written["unit_price_fit"] = plot_unit_price_fit(unit_panel, figures / "findings_unit_prices.png")

    industry_panel = pd.read_csv(required["benchmark panel"])
    written["gravitation"] = plot_gravitation_coefficients(
        industry_panel, figures / "findings_gravitation.png"
    )

    current = pd.read_csv(required["forecast metrics"])
    long_run_path = tables / "gravitation_long_run_forecast_metrics.csv"
    long_run = pd.read_csv(long_run_path) if long_run_path.exists() else None
    written["forecast"] = plot_forecast_horizons(
        current, long_run, figures / "findings_forecast.png"
    )

    summary = pd.read_csv(required["industry summary"])
    written["dispersion"] = plot_dispersion_and_deflator(
        summary, figures / "findings_dispersion.png"
    )

    coverage = pd.read_csv(required["capital coverage"])
    inventories = pd.read_csv(required["inventory stocks"])
    written["capital"] = plot_capital_composition(
        coverage, inventories, figures / "findings_capital.png"
    )

    return written
