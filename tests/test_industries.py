"""Tests for the industry module and the BEA Use-table parser."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.data.bea_io import BEAIOError, parse_use_sheet
from usa_marxian.model.industries import (
    add_industry_ratios,
    industry_report,
    latest_dispersion,
    year_summary,
)


@pytest.fixture
def industry_panel() -> pd.DataFrame:
    rows = []
    base = {
        "A": dict(C=100.0, V=40.0, T=5.0, GOS=55.0, N=100.0, GO=200.0),
        "B": dict(C=50.0, V=30.0, T=5.0, GOS=15.0, N=50.0, GO=100.0),
        "C": dict(C=200.0, V=20.0, T=10.0, GOS=20.0, N=50.0, GO=250.0),
    }
    for year in (2019, 2020):
        for code, values in base.items():
            row = {"year": year, "industry_code": code, "industry_name": f"Industry {code}"}
            row.update(values)
            row["S"] = row["T"] + row["GOS"]
            row["K"] = row["C"] + row["V"]
            rows.append(row)
    return pd.DataFrame(rows)


def test_parse_use_sheet_fixture():
    rows = [
        (None, "Commodities/Industries", "A", "B", "F010", None),
        ("IOCode", "Name", "Industry A", "Industry B", "PCE", "Total"),
        ("A", "Industry A", 1, 2, 3, 6),
        (None, "Total Intermediate", 100, 50, 0, 150),
        (None, "Compensation of employees", 40, 30, 0, 70),
        (None, "Taxes on production and imports, less subsidies", 5, 5, 0, 10),
        (None, "Gross operating surplus", 55, 15, 0, 70),
        (None, "Total Value Added", 100, 50, 0, 150),
        (None, "Total Industry Output", 200, 100, 0, 300),
    ]
    frame = parse_use_sheet(rows, 2020)
    assert len(frame) == 2
    assert list(frame["industry_code"]) == ["A", "B"]
    assert frame.loc[0, "C"] == 100
    assert frame.loc[0, "N"] == 100
    assert frame.loc[0, "GO"] == 200


def test_parse_use_sheet_rejects_missing_rows():
    rows = [
        (None, "Commodities/Industries", "A", "F010", None),
        ("IOCode", "Name", "Industry A", "PCE", "Total"),
        ("A", "Industry A", 1, 2, 3),
        (None, "Total Intermediate", 100, 0, 100),
    ]
    with pytest.raises(BEAIOError):
        parse_use_sheet(rows, 2020)


def test_industry_ratios_and_summary(industry_panel):
    enriched = add_industry_ratios(industry_panel)
    assert {"R_cost", "PP_K", "PP_V", "r", "abs_gap_pct_K"}.issubset(enriched.columns)
    for _, group in enriched.groupby("year"):
        assert np.isclose(group["PP_K"].sum(), group["GO"].sum())
        assert np.isclose(group["R_cost"].iloc[0], group["S"].sum() / group["K"].sum())

    summary = year_summary(industry_panel)
    assert len(summary) == 2
    assert summary["n_industries"].eq(3).all()
    assert (summary["rate_weighted_cv"] >= 0).all()
    assert summary["mae_pct_K"].between(0, 100).all()


def test_industry_report_and_latest(industry_panel):
    report = industry_report(industry_panel)
    assert report["n_industries"] == 3
    assert report["latest_year"] == 2020
    assert 0 < report["latest"]["R_cost"] < 1

    latest = latest_dispersion(industry_panel)
    assert len(latest) == 3
    assert latest["r"].is_monotonic_decreasing
