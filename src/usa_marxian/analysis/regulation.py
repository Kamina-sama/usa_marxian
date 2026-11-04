"""Does the aggregate rate of profit regulate industry rates?

Moseley's price equation, ``PP_i = K_i + R·M_i``, presupposes that the aggregate
rate ``R = ΣS/ΣM`` disciplines industry rates through capital mobility. Without
that, ``R`` is an arithmetic average and the good fit of the price equation can
be produced by a common markup instead.

Three tests, each able to fail:

1. **Convergence** — do industry rates move toward ``R``?
2. **Identification** — is that convergence to ``R``, or reversion to each
   industry's own mean? With two-way fixed effects the two regressors are
   collinear, so the convergence coefficient cannot tell them apart. This
   module reports that rather than reporting a number that looks like evidence.
3. **Mechanism** — does capital flow toward industries earning above ``R``?
   That is the channel the theory names, and it is not mechanically tied to
   measurement noise.

The dispersion of rates is reported alongside, because a regulating rate should
narrow dispersion over time.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from linearmodels.panel import PanelOLS


def build_regulation_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """Profit on capital advanced, the aggregate rate, and the gap."""
    required = {"year", "industry_code", "S_net", "M"}
    missing = sorted(required - set(panel.columns))
    if missing:
        raise KeyError(f"panel is missing columns: {', '.join(missing)}")

    frame = panel.loc[:, [*sorted(required), *(
        ["is_market"] if "is_market" in panel.columns else []
    )]].copy()
    if "is_market" in frame.columns:
        frame = frame.loc[frame["is_market"]]
    frame["r"] = frame["S_net"] / frame["M"]
    aggregate = frame.groupby("year").apply(
        lambda block: block["S_net"].sum() / block["M"].sum(),
        include_groups=False,
    )
    frame["R"] = frame["year"].map(aggregate)
    frame["gap"] = frame["r"] - frame["R"]
    return frame.sort_values(["industry_code", "year"]).reset_index(drop=True)


def dispersion_by_year(panel: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional dispersion of industry rates, year by year."""
    grouped = panel.groupby("year")
    table = grouped.apply(
        lambda block: pd.Series(
            {
                "n": float(len(block)),
                "R": float(block["S_net"].sum() / block["M"].sum()),
                "cv": float(block["r"].std() / block["r"].mean()),
                "iqr": float(block["r"].quantile(0.75) - block["r"].quantile(0.25)),
                "p90_p10": float(
                    block["r"].quantile(0.90) - block["r"].quantile(0.10)
                ),
                "mean_abs_gap": float(block["gap"].abs().mean()),
            }
        ),
        include_groups=False,
    )
    return table


def _panel_fit(frame: pd.DataFrame, dependent: str, regressor: str):
    data = frame.dropna(subset=[dependent, regressor]).set_index(
        ["industry_code", "year"]
    )
    model = PanelOLS(
        data[dependent],
        data[[regressor]],
        entity_effects=True,
        time_effects=True,
    )
    return model.fit(cov_type="clustered", cluster_entity=True)


def _half_life(beta: float) -> float:
    if -1.0 < beta < 0.0:
        return float(-np.log(2) / np.log(1 + beta))
    return float("nan")


def convergence_test(panel: pd.DataFrame) -> dict:
    """Movement of industry rates toward the aggregate, and its identification."""
    frame = panel.copy()
    grouped = frame.groupby("industry_code", group_keys=False)
    frame["dr"] = grouped["r"].diff()
    frame["gap_lag"] = grouped["gap"].shift(1)
    frame["mean_r"] = grouped["r"].transform("mean")
    frame["dev_own"] = grouped["r"].shift(1) - frame["mean_r"]

    toward_R = _panel_fit(frame, "dr", "gap_lag")
    toward_own = _panel_fit(frame, "dr", "dev_own")
    beta = float(toward_R.params["gap_lag"])

    # With entity and time effects, (r_{t-1} - R_{t-1}) and (r_{t-1} - mean_i)
    # differ only by a component that is additive in entity and time, so they
    # are absorbed into the effects. Identical coefficients are the symptom.
    identical = abs(
        beta - float(toward_own.params["dev_own"])
    ) < 1e-8 and abs(
        float(toward_R.std_errors["gap_lag"])
        - float(toward_own.std_errors["dev_own"])
    ) < 1e-8

    return {
        "beta_toward_R": beta,
        "std_error": float(toward_R.std_errors["gap_lag"]),
        "p_value": float(toward_R.pvalues["gap_lag"]),
        "half_life_years": _half_life(beta),
        "beta_toward_own_mean": float(toward_own.params["dev_own"]),
        "identified": not identical,
        "nobs": int(toward_R.nobs),
        "note": (
            "Coefficients on the gap to R and on the deviation from the "
            "industry's own mean are identical, because two-way fixed effects "
            "absorb the difference. This regression cannot distinguish "
            "regulation by R from ordinary mean reversion."
            if identical
            else "The two specifications differ, so R carries separate information."
        ),
    }


