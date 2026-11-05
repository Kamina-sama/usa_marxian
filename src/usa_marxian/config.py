"""Typed configuration loading for the project."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, field_validator

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseModel):
    """Global pipeline settings, loaded from ``config/settings.yaml``."""

    model_config = ConfigDict(validate_default=True)

    frequency: Literal["annual"] = "annual"
    start_year: int = 1948
    end_year: int | None = None
    base_year: int = 2017
    hours_method: Literal["ces", "nipa", "indexed"] = "indexed"
    include_inventories: bool = True
    capital_proxy: Literal["fixed_assets", "working_capital"] = "working_capital"
    cache_max_age_days: int = 30
    raw_dir: Path = Path("data/raw")
    processed_dir: Path = Path("data/processed")
    output_dir: Path = Path("output")

    @field_validator("raw_dir", "processed_dir", "output_dir", mode="after")
    @classmethod
    def _resolve_relative_to_root(cls, value: Path) -> Path:
        return value if value.is_absolute() else PROJECT_ROOT / value

    @classmethod
    def load(cls, path: str | Path = "config/settings.yaml") -> Settings:
        path = Path(path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return cls(**data)

    def ensure_directories(self) -> None:
        for directory in (self.raw_dir, self.processed_dir, self.output_dir):
            directory.mkdir(parents=True, exist_ok=True)
        for sub in ("figures", "tables"):
            (self.output_dir / sub).mkdir(parents=True, exist_ok=True)


class SeriesSpec(BaseModel):
    """One raw data series and how to load it."""

    label: str
    provider: Literal["fred", "bls", "bea"]
    series_id: str
    units: str
    frequency: Literal["annual", "quarterly", "monthly"]
    agg: Literal["mean", "last", "sum"] = "mean"
    scale: float = 1.0
    optional: bool = False
    notes: str = ""


class SeriesCatalog(BaseModel):
    """Mapping of economic role -> raw series specification."""

    roles: dict[str, SeriesSpec]

    @classmethod
    def load(cls, path: str | Path = "config/series.yaml") -> SeriesCatalog:
        path = Path(path)
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        with path.open(encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return cls(**data)

    def __getitem__(self, role: str) -> SeriesSpec:
        return self.roles[role]

    def get(self, role: str) -> SeriesSpec | None:
        return self.roles.get(role)


class APIConfig(BaseModel):
    """Optional API credentials, read from the environment (never hard-coded)."""

    fred_api_key: str | None = None
    bea_api_key: str | None = None
    bls_api_key: str | None = None
    census_api_key: str | None = None

    @classmethod
    def from_env(cls) -> APIConfig:
        import os

        load_dotenv(PROJECT_ROOT / ".env")
        return cls(
            fred_api_key=os.getenv("FRED_API_KEY") or None,
            bea_api_key=os.getenv("BEA_API_KEY") or None,
            bls_api_key=os.getenv("BLS_API_KEY") or None,
            census_api_key=os.getenv("CENSUS_API_KEY") or None,
        )


class ProjectConfig(BaseModel):
    """Bundle of settings, catalog and credentials."""

    settings: Settings = Field(default_factory=Settings)
    catalog: SeriesCatalog
    api: APIConfig = Field(default_factory=APIConfig.from_env)

    @classmethod
    def load(
        cls,
        settings_path: str | Path = "config/settings.yaml",
        catalog_path: str | Path = "config/series.yaml",
    ) -> ProjectConfig:
        return cls(
            settings=Settings.load(settings_path),
            catalog=SeriesCatalog.load(catalog_path),
            api=APIConfig.from_env(),
        )
