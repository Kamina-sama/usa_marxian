"""Tests for the value of labour power construction and identification."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest

from usa_marxian.model import value_of_labour_power as volp


def _panel(n: int = 26, seed: int = 3) -> pd.DataFrame:
    """Synthetic panel with the real panel's structure and known trends."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=float)
    years = np.arange(1998, 1998 + n)

    wage_share = 0.65 * np.exp(-0.0024 * t)
    consumption_share = 0.97 * np.exp(0.0042 * t)
    price_value = 0.87 * np.exp(rng.normal(0.0, 0.002, n))
    lam = wage_share * consumption_share / price_value

    return pd.DataFrame(
        {
            "year": years,
            "lambda_actual": lam,
            "lambda_domestic": lam * 0.96,
            "lambda_wage_financed": lam / consumption_share,
            "wage_share": wage_share,
            "consumption_share_of_wage": consumption_share,
            "price_to_value_ratio": price_value,
            "wedge": lam / wage_share,
            "wage_financed_ratio": (lam / consumption_share) / wage_share,
            "coherence": np.full(n, 0.957),
            "coverage_share": np.full(n, 0.838),
            "import_share": np.full(n, 0.14),
            "pv_consumption": price_value,
            "pv_investment": np.full(n, 1.13),
            "pv_government": np.full(n, 1.11),
            "pv_exports": np.full(n, 1.29),
        }
    ).set_index("year")


def test_labour_values_match_a_hand_computed_economy():
    matrix = pd.DataFrame(
        [[0.5, 0.0], [0.0, 0.0]], index=["a", "b"], columns=["a", "b"]
    )
    hours = pd.Series({"a": 0.1e6, "b": 0.2e6})
    output = pd.Series({"a": 1.0, "b": 1.0})  # millions of 2017 dollars
    values = volp._labour_values(matrix, hours, output)
    assert values["a"] == pytest.approx(0.2, rel=1e-9)
    assert values["b"] == pytest.approx(0.2, rel=1e-9)


def test_trend_test_recovers_a_known_growth_rate():
    panel = _panel()
    result = volp.trend_test(panel, "consumption_share_of_wage")
    assert result.trend_per_year == pytest.approx(0.0042, abs=5e-4)
    assert result.trend_p_value < 0.01


def test_identification_test_reports_a_flat_wage_financed_ratio():
    identification = volp.identification_test(_panel())
    assert identification["price_value_flat"] is True
    assert abs(identification["price_value_trend"]["trend_per_year"]) < 1e-3


def test_run_rejects_constancy_and_refuses_separate_identification():
    result = volp.run_volp_tests(_panel())
    assert result["customary_claim_rejected"] is True
    assert "not separately identified" in result["verdict"]
    assert result["gradient_years_consumption_below_investment"] == result["sample"][
        "n_years"
    ]
    assert result["sample"]["mean_coverage"] == pytest.approx(0.838)


def test_wage_financed_basket_tracks_the_wage_share():
    panel = _panel()
    ratio_trend = volp.trend_test(panel, "wage_financed_ratio").trend_per_year
    assert abs(ratio_trend) < 5e-4


def test_write_outputs_creates_panel_and_summary(tmp_path):
    panel = _panel()
    result = volp.run_volp_tests(panel)
    paths = volp.write_outputs(panel, result, tmp_path)
    assert paths["panel"].exists()
    assert paths["json"].exists()
    payload = json.loads(paths["json"].read_text())
    assert "verdict" in payload
    table = pd.read_csv(paths["panel"])
    assert "lambda_actual" in table.columns
    assert len(table) == len(panel)


def test_build_basket_panel_explains_missing_artifacts(tmp_path):
    with pytest.raises(FileNotFoundError, match="usa-marxian industries"):
        volp.build_basket_panel(tmp_path)