def capital_mobility_test(
    panel: pd.DataFrame, state: pd.DataFrame
) -> dict:
    """Does investment flow toward industries earning above the aggregate rate?"""
    merged = panel.merge(
        state.loc[:, ["year", "industry_code", "investment", "capital"]],
        on=["year", "industry_code"],
        how="left",
    )
    merged["inv_rate"] = merged["investment"] / merged["capital"]
    grouped = merged.groupby("industry_code", group_keys=False)
    merged["inv_rate_next"] = grouped["inv_rate"].shift(-1)
    merged["gap_lag"] = grouped["gap"].shift(1)

    result = _panel_fit(merged, "inv_rate_next", "gap_lag")
    beta = float(result.params["gap_lag"])
    p_value = float(result.pvalues["gap_lag"])
    return {
        "beta": beta,
        "std_error": float(result.std_errors["gap_lag"]),
        "p_value": p_value,
        "nobs": int(result.nobs),
        "supported": bool(beta > 0 and p_value < 0.05),
    }


def persistence_test(panel: pd.DataFrame) -> dict:
    """Are deviations from R persistent? 1.0 would mean never closing."""
    frame = panel.copy()
    grouped = frame.groupby("industry_code", group_keys=False)
    frame["abs_gap"] = frame["gap"].abs()
    frame["abs_gap_next"] = grouped["abs_gap"].shift(-1)
    result = _panel_fit(frame, "abs_gap_next", "abs_gap")
    return {
        "beta": float(result.params["abs_gap"]),
        "p_value": float(result.pvalues["abs_gap"]),
        "nobs": int(result.nobs),
    }


def run_regulation_tests(
    panel: pd.DataFrame,
    state: pd.DataFrame | None = None,
) -> dict:
    """Assemble the convergence, mechanism and dispersion results."""
    regulation = build_regulation_panel(panel)
    dispersion = dispersion_by_year(regulation)
    convergence = convergence_test(regulation)
    persistence = persistence_test(regulation)

    years = dispersion.index.to_numpy(dtype=float)
    cv_trend = float(np.polyfit(years, np.log(dispersion["cv"].to_numpy()), 1)[0])
    iqr_trend = float(np.polyfit(years, dispersion["iqr"].to_numpy(), 1)[0])

    mobility = (
        capital_mobility_test(regulation, state) if state is not None else None
    )

    narrowing = cv_trend < 0 and convergence["identified"]
    if not narrowing:
        verdict = (
            "Industry profit rates do not converge on the aggregate rate in any "
            "way this data can identify. Dispersion is flat or rising "
            f"(CV trend {100 * cv_trend:+.2f}%/yr, IQR trend "
            f"{iqr_trend * 100:+.2f} pp/yr), and the apparent convergence "
            "coefficient is indistinguishable from mean reversion."
        )
    else:
        verdict = (
            "Industry profit rates converge toward the aggregate rate and "
            "dispersion narrows, which supports treating R as a regulating "
            "average."
        )
    if mobility is not None and not mobility["supported"]:
        verdict += (
            " There is no detectable capital-mobility response to support the "
            f"mechanism (beta {mobility['beta']:+.4f}, p={mobility['p_value']:.3f}); "
            "a null here is consistent with the mechanism being absent, and also "
            "with other forces offsetting it."
        )

    return {
        "sample": {
            "start_year": int(regulation["year"].min()),
            "end_year": int(regulation["year"].max()),
            "n_industries": int(regulation["industry_code"].nunique()),
        },
        "dispersion": dispersion.reset_index().to_dict(orient="records"),
        "dispersion_trend": {"cv": cv_trend, "iqr": iqr_trend},
        "convergence": convergence,
        "persistence": persistence,
        "capital_mobility": mobility,
        "verdict": verdict,
    }


def write_outputs(panel: pd.DataFrame, result: dict, output_dir: Path) -> dict[str, Path]:
    """Persist the dispersion table and the summary."""
    import json

    tables = output_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)

    dispersion_path = tables / "profit_rate_regulation.csv"
    pd.DataFrame(result["dispersion"]).to_csv(dispersion_path, index=False)

    json_path = output_dir / "regulation.json"
    with json_path.open("w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, default=float)

    return {"dispersion": dispersion_path, "json": json_path}
