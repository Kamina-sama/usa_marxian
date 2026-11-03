"""FRED access.

The primary path uses FRED's keyless CSV endpoint, which returns the same
observations as the official API for a single series:

    https://fred.stlouisfed.org/graph/fredgraph.csv?id=GDPA

An API-key path is available for users who need metadata, vintages or bulk
downloads, but it is not required by the default pipeline.
"""

from __future__ import annotations

import io
from typing import Any

import pandas as pd
import requests

FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
FRED_API_URL = "https://api.stlouisfed.org/fred/series/observations"
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}


class FredError(RuntimeError):
    """Raised when FRED returns an error or an unexpected payload."""


def _parse_csv(text: str) -> pd.DataFrame:
    if not text or text.lstrip().startswith("<"):
        raise FredError("FRED returned HTML/empty content instead of CSV")
    frame = pd.read_csv(io.StringIO(text))
    if frame.shape[1] < 2:
        raise FredError(f"Unexpected FRED CSV shape: {frame.shape}")
    frame = frame.iloc[:, :2].copy()
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    # FRED encodes missing observations as "." in the CSV endpoint.
    frame["value"] = pd.to_numeric(frame["value"].replace(".", pd.NA), errors="coerce")
    frame = frame.dropna(subset=["date"]).drop_duplicates(subset=["date"])
    return frame.sort_values("date").reset_index(drop=True)


def fetch_series(
    series_id: str,
    *,
    timeout: float = 30.0,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Download one series from the keyless FRED CSV endpoint.

    Returns a frame with columns ``date`` and ``value``.
    """
    client = session or requests
    response = client.get(
        FRED_CSV_URL,
        params={"id": series_id},
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    if response.status_code == 404:
        raise FredError(f"FRED series not found: {series_id}")
    response.raise_for_status()
    return _parse_csv(response.text)


def fetch_series_api(series_id: str, api_key: str) -> pd.DataFrame:
    """Download one series through the official FRED API (optional)."""
    response = requests.get(
        FRED_API_URL,
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "observation_start": "1900-01-01",
        },
        headers=DEFAULT_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    payload: dict[str, Any] = response.json()
    observations = payload.get("observations", [])
    frame = pd.DataFrame(observations)
    if frame.empty:
        raise FredError(f"No observations returned for {series_id}")
    frame = frame[["date", "value"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["value"] = pd.to_numeric(frame["value"].replace(".", pd.NA), errors="coerce")
    return frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)


def series_metadata(series_id: str, api_key: str) -> dict[str, Any]:
    """Fetch series metadata. Requires a FRED API key."""
    response = requests.get(
        "https://api.stlouisfed.org/fred/series",
        params={"series_id": series_id, "api_key": api_key, "file_type": "json"},
        headers=DEFAULT_HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    return response.json().get("seriess", [{}])[0]
