"""Tests for detailed inventory mapping and combination."""

from __future__ import annotations

import numpy as np
import pandas as pd

from usa_marxian.data.bea_inventory_detail import (
    combine_detail_with_broad,
    map_detail_to_io,
)


def test_map_detail_to_io_aggregates_and_avoids_subtotals():
    detail = pd.DataFrame(
        {
            "year": [2023] * 6,
            "line_label": [
                "Wood product manufacturing",
                "Food manufacturing",
                "Beverage and tobacco product manufacturing",
                "Motor vehicle and parts dealers",
                "General merchandise stores",
                "Department stores",
            ],
            "value": [10.0, 30.0, 5.0, 40.0, 50.0, 20.0],
        }
    )
    mapped = map_detail_to_io(detail).set_index("industry_code")["M_inv"]

    assert np.isclose(mapped["321"], 10.0)
    assert np.isclose(mapped["311FT"], 35.0)
    assert np.isclose(mapped["441"], 40.0)
    assert np.isclose(mapped["452"], 50.0)
    assert np.isclose(mapped.sum(), 135.0)


def test_combine_detail_with_broad_replaces_only_detail_categories():
    detail = pd.DataFrame(
        {
            "year": [2023, 2023],
            "industry_code": ["321", "441"],
            "M_inv": [10.0, 40.0],
            "inventory_category": [
                "BEA 1BUC manufacturing detail",
                "BEA 1BUC retail detail",
            ],
            "inventory_source": ["BEA 1BUC detail", "BEA 1BUC detail"],
        }
    )
    broad = pd.DataFrame(
        {
            "year": [2023] * 4,
            "industry_code": ["321", "441", "111CA", "513"],
            "M_inv": [99.0, 99.0, 5.0, 7.0],
            "inventory_category": [
                "Manufacturing",
                "Motor vehicle and parts dealers",
                "Farm",
                "Other industries",
            ],
        }
    )

    combined = combine_detail_with_broad(detail, broad).set_index("industry_code")["M_inv"]

    assert np.isclose(combined["321"], 10.0)
    assert np.isclose(combined["441"], 40.0)
    assert np.isclose(combined["111CA"], 5.0)
    assert np.isclose(combined["513"], 7.0)
    assert np.isclose(combined.sum(), 62.0)
