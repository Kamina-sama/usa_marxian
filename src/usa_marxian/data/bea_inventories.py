"""Industry inventory stocks from BEA NIPA Table 5.8.5B.

BEA publishes private inventory stocks by broad industry quarterly. The
year-end (Q4) values are the stock at the end of the year, consistent with the
BEA fixed-asset stocks.

Table 5.8.5B has nine usable categories:

    Farm
    Mining, utilities, and construction
    Manufacturing
    Wholesale trade
    Motor vehicle and parts dealers
    Food and beverage stores
    General merchandise stores
    Other retail stores
    Other industries

Farm, wholesale and the four retail categories map directly to IO industries.
Mining/utilities/construction and manufacturing are allocated within the group
in proportion to gross output. "Other industries" is allocated across the
remaining market industries in proportion to gross output.

The broad totals are official BEA data; the within-group allocation is a proxy
and is documented as such.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import requests

SECTION5_URL = "https://apps.bea.gov/national/Release/XLS/Survey/Section5All_xls.xlsx"
SECTION5_FILENAME = "Section5All_xls.xlsx"
INVENTORY_SHEET = "T50805B-Q"
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}

NON_MARKET_CODES = {"HS", "GFGD", "GFGN", "GFE", "GSLG", "GSLE"}

MANUFACTURING_CODES = [
    "311FT",
    "313TT",
    "315AL",
    "321",
    "322",
    "323",
    "324",
    "325",
    "326",
    "327",
    "331",
    "332",
    "333",
    "334",
    "335",
    "3361MV",
    "3364OT",
    "337",
    "339",
]

MINING_UTILITIES_CONSTRUCTION = ["211", "212", "213", "22", "23"]

DIRECT_CODES = {
    "Farm": ["111CA"],
    "Wholesale trade": ["42"],
    "Motor vehicle and parts dealers": ["441"],
    "Food and beverage stores": ["445"],
    "General merchandise stores": ["452"],
    "Other retail stores": ["4A0"],
}

GROUP_CODES = {
    "Mining, utilities, and construction": MINING_UTILITIES_CONSTRUCTION,
    "Manufacturing": MANUFACTURING_CODES,
}

OTHER_CATEGORY = "Other industries"
COMPONENT_CATEGORIES = list(DIRECT_CODES) + list(GROUP_CODES) + [OTHER_CATEGORY]


class BEAInventoryError(RuntimeError):
    """Raised when the inventory table cannot be parsed or allocated."""


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


def download_section5(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    timeout: float = 120.0,
) -> Path:
    """Download the NIPA Section 5 workbook and return its path."""
    path = raw_dir / "bea" / SECTION5_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return path

    response = requests.get(SECTION5_URL, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise BEAInventoryError("BEA Section 5 download did not return an xlsx file")
    tmp = path.with_suffix(".xlsx.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)

    metadata = {
        "source_url": SECTION5_URL,
        "sheet": INVENTORY_SHEET,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": int(path.stat().st_size),
    }
    (path.parent / "Section5All_xls.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return path


def parse_inventory_stocks(
    path: Path,
    *,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Parse Q4 private inventory stocks by broad category.

    Returns ``year, category, value`` in millions of current dollars.
    """
    wanted = set(years)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        sheet = workbook[INVENTORY_SHEET]
        rows = list(sheet.iter_rows(min_row=8, max_row=40, values_only=True))
    finally:
        workbook.close()

    if not rows:
        raise BEAInventoryError("Inventory sheet is empty")

    header = rows[0]
    quarter_columns = {
        int(value[:4]): index
        for index, value in enumerate(header)
        if isinstance(value, str) and value.strip().endswith("Q4")
    }
    if not quarter_columns:
        raise BEAInventoryError("No Q4 columns found in inventory table")

    records = []
    total_by_year = {}
    component_by_year = {}

    for row in rows[1:]:
        if not row or len(row) < 3:
            continue
        label = " ".join(str(row[1]).split()) if row[1] is not None else ""
        if label == "Addenda:":
            break
        if label not in set(COMPONENT_CATEGORIES) | {"Private inventories"}:
            continue

        for year, column in quarter_columns.items():
            if year not in wanted:
                continue
            value = _num(row[column])
            if label == "Private inventories":
                total_by_year[year] = value
            else:
                records.append({"year": int(year), "category": label, "value": value})
                component_by_year[year] = component_by_year.get(year, 0.0) + value

    if not records:
        raise BEAInventoryError("No inventory observations parsed")

    for year, total in total_by_year.items():
        components = component_by_year.get(year, 0.0)
        if total > 0 and abs(components / total - 1.0) > 0.01:
            raise BEAInventoryError(
                f"Inventory components do not sum to total in {year}: "
                f"{components:.0f} vs {total:.0f}"
            )

    return pd.DataFrame(records)


