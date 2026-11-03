"""Tests for sector mapping, CFC allocation and deflator merging."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.sectors import allocate_cfc, attach_input_deflator


def _panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "year": [2020, 2020, 2020],
            "industry_code": ["A", "B", "GFGD"],
            "industry_name": ["A", "B", "Government"],
            "C": [10.0, 20.0, 30.0],
            "V": [5.0, 5.0, 10.0],
            "T": [1.0, 1.0, 1.0],
            "GOS": [60.0, 40.0, 10.0],
            "N": [66.0, 46.0, 21.0],
            "GO": [76.0, 66.0, 51.0],
        }
    )


def test_allocate_cfc_is_proportional_to_gos():
    cfc = pd.DataFrame(
        [{"year": 2020, "kind": "corporate", "label": "Sector", "value": 100.0}]
    )
    config = {
        "cfc_groups": {
            "sector": {
                "corporate": ["Sector"],
                "noncorporate": [],
                "industries": ["A", "B"],
            }
        }
    }
    out = allocate_cfc(_panel(), cfc, config)
    assert out.loc[out.industry_code == "A", "CFC"].iloc[0] == 60.0
    assert out.loc[out.industry_code == "B", "CFC"].iloc[0] == 40.0
    assert out.loc[out.industry_code == "GFGD", "CFC"].isna().all()
    assert out["CFC"].sum() == 100.0


def test_allocate_cfc_handles_missing_year():
    cfc = pd.DataFrame(
        [{"year": 2021, "kind": "corporate", "label": "Sector", "value": 90.0}]
    )
    config = {
        "cfc_groups": {
            "sector": {
                "corporate": ["Sector"],
                "noncorporate": [],
                "industries": ["A", "B"],
            }
        }
    }
    out = allocate_cfc(_panel(), cfc, config)
    assert out["CFC"].isna().all()


def test_attach_input_deflator_uses_use_weights():
    use = pd.DataFrame(
        {
            "year": [2017, 2017, 2017, 2017],
            "industry_code": ["A", "A", "B", "B"],
            "commodity_code": ["A", "B", "A", "B"],
            "value": [60.0, 40.0, 0.0, 100.0],
        }
    )
    prices = pd.DataFrame(
        {
            "year": [2017, 2017, 2018, 2018],
            "sector": ["s1", "s2", "s1", "s2"],
            "go_price": [100.0, 100.0, 110.0, 120.0],
        }
    )
    panel = pd.DataFrame(
        {
            "year": [2017, 2017, 2018, 2018],
            "industry_code": ["A", "B", "A", "B"],
        }
    )
    config = {
        "deflators": {
            "s1": {"industries": ["A"]},
            "s2": {"industries": ["B"]},
        }
    }

    attached = attach_input_deflator(panel, use, prices, config, base_year=2017)

    a_2018 = attached.loc[
        (attached["year"] == 2018) & (attached["industry_code"] == "A"), "input_price"
    ].iloc[0]
    b_2018 = attached.loc[
        (attached["year"] == 2018) & (attached["industry_code"] == "B"), "input_price"
    ].iloc[0]
    assert np.isclose(a_2018, 0.6 * 110 + 0.4 * 120)
    assert np.isclose(b_2018, 120.0)
