"""BLS manufacturing hours and earnings.

BEA Table 6.9D (hours worked by industry) was discontinued, so manufacturing
hours come from BLS CES instead:

    CES3000000001  all employees, manufacturing (thousands)
    CES3000000002  average weekly hours, manufacturing
    CES3000000003  average hourly earnings, manufacturing

These are aggregate manufacturing series, not 3-digit industry series. They are
used to split the common hours-per-FTE into a manufacturing and a
non-manufacturing rate.
"""

from __future__ import annotations

import pandas as pd

from .bls import fetch_annual_series

MANUFACTURING_SERIES = {
    "employees": "CES3000000001",
    "weekly_hours": "CES3000000002",
    "hourly_earnings": "CES3000000003",
}


def fetch_manufacturing_hours(
    api_key: str,
    *,
    start_year: int = 1998,
    end_year: int | None = None,
) -> pd.DataFrame:
    """Return annual manufacturing employees, weekly hours and total hours.

    ``manufacturing_hours_bn`` is billions of hours:
    ``employees(thousands) * weekly_hours * 52 / 1e6``.
    """
    end = end_year or pd.Timestamp.today().year
    frames = []
    for column, series_id in MANUFACTURING_SERIES.items():
        annual = fetch_annual_series(
            series_id,
            start_year=start_year,
            end_year=end,
            api_key=api_key,
        )
        if annual.empty:
            raise ValueError(f"BLS series returned no data: {series_id}")
        annual = annual.rename(columns={"value": column})
        frames.append(annual.set_index("year"))

    frame = pd.concat(frames, axis=1).sort_index()
    frame["manufacturing_hours_bn"] = (
        frame["employees"] * frame["weekly_hours"] * 52.0 / 1e6
    )
    return frame.reset_index()
