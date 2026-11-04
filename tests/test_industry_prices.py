"""Tests for the BEA industry price attachment."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.bea_industry_prices import attach_industry_prices


def test_attach_industry_prices_replaces_sector_values():
    panel = pd.DataFrame(
        {
            "year": [2020, 2020],
            "industry_code": ["A", "B"],
            "C": [100.0, 100.0],
            "V": [50.0, 50.0],
            "N": [150.0, 150.0],
            "GO": [200.0, 200.0],
            "go_price": [100.0, 100.0],
            "va_price": [100.0, 100.0],
            "input_price": [100.0, 100.0],
        }
    )
    prices = pd.DataFrame(
        {
            "year": [2020, 2020],
            "industry_code": ["A", "B"],
            "go_price": [110.0, 120.0],
            "va_price": [105.0, 115.0],
            "input_price": [108.0, 118.0],
        }
    )

    attached = attach_industry_prices(panel, prices)

    assert np.isclose(attached.loc[0, "go_price"], 110.0)
    assert np.isclose(attached.loc[1, "go_price"], 120.0)
    assert np.isclose(attached.loc[0, "GO_real"], 200.0 * 1e6 / 1.10)
    assert np.isclose(attached.loc[0, "C_real"], 100.0 * 1e6 / 1.08)
    assert (attached["price_source"] == "bea_gdpbyindustry").all()
