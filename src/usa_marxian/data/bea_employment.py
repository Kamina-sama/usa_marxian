"""Industry employment and wage rates from BEA NIPA Table 6.5D.

BEA NIPA Table 6.5D gives full-time equivalent employees by industry, 1998
forward, keyless inside the Section 6 workbook. FTE is the industry-specific
employment weight; multiplying by the macro hours-per-FTE gives industry labour
hours, and dividing the Use table's compensation by hours gives industry wage
rates.

This replaces the compensation-proportional allocation of hours. The remaining
assumption is a common annual hours-per-FTE across industries.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import yaml

from ..config import PROJECT_ROOT
from ..model.industries import NON_MARKET_CODES
from .sectors import download_section6

FTE_SHEET = "T60500D-A"
EMPLOYMENT_CONFIG_PATH = PROJECT_ROOT / "config" / "employment_mapping.yaml"


class BEAEmploymentError(RuntimeError):
    """Raised when the FTE table or mapping cannot be parsed."""


def _num(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip().replace(",", "").replace("\xa0", "")
    if text in {"", "...", ".....", "n/a", "N/A", "—", "-"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _normalise_label(value: object) -> str:
    text = str(value)
    text = re.sub(r"\\\d+\\", "", text)
    return " ".join(text.split())


def load_employment_config(path: Path = EMPLOYMENT_CONFIG_PATH) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if "fte_to_io" not in config:
        raise BEAEmploymentError("employment_mapping.yaml is missing fte_to_io")
    return config["fte_to_io"]


def parse_fte(path: Path, *, years: range = range(1998, 2026)) -> pd.DataFrame:
    """Parse Table 6.5D into a long frame of ``year, fte_code, fte_name, fte``.

    ``fte`` is in thousands of full-time equivalent employees.
    """
    wanted = set(years)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        if FTE_SHEET not in workbook.sheetnames:
            raise BEAEmploymentError(f"Sheet {FTE_SHEET} not found")
        sheet = workbook[FTE_SHEET]
        rows = list(sheet.iter_rows(min_row=8, values_only=True))
    finally:
        workbook.close()

    if len(rows) < 3:
        raise BEAEmploymentError("FTE table is empty")

    header = rows[0]
    year_columns = {}
    for index, value in enumerate(header):
        if isinstance(value, (int, float)) and int(value) in wanted:
            year_columns[int(value)] = index
        elif isinstance(value, str) and value.strip().isdigit() and int(value.strip()) in wanted:
            year_columns[int(value.strip())] = index
    if not year_columns:
        raise BEAEmploymentError("No year columns found in FTE table")

    records = []
    for row in rows[1:]:
        if not row or len(row) < 3 or row[1] is None:
            continue
        label = _normalise_label(row[1])
        code = str(row[0]).strip()
        if not label or label in {"Full-time equivalent employees", "Domestic industries", "Private industries"}:
            continue
        for year, index in year_columns.items():
            records.append(
                {"year": int(year), "fte_code": code, "fte_name": label, "fte": _num(row[index])}
            )
    return pd.DataFrame(records)


def map_fte_to_io(fte: pd.DataFrame, config: dict[str, str]) -> pd.DataFrame:
    """Map detailed FTE lines to IO industries and sum within each code."""
    mapped = fte.copy()
    mapped["industry_code"] = mapped["fte_name"].map(config)
    mapped = mapped.dropna(subset=["industry_code"])
    if mapped.empty:
        raise BEAEmploymentError("No FTE lines mapped to IO industries")
    return (
        mapped.groupby(["year", "industry_code"], as_index=False)
        .agg(fte=("fte", "sum"), n_fte_lines=("fte_name", "nunique"))
        .sort_values(["year", "industry_code"])
    )


def load_industry_employment(
    raw_dir: Path,
    *,
    force: bool = False,
    years: range = range(1998, 2026),
    config_path: Path = EMPLOYMENT_CONFIG_PATH,
) -> pd.DataFrame:
    """Return ``year, industry_code, fte`` (thousands of FTE)."""
    path = download_section6(raw_dir, force=force)
    fte = parse_fte(path, years=years)
    config = load_employment_config(config_path)
    return map_fte_to_io(fte, config)


def attach_employment(
    panel: pd.DataFrame,
    employment: pd.DataFrame,
    hours: pd.Series,
) -> pd.DataFrame:
    """Attach FTE-based hours and wage rates to the industry panel.

    ``hours`` is the macro total labour hours in billions (indexed by year).
    """
    out = panel.merge(
        employment.loc[:, ["year", "industry_code", "fte"]],
        on=["year", "industry_code"],
        how="left",
        validate="many_to_one",
    )

    market_mask = ~out["industry_code"].astype(str).isin(NON_MARKET_CODES)
    total_fte = (
        out.loc[market_mask].dropna(subset=["fte"])
        .groupby("year")["fte"]
        .sum()
    )
    hours_per_fte = (hours * 1e9) / (total_fte * 1e3)

    out["hours_per_fte"] = out["year"].map(hours_per_fte)
    has_fte = out["fte"].notna()
    out["labour_hours"] = np.where(
        market_mask & has_fte,
        out["fte"] * 1000.0 * out["hours_per_fte"],
        np.nan,
    )
    out["hours_source"] = np.where(
        market_mask & has_fte, "fte", "missing"
    )

    if "V" in out.columns:
        out["wage_rate_i"] = out["V"] * 1e6 / out["labour_hours"]
    return out


def employment_coverage(panel: pd.DataFrame, hours: pd.Series | None = None) -> pd.DataFrame:
    """Per-year coverage of measured versus missing employment (market only)."""
    market = panel.loc[~panel["industry_code"].astype(str).isin(NON_MARKET_CODES)]
    grouped = (
        market.groupby("year")
        .agg(
            n_industries=("industry_code", "nunique"),
            n_fte=("fte", lambda s: int(s.notna().sum())),
            total_fte=("fte", "sum"),
            total_hours=("labour_hours", "sum"),
        )
        .reset_index()
    )
    grouped["hours_bn"] = grouped["total_hours"] / 1e9
    if hours is not None:
        grouped["macro_hours_bn"] = hours.reindex(grouped["year"]).to_numpy()
        grouped["gap_pct"] = 100.0 * (
            grouped["hours_bn"] / grouped["macro_hours_bn"] - 1.0
        )
    return grouped
