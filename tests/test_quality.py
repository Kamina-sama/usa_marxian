"""Tests for data-quality reporting."""

from __future__ import annotations

from usa_marxian.data.quality import coverage_table, panel_summary, write_quality


def test_coverage_table(raw_panel):
    table = coverage_table(raw_panel)
    assert len(table) == raw_panel.shape[1]
    assert table["n_obs"].min() > 0
    assert {"series", "missing_years", "flag_extreme_change"}.issubset(table.columns)


def test_coverage_flags_missing(raw_panel):
    panel = raw_panel.copy()
    panel.loc[1995, "gdp"] = None
    table = coverage_table(panel)
    row = table.loc[table["series"] == "gdp"].iloc[0]
    assert row["n_missing"] == 1
    assert 1995 in row["missing_years"]


def test_write_quality(tmp_path, raw_panel):
    summary = write_quality(
        raw_panel,
        csv_path=tmp_path / "quality.csv",
        json_path=tmp_path / "quality.json",
    )
    assert (tmp_path / "quality.csv").exists()
    assert (tmp_path / "quality.json").exists()
    assert summary["n_series"] == raw_panel.shape[1]
    assert summary["n_rows"] == raw_panel.shape[0]


def test_panel_summary_complete_years(raw_panel):
    summary = panel_summary(raw_panel)
    assert summary["n_complete_years"] == len(raw_panel)
