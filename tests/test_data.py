"""Offline tests for raw-data parsing."""

from __future__ import annotations

import pandas as pd
import pytest

from usa_marxian.data import bea, bls, fred
from usa_marxian.data.build import annualize


def test_fred_parse_csv_handles_missing_values():
    text = "observation_date,GDPA\n1990-01-01,100.0\n1991-01-01,.\n1992-01-01,110.0\n"
    frame = fred._parse_csv(text)
    assert list(frame.columns) == ["date", "value"]
    assert frame["value"].isna().sum() == 1
    assert frame.loc[2, "value"] == pytest.approx(110.0)


def test_fred_parse_rejects_html():
    with pytest.raises(fred.FredError):
        fred._parse_csv("<!doctype html><html></html>")


def test_annualize_quarterly_mean(fred_spec):
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["1990-03-31", "1990-06-30", "1990-09-30", "1990-12-31", "1991-03-31"]
            ),
            "value": [10.0, 20.0, 30.0, 40.0, 50.0],
        }
    )
    annual = annualize(frame, fred_spec)
    assert annual.loc[1990] == pytest.approx(25.0)
    assert annual.loc[1991] == pytest.approx(50.0)


def test_bea_flat_file_parse(monkeypatch):
    text = (
        "%SeriesCode,Period,Value\n"
        'A001RC,1929,"105,322"\n'
        "A001RC,1930,92500\n"
        "A191RC,1929,104000\n"
    )

    class FakeResponse:
        status_code = 200
        text = ""

        def raise_for_status(self):
            return None

    def fake_get(*args, **kwargs):
        response = FakeResponse()
        response.text = text
        return response

    monkeypatch.setattr(bea.requests, "get", fake_get)
    frame = bea.fetch_nipa_flat()
    assert set(frame.columns) == {"series_code", "year", "value"}
    gdp = frame.loc[frame["series_code"] == "A001RC"]
    assert gdp.loc[gdp["year"].eq(1929), "value"].iloc[0] == pytest.approx(105322.0)


def test_bls_parse(monkeypatch):
    payload = {
        "status": "REQUEST_SUCCEEDED",
        "Results": {
            "series": [
                {
                    "seriesID": "CES0000000001",
                    "data": [
                        {"year": "2024", "period": "M01", "value": "100"},
                        {"year": "2024", "period": "M02", "value": "102"},
                        {"year": "2024", "period": "M13", "value": "101"},
                    ],
                }
            ]
        },
    }

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return payload

    monkeypatch.setattr(bls.requests, "post", lambda *a, **k: FakeResponse())
    out = bls.fetch_series(["CES0000000001"], start_year=2024, end_year=2024)
    frame = out["CES0000000001"]
    assert len(frame) == 3
    assert frame["value"].iloc[-1] == pytest.approx(101.0)
