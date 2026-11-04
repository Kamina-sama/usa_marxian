"""Tests for the MELT identity audit and the deliberately vacuous design B.

The interesting property to pin down is that the distribution regression
detects its own degeneracy. A test that silently returned a p-value on
identity-generated data would be worse than no test at all.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from usa_marxian.model import value_theory as vt


def _accounts(n: int = 60, seed: int = 0) -> pd.DataFrame:
    """Synthetic accounts that satisfy the MELT identities exactly."""
    rng = np.random.default_rng(seed)
    years = np.arange(1950, 1950 + n)
    labour = pd.Series(rng.uniform(100.0, 270.0, n), index=years)

    productivity = pd.Series(
        np.linspace(30.0, 70.0, n) * np.exp(rng.normal(0.0, 0.008, n)), index=years
    )
    deflator = pd.Series(np.linspace(15.0, 100.0, n), index=years)
    real_new_value = productivity * labour
    new_value = deflator * real_new_value
    melt = new_value / labour

    wage_share = pd.Series(
        np.linspace(0.62, 0.58, n) * np.exp(rng.normal(0.0, 0.004, n)), index=years
    )
    wages = wage_share * new_value

    return pd.DataFrame(
        {
            "N": new_value,
            "L": labour,
            "new_value_real": real_new_value,
            "melt": melt,
            "melt_real": real_new_value / labour,
            "V": wages,
            "wage_share": wage_share,
            "melt_ndp": melt,
            "melt_gdp": melt * 1.2,
            "melt_nnp": melt * 0.99,
            "melt_nnp_factor": melt * 0.91,
        }
    )


def _robustness() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "name": ["baseline", "hours_nipa", "hours_ces", "melt_gdp"],
            "hours_method": ["indexed", "nipa", "ces", "indexed"],
            "value_added": ["ndp", "ndp", "ndp", "ndp"],
            "melt_mean": [29.2, 27.7, 74.6, 34.5],
            "melt_cv": [0.869, 0.846, 0.173, 0.879],
            "melt_trend": [0.0505, 0.0506, 0.0290, 0.0513],
        }
    )


def test_identities_hold_to_machine_precision():
    audit = vt.audit_melt_identities(_accounts())
    assert audit["melt_from_N_over_L"] < 1e-9
    assert audit["real_melt_equals_productivity"] < 1e-9
    assert audit["melt_equals_price_times_productivity"] < 1e-9
    assert audit["wage_share_equals_V_over_mL"] < 1e-9
    assert audit["log_decomposition_residual"] < 1e-9


def test_distribution_test_detects_its_own_vacuity():
    result = vt.test_melt_distribution(_accounts())
    assert result.degenerate is True
    assert result.r2 == pytest.approx(1.0, abs=1e-12)
    assert result.max_abs_residual < 1e-9
    assert result.coefficients["dP"] == pytest.approx(1.0, abs=1e-9)
    assert result.coefficients["dq"] == pytest.approx(1.0, abs=1e-9)
    assert result.coefficients["dw"] == pytest.approx(0.0, abs=1e-9)
    assert result.p_values == {}
    assert "Vacuous" in result.verdict


def test_distribution_test_identifies_a_real_effect_when_present():
    """If the MELT is not P x q, the wage-share effect becomes estimable."""
    accounts = _accounts()
    rng = np.random.default_rng(11)
    share = np.log(accounts["wage_share"]).to_numpy()
    noise = rng.normal(0.0, 0.002, len(accounts))
    injected = 0.8 * share + noise
    accounts["melt"] = accounts["melt"].to_numpy() * np.exp(injected)

    result = vt.test_melt_distribution(accounts)
    assert result.degenerate is False
    assert result.coefficients["dw"] == pytest.approx(0.8, abs=0.15)
    assert result.p_values["dw"] < 0.05
    assert "wage share" in result.verdict


def test_concept_spread_reports_the_ambiguity():
    table = vt.melt_concept_spread(_accounts())
    assert set(table["concept"]) == {
        "melt_ndp",
        "melt_gdp",
        "melt_nnp",
        "melt_nnp_factor",
    }
    assert "spread_ratio" not in table.columns
    assert table["latest"].is_monotonic_decreasing


def test_hours_invariance_requires_robustness_columns():
    with pytest.raises(KeyError, match="melt_mean"):
        vt.melt_hours_invariance(pd.DataFrame({"name": ["a"]}))


def test_summary_separates_level_from_growth():
    accounts = _accounts()
    concepts = vt.melt_concept_spread(accounts)
    hours = vt.melt_hours_invariance(_robustness())
    summary = vt.summarise_measurement_spread(concepts, hours)
    assert summary["concept_spread_ratio"] == pytest.approx(1.2 / 0.91, rel=1e-6)
    assert summary["spec_level_spread_ratio"] == pytest.approx(74.6 / 27.7, rel=1e-9)
    assert summary["spec_trend_min"] < summary["spec_trend_max"]
    assert summary["covered_trend_min"] == pytest.approx(0.0505, abs=1e-9)
    assert set(summary["by_hours_method"]) == {"indexed", "nipa", "ces"}


def test_run_value_theory_tests_reports_vacuous_verdict():
    result = vt.run_value_theory_tests(_accounts(), _robustness())
    assert result["distribution"]["degenerate"] is True
    assert "cannot be tested against distribution" in result["verdict"]
    assert len(result["concept_spread"]) == 4
    assert len(result["hours_invariance"]) == 4


def test_write_outputs_creates_both_artifacts(tmp_path):
    result = vt.run_value_theory_tests(_accounts(), _robustness())
    paths = vt.write_outputs(result, tmp_path)
    assert paths["json"].exists()
    assert paths["concepts"].exists()
    payload = json.loads(paths["json"].read_text())
    assert payload["distribution"]["degenerate"] is True
    table = pd.read_csv(paths["concepts"])
    assert "concept" in table.columns


def test_load_inputs_explains_a_missing_panel(tmp_path):
    with pytest.raises(FileNotFoundError, match="usa-marxian analyze"):
        vt.load_inputs(tmp_path / "processed", tmp_path / "tables")


def test_load_inputs_tolerates_missing_robustness(tmp_path):
    processed = tmp_path / "processed"
    processed.mkdir()
    _accounts(n=30).to_csv(processed / "accounts.csv")
    accounts, robustness = vt.load_inputs(processed, tmp_path / "tables")
    assert len(accounts) == 30
    assert robustness is None
