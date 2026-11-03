"""Tests for the derived Marxian accounts."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from usa_marxian.data.build import build_accounts, compute_hours, validate_accounts


def test_accounting_identities(raw_panel, settings):
    accounts = build_accounts(raw_panel, settings)

    assert np.allclose(accounts["P"], accounts["C"] + accounts["N"])
    assert np.allclose(accounts["K"], accounts["C"] + accounts["V"])
    assert np.allclose(accounts["S"], accounts["N"] - accounts["V"])
    assert np.allclose(accounts["S"], accounts["P"] - accounts["K"])

    validate_accounts(accounts)


def test_melt_is_new_value_per_hour(raw_panel, settings):
    accounts = build_accounts(raw_panel, settings)
    assert np.allclose(accounts["melt"], accounts["N"] / accounts["L"])
    assert (accounts["melt"] > 0).all()


def test_rate_of_profit_decomposition(raw_panel, settings):
    accounts = build_accounts(raw_panel, settings)
    assert np.allclose(accounts["rate_profit"], accounts["rate_profit_identity"])
    assert np.allclose(
        accounts["rate_profit"],
        (accounts["S"] / accounts["V"]) / (accounts["M"] / accounts["V"]),
    )


def test_hours_ces_units():
    raw = pd.DataFrame(
        {
            "employment": [135_000.0],  # thousands of persons
            "weekly_hours": [34.0],
        }
    )
    hours = compute_hours(raw, "ces")
    # 135,000 thousand x 34 h/week x 52 weeks = 238.68 billion hours
    assert hours.iloc[0] == pytest.approx(238.68)


def test_hours_nipa_passthrough():
    raw = pd.DataFrame({"hours_nipa": [260.0]})
    assert compute_hours(raw, "nipa").iloc[0] == pytest.approx(260.0)


def test_hours_indexed_benchmark():
    raw = pd.DataFrame(
        {
            "hours_index": [100.0, 110.0],
            "hours_nipa": [250.0, 250.0],
        },
        index=[2017, 2018],
    )
    hours = compute_hours(raw, "indexed", base_year=2017)
    assert hours.loc[2017] == pytest.approx(250.0)
    assert hours.loc[2018] == pytest.approx(275.0)


def test_validate_accounts_detects_break(raw_panel, settings):
    accounts = build_accounts(raw_panel, settings)
    accounts.loc[2000, "S"] = accounts.loc[2000, "S"] + 1.0
    with pytest.raises(AssertionError):
        validate_accounts(accounts)
