"""BEA access.

The primary path downloads BEA's annual NIPA flat file:

    https://apps.bea.gov/national/Release/TXT/NipaDataA.txt

It is keyless and contains every annual NIPA series, keyed by BEA series code
(for example ``A001RC`` = GDP). An optional ``beaapi`` path is provided for
users who need quarterly data or arbitrary tables.
"""

from __future__ import annotations

import io

import pandas as pd
import requests

NIPA_ANNUAL_URL = "https://apps.bea.gov/national/Release/TXT/NipaDataA.txt"
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}


class BEAError(RuntimeError):
    """Raised when BEA returns an unexpected payload."""


def fetch_nipa_flat(url: str = NIPA_ANNUAL_URL, *, timeout: float = 60.0) -> pd.DataFrame:
    """Download and parse the annual NIPA flat file.

    Returns a long frame with columns ``series_code``, ``year`` and ``value``.
    """
    response = requests.get(url, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    text = response.text
    if not text.lstrip().startswith("%SeriesCode"):
        raise BEAError("Unexpected BEA flat-file header")

    frame = pd.read_csv(io.StringIO(text), dtype=str)
    frame.columns = [column.lstrip("%").strip().lower() for column in frame.columns]
    frame = frame.rename(columns={"seriescode": "series_code"})
    frame["year"] = pd.to_numeric(frame["period"], errors="coerce").astype("Int64")
    frame["value"] = pd.to_numeric(
        frame["value"].str.replace(",", "", regex=False), errors="coerce"
    )
    return frame.dropna(subset=["year"]).loc[:, ["series_code", "year", "value"]]


def fetch_nipa_series(
    series_code: str,
    *,
    url: str = NIPA_ANNUAL_URL,
    timeout: float = 60.0,
) -> pd.DataFrame:
    """Return one annual NIPA series as ``DataFrame[date, value]``."""
    frame = fetch_nipa_flat(url=url, timeout=timeout)
    subset = frame.loc[frame["series_code"] == series_code, ["year", "value"]].copy()
    if subset.empty:
        raise BEAError(f"NIPA series code not found: {series_code}")
    subset["date"] = pd.to_datetime(subset["year"].astype(int).astype(str) + "-01-01")
    return subset.loc[:, ["date", "value"]].sort_values("date").reset_index(drop=True)


def fetch_table_api(table_name: str, api_key: str, *, frequency: str = "A") -> pd.DataFrame:
    """Optional BEA API access for arbitrary tables."""
    response = requests.get(
        "https://apps.bea.gov/api/data/",
        params={
            "UserID": api_key,
            "method": "GetData",
            "datasetname": "NIPA",
            "TableName": table_name,
            "Frequency": frequency,
            "Year": "ALL",
            "ResultFormat": "JSON",
        },
        headers=DEFAULT_HEADERS,
        timeout=60,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get("BEAAPI", {}).get("Results", {}).get("Data", [])
    if not data:
        raise BEAError(f"No BEA data returned for table {table_name}")
    return pd.DataFrame(data)
