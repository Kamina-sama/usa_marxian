"""BEA GDP-by-Industry price indexes at the 71-industry level.

The BEA API dataset ``GDPbyIndustry`` provides chain-type price indexes for
gross output, value added and intermediate inputs. These are the correct
industry-level deflators; the FRED GOPI/VAPI series we used earlier are only
broad sectors.

Table IDs:
    18 - gross output price index
    11 - value added price index
    23 - intermediate inputs price index
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import requests

BEA_API_URL = "https://apps.bea.gov/api/data/"
PRICE_TABLES = {
    "go_price": "18",
    "va_price": "11",
    "input_price": "23",
}
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}


class BEAIndustryPriceError(RuntimeError):
    """Raised when the GDP-by-Industry price tables cannot be fetched."""


def _num(value) -> float:
    if value is None:
        return float("nan")
    if isinstance(value, (int, float, np.integer, np.floating)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if text in {"", "...", ".....", "n/a", "N/A", "—", "-"}:
        return float("nan")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def fetch_price_table(
    table_id: str,
    api_key: str,
    *,
    frequency: str = "A",
    year: str = "ALL",
    industry: str = "ALL",
    timeout: float = 120.0,
) -> pd.DataFrame:
    """Fetch one GDP-by-Industry table as ``year, industry_code, value``."""
    response = requests.get(
        BEA_API_URL,
        params={
            "UserID": api_key,
            "method": "GetData",
            "datasetname": "GDPbyIndustry",
            "TableID": table_id,
            "Frequency": frequency,
            "Industry": industry,
            "Year": year,
            "ResultFormat": "JSON",
        },
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json().get("BEAAPI", {})
    if "Error" in payload:
        raise BEAIndustryPriceError(str(payload["Error"]))
    results = payload.get("Results", [])
    if not results:
        raise BEAIndustryPriceError(f"No Results for TableID {table_id}")

    rows = results[0].get("Data", []) if isinstance(results, list) else results.get("Data", [])
    if not rows:
        raise BEAIndustryPriceError(f"No Data for TableID {table_id}")

    records = []
    for row in rows:
        year_value = row.get("Year")
        if year_value is None or not str(year_value).isdigit():
            continue
        records.append(
            {
                "year": int(year_value),
                "industry_code": str(row.get("Industry", "")).strip(),
                "value": _num(row.get("DataValue")),
            }
        )
    frame = pd.DataFrame(records)
    if frame.empty:
        raise BEAIndustryPriceError(f"Empty parsed table for TableID {table_id}")
    return frame


def load_industry_prices(
    raw_dir: Path,
    api_key: str,
    *,
    force: bool = False,
    max_age_days: int = 365,
) -> pd.DataFrame:
    """Fetch and cache gross-output, value-added and intermediate-input indexes."""
    base = raw_dir / "bea"
    base.mkdir(parents=True, exist_ok=True)
    frames = []
    for column, table_id in PRICE_TABLES.items():
        path = base / f"gdpbyindustry_{table_id}.csv"
        if path.exists() and not force:
            age_days = (datetime.now().timestamp() - path.stat().st_mtime) / 86_400
            if age_days < max_age_days:
                frame = pd.read_csv(path)
            else:
                frame = fetch_price_table(table_id, api_key)
                frame.to_csv(path, index=False)
        else:
            frame = fetch_price_table(table_id, api_key)
            frame.to_csv(path, index=False)
            metadata = {
                "source_url": BEA_API_URL,
                "dataset": "GDPbyIndustry",
                "table_id": table_id,
                "downloaded_at_utc": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "rows": int(frame.shape[0]),
            }
            (base / f"gdpbyindustry_{table_id}.json").write_text(
                json.dumps(metadata, indent=2), encoding="utf-8"
            )
        frames.append(frame.rename(columns={"value": column}))

    combined = frames[0]
    for frame in frames[1:]:
        combined = combined.merge(
            frame, on=["year", "industry_code"], how="outer"
        )
    return combined.sort_values(["year", "industry_code"]).reset_index(drop=True)


def attach_industry_prices(
    panel: pd.DataFrame,
    prices: pd.DataFrame,
) -> pd.DataFrame:
    """Replace broad-sector prices with 71-industry BEA price indexes."""
    out = panel.copy()
    out = out.merge(
        prices,
        on=["year", "industry_code"],
        how="left",
        suffixes=("", "_bea"),
        validate="many_to_one",
    )

    for column in ("go_price", "va_price", "input_price"):
        bea_column = f"{column}_bea"
        if bea_column not in out.columns:
            continue
        out[column] = out[bea_column].where(out[bea_column].notna(), out[column])
        out = out.drop(columns=[bea_column])

    out["price_source"] = "bea_gdpbyindustry"
    missing = out[["go_price", "va_price", "input_price"]].isna().any(axis=1)
    out.loc[missing, "price_source"] = "sector_fallback"

    def real(value: pd.Series, deflator: pd.Series) -> pd.Series:
        return value * 1e6 / (deflator / 100.0)

    out["C_real"] = real(out["C"], out["input_price"])
    out["V_real"] = real(out["V"], out["va_price"])
    out["N_real"] = real(out["N"], out["va_price"])
    out["GO_real"] = real(out["GO"], out["go_price"])
    out["S_real"] = out["N_real"] - out["V_real"]
    out["K_real"] = out["C_real"] + out["V_real"]
    return out
