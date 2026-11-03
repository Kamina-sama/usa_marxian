"""BEA input-output tables: download, extract and parse.

The industry accounts are built from BEA's summary-level Use table
(producer prices, after redefinitions), which is published keyless inside a
single archive:

    https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip

Each annual sheet contains, for 71 industries:

    C_i    total intermediate consumption
    V_i    compensation of employees
    T_i    taxes on production and imports, less subsidies
    GOS_i  gross operating surplus
    N_i    total value added
    GO_i   total industry output

The identity ``C_i + N_i = GO_i`` holds by construction (up to rounding).
"""

from __future__ import annotations

import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
import requests

IO_ARCHIVE_URL = "https://apps.bea.gov/industry/iTables%20Static%20Files/AllTablesIO.zip"
USE_MEMBER = "IOUse_After_Redefinitions_PRO_1997-2023_Summary.xlsx"
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}


class BEAIOError(RuntimeError):
    """Raised when the IO archive or sheet cannot be parsed."""


def _num(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in {"", "...", ".....", "n/a", "N/A", "—", "-"}:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def download_archive(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
    timeout: float = 120.0,
) -> Path:
    """Download the BEA IO archive into ``raw_dir/bea`` and return its path."""
    path = raw_dir / "bea" / "AllTablesIO.zip"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not force:
        age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
        if age_days < max_age_days:
            return path

    response = requests.get(IO_ARCHIVE_URL, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    if not response.content.startswith(b"PK"):
        raise BEAIOError("BEA IO download did not return a zip archive")
    tmp = path.with_suffix(".zip.tmp")
    tmp.write_bytes(response.content)
    tmp.replace(path)

    metadata = {
        "source_url": IO_ARCHIVE_URL,
        "member": USE_MEMBER,
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": int(path.stat().st_size),
    }
    (path.parent / "AllTablesIO.json").write_text(
        json.dumps(metadata, indent=2), encoding="utf-8"
    )
    return path


def extract_use_table(zip_path: Path, *, force: bool = False) -> Path:
    """Extract the summary Use workbook next to the archive."""
    destination = zip_path.parent / USE_MEMBER
    if destination.exists() and not force:
        if destination.stat().st_mtime >= zip_path.stat().st_mtime:
            return destination

    with zipfile.ZipFile(zip_path) as archive:
        try:
            archive.extract(USE_MEMBER, path=zip_path.parent)
        except KeyError as exc:
            raise BEAIOError(f"Member not found in archive: {USE_MEMBER}") from exc
    return destination


def parse_use_sheet(rows: list[tuple], year: int) -> pd.DataFrame:
    """Parse one Use sheet.

    ``rows`` must start at the header row (the sheet's row 6). The parser finds
    the 71 industry columns before the final-demand block and the named value
    added rows.
    """
    if len(rows) < 8:
        raise BEAIOError("Use sheet is too short to parse")

    codes, names = rows[0], rows[1]
    industry_columns = []
    for index in range(2, len(codes)):
        code = codes[index]
        if isinstance(code, str) and code.startswith("F") and len(code) > 2:
            break
        if code and index < len(names):
            industry_columns.append(index)

    if not industry_columns:
        raise BEAIOError("No industry columns found")

    by_name = {
        str(row[1]).strip(): row
        for row in rows[2:]
        if row and len(row) > 1 and row[1] is not None
    }
    required = {
        "Total Intermediate",
        "Compensation of employees",
        "Taxes on production and imports, less subsidies",
        "Gross operating surplus",
        "Total Value Added",
        "Total Industry Output",
    }
    missing = required.difference(by_name)
    if missing:
        raise BEAIOError(f"Missing Use-table rows: {sorted(missing)}")

    records = []
    for index in industry_columns:
        records.append(
            {
                "year": int(year),
                "industry_code": str(codes[index]).strip(),
                "industry_name": str(names[index]).strip(),
                "C": _num(by_name["Total Intermediate"][index]),
                "V": _num(by_name["Compensation of employees"][index]),
                "T": _num(by_name["Taxes on production and imports, less subsidies"][index]),
                "GOS": _num(by_name["Gross operating surplus"][index]),
                "N": _num(by_name["Total Value Added"][index]),
                "GO": _num(by_name["Total Industry Output"][index]),
            }
        )
    return pd.DataFrame(records)


def build_industry_panel(
    raw_dir: Path,
    *,
    max_age_days: int = 365,
    force: bool = False,
) -> pd.DataFrame:
    """Download, parse and concatenate all annual Use tables."""
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
            frames.append(parse_use_sheet(rows, int(sheet_name)))
    finally:
        workbook.close()

    if not frames:
        raise BEAIOError("No annual sheets found in the Use workbook")

    panel = pd.concat(frames, ignore_index=True)
    panel["S"] = panel["T"] + panel["GOS"]
    panel["K"] = panel["C"] + panel["V"]
    panel["residual"] = panel["GO"] - (panel["C"] + panel["N"])
    panel = panel.sort_values(["year", "industry_code"]).reset_index(drop=True)
    return panel
