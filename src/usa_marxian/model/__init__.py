"""Marxian model objects: MELT, aggregates and distribution."""

from __future__ import annotations

from .equalities import check_two_equalities, profit_rate_decomposition
from .industries import add_industry_ratios, industry_report, year_summary
from .melt import melt_summary, melt_trend
from .robustness import DEFAULT_SPECS, Spec, run_specifications

__all__ = [
    "DEFAULT_SPECS",
    "Spec",
    "add_industry_ratios",
    "check_two_equalities",
    "industry_report",
    "melt_summary",
    "melt_trend",
    "profit_rate_decomposition",
    "run_specifications",
    "year_summary",
]
