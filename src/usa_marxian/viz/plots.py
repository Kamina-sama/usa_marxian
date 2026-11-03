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
