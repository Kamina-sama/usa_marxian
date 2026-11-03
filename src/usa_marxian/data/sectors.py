"""Sector price indexes and industry capital consumption.

Two BEA/FRED sources are used:

* FRED series from the GDP-by-Industry release provide broad-sector value-added
  and gross-output price indexes (2017=100). These are used to deflate industry
  accounts instead of applying the single GDP deflator to every industry.
* BEA NIPA Section 6 tables 6.13D and 6.22D provide noncorporate and corporate
  capital consumption allowances by industry. They are used to convert gross
  operating surplus into net surplus-value.

The NIPA CFC tables are coarser than the 71 IO industries, so CFC is allocated
within each broad group in proportion to gross operating surplus. The allocation
is explicit and reversible; it is not a claim of precise industry measurement.
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

from ..config import PROJECT_ROOT, SeriesSpec
from .build import annualize
from .cache import load_raw_series

SECTOR_CONFIG_PATH = PROJECT_ROOT / "config" / "sectors.yaml"
SECTION6_URL = "https://apps.bea.gov/national/Release/XLS/Survey/Section6All_xls.xlsx"
SECTION6_FILENAME = "Section6All_xls.xlsx"
SECTION6_CFC_SHEETS = {"corporate": "T62200D-A", "noncorporate": "T61300D-A"}
TOTAL_CFC_SERIES = "COFC"
GOVERNMENT_CODES = ["GFGD", "GFGN", "GFE", "GSLG", "GSLE"]
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.2 (research project)"}


def load_sector_config(path: str | Path = SECTOR_CONFIG_PATH) -> dict:
    with Path(path).open(encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def _annual_index(frame: pd.DataFrame, spec: SeriesSpec) -> pd.Series:
    return annualize(frame, spec)


def fetch_sector_prices(
    config: dict,
    raw_dir: Path,
    *,
    max_age_days: int = 30,
    force: bool = False,
) -> pd.DataFrame:
    """Fetch broad-sector value-added and gross-output price indexes."""
    records = []
    for sector, spec in config.get("deflators", {}).items():
        for kind in ("va_price", "go_price"):
            series_id = spec[kind]
            series_spec = SeriesSpec(
                label=f"{spec['label']} - {kind}",
                provider="fred",
                series_id=series_id,
                units="index_2017_100",
                frequency="quarterly",
                agg="mean",
                scale=1.0,
            )
            frame = load_raw_series(
                series_spec,
                raw_dir,
                max_age_days=max_age_days,
                force=force,
            )
            annual = _annual_index(frame, series_spec)
            annual.name = f"{sector}|{kind}"
            records.append(annual)

    prices = pd.concat(records, axis=1).sort_index()
    prices.index.name = "year"

    long = prices.reset_index().melt(id_vars="year", var_name="key", value_name="value")
    long[["sector", "kind"]] = long["key"].str.split("|", n=1, expand=True)
    wide = long.pivot_table(
        index=["year", "sector"], columns="kind", values="value", aggfunc="first"
    ).reset_index()
    return wide.loc[:, ["year", "sector", "va_price", "go_price"]]


def merge_sector_prices(panel: pd.DataFrame, prices: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Attach sector, va_price and go_price to the industry panel."""
    code_to_sector = {}
    for sector, spec in config.get("deflators", {}).items():
        for code in spec["industries"]:
            code_to_sector[str(code)] = sector

    out = panel.copy()
    out["sector"] = out["industry_code"].astype(str).map(code_to_sector)
    out = out.merge(prices, on=["year", "sector"], how="left", validate="many_to_one")
    return out


def fetch_total_cfc(
    raw_dir: Path,
    *,
    max_age_days: int = 30,
    force: bool = False,
) -> pd.Series:
    """Total-economy consumption of fixed capital, in millions of dollars."""
    spec = SeriesSpec(
        label="Consumption of fixed capital",
        provider="fred",
        series_id=TOTAL_CFC_SERIES,
        units="billions_usd",
        frequency="quarterly",
        agg="mean",
        scale=1.0,
    )
    frame = load_raw_series(spec, raw_dir, max_age_days=max_age_days, force=force)
    annual = annualize(frame, spec)
    return annual * 1000.0


