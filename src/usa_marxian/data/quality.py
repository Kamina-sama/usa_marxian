"""Data-quality checks for the raw panel and derived accounts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


def coverage_table(panel: pd.DataFrame, *, z_threshold: float = 5.0) -> pd.DataFrame:
    """Per-series coverage, missing years, sign problems and extreme changes."""
    rows = []
    for column in panel.columns:
        series = pd.to_numeric(panel[column], errors="coerce")
        valid = series.dropna()
        missing_years = [int(year) for year in series.index[series.isna()]]
        pct_change = series.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
        change = pct_change.dropna()
        if change.size >= 3 and change.std(ddof=1) > 0:
            z_scores = (change - change.mean()) / change.std(ddof=1)
            max_abs_z = float(z_scores.abs().max())
        else:
            max_abs_z = float("nan")

        rows.append(
            {
                "series": column,
                "n_obs": int(valid.size),
                "first_year": int(valid.index.min()) if not valid.empty else None,
                "last_year": int(valid.index.max()) if not valid.empty else None,
                "n_missing": int(series.isna().sum()),
                "missing_years": missing_years,
                "n_negative": int((valid < 0).sum()),
                "n_zero": int((valid == 0).sum()),
                "max_abs_z_change": max_abs_z,
                "flag_extreme_change": bool(np.isfinite(max_abs_z) and max_abs_z > z_threshold),
            }
        )
    return pd.DataFrame(rows)


def panel_summary(
    panel: pd.DataFrame,
    *,
    core_columns: list[str] | None = None,
) -> dict:
    """High-level shape and completeness of the panel.

    ``n_complete_years`` counts years complete across *all* loaded series,
    which is restrictive because some robustness series have short histories.
    ``n_complete_years_core`` counts only the columns needed by the baseline
    accounts.
    """
    complete = panel.dropna()
    summary = {
        "n_rows": int(panel.shape[0]),
        "n_series": int(panel.shape[1]),
        "start_year": int(panel.index.min()) if len(panel) else None,
        "end_year": int(panel.index.max()) if len(panel) else None,
        "n_complete_years": int(complete.shape[0]),
        "first_complete_year": int(complete.index.min()) if len(complete) else None,
        "last_complete_year": int(complete.index.max()) if len(complete) else None,
        "columns": list(panel.columns),
    }
    if core_columns:
        present = [column for column in core_columns if column in panel.columns]
        core = panel.loc[:, present].dropna()
        summary.update(
            {
                "core_columns": present,
                "n_complete_years_core": int(core.shape[0]),
                "first_complete_year_core": int(core.index.min()) if len(core) else None,
                "last_complete_year_core": int(core.index.max()) if len(core) else None,
            }
        )
    return summary


def write_quality(
    panel: pd.DataFrame,
    *,
    csv_path: Path,
    json_path: Path,
    z_threshold: float = 5.0,
    core_columns: list[str] | None = None,
) -> dict:
    """Write the coverage table and a JSON summary; return the summary."""
    table = coverage_table(panel, z_threshold=z_threshold)
    summary = panel_summary(panel, core_columns=core_columns)
    summary["series_with_flags"] = table.loc[
        table["flag_extreme_change"], "series"
    ].tolist()
    summary["series_with_negatives"] = table.loc[table["n_negative"] > 0, "series"].tolist()

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)
    json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary
