"""Tests of the MELT against distribution — and why that test is empty.

This module implements design B of the value-theory test plan: *is the
monetary expression of labour time independent of distribution?*  Running it
honestly produces a negative result about the test itself, so the module is
built to detect its own vacuity and say so instead of reporting a p-value.

The identities, all exact by construction and verified numerically in
:func:`audit_melt_identities`:

    m         = N / L                    definition of the MELT
    P         = N / N_real               NDP deflator
    q         = N_real / L               real new value per hour
    => m      = P * q                    exact decomposition
    => m_real = q                        the "real MELT" is productivity
    => V/(mL) = V/N = wage share         distribution cancels out of m

Because ``log m ≡ log P + log q``, regressing ``Δlog m`` on ``Δlog P``,
``Δlog q`` and any distributional variable returns coefficients
``(1, 1, 0)`` with R² = 1 and a residual at machine precision.  A test that
cannot fail cannot inform.

What survives is a measurement question: is ``m`` a well-defined object at
all?  :func:`melt_concept_spread` and :func:`melt_hours_invariance` answer
that. The *level* is not identified — it is a choice of value-added concept
(1.32x across NDP, GDP, NNP and factor income) and of hours coverage (2.8x,
driven by the CES measure, which counts only private hours). The *growth
rate* is the robust object: close to 5%/yr under every concept, and stable to
a few hundredths of a percentage point once hours coverage is held fixed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

# Machine-precision residual below which the regression is declared vacuous.
DEGENERACY_TOLERANCE = 1e-9

MELT_CONCEPTS = {
    "melt_ndp": "net domestic product (default)",
    "melt_gdp": "gross domestic product",
    "melt_nnp": "net national product",
    "melt_nnp_factor": "net national factor income",
}

HOURS_SPECS = {
    "indexed": "nonfarm business index scaled to 2017 NIPA total",
    "nipa": "NIPA total-economy hours worked",
    "ces": "private employment x weekly hours (starts 2006)",
}


@dataclass
class MeltTest:
    """Outcome of the distribution test, including whether it was vacuous."""

    terms: list[str]
    coefficients: dict[str, float]
    r2: float
    max_abs_residual: float
    degenerate: bool
    nobs: int
    standard_errors: dict[str, float] = field(default_factory=dict)
    p_values: dict[str, float] = field(default_factory=dict)
    verdict: str = ""

    def as_dict(self) -> dict:
        return {
            "terms": list(self.terms),
            "coefficients": dict(self.coefficients),
            "standard_errors": dict(self.standard_errors),
            "p_values": dict(self.p_values),
            "r2": float(self.r2),
            "max_abs_residual": float(self.max_abs_residual),
            "degenerate": bool(self.degenerate),
            "nobs": int(self.nobs),
            "verdict": self.verdict,
        }


def _require(accounts: pd.DataFrame, columns: set[str]) -> None:
    missing = sorted(columns - set(accounts.columns))
    if missing:
        raise KeyError(f"accounts frame is missing columns: {', '.join(missing)}")


def audit_melt_identities(accounts: pd.DataFrame) -> dict:
    """Check the four identities that make the distribution test degenerate.

    Returns the maximum absolute deviation for each, in the units of the
    variable involved. Every entry should be at rounding error.
    """
    _require(
        accounts,
        {"N", "L", "melt", "melt_real", "new_value_real", "V", "wage_share"},
    )
    labour = accounts["L"]
    new_value = accounts["N"]
    real_new_value = accounts["new_value_real"]
    melt = accounts["melt"]

    deflator = new_value / real_new_value
    productivity = real_new_value / labour

    log_decomposition = (
        np.log(melt).diff()
        - np.log(deflator).diff()
        - np.log(productivity).diff()
    )

    return {
        "n_years": int(len(accounts)),
        "melt_from_N_over_L": float((melt - new_value / labour).abs().max()),
        "real_melt_equals_productivity": float(
            (accounts["melt_real"] - productivity).abs().max()
        ),
        "melt_equals_price_times_productivity": float(
            (melt - deflator * productivity).abs().max()
        ),
        "wage_share_equals_V_over_mL": float(
            (accounts["wage_share"] - accounts["V"] / (melt * labour)).abs().max()
        ),
        "log_decomposition_residual": float(log_decomposition.abs().max()),
    }


def test_melt_distribution(
    accounts: pd.DataFrame,
    *,
    tolerance: float = DEGENERACY_TOLERANCE,
) -> MeltTest:
    """Regress MELT growth on price, productivity and the wage share.

    The wage-share coefficient is the quantity of interest: the theory says
    the MELT is determined before distribution, so it should be zero. It is
    zero — but for the wrong reason, because ``log m = log P + log q`` holds
    exactly. The result object reports the degeneracy instead of a p-value.
    """
    _require(
        accounts,
        {"N", "L", "melt", "new_value_real", "wage_share"},
    )
    deflator = accounts["N"] / accounts["new_value_real"]
    productivity = accounts["new_value_real"] / accounts["L"]

    frame = pd.DataFrame(
        {
            "dm": np.log(accounts["melt"]).diff(),
            "dP": np.log(deflator).diff(),
            "dq": np.log(productivity).diff(),
            "dw": np.log(accounts["wage_share"]).diff(),
        }
    ).dropna()
    if len(frame) < 10:
        raise ValueError("not enough observations for the distribution test")

    terms = ["const", "dP", "dq", "dw"]
    design = np.column_stack(
        [np.ones(len(frame)), frame[["dP", "dq", "dw"]].to_numpy(dtype=float)]
    )
    target = frame["dm"].to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(design, target, rcond=None)
    residual = target - design @ beta
    max_abs_residual = float(np.abs(residual).max())
    total_variance = float(np.var(target))
    r2 = 1.0 - float(np.var(residual)) / total_variance if total_variance else float("nan")

    degenerate = max_abs_residual <= tolerance
    standard_errors: dict[str, float] = {}
    p_values: dict[str, float] = {}
    if not degenerate:
        from scipy import stats

        dof = max(len(frame) - design.shape[1], 1)
        sigma2 = float(residual @ residual) / dof
        covariance = sigma2 * np.linalg.pinv(design.T @ design)
        errors = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
        for name, value, error in zip(terms, beta, errors, strict=True):
            standard_errors[name] = float(error)
            if error > 0:
                p_values[name] = float(
                    2 * stats.t.sf(abs(value / error), dof)
                )

    if degenerate:
        verdict = (
            "Vacuous: log m = log P + log q holds exactly, so the wage-share "
            "coefficient is zero by construction. This test cannot fail and "
            "therefore cannot inform. See docs/value_theory.md."
        )
    else:
        wage_p = p_values.get("dw")
        if wage_p is None:
            verdict = "Regression estimated, but no usable wage-share standard error."
        elif wage_p < 0.05:
            verdict = (
                "The MELT moves with the wage share conditional on price and "
                "productivity, which contradicts the claim that it is "
                "determined before distribution."
            )
        else:
            verdict = (
                "No evidence that the MELT moves with distribution once price "
                "and productivity are controlled for."
            )

    return MeltTest(
        terms=terms,
        coefficients={
            name: float(value) for name, value in zip(terms, beta, strict=True)
        },
        r2=float(r2),
        max_abs_residual=max_abs_residual,
        degenerate=degenerate,
        nobs=int(len(frame)),
        standard_errors=standard_errors,
        p_values=p_values,
        verdict=verdict,
    )


def melt_concept_spread(accounts: pd.DataFrame) -> pd.DataFrame:
    """How much the MELT level depends on which value-added concept you pick.

    All four variants are exact ratios of the same accounts, differing only by
    depreciation and taxes. If there were one "value of money", they would be
    proportional. They are not, and the spread measures the ambiguity.
    """
    available = [name for name in MELT_CONCEPTS if name in accounts.columns]
    if not available:
        raise KeyError("no MELT variant columns found in the accounts frame")

    rows = []
    for name in available:
        series = accounts[name].replace([np.inf, -np.inf], np.nan).dropna()
        if len(series) < 3:
            continue
        slope = float(
            np.polyfit(series.index.to_numpy(dtype=float), np.log(series), 1)[0]
        )
        rows.append(
            {
                "concept": name,
                "definition": MELT_CONCEPTS[name],
                "mean": float(series.mean()),
                "latest": float(series.iloc[-1]),
                "log_trend_per_year": slope,
                "coefficient_of_variation": float(series.std() / series.mean()),
            }
        )

    table = pd.DataFrame(rows)
    if "melt_ndp" in available:
        base = float(accounts["melt_ndp"].dropna().iloc[-1])
        table["ratio_to_ndp_latest"] = table["latest"] / base
    return table.sort_values("latest", ascending=False).reset_index(drop=True)


def melt_hours_invariance(robustness: pd.DataFrame) -> pd.DataFrame:
    """Sensitivity of the MELT to the hours measure and the other switches.

    The theory treats the MELT as a property of money. If it is, changing how
    labour hours are counted should change its scale but not its trend. The
    table reports both so the reader can judge.
    """
    if "melt_mean" not in robustness.columns:
        raise KeyError("robustness table has no melt_mean column")

    columns = [
        column
        for column in ("name", "hours_method", "value_added", "melt_numerator")
        if column in robustness.columns
    ]
    table = robustness.loc[:, [*columns, "melt_mean", "melt_cv", "melt_trend"]].copy()
    table = table.dropna(subset=["melt_mean", "melt_trend"])
    table["melt_mean"] = table["melt_mean"].astype(float)
    table["melt_trend"] = table["melt_trend"].astype(float)
    return table.sort_values("melt_trend").reset_index(drop=True)


def summarise_measurement_spread(
    concepts: pd.DataFrame,
    hours: pd.DataFrame | None,
) -> dict:
    """Headline ranges for the only non-degenerate MELT questions."""
    summary = {
        "concept_level_min": float(concepts["latest"].min()),
        "concept_level_max": float(concepts["latest"].max()),
        "concept_spread_ratio": float(
            concepts["latest"].max() / concepts["latest"].min()
        ),
        "concept_trend_min": float(concepts["log_trend_per_year"].min()),
        "concept_trend_max": float(concepts["log_trend_per_year"].max()),
    }
    if hours is not None and not hours.empty:
        summary["spec_level_min"] = float(hours["melt_mean"].min())
        summary["spec_level_max"] = float(hours["melt_mean"].max())
        summary["spec_level_spread_ratio"] = (
            summary["spec_level_max"] / summary["spec_level_min"]
        )
        summary["spec_trend_min"] = float(hours["melt_trend"].min())
        summary["spec_trend_max"] = float(hours["melt_trend"].max())
        if "hours_method" in hours.columns:
            by_method = {}
            for method, group in hours.groupby("hours_method"):
                by_method[str(method)] = {
                    "n_specs": int(len(group)),
                    "level_min": float(group["melt_mean"].min()),
                    "level_max": float(group["melt_mean"].max()),
                    "trend_min": float(group["melt_trend"].min()),
                    "trend_max": float(group["melt_trend"].max()),
                }
            summary["by_hours_method"] = by_method
            covered = hours.loc[hours["hours_method"] != "ces"]
            if not covered.empty:
                summary["covered_trend_min"] = float(covered["melt_trend"].min())
                summary["covered_trend_max"] = float(covered["melt_trend"].max())
                summary["covered_level_min"] = float(covered["melt_mean"].min())
                summary["covered_level_max"] = float(covered["melt_mean"].max())
    return summary


def run_value_theory_tests(
    accounts: pd.DataFrame,
    robustness: pd.DataFrame | None = None,
) -> dict:
    """Run the MELT tests and return a JSON-safe summary."""
    identities = audit_melt_identities(accounts)
    distribution = test_melt_distribution(accounts)
    concepts = melt_concept_spread(accounts)
    hours = melt_hours_invariance(robustness) if robustness is not None else None
    summary = summarise_measurement_spread(concepts, hours)

    return {
        "identities": identities,
        "distribution": distribution.as_dict(),
        "concept_spread": concepts.to_dict(orient="records"),
        "hours_invariance": hours.to_dict(orient="records") if hours is not None else [],
        "measurement_spread": summary,
        "verdict": (
            "The MELT cannot be tested against distribution: m = P x q and "
            "V/(mL) = V/N are identities. What can be tested is whether the "
            "MELT is a well-defined object: its level is a choice of numerator "
            f"({summary['concept_spread_ratio']:.2f}x across value-added "
            "concepts) and of hours coverage, not a fact about money, while "
            "its growth rate is close to identical across concepts and about "
            f"{100 * summary['concept_trend_min']:.1f}%/yr throughout."
        ),
    }


def load_inputs(
    processed: Path,
    tables: Path,
) -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Read the artifacts the tests need, tolerating a missing robustness table."""
    accounts_path = processed / "accounts.csv"
    if not accounts_path.exists():
        raise FileNotFoundError(
            f"{accounts_path} not found; run `usa-marxian analyze` first"
        )
    accounts = pd.read_csv(accounts_path, index_col=0)
    robustness_path = tables / "robustness.csv"
    robustness = (
        pd.read_csv(robustness_path) if robustness_path.exists() else None
    )
    return accounts, robustness


def write_outputs(result: dict, output_dir: Path) -> dict[str, Path]:
    """Persist the test summary and the concept-spread table."""
    import json

    tables = output_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "value_theory.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, default=float)

    csv_path = tables / "melt_concept_spread.csv"
    pd.DataFrame(result["concept_spread"]).to_csv(csv_path, index=False)

    return {"json": json_path, "concepts": csv_path}
