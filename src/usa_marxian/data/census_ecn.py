"""Census Economic Census data for the regulating-capital benchmark.

The Economic Census (US Basic Data, ``ecnbasic``) gives NAICS-level receipts,
payroll, cost of materials and operating expenses; the size-category table
(``ecnsize``) gives concentration (HHI, top-firm shares). These are the inputs
for cost heterogeneity and regulating cost.

These Census endpoints require a free API key (they return "Missing Key"
without one). The module degrades gracefully: without a key it returns ``None``
and the regulating benchmark is skipped.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
import yaml

from ..config import PROJECT_ROOT

ECN_BASIC_URL = "https://api.census.gov/data/2017/ecnbasic"
ECN_SIZE_URL = "https://api.census.gov/data/2012/ecnsize"
CENSUS_MAPPING_PATH = PROJECT_ROOT / "config" / "census_mapping.yaml"
DEFAULT_HEADERS = {"User-Agent": "usa-marxian/0.1 (research project)"}


class CensusError(RuntimeError):
    """Raised when the Census API returns an error."""


def load_census_config(path: Path = CENSUS_MAPPING_PATH) -> dict[str, str]:
    with Path(path).open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle) or {}
    if "naics_to_io" not in config:
        raise CensusError("census_mapping.yaml is missing naics_to_io")
    return {str(key): str(value) for key, value in config["naics_to_io"].items()}


def map_naics_to_io(naics_codes: pd.Series, config: dict[str, str]) -> pd.Series:
    """Map NAICS codes to IO codes using the longest matching prefix."""

    def match(code: str) -> str | None:
        code = str(code)
        best = None
        best_len = 0
        for prefix, io_code in config.items():
            if code.startswith(prefix) and len(prefix) > best_len:
                best = io_code
                best_len = len(prefix)
        return best

    return naics_codes.astype(str).map(match)


def fetch_ecn_basic(api_key: str, *, timeout: float = 60.0) -> pd.DataFrame:
    """Fetch 2017 Economic Census basic data at NAICS level."""
    response = requests.get(
        ECN_BASIC_URL,
        params={
            "get": "NAICS2017,RCPTOT,PAYANN,CSTMPRT,OPEX,EMP,FIRM,INDLEVEL",
            "for": "us:*",
            "key": api_key,
        },
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    _raise_if_error(response)
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise CensusError("Census ecnbasic returned an empty table")
    return pd.DataFrame(payload[1:], columns=payload[0])


def fetch_ecn_size(api_key: str, *, timeout: float = 60.0) -> pd.DataFrame:
    """Fetch 2012 Economic Census size-category and concentration data."""
    response = requests.get(
        ECN_SIZE_URL,
        params={
            "get": "NAICS2012,CONCENFI,RCPTOT,PAYANN,EMP,INDLEVEL",
            "for": "us:*",
            "key": api_key,
        },
        headers=DEFAULT_HEADERS,
        timeout=timeout,
    )
    _raise_if_error(response)
    payload = response.json()
    if not isinstance(payload, list) or len(payload) < 2:
        raise CensusError("Census ecnsize returned an empty table")
    return pd.DataFrame(payload[1:], columns=payload[0])


def _raise_if_error(response: requests.Response) -> None:
    if response.status_code != 200:
        raise CensusError(f"Census API returned {response.status_code}")
    if "Missing Key" in response.text or "Invalid Key" in response.text:
        raise CensusError("Census API key missing or invalid")


def load_regulating_data(
    raw_dir: Path,
    api_key: str | None,
    *,
    max_age_days: int = 365,
    force: bool = False,
) -> pd.DataFrame | None:
    """Load unit cost and within-industry cost dispersion by IO industry.

    Returns ``industry_code, unit_cost, unit_cost_min, cost_cv, n_subindustries``.
    The dispersion is across 6-digit NAICS sub-industries inside each IO industry;
    it is a sub-industry proxy, not a firm-level distribution.
    """
    if not api_key:
        return None

    cache = raw_dir / "census"
    cache.mkdir(parents=True, exist_ok=True)
    basic_path = cache / "ecnbasic.csv"

    def _cached(path: Path, fetch):
        if path.exists() and not force:
            age_days = (time.time() - path.stat().st_mtime) / 86_400
            if age_days < max_age_days:
                return pd.read_csv(path, dtype=str)
        frame = fetch()
        frame.to_csv(path, index=False)
        return frame

    basic = _cached(basic_path, lambda: fetch_ecn_basic(api_key))
    basic = basic.loc[basic["INDLEVEL"].astype(str) == "6"].copy()
    config = load_census_config()
    basic["industry_code"] = map_naics_to_io(basic["NAICS2017"], config)
    basic = basic.dropna(subset=["industry_code"])

    for column in ["RCPTOT", "PAYANN", "CSTMPRT"]:
        basic[column] = pd.to_numeric(basic[column], errors="coerce")
    basic["unit_cost_sub"] = (basic["PAYANN"] + basic["CSTMPRT"]) / basic["RCPTOT"]
    basic = basic.loc[
        (basic["RCPTOT"] > 0)
        & basic["unit_cost_sub"].notna()
        & (basic["unit_cost_sub"] > 0)
    ]

    rows = []
    for industry_code, group in basic.groupby("industry_code"):
        receipts = group["RCPTOT"].sum()
        unit_cost = (group["PAYANN"].sum() + group["CSTMPRT"].sum()) / receipts
        subsidies = group["unit_cost_sub"]
        rows.append(
            {
                "industry_code": industry_code,
                "unit_cost": float(unit_cost),
                "unit_cost_min": float(subsidies.min()),
                "cost_cv": float(subsidies.std(ddof=1) / subsidies.mean())
                if len(subsidies) > 1
                else float("nan"),
                "n_subindustries": int(len(subsidies)),
            }
        )

    result = pd.DataFrame(rows)
    metadata = {
        "downloaded_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_industries": int(result.shape[0]),
        "n_subindustries": int(basic.shape[0]),
    }
    (cache / "census.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return result