def _allocate(total: float, members: pd.DataFrame) -> dict[str, float]:
    if members.empty or total == 0:
        return {}
    weights = members["GO"].clip(lower=0).to_numpy(dtype=float)
    if not np.isfinite(weights).all() or weights.sum() <= 0:
        weights = np.ones(len(members), dtype=float)
    shares = weights / weights.sum()
    return {
        str(code): float(total * share)
        for code, share in zip(members["industry_code"], shares, strict=False)
    }


def allocate_inventory_stock(panel: pd.DataFrame, totals: pd.DataFrame) -> pd.DataFrame:
    """Allocate broad inventory totals to IO industries.

    ``panel`` must contain ``year``, ``industry_code``, ``GO`` and be one row per
    industry-year. Returns ``year, industry_code, M_inv, inventory_category`` in
    millions of current dollars.
    """
    required = {"year", "industry_code", "GO"}
    missing = required.difference(panel.columns)
    if missing:
        raise BEAInventoryError(f"Panel missing columns: {sorted(missing)}")

    market = panel.loc[~panel["industry_code"].astype(str).isin(NON_MARKET_CODES)].copy()
    assigned = set(DIRECT_CODES.get("Farm", []))
    for codes in DIRECT_CODES.values():
        assigned.update(codes)
    for codes in GROUP_CODES.values():
        assigned.update(codes)
    other_codes = sorted(set(market["industry_code"].astype(str)) - assigned)
    if not other_codes:
        raise BEAInventoryError("No industries left for the 'Other industries' category")

    records = []
    for year, group in market.groupby("year", sort=True):
        year_totals = totals.loc[totals["year"] == year].set_index("category")["value"]
        if year_totals.empty:
            continue

        for category, codes in DIRECT_CODES.items():
            total = float(year_totals.get(category, 0.0))
            members = group.loc[group["industry_code"].astype(str).isin(codes)]
            for code in members["industry_code"].astype(str):
                records.append(
                    {
                        "year": int(year),
                        "industry_code": code,
                        "M_inv": total,
                        "inventory_category": category,
                    }
                )

        for category, codes in GROUP_CODES.items():
            total = float(year_totals.get(category, 0.0))
            members = group.loc[group["industry_code"].astype(str).isin(codes)]
            allocation = _allocate(total, members)
            for code, value in allocation.items():
                records.append(
                    {
                        "year": int(year),
                        "industry_code": code,
                        "M_inv": value,
                        "inventory_category": category,
                    }
                )

        total = float(year_totals.get(OTHER_CATEGORY, 0.0))
        members = group.loc[group["industry_code"].astype(str).isin(other_codes)]
        allocation = _allocate(total, members)
        for code, value in allocation.items():
            records.append(
                {
                    "year": int(year),
                    "industry_code": code,
                    "M_inv": value,
                    "inventory_category": OTHER_CATEGORY,
                }
            )

    if not records:
        raise BEAInventoryError("Inventory allocation produced no rows")

    allocated = pd.DataFrame(records)
    return (
        allocated.groupby(["year", "industry_code"], as_index=False)
        .agg(M_inv=("M_inv", "sum"), inventory_category=("inventory_category", "first"))
        .sort_values(["year", "industry_code"])
    )


def load_industry_inventories(
    raw_dir: Path,
    panel: pd.DataFrame,
    *,
    max_age_days: int = 365,
    force: bool = False,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Download, parse and allocate industry inventory stocks."""
    path = download_section5(raw_dir, max_age_days=max_age_days, force=force)
    totals = parse_inventory_stocks(path, years=years)
    return allocate_inventory_stock(panel, totals)
