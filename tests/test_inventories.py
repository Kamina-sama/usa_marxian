"""Tests for broad-sector inventory allocation."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.bea_inventories import allocate_inventory_stock


def test_allocate_inventory_stock_sums_and_direct_maps():
    panel = pd.DataFrame(
        {
            "year": [2020] * 10,
            "industry_code": [
                "111CA",
                "211",
                "42",
                "441",
                "445",
                "452",
                "4A0",
                "311FT",
                "513",
                "HS",
            ],
            "GO": [100.0, 200.0, 300.0, 400.0, 10.0, 10.0, 10.0, 500.0, 600.0, 700.0],
        }
    )
    totals = pd.DataFrame(
        {
            "year": [2020] * 9,
            "category": [
                "Farm",
                "Mining, utilities, and construction",
                "Manufacturing",
                "Wholesale trade",
                "Motor vehicle and parts dealers",
                "Food and beverage stores",
                "General merchandise stores",
                "Other retail stores",
                "Other industries",
            ],
            "value": [100.0, 50.0, 200.0, 300.0, 40.0, 20.0, 30.0, 10.0, 80.0],
        }
    )

    allocated = allocate_inventory_stock(panel, totals)
    by_code = allocated.set_index("industry_code")["M_inv"]

    assert np.isclose(by_code["111CA"], 100.0)
    assert np.isclose(by_code["211"], 50.0)
    assert np.isclose(by_code["42"], 300.0)
    assert np.isclose(by_code["441"], 40.0)
    assert np.isclose(by_code["311FT"], 200.0)
    assert np.isclose(by_code["513"], 80.0)
    assert "HS" not in by_code.index
    assert np.isclose(allocated["M_inv"].sum(), 830.0)
