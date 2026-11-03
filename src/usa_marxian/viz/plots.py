"""Plotting helpers."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

plt.rcParams.update(
    {
        "figure.dpi": 120,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.alpha": 0.25,
        "font.size": 10,
    }
)


def _finish(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def plot_melt(accounts: pd.DataFrame, path: Path, *, real: bool = False) -> Path:
    column = "melt_real" if real else "melt"
    label = "constant 2017 USD per hour" if real else "current USD per hour"
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(accounts.index, accounts[column], color="#1f4e79", linewidth=1.8)
    ax.set_title("Monetary expression of labour time (MELT)")
    ax.set_xlabel("Year")
    ax.set_ylabel(label)
    return _finish(fig, path)


def plot_distribution(accounts: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(accounts.index, accounts["rate_surplus_value"], label="S / V", linewidth=1.8)
    ax.plot(accounts.index, accounts["profit_share"], label="S / N", linewidth=1.8)
    ax.plot(accounts.index, accounts["wage_share"], label="V / N", linewidth=1.8)
    ax.set_title("Distribution of new value")
    ax.set_xlabel("Year")
    ax.set_ylabel("Ratio")
    ax.legend(frameon=False)
    return _finish(fig, path)


def plot_profit_rate(accounts: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(accounts.index, 100 * accounts["rate_profit"], color="#8b1a1a", linewidth=1.9)
    ax.set_title("General rate of profit, R = S / M")
    ax.set_xlabel("Year")
    ax.set_ylabel("Percent")
    return _finish(fig, path)


def plot_composition(accounts: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(accounts.index, accounts["composition"], color="#4a6b3a", linewidth=1.9)
    ax.set_title("Composition of capital, M / V")
    ax.set_xlabel("Year")
    ax.set_ylabel("Ratio")
    return _finish(fig, path)


def plot_robustness(table: pd.DataFrame, path: Path) -> Path:
    """Compare the LTV slope and terminal profit rate across specifications."""
    valid = table.loc[table["error"].isna()].copy() if "error" in table else table.copy()
    valid = valid.iloc[::-1]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    axes[0].barh(valid["name"], valid["ltv_slope"], color="#1f4e79")
    axes[0].axvline(1.0, color="#8b1a1a", linestyle="--", linewidth=1.2)
    axes[0].set_title("LTV slope on log L")
    axes[0].set_xlabel("Slope (dashed line = 1)")

    axes[1].barh(valid["name"], 100 * valid["rate_profit_last"], color="#4a6b3a")
    axes[1].set_title("Rate of profit, last year")
    axes[1].set_xlabel("Percent")
    return _finish(fig, path)


def plot_industry_dispersion(summary: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(summary["year"], summary["rate_weighted_cv"], color="#8b1a1a", linewidth=1.9)
    ax.set_title("Dispersion of industry surplus-value rates")
    ax.set_xlabel("Year")
    ax.set_ylabel("Weighted coefficient of variation")
    return _finish(fig, path)


def plot_gravitation_deviation(by_year: pd.DataFrame, path: Path) -> Path:
    fig, ax1 = plt.subplots(figsize=(9, 4.5))
    ax1.plot(by_year["year"], by_year["mean_abs_d"], color="#8b1a1a", linewidth=1.9)
    ax1.set_xlabel("Year")
    ax1.set_ylabel("Mean absolute deviation")
    ax2 = ax1.twinx()
    ax2.plot(
        by_year["year"],
        100 * by_year["share_within_25pct"],
        color="#1f4e79",
        linewidth=1.6,
        linestyle="--",
    )
    ax2.set_ylabel("% within 25%")
    ax1.set_title("Deviation of gross output from prices of production")
    return _finish(fig, path)


def plot_gravitation_forecast(metrics: pd.DataFrame, path: Path) -> Path:
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for model, group in metrics.groupby("model"):
        group = group.sort_values("horizon")
        ax.plot(group["horizon"], group["rmse_log"], marker="o", linewidth=1.8, label=model)
    ax.set_xlabel("Forecast horizon (years)")
    ax.set_ylabel("Log RMSE (lower is better)")
    ax.set_title("Out-of-sample forecasts of gross output")
    ax.legend(frameon=False)
    return _finish(fig, path)


def plot_pp_vs_go(latest: pd.DataFrame, path: Path) -> Path:
    column = "PP_market" if "PP_market" in latest.columns else "PP"
    frame = latest.loc[(latest["GO"] > 0) & (latest[column] > 0)].copy()
    if "is_market" in frame.columns:
        frame = frame.loc[frame["is_market"]]
    fig, ax = plt.subplots(figsize=(6.5, 6))
    ax.scatter(frame[column], frame["GO"], s=18, alpha=0.7, color="#1f4e79")
    low = min(frame[column].min(), frame["GO"].min())
    high = max(frame[column].max(), frame["GO"].max())
    ax.plot([low, high], [low, high], color="#8b1a1a", linestyle="--", linewidth=1.2)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_title(
        "Prices of production vs gross output, "
        f"{int(frame['year'].iloc[0])} (market industries, actual M_i)"
    )
    ax.set_xlabel("PP_i = K_i + R M_i, log scale")
    ax.set_ylabel("Observed gross output, log scale")
    return _finish(fig, path)
