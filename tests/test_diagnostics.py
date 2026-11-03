"""Tests for the time-series diagnostics."""

from __future__ import annotations

import numpy as np

from usa_marxian.analysis.diagnostics import (
    adf_test,
    bootstrap_ltv_slope,
    chow_test,
    diagnostics_table,
    first_difference_ltv,
    kpss_test,
    scan_break,
    trend_augmented_ltv,
    zivot_andrews_test,
)


def test_unit_root_tests_return_finite_statistics(accounts):
    for result in (
        adf_test(accounts["melt"]),
        kpss_test(accounts["melt"]),
        zivot_andrews_test(accounts["melt"]),
    ):
        assert np.isfinite(result.statistic)
        assert 0.0 <= result.p_value <= 1.0


def test_chow_and_break_scan(accounts):
    f_stat, p_value = chow_test(accounts, 2005)
    assert np.isfinite(f_stat)
    assert 0.0 <= p_value <= 1.0

    scan = scan_break(accounts, min_segment=5)
    assert scan["break_year"] is not None
    assert np.isfinite(scan["f_stat"])


def test_first_difference_and_trend_augmented(accounts):
    fd = first_difference_ltv(accounts)
    ta = trend_augmented_ltv(accounts)
    assert np.isfinite(fd["slope"])
    assert fd["nobs"] == len(accounts) - 1
    assert np.isfinite(ta["slope"])
    assert "trend_coefficient" in ta


def test_bootstrap_interval(accounts):
    result = bootstrap_ltv_slope(accounts, n_boot=200, seed=7)
    assert result["ci_low"] <= result["mean"] <= result["ci_high"]
    assert 0.0 <= result["share_above_one"] <= 1.0
    assert result["n_boot"] > 100


def test_diagnostics_table_shape(accounts):
    table = diagnostics_table(accounts)
    assert len(table) >= 10
    assert {"block", "test", "statistic", "p_value", "detail"}.issubset(table.columns)
    assert "ltv_break_scan" in set(table["block"])
