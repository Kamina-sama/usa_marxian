"""Tests for alternative specifications."""

from __future__ import annotations

import numpy as np
import pytest

from usa_marxian.model.robustness import (
    DEFAULT_SPECS,
    Spec,
    run_specification,
    run_specifications,
    specification_ranges,
    with_spec,
)


def test_all_default_specs_run(raw_panel, settings):
    table = run_specifications(raw_panel, settings)
    assert len(table) == len(DEFAULT_SPECS)
    assert table["error"].isna().all(), table.loc[table["error"].notna(), ["name", "error"]]

    baseline = table.loc[table["name"] == "baseline"].iloc[0]
    assert baseline["n_years"] > 10
    assert np.isfinite(baseline["ltv_slope"])
    assert 0 < baseline["rate_profit_last"] < 1
    assert np.isfinite(baseline["property_check_mean_ratio"])


def test_spec_ranges_cover_metrics(raw_panel, settings):
    table = run_specifications(raw_panel, settings)
    ranges = specification_ranges(table)
    assert {"metric", "min", "max", "n_specs"}.issubset(ranges.columns)
    assert "ltv_slope" in set(ranges["metric"])
    assert (ranges["min"] <= ranges["max"]).all()


def test_single_spec_and_with_spec(raw_panel, settings):
    record = run_specification(raw_panel, settings, Spec("only"))
    assert record["name"] == "only"
    assert record["error"] is None

    changed = with_spec(Spec("base"), value_added="nnp", melt_numerator="nnp")
    assert changed.value_added == "nnp"
    assert changed.melt_numerator == "nnp"


def test_nnp_spec_differs_from_ndp(raw_panel, settings):
    ndp = run_specification(raw_panel, settings, Spec("ndp"))
    nnp = run_specification(raw_panel, settings, Spec("nnp", value_added="nnp", melt_numerator="nnp"))
    assert nnp["melt_mean"] != pytest.approx(ndp["melt_mean"])
    assert nnp["n_years"] == ndp["n_years"]
