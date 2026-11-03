"""Detailed manufacturing and retail inventory stocks from BEA Table 1BUC.

BEA's NIPA underlying-detail API is keyless. Table 1BUC gives current-dollar
manufacturing and trade inventories, seasonally adjusted, end of period, for
1997 forward at a detailed NAICS level.

The detailed rows map almost one-to-one to the IO manufacturing and retail
industries:

* manufacturing rows map to the 19 IO manufacturing codes;
* retail rows map to the four IO retail codes;
* wholesale has only one IO code, so the broad Table 5.8.5B total is used;
* farm, mining/utilities/construction and "other industries" remain from the
  broad Table 5.8.5B allocation.

The detailed manufacturing and retail totals reconcile exactly to the broad
Table 5.8.5B totals on the current vintage.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

from .bea_inventories import (
    BEAInventoryError,
    allocate_inventory_stock,
    download_section5,
    parse_inventory_stocks,
)

ITABLE_STEP_URL = "https://apps.bea.gov/iTable/core/data/app/GetStep"
ITABLE_APP_ID = 19
ITABLE_TABLE_ID = "U001BC"
DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "usa-marxian/0.1 (research project)",
}

# Detailed BEA Table 1BUC label -> IO industry code.
DETAIL_TO_IO = {
    # Durable manufacturing
    "Wood product manufacturing": "321",
    "Nonmetallic mineral product manufacturing": "327",
    "Primary metal manufacturing": "331",
    "Fabricated metal product manufacturing": "332",
    "Machinery manufacturing": "333",
    "Computer and electronic product manufacturing": "334",
    "Electrical equipment, appliance, and component manufacturing": "335",
    "Motor vehicle and parts manufacturing": "3361MV",
    "Other transportation equipment manufacturing": "3364OT",
    "Furniture and related product manufacturing": "337",
    "Miscellaneous durable goods manufacturing": "339",
    # Nondurable manufacturing
    "Food manufacturing": "311FT",
    "Beverage and tobacco product manufacturing": "311FT",
    "Textile mills": "313TT",
    "Textile product mills": "313TT",
    "Apparel manufacturing": "315AL",
    "Leather and allied product manufacturing": "315AL",
    "Paper manufacturing": "322",
    "Printing and related support activities": "323",
    "Petroleum and coal product manufacturing": "324",
    "Chemical manufacturing": "325",
    "Plastics and rubber product manufacturing": "326",
    # Retail
    "Motor vehicle and parts dealers": "441",
    "Food and beverage stores": "445",
    "General merchandise stores": "452",
    "Furniture, furnishings, electronics, and appliance stores": "4A0",
    "Building material and garden equipment and supplies dealers": "4A0",
    "Clothing and clothing accessories stores": "4A0",
    "Other retail stores": "4A0",
}

DETAIL_MANUFACTURING_CATEGORY = "BEA 1BUC manufacturing detail"
DETAIL_RETAIL_CATEGORY = "BEA 1BUC retail detail"
BROAD_CATEGORIES_REPLACED = {
    "Manufacturing",
    "Motor vehicle and parts dealers",
    "Food and beverage stores",
    "General merchandise stores",
    "Other retail stores",
}


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


def _post(payload: dict, *, timeout: float = 60.0) -> dict:
    response = requests.post(
        ITABLE_STEP_URL, json=payload, headers=DEFAULT_HEADERS, timeout=timeout
    )
    response.raise_for_status()
    return response.json()


def fetch_detail(first_year: int = 1997, last_year: int = 2025) -> pd.DataFrame:
    """Fetch Table 1BUC from the keyless BEA iTable core API."""
    step1 = _post(
        {"appid": ITABLE_APP_ID, "stepnum": 1, "data": [["Categories", "Underlying"]]}
    )
    tables = json.loads(step1["Prompts"][0]["PromtData"])["Table"]
    matches = [table for table in tables if table.get("TableId") == ITABLE_TABLE_ID]
    if not matches:
        raise BEAInventoryError(f"BEA table not found: {ITABLE_TABLE_ID}")
    table_key = str(matches[0]["TableKey"])

    step2 = _post(
        {
            "appid": ITABLE_APP_ID,
            "stepnum": 2,
            "data": [
                ["Categories", "Underlying"],
                ["NIPA_Table_List", table_key],
                ["First_Year", str(first_year)],
                ["Last_Year", str(last_year)],
                ["Series", "A"],
                ["Select_all_years", "1"],
            ],
        }
    )
    prompt = next(
        (item for item in step2.get("Prompts", []) if item.get("Name") == "TheTable"),
        None,
    )
    if prompt is None:
        raise BEAInventoryError("BEA detail response has no TheTable prompt")

    table = json.loads(json.loads(prompt["PromtData"])["Table"])
    rows = table.get("Data_Rows", [])
    if len(rows) < 3:
        raise BEAInventoryError("BEA detail table is empty")

    header = [cell.get("CV") for cell in rows[0]]
    year_columns = {
        index: int(value)
        for index, value in enumerate(header)
        if isinstance(value, str) and value.strip().isdigit()
    }
    if not year_columns:
        raise BEAInventoryError("BEA detail table has no year columns")

    records = []
    for row in rows[2:]:
        label = str(row[1].get("CV", "")).strip()
        if not label:
            continue
        for index, year in year_columns.items():
            records.append(
                {
                    "year": year,
                    "line_label": label,
                    "value": _num(row[index].get("CV")),
                }
            )
    return pd.DataFrame(records)


def load_detail(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    first_year: int = 1997,
    last_year: int = 2025,
) -> pd.DataFrame:
    """Load Table 1BUC, caching the parsed long table."""
    path = raw_dir / "bea" / "inventory_detail_U001BC.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return pd.read_csv(path)

    detail = fetch_detail(first_year=first_year, last_year=last_year)
    tmp = path.with_suffix(".csv.tmp")
    detail.to_csv(tmp, index=False)
    tmp.replace(path)
    metadata = {
        "source": ITABLE_STEP_URL,
        "table": ITABLE_TABLE_ID,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows": int(detail.shape[0]),
    }
    (path.parent / "inventory_detail_U001BC.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return detail


def map_detail_to_io(detail: pd.DataFrame) -> pd.DataFrame:
    """Aggregate detailed BEA rows to IO industries."""
    mapped = detail.loc[detail["line_label"].isin(DETAIL_TO_IO)].copy()
    if mapped.empty:
        raise BEAInventoryError("No detailed inventory rows matched the IO mapping")
    mapped["industry_code"] = mapped["line_label"].map(DETAIL_TO_IO)
    mapped["inventory_category"] = np.where(
        mapped["industry_code"].isin({"441", "445", "452", "4A0"}),
        DETAIL_RETAIL_CATEGORY,
        DETAIL_MANUFACTURING_CATEGORY,
    )
    mapped["inventory_source"] = "BEA 1BUC detail"
    return (
        mapped.groupby(["year", "industry_code"], as_index=False)
        .agg(
            M_inv=("value", "sum"),
            inventory_category=("inventory_category", "first"),
            inventory_source=("inventory_source", "first"),
        )
        .sort_values(["year", "industry_code"])
    )


def combine_detail_with_broad(
    detail: pd.DataFrame,
    broad: pd.DataFrame,
) -> pd.DataFrame:
    """Replace broad manufacturing/retail allocations with detailed data."""
    broad_keep = broad.loc[~broad["inventory_category"].isin(BROAD_CATEGORIES_REPLACED)].copy()
    broad_keep["inventory_source"] = "BEA 5.8.5B broad allocation"
    combined = pd.concat([broad_keep, detail], ignore_index=True)
    return (
        combined.groupby(["year", "industry_code"], as_index=False)
        .agg(
            M_inv=("M_inv", "sum"),
            inventory_category=("inventory_category", "first"),
            inventory_source=("inventory_source", "first"),
        )
        .sort_values(["year", "industry_code"])
    )


def load_industry_inventories_detail(
    raw_dir: Path,
    panel: pd.DataFrame,
    *,
    max_age_days: int = 365,
    force: bool = False,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Load detailed manufacturing/retail inventories and combine with broad data.

    Falls back to the broad allocation if the detailed table is unavailable.
    """
    section5 = download_section5(raw_dir, max_age_days=max_age_days, force=force)
    totals = parse_inventory_stocks(section5, years=years)
    broad = allocate_inventory_stock(panel, totals)

    try:
        detail_raw = load_detail(
            raw_dir,
            max_age_days=max_age_days,
            force=force,
            first_year=min(years),
            last_year=max(years),
        )
        detail = map_detail_to_io(detail_raw)
    except Exception as exc:  # fall back to the broad allocation
        import warnings

        warnings.warn(
            f"Detailed inventory table unavailable, using broad allocation: {exc}",
            stacklevel=2,
        )
        broad["inventory_source"] = "BEA 5.8.5B broad allocation"
        return broad

    # Validate detailed manufacturing and retail sums against Table 5.8.5B.
    broad_by_category = broad.groupby(["year", "inventory_category"])["M_inv"].sum()
    for year in sorted(detail["year"].unique()):
        detail_m = detail.loc[
            (detail["year"] == year)
            & (detail["inventory_category"] == DETAIL_MANUFACTURING_CATEGORY),
            "M_inv",
        ].sum()
        detail_r = detail.loc[
            (detail["year"] == year)
            & (detail["inventory_category"] == DETAIL_RETAIL_CATEGORY),
            "M_inv",
        ].sum()
        broad_m = broad_by_category.get((year, "Manufacturing"), 0.0)
        broad_r = sum(
            broad_by_category.get((year, category), 0.0)
            for category in (
                "Motor vehicle and parts dealers",
                "Food and beverage stores",
                "General merchandise stores",
                "Other retail stores",
            )
        )
        if broad_m > 0 and abs(detail_m / broad_m - 1.0) > 0.01:
            raise BEAInventoryError(
                f"Detailed manufacturing inventories do not match broad total in {year}"
            )
        if broad_r > 0 and abs(detail_r / broad_r - 1.0) > 0.01:
            raise BEAInventoryError(
                f"Detailed retail inventories do not match broad total in {year}"
            )

    return combine_detail_with_broad(detail, broad)
