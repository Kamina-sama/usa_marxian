"""Build a fixed-capital matrix from BEA fixed-asset detail.

For each year this module produces:

    B[g, j]      real capital stock of capital good g used by industry j,
                 divided by industry j's real output
    Delta[g, j]  depreciation rate of that capital stock

The BEA detail workbooks give asset-by-industry stocks and depreciation. Asset
codes are mapped to IO capital-good industries in ``config/capital_assets.yaml``.
"""

from __future__ import annotations

import openpyxl
import pandas as pd
import yaml

from ..config import PROJECT_ROOT
from .bea_assets import download_detail, load_capital_config

CAPITAL_ASSET_CONFIG = PROJECT_ROOT / "config" / "capital_assets.yaml"


class CapitalMatrixError(RuntimeError):
    """Raised when the capital matrix cannot be built."""


def load_asset_config(path=CAPITAL_ASSET_CONFIG) -> dict[str, str]:
    with open(path, encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    groups = config.get("asset_groups", {})
    mapping = {}
    for industry_code, assets in groups.items():
        for asset in assets:
            mapping[str(asset)] = str(industry_code)
    if not mapping:
        raise CapitalMatrixError("No asset-to-industry mapping found")
    return mapping


def parse_asset_detail(
    path,
    *,
    value_name: str,
    years: range = range(1997, 2026),
) -> pd.DataFrame:
    """Parse detailed asset rows for every industry sheet."""
    wanted = set(years)
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    records = []
    try:
        for sheet_name in workbook.sheetnames:
            if sheet_name in {"readme", "Datasets"}:
                continue
            sheet = workbook[sheet_name]
            rows = list(sheet.iter_rows(min_row=1, max_row=100, values_only=True))
            if len(rows) < 90:
                continue
            title = str(rows[0][0] or "")
            if " - " in title:
                fa_code = title.split(" - ", 1)[0].strip()
            else:
                fa_code = str(sheet_name).strip()

            header = rows[5]
            year_columns = {}
            for index, value in enumerate(header):
                if isinstance(value, (int, float)):
                    year_columns[int(value)] = index
                elif isinstance(value, str) and value.strip().isdigit():
                    year_columns[int(value.strip())] = index
            for row in rows[7:]:
                if not row or row[0] is None or row[1] is None:
                    continue
                asset_code = str(row[0]).strip()
                if asset_code in {"EQUIPMENT", "STRUCTURES", "IPP"}:
                    continue
                asset_name = " ".join(str(row[1]).split())
                for year, index in year_columns.items():
                    if year not in wanted or index >= len(row):
                        continue
                    value = row[index]
                    if value is None:
                        continue
                    try:
                        numeric = float(str(value).replace(",", ""))
                    except ValueError:
                        continue
                    records.append(
                        {
                            "year": int(year),
                            "fa_code": fa_code,
                            "asset_code": asset_code,
                            "asset_name": asset_name,
                            value_name: numeric,
                        }
                    )
    finally:
        workbook.close()
    if not records:
        raise CapitalMatrixError(f"No detailed asset rows parsed from {path}")
    return pd.DataFrame(records)


def _load_three(raw_dir, force: bool):
    current = parse_asset_detail(
        download_detail(raw_dir, kind="stock_current", force=force),
        value_name="K_current",
    )
    real = parse_asset_detail(
        download_detail(raw_dir, kind="stock_real", force=force),
        value_name="K_real",
    )
    depreciation = parse_asset_detail(
        download_detail(raw_dir, kind="depreciation", force=force),
        value_name="D_current",
    )
    frame = current.merge(
        real, on=["year", "fa_code", "asset_code"], how="outer"
    ).merge(
        depreciation,
        on=["year", "fa_code", "asset_code"],
        how="outer",
    )
    return frame


def build_capital_matrices(
    panel: pd.DataFrame,
    raw_dir,
    *,
    force: bool = False,
) -> dict[int, tuple[pd.DataFrame, pd.DataFrame]]:
    """Return ``{year: (B, Delta)}`` aligned to the panel industries."""
    asset_map = load_asset_config()
    industry_map = load_capital_config()["fa_to_io"]
    detail = _load_three(raw_dir, force)
    detail["industry_code"] = detail["fa_code"].map(industry_map)
    detail["capital_good"] = detail["asset_code"].map(asset_map)
    detail = detail.dropna(subset=["industry_code", "capital_good"])

    grouped = (
        detail.groupby(["year", "industry_code", "capital_good"], as_index=False)
        .agg(K_real=("K_real", "sum"), K_current=("K_current", "sum"), D=("D_current", "sum"))
    )
    grouped["delta"] = (
        grouped["D"] / grouped["K_current"].where(grouped["K_current"] > 0, 1.0)
    ).clip(0.0, 1.0)

    codes = sorted(
        panel.loc[~panel["industry_code"].isin(
            {"HS", "GFGD", "GFGN", "GFE", "GSLG", "GSLE"}
        ), "industry_code"].astype(str).unique()
    )
    matrices: dict[int, tuple[pd.DataFrame, pd.DataFrame]] = {}
    for year, group in grouped.groupby("year"):
        year_panel = panel.loc[panel["year"] == year].set_index("industry_code")
        if year_panel.empty or "quantity" not in year_panel.columns:
            continue
        q = year_panel["quantity"].reindex(codes)
        if q.isna().any() or (q <= 0).any():
            continue
        B = (
            group.pivot_table(
                index="capital_good",
                columns="industry_code",
                values="K_real",
                aggfunc="sum",
            )
            .reindex(columns=codes)
            .fillna(0.0)
        )
        B = B.div(q, axis=1)
        Delta = (
            group.pivot_table(
                index="capital_good",
                columns="industry_code",
                values="delta",
                aggfunc="mean",
            )
            .reindex(index=B.index, columns=codes)
            .fillna(0.0)
        )
        matrices[int(year)] = (B, Delta)
    if not matrices:
        raise CapitalMatrixError("No capital matrices could be built")
    return matrices
