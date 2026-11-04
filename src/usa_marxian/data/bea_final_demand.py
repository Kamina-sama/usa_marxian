"""Final-demand columns from the BEA Use table.

The summary Use sheet has, after the 71 industry columns, a block of final-use
columns: personal consumption, private investment, inventory change, exports,
imports and government. This module parses those columns and turns them into
real 2017-dollar demand components by industry and year.

The square model assumes each commodity is produced by the same-code industry,
so commodity demand maps directly to industry demand.
"""

from __future__ import annotations

import openpyxl
import pandas as pd

from .bea_io import BEAIOError, _num, download_archive, extract_use_table


def parse_final_demand_sheet(rows: list[tuple], year: int) -> pd.DataFrame:
    """Parse the final-demand block of one Use sheet.

    Returns ``year, commodity_code, final_code, final_name, value`` in millions
    of current dollars.
    """
    if len(rows) < 10:
        raise BEAIOError("Use sheet is too short to parse final demand")

    codes, names = rows[0], rows[1]
    final_columns = [
        index
        for index in range(2, len(codes))
        if isinstance(codes[index], str)
        and codes[index].startswith("F")
        and len(codes[index]) > 2
    ]
    if not final_columns:
        raise BEAIOError("No final-demand columns found")

    records = []
    for row in rows[2:]:
        if not row:
            continue
        code = row[0]
        if code is None:
            break
        if not isinstance(code, str) or not code.strip():
            continue
        commodity_code = code.strip()
        for index in final_columns:
            records.append(
                {
                    "year": int(year),
                    "commodity_code": commodity_code,
                    "final_code": str(codes[index]).strip(),
                    "final_name": str(names[index]).strip()
                    if index < len(names)
                    else "",
                    "value": _num(row[index]),
                }
            )
    return pd.DataFrame(records)


def load_final_demand(
    raw_dir, *, max_age_days: int = 365, force: bool = False
) -> pd.DataFrame:
    """Download and parse final-demand columns for all annual sheets."""
    zip_path = download_archive(raw_dir, max_age_days=max_age_days, force=force)
    workbook_path = extract_use_table(zip_path, force=force)

    workbook = openpyxl.load_workbook(workbook_path, read_only=True, data_only=True)
    frames = []
    try:
        for sheet_name in workbook.sheetnames:
            if not sheet_name.isdigit():
                continue
            sheet = workbook[sheet_name]
            rows = list(sheet.iter_rows(min_row=6, values_only=True))
            frames.append(parse_final_demand_sheet(rows, int(sheet_name)))
    finally:
        workbook.close()

    if not frames:
        raise BEAIOError("No final-demand data parsed")
    return pd.concat(frames, ignore_index=True)


def categorise_final_demand(frame: pd.DataFrame) -> pd.DataFrame:
    """Map BEA final-demand columns to C, I, G, X and M."""
    data = frame.copy()
    name = data["final_name"].str.lower()

    def category(row_name: str) -> str | None:
        if "personal consumption" in row_name:
            return "C"
        if "private fixed investment" in row_name or "private inventories" in row_name:
            return "I"
        if "exports" in row_name:
            return "X"
        if "imports" in row_name:
            return "M"
        if "federal" in row_name or "state and local" in row_name:
            return "G"
        return None

    data["category"] = name.map(category)
    data = data.dropna(subset=["category"])
    data.loc[data["category"] == "M", "value"] = data.loc[
        data["category"] == "M", "value"
    ].abs()
    return (
        data.groupby(["year", "commodity_code", "category"], as_index=False)
        .agg(value=("value", "sum"))
        .pivot(index=["year", "commodity_code"], columns="category", values="value")
        .fillna(0.0)
        .reset_index()
    )


def attach_final_demand(state: pd.DataFrame, demand: pd.DataFrame) -> pd.DataFrame:
    """Attach real final-demand components to the state table."""
    out = state.copy()
    if "go_price" not in out.columns:
        raise KeyError("State table has no go_price column")

    data = demand.rename(
        columns={
            "commodity_code": "industry_code",
            "C": "consumption",
            "I": "investment_demand",
            "G": "government",
            "X": "exports",
            "M": "imports",
        }
    )
    out = out.merge(
        data,
        on=["year", "industry_code"],
        how="left",
        validate="many_to_one",
    )
    for source, target in (
        ("consumption", "consumption_demand"),
        ("government", "government_demand"),
        ("exports", "exports_demand"),
        ("imports", "imports_demand"),
    ):
        if source not in out.columns:
            out[source] = 0.0
        out[target] = out[source].fillna(0.0) / (out["go_price"] / 100.0)
    return out
