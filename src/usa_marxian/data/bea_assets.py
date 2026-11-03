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

FA_DETAIL_BASE_URL = "https://apps.bea.gov/national/FA2004/Details/xls"
DETAIL_FILES = {
    "stock_current": "detailnonres_stk1.xlsx",
    "stock_real": "detailnonres_stk2.xlsx",
    "investment": "detailnonres_inv1.xlsx",
    "depreciation": "detailnonres_dep1.xlsx",
}
FA_DETAIL_FILENAME = DETAIL_FILES["stock_current"]
FA_DETAIL_URL = f"{FA_DETAIL_BASE_URL}/{FA_DETAIL_FILENAME}"
GOV_FA_URL = "https://apps.bea.gov/national/FixedAssets/Release/XLS/Section7All_xls.xlsx"
GOV_FA_FILENAME = "Section7All_xls.xlsx"
RES_FA_URL = "https://apps.bea.gov/national/FixedAssets/Release/XLS/Section5All_xls.xlsx"
RES_FA_FILENAME = "FixedAssets_Section5All_xls.xlsx"
SPECIAL_CAPITAL_CODES = {"HS", "GFE", "GFGD", "GFGN", "GSLE", "GSLG"}
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
    kind: str = "stock_current",
    max_age_days: int = 365,
    force: bool = False,
    timeout: float = 120.0,
) -> Path:
    """Download one fixed-asset detail workbook and return its path."""
    if kind not in DETAIL_FILES:
        raise ValueError(f"Unknown fixed-asset detail kind: {kind}")
    filename = DETAIL_FILES[kind]
    url = f"{FA_DETAIL_BASE_URL}/{filename}"
    path = raw_dir / "bea" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return path

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise BEAAssetsError("BEA fixed-assets download did not return an xlsx file")
    tmp = path.with_suffix(".xlsx.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)

    metadata = {
        "source_url": url,
        "kind": kind,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": int(path.stat().st_size),
    }
    (path.parent / filename.replace(".xlsx", ".json")).write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return path


def parse_detail_file(
    path: Path,
    *,
    value_name: str = "value",
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Parse one fixed-asset detail workbook.

    Returns a long frame with columns ``year``, ``fa_code``, ``fa_name`` and
    ``value_name``.
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
            if len(total_rows) == 0:
                continue  # auxiliary sheet, not an industry
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
                        value_name: total,
                    }
                )
    finally:
        workbook.close()

    if not records:
        raise BEAAssetsError("No fixed-asset observations parsed")
    return pd.DataFrame(records)


