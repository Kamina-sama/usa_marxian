"""Tests for configuration loading and the CLI surface."""

from __future__ import annotations

from usa_marxian.cli import main
from usa_marxian.config import ProjectConfig, SeriesCatalog, Settings


def test_settings_load_defaults():
    settings = Settings.load()
    assert settings.frequency == "annual"
    assert settings.hours_method in {"ces", "nipa", "indexed"}
    assert settings.raw_dir.is_absolute()


def test_catalog_has_required_roles():
    catalog = SeriesCatalog.load()
    for role in ("gdp", "cfc", "compensation", "capital_stock", "hours_index"):
        assert role in catalog.roles
        assert catalog[role].provider == "fred"


def test_project_config_bundles_parts():
    config = ProjectConfig.load()
    assert config.settings.start_year == 1948
    assert "gdp" in config.catalog.roles


def test_cli_info_runs(capsys):
    exit_code = main(["info"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Moseley's aggregate identities" in captured.out
    assert "GDPA" in captured.out
