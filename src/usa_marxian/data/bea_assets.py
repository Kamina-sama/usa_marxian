"""Actual industry capital stocks from the BEA fixed-asset detail tables.

The BEA Fixed Assets release publishes current-cost net stocks of private
nonresidential fixed assets for 74 detailed industries:

    https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_stk1.xlsx

Each industry sheet contains three top-level asset totals (equipment,
structures and intellectual property products). Their sum is the industry's
current-cost net fixed capital stock. Values are in millions of dollars, the
same units as the BEA IO Use table.

`config/industry_capital.yaml` maps the 74 detailed industries to the 71 IO
summary industries. Government units and housing have no private nonresidential
fixed assets; they fall back to the cost proxy and are flagged.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import requests
import yaml

from ..config import PROJECT_ROOT

FA_DETAIL_URL = "https://apps.bea.gov/national/FA2004/Details/xls/detailnonres_stk1.xlsx"
FA_DETAIL_FILENAME = "detailnonres_stk1.xlsx"
CAPITAL_CONFIG_PATH = PROJECT_ROOT / "config" / "industry_capital.yaml"
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}

TOTAL_LABELS = {
    "TOTAL EQUIPMENT",
    "TOTAL STRUCTURES",
    "TOTAL INTELLECTUAL PROPERTY PRODUCTS",
}


class BEAAssetsError(RuntimeError):
    """Raised when the fixed-asset detail file cannot be parsed."""


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


def load_capital_config(path: Path = CAPITAL_CONFIG_PATH) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if "fa_to_io" not in config:
        raise BEAAssetsError("industry_capital.yaml is missing fa_to_io")
    return config


def download_detail(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    timeout: float = 120.0,
) -> Path:
    """Download the fixed-asset detail workbook and return its path."""
    path = raw_dir / "bea" / FA_DETAIL_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return path

    response = requests.get(FA_DETAIL_URL, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise BEAAssetsError("BEA fixed-assets download did not return an xlsx file")
    tmp = path.with_suffix(".xlsx.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)

    metadata = {
        "source_url": FA_DETAIL_URL,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": int(path.stat().st_size),
    }
    (path.parent / "detailnonres_stk1.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return path


def parse_fixed_assets(
    path: Path,
    *,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Parse current-cost net stocks by detailed fixed-asset industry.

    Returns a long frame with columns ``year``, ``fa_code``, ``fa_name`` and
    ``M`` (millions of current dollars).
    """
    wanted = set(years)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records = []

    try:
        for sheet_name in workbook.sheetnames:
            if sheet_name in {"readme", "Datasets"}:
                continue
            sheet = workbook[sheet_name]
            rows = list(sheet.iter_rows(min_row=1, max_row=110, values_only=True))
            if len(rows) < 82:
                continue

            title = str(rows[0][0] or "").replace("\xa0", " ").strip()
            if " - " in title:
                fa_code, fa_name = title.split(" - ", 1)
            else:
                fa_code, fa_name = sheet_name, title
            fa_code = fa_code.strip()
            fa_name = " ".join(fa_name.split())

            header = rows[5]
            year_columns = {}
            for index, value in enumerate(header):
                if isinstance(value, (int, float)):
                    year_columns[int(value)] = index
                elif isinstance(value, str) and value.strip().isdigit():
                    year_columns[int(value.strip())] = index

            total_rows = [
                row
                for row in rows
                if row
                and len(row) > 1
                and row[1] is not None
                and " ".join(str(row[1]).split()).upper() in TOTAL_LABELS
            ]
            if len(total_rows) != 3:
                raise BEAAssetsError(
                    f"{sheet_name}: expected 3 total asset rows, found {len(total_rows)}"
                )

            for year, column in year_columns.items():
                if year not in wanted:
                    continue
                total = sum(_num(row[column]) for row in total_rows)
                records.append(
                    {
                        "year": int(year),
                        "fa_code": fa_code,
                        "fa_name": fa_name,
                        "M": total,
                    }
                )
    finally:
        workbook.close()

    if not records:
        raise BEAAssetsError("No fixed-asset observations parsed")
    return pd.DataFrame(records)


def load_industry_capital(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    years: range = range(1997, 2026),
    config_path: Path = CAPITAL_CONFIG_PATH,
) -> pd.DataFrame:
    """Return ``year, industry_code, M`` in millions of current dollars."""
    config = load_capital_config(config_path)
    detail_path = download_detail(raw_dir, max_age_days=max_age_days, force=force)
    fixed_assets = parse_fixed_assets(detail_path, years=years)

    mapping = {str(key): str(value) for key, value in config["fa_to_io"].items()}
    fixed_assets["industry_code"] = fixed_assets["fa_code"].map(mapping)
    unmapped = sorted(fixed_assets.loc[fixed_assets["industry_code"].isna(), "fa_code"].unique())
    if unmapped:
        raise BEAAssetsError(f"Unmapped fixed-asset industries: {unmapped}")

    capital = (
        fixed_assets.groupby(["year", "industry_code"], as_index=False)
        .agg(M=("M", "sum"), n_fa_industries=("fa_code", "nunique"))
        .sort_values(["year", "industry_code"])
    )
    return capital


