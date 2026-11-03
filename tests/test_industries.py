"""Tests for the industry module and the BEA Use-table parser."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.data.bea_io import BEAIOError, parse_use_sheet
from usa_marxian.model.industries import (
    add_industry_ratios,
    industry_reconciliation,
    industry_report,
    latest_dispersion,
    proxy_sensitivity,
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
    assert {
        "R_benchmark",
        "PP",
        "PP_V",
        "r",
        "abs_gap_pct_PP",
        "M_proxy",
        "S_gross",
        "K_gross",
        "S_net",
        "K_net",
    }.issubset(enriched.columns)
    for _, group in enriched.groupby("year"):
        assert np.isclose(group["PP"].sum(), group["GO"].sum())
        assert np.isclose(
            group["R_benchmark"].iloc[0],
            group["S_gross"].sum() / group["K_gross"].sum(),
        )

    summary = year_summary(industry_panel)
    assert len(summary) == 2
    assert summary["n_industries"].eq(3).all()
    assert (summary["rate_weighted_cv"] >= 0).all()
    assert summary["mae_pct_PP"].between(0, 100).all()


def test_net_accounts_with_cfc(industry_panel):
    panel = industry_panel.copy()
    panel["CFC"] = 10.0
    enriched = add_industry_ratios(panel)
    assert (enriched["surplus_basis"] == "net").all()
    assert np.allclose(enriched["K_net"] + enriched["S_net"], enriched["GO"])
    assert np.allclose(enriched["C_total"], enriched["C"] + enriched["CFC"])
    assert (enriched["r_net"] < enriched["r_gross"]).all()

    # Depreciation is reclassified from surplus to constant capital, not
    # double counted: the total value identity is unchanged.
    for _, group in enriched.groupby("year"):
        assert np.isclose(group["PP"].sum(), group["GO"].sum())


def test_pp_formula_uses_selected_capital_proxy(industry_panel):
    enriched = add_industry_ratios(industry_panel, capital_proxy="output")
    for _, group in enriched.groupby("year"):
        assert np.allclose(group["M_proxy"], group["GO"])
        assert np.allclose(
            group["PP"],
            group["K_gross"] + group["R_benchmark"] * group["M_proxy"],
        )
        # The old shortcut K(1+R) is only valid when M_i = K_i.
        assert not np.allclose(
            group["PP"],
            group["K_gross"] * (1.0 + group["R_benchmark"]),
        )


def test_fixed_assets_proxy_uses_supplied_stock(industry_panel):
    panel = industry_panel.copy()
    panel["M"] = (panel["C"] + panel["V"]) * 2.0
    enriched = add_industry_ratios(panel, capital_proxy="fixed_assets")
    for _, group in enriched.groupby("year"):
        assert np.allclose(group["M_proxy"], group["M"])
        assert np.allclose(
            group["PP"],
            group["K_net"] + group["R_benchmark"] * group["M_proxy"],
        )


def test_proxy_sensitivity(industry_panel):
    table = proxy_sensitivity(industry_panel)
    assert set(table["capital_proxy"]) == {"cost", "output", "value_added"}
    assert (table["mae_pct_PP"] >= 0).all()
    assert np.isfinite(table["mae_pct_PP"]).all()


def test_industry_reconciliation(industry_panel):
    accounts = pd.DataFrame(
        {"P": [300.0, 300.0], "C": [20.0, 20.0], "N": [280.0, 280.0], "S": [100.0, 100.0]},
        index=[2019, 2020],
    )
    table = industry_reconciliation(industry_panel, accounts)
    assert len(table) == 2
    assert {"industry_N", "gdp", "gap_N", "industry_CFC", "macro_CFC", "gap_CFC"}.issubset(
        table.columns
    )
    assert np.allclose(table["industry_N"] - table["gap_N"], table["gdp"])
    assert np.allclose(table["industry_CFC"] - table["gap_CFC"], table["macro_CFC"])


def test_industry_report_and_latest(industry_panel):
    report = industry_report(industry_panel)
    assert report["n_industries"] == 3
    assert report["latest_year"] == 2020
    assert 0 < report["latest"]["R_benchmark"] < 1
    assert report["surplus_basis"] == "gross"

    latest = latest_dispersion(industry_panel)
    assert len(latest) == 3
    assert latest["r"].is_monotonic_decreasing
    assert {"M_proxy", "PP", "abs_gap_pct_PP"}.issubset(latest.columns)
