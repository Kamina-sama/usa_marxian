"""On-disk caching for raw series.

Every downloaded series is stored as CSV under ``data/raw/<provider>/``. A
cached file younger than ``max_age_days`` is reused, which keeps repeated
analysis runs fast and makes the pipeline reproducible offline.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pandas as pd

from ..config import SeriesSpec
from . import bea, bls, fred


def series_cache_path(raw_dir: Path, provider: str, series_id: str) -> Path:
    return raw_dir / provider / f"{series_id}.csv"


def _is_fresh(path: Path, max_age_days: int) -> bool:
    if not path.exists():
        return False
    age_seconds = time.time() - path.stat().st_mtime
    return age_seconds < max_age_days * 86_400


def _write_atomic(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(tmp, index=False)
    os.replace(tmp, path)


def load_raw_series(
    spec: SeriesSpec,
    raw_dir: Path,
    *,
    max_age_days: int = 30,
    start_year: int = 1948,
    end_year: int | None = None,
    fred_api_key: str | None = None,
    bls_api_key: str | None = None,
    bea_api_key: str | None = None,
) -> pd.DataFrame:
    """Load one raw series, using the cache when fresh.

    Returns a frame with at least ``date`` and ``value``.
    """
    path = series_cache_path(raw_dir, spec.provider, spec.series_id)
    if _is_fresh(path, max_age_days):
        return pd.read_csv(path, parse_dates=["date"])

    if spec.provider == "fred":
        if fred_api_key:
            try:
                frame = fred.fetch_series_api(spec.series_id, fred_api_key)
            except Exception:  # fall back to the keyless endpoint
                frame = fred.fetch_series(spec.series_id)
        else:
            frame = fred.fetch_series(spec.series_id)
    elif spec.provider == "bls":
        frame = bls.fetch_series(
            [spec.series_id],
            start_year=start_year,
            end_year=end_year or pd.Timestamp.today().year,
            api_key=bls_api_key,
        ).get(spec.series_id, pd.DataFrame(columns=["date", "value"]))
    elif spec.provider == "bea":
        frame = bea.fetch_nipa_series(spec.series_id)
    else:  # pragma: no cover - guarded by the pydantic literal
        raise ValueError(f"Unknown provider: {spec.provider}")

    if frame.empty:
        raise ValueError(f"No observations returned for {spec.provider}:{spec.series_id}")

    _write_atomic(frame, path)
    return frame