def attach_capital_stock(
    panel: pd.DataFrame,
    capital: pd.DataFrame,
    *,
    inventories: pd.DataFrame | None = None,
    fallback: str = "cost",
) -> pd.DataFrame:
    """Merge actual fixed-asset and inventory stocks into the industry panel.

    ``M_assets`` is the actual BEA fixed-asset stock (millions); ``M_inv`` is the
    allocated inventory stock (millions). ``M`` equals their sum where fixed
    assets are available and the configured fallback otherwise.
    ``capital_source`` records which was used.
    """
    out = panel.copy()
    if "K" not in out.columns:
        out["K"] = out["C"] + out["V"]

    out = out.merge(
        capital.loc[:, ["year", "industry_code", "M"]].rename(columns={"M": "M_assets"}),
        on=["year", "industry_code"],
        how="left",
    )
    if inventories is not None:
        out = out.merge(
            inventories.loc[
                :, ["year", "industry_code", "M_inv", "inventory_category"]
            ],
            on=["year", "industry_code"],
            how="left",
        )
    else:
        out["M_inv"] = 0.0
        out["inventory_category"] = None

    out["M_inv"] = out["M_inv"].fillna(0.0)
    out["M_assets"] = out["M_assets"].where(out["M_assets"] > 0)
    actual = out["M_assets"].notna()

    if fallback == "cost":
        out["M"] = np.where(
            actual,
            out["M_assets"].fillna(0.0) + out["M_inv"],
            out["K"],
        )
    elif fallback == "nan":
        out["M"] = np.where(
            actual,
            out["M_assets"].fillna(0.0) + out["M_inv"],
            np.nan,
        )
    else:
        raise ValueError(f"Unknown capital fallback: {fallback}")

    out["capital_source"] = np.where(
        actual & (out["M_inv"] > 0),
        "fixed_assets+inventories",
        np.where(actual, "fixed_assets", f"{fallback}_proxy"),
    )

    return out


def capital_coverage(
    panel: pd.DataFrame,
    macro: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Per-year coverage of actual versus proxied capital stocks.

    ``macro`` is the macro accounts frame indexed by year with columns
    ``M_fixed_only`` (fixed assets) and ``M`` (fixed assets plus inventories),
    both in billions.
    """
    grouped = (
        panel.groupby("year")
        .agg(
            n_industries=("industry_code", "nunique"),
            n_actual=(
                "capital_source",
                lambda s: int(s.astype(str).str.startswith("fixed_assets").sum()),
            ),
            n_proxy=(
                "capital_source",
                lambda s: int((~s.astype(str).str.startswith("fixed_assets")).sum()),
            ),
            total_M_assets_mn=("M_assets", "sum"),
            total_M_inv_mn=("M_inv", "sum"),
            total_M_used_mn=("M", "sum"),
        )
        .reset_index()
    )
    grouped["total_M_assets_bn"] = grouped["total_M_assets_mn"] / 1000.0
    grouped["total_M_inv_bn"] = grouped["total_M_inv_mn"] / 1000.0
    grouped["total_M_actual_bn"] = (
        grouped["total_M_assets_bn"] + grouped["total_M_inv_bn"]
    )

    if macro is not None and {"M_fixed_only", "M"}.issubset(macro.columns):
        macro_fixed = macro["M_fixed_only"].reindex(grouped["year"]).to_numpy()
        macro_total = macro["M"].reindex(grouped["year"]).to_numpy()
        macro_inventory = macro_total - macro_fixed
        grouped["macro_fixed_bn"] = macro_fixed
        grouped["macro_inv_bn"] = macro_inventory
        grouped["macro_M_bn"] = macro_total
        grouped["gap_fixed_pct"] = 100.0 * (
            grouped["total_M_assets_bn"] / grouped["macro_fixed_bn"] - 1.0
        )
        grouped["gap_inv_pct"] = 100.0 * (
            grouped["total_M_inv_bn"] / grouped["macro_inv_bn"] - 1.0
        )
        grouped["gap_total_pct"] = 100.0 * (
            grouped["total_M_actual_bn"] / grouped["macro_M_bn"] - 1.0
        )
    return grouped