def download_section6(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    timeout: float = 90.0,
) -> Path:
    path = raw_dir / "bea" / SECTION6_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return path

    response = requests.get(SECTION6_URL, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise RuntimeError("BEA Section 6 download did not return an xlsx file")
    tmp = path.with_suffix(".xlsx.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)

    metadata = {
        "source_url": SECTION6_URL,
        "sheets": list(SECTION6_CFC_SHEETS.values()),
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": int(path.stat().st_size),
    }
    (path.parent / "Section6All_xls.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return path


def parse_section6_cfc(path: Path) -> pd.DataFrame:
    """Parse corporate and noncorporate CFC tables into a long frame."""
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records = []
    try:
        for kind, sheet_name in SECTION6_CFC_SHEETS.items():
            if sheet_name not in workbook.sheetnames:
                continue
            sheet = workbook[sheet_name]
            rows = list(sheet.iter_rows(min_row=8, values_only=True))
            if not rows:
                continue

            header = rows[0]
            year_columns = {}
            for index, value in enumerate(header):
                if isinstance(value, (int, float)) and 1900 < int(value) < 2100:
                    year_columns[index] = int(value)
                elif isinstance(value, str) and value.strip().isdigit():
                    candidate = int(value.strip())
                    if 1900 < candidate < 2100:
                        year_columns[index] = candidate

            for row in rows[1:]:
                if len(row) < 2 or row[1] is None:
                    continue
                label = str(row[1]).strip()
                if not label or label.startswith("Note"):
                    continue
                for index, year in year_columns.items():
                    if index >= len(row):
                        continue
                    raw_value = row[index]
                    if raw_value is None:
                        continue
                    if isinstance(raw_value, str):
                        text = raw_value.strip().replace(",", "")
                        if text in {"", "...", ".....", "n/a", "N/A", "—", "-"}:
                            continue
                        try:
                            value = float(text)
                        except ValueError:
                            continue
                    else:
                        value = float(raw_value)

                    records.append(
                        {
                            "year": year,
                            "kind": kind,
                            "label": label,
                            "value": value,
                        }
                    )
    finally:
        workbook.close()

    frame = pd.DataFrame(records)
    if frame.empty:
        raise RuntimeError("No CFC observations parsed from Section 6")
    return frame


def allocate_cfc(
    panel: pd.DataFrame,
    cfc: pd.DataFrame,
    config: dict,
) -> pd.DataFrame:
    """Allocate sector-level CFC to IO industries in proportion to GOS."""
    lookup = {
        (int(row.year), str(row.kind), str(row.label)): float(row.value)
        for row in cfc.itertuples(index=False)
    }
    groups = config.get("cfc_groups", {})

    out = panel.copy()
    # NaN means "no CFC observation for this year", which lets the model drop
    # 1997 from the net sample rather than silently treating it as zero CFC.
    out["CFC"] = np.nan
    out["cfc_group"] = None

    for year, group_frame in out.groupby("year", sort=False):
        for group_name, spec in groups.items():
            total = 0.0
            for kind in ("corporate", "noncorporate"):
                for label in spec.get(kind, []):
                    total += lookup.get((int(year), kind, label), 0.0)
            if total == 0:
                continue

            codes = [str(code) for code in spec["industries"]]
            mask = group_frame["industry_code"].astype(str).isin(codes)
            if not mask.any():
                continue

            subset = group_frame.loc[mask]
            weights = subset["GOS"].clip(lower=0.0).to_numpy(dtype=float)
            if weights.sum() <= 0:
                weights = subset["GO"].clip(lower=0.0).to_numpy(dtype=float)
            if weights.sum() <= 0:
                weights = np.ones(len(subset), dtype=float)

            allocation = total * weights / weights.sum()
            out.loc[subset.index, "CFC"] = allocation
            out.loc[subset.index, "cfc_group"] = group_name

    return out


def attach_sector_data(
    panel: pd.DataFrame,
    *,
    raw_dir: Path,
    config: dict | None = None,
    max_age_days: int = 30,
    force: bool = False,
) -> pd.DataFrame:
    """Merge price indexes and allocate CFC in one step."""
    config = config or load_sector_config()
    prices = fetch_sector_prices(
        config, raw_dir, max_age_days=max_age_days, force=force
    )
    enriched = merge_sector_prices(panel, prices, config)

    section6 = download_section6(raw_dir, force=force)
    cfc = parse_section6_cfc(section6)
    enriched = allocate_cfc(enriched, cfc, config)

    # The Section 6 tables cover private capital consumption only. The
    # remaining total-economy CFC belongs mostly to government fixed capital;
    # allocate it to government industries so that the industry net accounts
    # reconcile to NDP rather than to GDP minus private CFC.
    total_cfc = fetch_total_cfc(raw_dir, max_age_days=max_age_days, force=force)
    private_cfc = enriched.groupby("year")["CFC"].sum(min_count=1)
    government_cfc = (total_cfc - private_cfc).clip(lower=0.0)

    for year, value in government_cfc.dropna().items():
        mask = (enriched["year"] == int(year)) & enriched["industry_code"].astype(str).isin(
            GOVERNMENT_CODES
        )
        if not mask.any() or value <= 0:
            continue
        weights = enriched.loc[mask, "N"].clip(lower=0.0).to_numpy(dtype=float)
        if weights.sum() <= 0:
            weights = enriched.loc[mask, "GO"].clip(lower=0.0).to_numpy(dtype=float)
        if weights.sum() <= 0:
            weights = np.ones(mask.sum(), dtype=float)
        allocation = float(value) * weights / weights.sum()
        enriched.loc[mask, "CFC"] = enriched.loc[mask, "CFC"].fillna(0.0) + allocation

    return enriched