def parse_fixed_assets(
    path: Path,
    *,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Backward-compatible parser for current-cost net stocks."""
    return parse_detail_file(path, value_name="M", years=years)


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


def load_industry_capital_detail(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    years: range = range(1997, 2026),
    config_path: Path = CAPITAL_CONFIG_PATH,
) -> pd.DataFrame:
    """Return current and constant-price stocks, investment and depreciation.

    Columns: ``year, industry_code, M_current, M_real, I_current, D_current``.
    Values are millions of dollars; ``M_real`` is in 2017 dollars.
    """
    config = load_capital_config(config_path)
    mapping = {str(key): str(value) for key, value in config["fa_to_io"].items()}
    column_by_kind = {
        "stock_current": "M_current",
        "stock_real": "M_real",
        "investment": "I_current",
        "depreciation": "D_current",
    }

    merged = None
    for kind, column in column_by_kind.items():
        path = download_detail(
            raw_dir, kind=kind, max_age_days=max_age_days, force=force
        )
        detail = parse_detail_file(path, value_name=column, years=years)
        detail["industry_code"] = detail["fa_code"].map(mapping)
        unmapped = sorted(
            detail.loc[detail["industry_code"].isna(), "fa_code"].unique()
        )
        if unmapped:
            raise BEAAssetsError(f"Unmapped fixed-asset industries: {unmapped}")
        grouped = (
            detail.groupby(["year", "industry_code"], as_index=False)[column]
            .sum()
        )
        merged = grouped if merged is None else merged.merge(
            grouped, on=["year", "industry_code"], how="outer"
        )

    if merged is None:
        raise BEAAssetsError("No fixed-asset detail observations parsed")
    return merged.sort_values(["year", "industry_code"]).reset_index(drop=True)


def download_fixed_assets_section(
    raw_dir: Path,
    url: str,
    filename: str,
    *,
    max_age_days: int = 365,
    force: bool = False,
    timeout: float = 120.0,
) -> Path:
    """Download a BEA Fixed Assets section workbook."""
    path = raw_dir / "bea" / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return path

    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise BEAAssetsError(f"BEA fixed-assets download did not return xlsx: {url}")
    tmp = path.with_suffix(".xlsx.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)
    return path


def parse_fixed_assets_table(
    path: Path,
    sheet_name: str,
    labels: set[str],
) -> pd.DataFrame:
    """Parse selected labels from a BEA Fixed Assets annual table.

    The first occurrence of each label is used; some tables repeat
    "National defense" and "Nondefense" in a nonresidential addendum.
    """
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook[sheet_name]
        rows = list(sheet.iter_rows(min_row=8, max_row=sheet.max_row, values_only=True))
    finally:
        workbook.close()
    if not rows:
        raise BEAAssetsError(f"{sheet_name}: empty fixed-assets table")

    header = rows[0]
    year_columns = {}
    for index, value in enumerate(header):
        if isinstance(value, (int, float)):
            year_columns[int(value)] = index
        elif isinstance(value, str) and value.strip().isdigit():
            year_columns[int(value.strip())] = index
    if not year_columns:
        raise BEAAssetsError(f"{sheet_name}: no year columns")

    found: dict[str, dict[int, float]] = {}
    for row in rows[1:]:
        if not row or len(row) <= 1 or row[1] is None:
            continue
        label = " ".join(str(row[1]).split())
        if label not in labels or label in found:
            continue
        found[label] = {
            year: _num(row[index])
            for year, index in year_columns.items()
            if index < len(row)
        }

    missing = labels.difference(found)
    if missing:
        raise BEAAssetsError(f"{sheet_name}: missing labels {sorted(missing)}")

    records = []
    for label, values in found.items():
        for year, value in values.items():
            records.append({"year": year, "label": label, "value": value})
    return pd.DataFrame(records)


def load_government_housing_capital(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Actual fixed-asset stocks for government units and owner-occupied housing.

    Returns ``year, industry_code, M, capital_source`` in millions.
    Federal fixed assets equal defense plus nondefense, so federal government
    enterprises are zero in this source. All government enterprise fixed assets
    are therefore state and local.
    """
    gov_path = download_fixed_assets_section(
        raw_dir, GOV_FA_URL, GOV_FA_FILENAME, max_age_days=max_age_days, force=force
    )
    res_path = download_fixed_assets_section(
        raw_dir, RES_FA_URL, RES_FA_FILENAME, max_age_days=max_age_days, force=force
    )

    gov = parse_fixed_assets_table(
        gov_path,
        "FAAt701-A",
        {
            "National defense",
            "Nondefense",
            "General government fixed assets",
            "Government enterprise fixed assets",
        },
    ).pivot(index="year", columns="label", values="value")
    res = parse_fixed_assets_table(
        res_path,
        "FAAt501-A",
        {"Owner-occupied"},
    ).pivot(index="year", columns="label", values="value")

    frame = gov.join(res, how="inner")
    frame = frame.loc[frame.index.isin(list(years))].sort_index()

    general = frame["General government fixed assets"]
    defense = frame["National defense"]
    nondefense = frame["Nondefense"]
    enterprise = frame["Government enterprise fixed assets"]
    state_local_general = general - defense - nondefense
    if (state_local_general < 0).any():
        raise BEAAssetsError("Negative state/local general government capital")

    special = pd.DataFrame(
        {
            "HS": frame["Owner-occupied"],
            "GFGD": defense,
            "GFGN": nondefense,
            "GFE": 0.0,
            "GSLE": enterprise,
            "GSLG": state_local_general,
        }
    )
    special = special.reset_index().melt(
        id_vars="year", var_name="industry_code", value_name="M"
    )
    special["capital_source"] = np.where(
        special["industry_code"] == "HS",
        "residential_fixed_assets",
        "government_fixed_assets",
    )
    return special.loc[:, ["year", "industry_code", "M", "capital_source"]]


def attach_capital_stock(
    panel: pd.DataFrame,
    capital: pd.DataFrame,
    *,
    inventories: pd.DataFrame | None = None,
    special: pd.DataFrame | None = None,
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
    if special is not None:
        out = out.merge(
            special.loc[:, ["year", "industry_code", "M", "capital_source"]].rename(
                columns={"M": "M_special", "capital_source": "special_source"}
            ),
            on=["year", "industry_code"],
            how="left",
        )
    else:
        out["M_special"] = np.nan
        out["special_source"] = None

    if inventories is not None:
        inventory_columns = ["year", "industry_code", "M_inv", "inventory_category"]
        if "inventory_source" in inventories.columns:
            inventory_columns.append("inventory_source")
        out = out.merge(
            inventories.loc[:, inventory_columns],
            on=["year", "industry_code"],
            how="left",
        )
        if "inventory_source" not in out.columns:
            out["inventory_source"] = "broad"
    else:
        out["M_inv"] = 0.0
        out["inventory_category"] = None
        out["inventory_source"] = None

    out["M_inv"] = out["M_inv"].fillna(0.0)
    out["M_assets"] = out["M_assets"].where(out["M_assets"].notna())
    out["M_assets"] = out["M_assets"].fillna(out["M_special"])
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

    base_source = np.where(
        actual & (out["M_inv"] > 0),
        "fixed_assets+inventories",
        np.where(actual, "fixed_assets", f"{fallback}_proxy"),
    )
    out["capital_source"] = out["special_source"].where(
        out["special_source"].notna(), base_source
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
    data = panel.copy()
    data["is_special"] = data["industry_code"].astype(str).isin(SPECIAL_CAPITAL_CODES)
    data["M_assets_private"] = data["M_assets"].where(~data["is_special"], 0.0)
    data["M_assets_special"] = data["M_assets"].where(data["is_special"], 0.0)

    grouped = (
        data.groupby("year")
        .agg(
            n_industries=("industry_code", "nunique"),
            n_actual=(
                "capital_source",
                lambda s: int((s.astype(str) != "cost_proxy").sum()),
            ),
            n_proxy=(
                "capital_source",
                lambda s: int((s.astype(str) == "cost_proxy").sum()),
            ),
            total_M_assets_mn=("M_assets", "sum"),
            private_M_assets_mn=("M_assets_private", "sum"),
            special_M_assets_mn=("M_assets_special", "sum"),
            total_M_inv_mn=("M_inv", "sum"),
            total_M_used_mn=("M", "sum"),
        )
        .reset_index()
    )
    grouped["total_M_assets_bn"] = grouped["total_M_assets_mn"] / 1000.0
    grouped["private_M_assets_bn"] = grouped["private_M_assets_mn"] / 1000.0
    grouped["special_M_assets_bn"] = grouped["special_M_assets_mn"] / 1000.0
    grouped["total_M_inv_bn"] = grouped["total_M_inv_mn"] / 1000.0
    grouped["total_M_actual_bn"] = (
        grouped["total_M_assets_bn"] + grouped["total_M_inv_bn"]
    )
    grouped["private_M_actual_bn"] = (
        grouped["private_M_assets_bn"] + grouped["total_M_inv_bn"]
    )

    if macro is not None and {"M_fixed_only", "M"}.issubset(macro.columns):
        macro_fixed = macro["M_fixed_only"].reindex(grouped["year"]).to_numpy()
        macro_total = macro["M"].reindex(grouped["year"]).to_numpy()
        macro_inventory = macro_total - macro_fixed
        grouped["macro_fixed_bn"] = macro_fixed
        grouped["macro_inv_bn"] = macro_inventory
        grouped["macro_M_bn"] = macro_total
        grouped["gap_fixed_pct"] = 100.0 * (
            grouped["private_M_assets_bn"] / grouped["macro_fixed_bn"] - 1.0
        )
        grouped["gap_inv_pct"] = 100.0 * (
            grouped["total_M_inv_bn"] / grouped["macro_inv_bn"] - 1.0
        )
        grouped["gap_total_pct"] = 100.0 * (
            grouped["private_M_actual_bn"] / grouped["macro_M_bn"] - 1.0
        )
    return grouped
