"""BLS public API access (v1 keyless, v2 with key)."""

from __future__ import annotations

import pandas as pd
import requests

BLS_V1_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
BLS_V2_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
DEFAULT_HEADERS = {"Content-Type": "application/json", "User-Agent": "usa-marxian/0.1"}


class BLSError(RuntimeError):
    """Raised when the BLS API returns a failure status."""


def fetch_series(
    series_ids: list[str],
    *,
    start_year: int,
    end_year: int,
    api_key: str | None = None,
    timeout: float = 30.0,
) -> dict[str, pd.DataFrame]:
    """Fetch one or more BLS series.

    Returns ``{series_id: DataFrame[date, value]}``. Monthly observations are
    returned as-is; annual averages (period ``M13``) are included when the API
    provides them.
    """
    url = BLS_V2_URL if api_key else BLS_V1_URL
    payload: dict[str, object] = {
        "seriesid": series_ids,
        "startyear": str(start_year),
        "endyear": str(end_year),
    }
    if api_key:
        payload["registrationkey"] = api_key
        payload["annualaverage"] = True

    response = requests.post(url, json=payload, headers=DEFAULT_HEADERS, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    if body.get("status") != "REQUEST_SUCCEEDED":
        raise BLSError(f"BLS request failed: {body.get('message')}")

    out: dict[str, pd.DataFrame] = {}
    for series in body.get("Results", {}).get("series", []):
        rows = []
        for item in series.get("data", []):
            year = int(item["year"])
            period = item["period"]
            if period == "M13":
                month = 12
            elif period.startswith("M"):
                month = int(period[1:])
            else:
                continue
            value = pd.to_numeric(item.get("value"), errors="coerce")
            rows.append({"date": pd.Timestamp(year=year, month=month, day=1), "value": value})
        frame = pd.DataFrame(rows)
        if not frame.empty:
            frame = frame.sort_values("date").reset_index(drop=True)
        out[series["seriesID"]] = frame
    return out


def fetch_annual_series(
    series_id: str,
    *,
    start_year: int,
    end_year: int,
    api_key: str | None = None,
) -> pd.DataFrame:
    """Fetch one BLS series and collapse monthly observations to annual means.

    Annual averages published by BLS (period ``M13``) are used when present.
    """
    frame = fetch_series(
        [series_id],
        start_year=start_year,
        end_year=end_year,
        api_key=api_key,
    ).get(series_id, pd.DataFrame(columns=["date", "value"]))
    if frame.empty:
        return frame
    annual = frame.groupby(frame["date"].dt.year)["value"].mean().reset_index()
    annual.columns = ["year", "value"]
    return annual
