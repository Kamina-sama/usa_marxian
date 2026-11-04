"""Command line interface.

Examples
--------
    usa-marxian info
    usa-marxian fetch [--refresh]
    usa-marxian analyze [--no-robustness] [--no-diagnostics]
    usa-marxian industries
    usa-marxian all
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from .config import ProjectConfig
from .data.build import build_raw_panel, report_series_map
from .pipeline import run, run_industries


def _load(args: argparse.Namespace) -> ProjectConfig:
    return ProjectConfig.load(settings_path=args.settings, catalog_path=args.catalog)


def _print_report(report: dict) -> None:
    sample = report["sample"]
    print(
        f"Sample: {sample['start_year']}-{sample['end_year']} "
        f"({sample['n_years']} years, hours_method={sample['hours_method']})"
    )

    melt = report["melt"]
    print(
        "MELT: mean {mean:.2f} USD/hour, trend {trend:+.2%}/year (p={p:.3f}), "
        "ADF p={adf:.3f}".format(
            mean=melt["mean"],
            trend=melt["trend_per_year"],
            p=melt["trend_p_value"],
            adf=melt["adf_p_value"],
        )
    )

    ltv = report["ltv"]
    print(
        "LTV, real N: slope on log L = {slope:.3f} (95% CI {lo:.3f} to {hi:.3f}); "
        "p(slope=1)={p:.3f}; cointegration p={cp:.3f}".format(
            slope=ltv["slope"],
            lo=ltv["ci_low"],
            hi=ltv["ci_high"],
            p=ltv["p_value_slope_one"],
            cp=ltv["coint_p"],
        )
    )
    if "ltv_nominal" in report:
        nominal = report["ltv_nominal"]
        print(
            "LTV, nominal N: slope = {slope:.3f}; p(slope=1)={p:.3f}".format(
                slope=nominal["slope"], p=nominal["p_value_slope_one"]
            )
        )

    profit = report["profit_rate"]
    print(
        "Rate of profit: {first:.1%} in {fy} -> {last:.1%} in {ly} "
        "(mean {mean:.1%})".format(
            first=profit["first_value"],
            fy=profit["first_year"],
            last=profit["last_value"],
            ly=profit["last_year"],
            mean=profit["mean"],
        )
    )

    check = report.get("property_income", {})
    if check:
        print(
            "Property-income check: mean ratio to S = {ratio:.3f}; "
            "mean gap = {gap:.1f} bn ({pct:+.1f}% of S)".format(
                ratio=check["mean_ratio"],
                gap=check["mean_gap_bn"],
                pct=check["mean_gap_pct_of_S"],
            )
        )

    ranges = report.get("robustness_ranges", [])
    if ranges:
        summary = {row["metric"]: row for row in ranges}
        if "ltv_slope" in summary:
            row = summary["ltv_slope"]
            print(f"Robustness: LTV slope ranges {row['min']:.3f} to {row['max']:.3f}")
        if "rate_profit_last" in summary:
            row = summary["rate_profit_last"]
            print(
                "Robustness: last-year profit rate ranges "
                f"{row['min']:.1%} to {row['max']:.1%}"
            )

    gravitation = report.get("gravitation", {})
    long_run = gravitation.get("long_run") if isinstance(gravitation, dict) else None
    if long_run:
        long_dev = long_run["deviation"]
        long_ecm = long_run["error_correction"]
        long_metrics = {
            int(row["horizon"]): row
            for row in long_run["forecast_metrics"]
            if row["model"] == "pp"
        }
        print(
            "Long-run PP: mean abs {mae:.1%}; half-life {hl:.1f}y; "
            "ECM GO beta={b:.3f} (p={p:.3f})".format(
                mae=long_dev["mean_abs_d"],
                hl=long_dev["ar1_half_life_years"] or float("nan"),
                b=long_ecm["delta_log_GO"]["beta"],
                p=long_ecm["delta_log_GO"]["p_value"],
            )
        )
        if 1 in long_metrics:
            print(
                "Long-run PP forecast, 1y log RMSE: PP {pp:.3f} vs naive {nv:.3f}".format(
                    pp=long_metrics[1]["rmse_log"],
                    nv=next(
                        (
                            row["rmse_log"]
                            for row in long_run["forecast_metrics"]
                            if row["horizon"] == 1 and row["model"] == "naive"
                        ),
                        float("nan"),
                    ),
                )
            )

    diagnostics = report.get("diagnostics", [])
    if diagnostics:
        for row in diagnostics:
            if row["block"] == "ltv_break_scan":
                print(
                    "Break scan: largest Chow F at {year} (F={f:.2f}, p={p:.3f})".format(
                        year=str(row["detail"]).split("=")[-1],
                        f=row["statistic"],
                        p=row["p_value"],
                    )
                )


def cmd_info(args: argparse.Namespace) -> int:
    config = _load(args)
    print("Moseley's aggregate identities")
    print("  P = C + N          value-price = constant capital + new value")
    print("  S = N - V          surplus-value = new value - variable capital")
    print("  R = S / M          general rate of profit")
    print("  N = m * L          new value = MELT * labour hours")
    print("  PP_i = K_i + R M_i price of production of industry i")
    print()
    print("Accounting layers")
    print("  macro:      NIPA net value added, property-income check")
    print("  robustness: NDP/NNP, nonresidential/total capital, hours methods")
    print("  industry:   BEA summary Use table, 71 industries, 1998-2023")
    print()
    print("Series mapping")
    mapping = report_series_map(config)
    for row in mapping.itertuples(index=False):
        optional = " (optional)" if row.optional else ""
        print(f"  {row.role:<24} {row.provider}:{row.series_id:<18} {row.units}{optional}")
    print()
    print("Data access: keyless by default (FRED CSV, BLS v1, BEA flat file, BEA IO zip).")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    config = _load(args)
    config.settings.ensure_directories()
    panel = build_raw_panel(config, refresh=args.refresh)
    path = config.settings.processed_dir / "raw_panel.csv"
    panel.to_csv(path, index_label="year")
    print(f"Raw panel: {panel.shape[0]} years x {panel.shape[1]} series -> {path}")
    print(panel.tail(3).to_string())
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    config = _load(args)
    result = run(
        config=config,
        save=True,
        make_plots=not args.no_plots,
        with_robustness=not args.no_robustness,
        with_diagnostics=not args.no_diagnostics,
        refresh=args.refresh,
    )
    _print_report(result.report)
    print()
    print(f"Accounts: {config.settings.processed_dir / 'accounts.csv'}")
    print(f"Tables:   {config.settings.output_dir / 'tables'}")
    if not args.no_plots:
        print(f"Figures:  {config.settings.output_dir / 'figures'}")
    return 0


def _print_gravitation(gravitation: dict) -> None:
    if not gravitation:
        return
    deviation = gravitation["deviation"]
    adjustment = gravitation["error_correction"]
    half_life = deviation["ar1_half_life_years"]
    half_life_text = f"{half_life:.1f}" if half_life is not None else "n/a"
    print("Gravitation tests")
    print(
        "  deviations: mean abs {mean:.1%}; within 25% = {band:.1%}; "
        "autocorrelation {ac:.2f}; half-life {hl} years".format(
            mean=deviation["mean_abs_d"],
            band=deviation["share_within_25pct"],
            ac=deviation["autocorrelation_lag1"],
            hl=half_life_text,
        )
    )
    print(
        "  ECM: GO adjusts to PP with beta={go:+.3f} (p={gop:.3f}); "
        "PP adjusts to GO with beta={pp:+.3f} (p={ppp:.3f})".format(
            go=adjustment["delta_log_GO"]["beta"],
            gop=adjustment["delta_log_GO"]["p_value"],
            pp=adjustment["delta_log_PP"]["beta"],
            ppp=adjustment["delta_log_PP"]["p_value"],
        )
    )
    metrics = pd.DataFrame(gravitation["forecast_metrics"])
    for horizon in sorted(metrics["horizon"].unique()):
        rows = metrics.loc[metrics["horizon"] == horizon].sort_values("rmse_log")
        values = ", ".join(
            f"{row.model} {row.rmse_log:.3f}" for row in rows.itertuples(index=False)
        )
        print(f"  forecast log RMSE, {int(horizon)}y: {values}")
    print(f"  verdict: {gravitation['verdict']}")


def cmd_industries(args: argparse.Namespace) -> int:
    config = _load(args)
    result = run_industries(
        config=config,
        save=True,
        make_plots=not args.no_plots,
        refresh=args.refresh,
        with_gravitation=not args.no_gravitation,
    )
    report = result.report
    state = report.get("state_space")
    if state:
        print(
            "State space: {n} industries x {y} years; "
            "p, q, k, I, u, w, l and {m} annual matrices".format(
                n=state["n_industries"],
                y=state["n_years"],
                m=state["n_matrices"],
            )
        )
    stock_flow = report.get("stock_flow")
    if stock_flow:
        metrics = {row["variable"]: row for row in stock_flow["metrics"]}
        print(
            "Stock-flow fit: price RMSE {p:.3f}, quantity RMSE {q:.3f}, "
            "capital RMSE {k:.3f}".format(
                p=metrics["price"]["rmse_log"],
                q=metrics["quantity"]["rmse_log"],
                k=metrics["capital"]["rmse_log"],
            )
        )
    latest = report["latest"]
    means = report["sample_means"]
    print(
        "Industries: {n} industries, {start}-{end}; latest {year}; "
        "basis={basis}, M proxy={proxy}".format(
            n=report["n_industries"],
            start=report["sample_start"],
            end=report["sample_end"],
            year=report["latest_year"],
            basis=report["surplus_basis"],
            proxy=report["capital_proxy"],
        )
    )
    print(
        "Latest market industries: R = S/M = {r:.1%}; CV of r_i = {cv:.3f}; "
        "p90/p10 = {p:.2f}; MAE(PP vs GO) = {mae:.1f}%; corr = {corr:.3f}".format(
            r=latest["R_benchmark_market"],
            cv=latest["rate_weighted_cv_market"],
            p=latest["rate_p90_p10_market"],
            mae=latest["mae_pct_PP_market"],
            corr=latest["corr_PP_market"],
        )
    )
    print(
        "Full sample (incl. government and housing): R = {r:.1%}; "
        "CV = {cv:.3f}; p90/p10 = {p:.2f}".format(
            r=latest["R_benchmark"],
            cv=latest["rate_weighted_cv"],
            p=latest["rate_p90_p10"],
        )
    )
    print(
        "Full sample means: CV = {cv:.3f}; MAE(PP) = {mae:.1f}%; "
        "MAE(PP_V) = {maev:.1f}%; share within 25% = {share:.1%}".format(
            cv=means["rate_weighted_cv"],
            mae=means["mae_pct_PP"],
            maev=means["mae_pct_PP_V"],
            share=means["share_within_25pct_PP"],
        )
    )
    print(
        "Market sample means: p90/p10 = {p:.2f}; MAE(PP) = {mae:.1f}%; "
        "MAE(PP_long) = {mael:.1f}%; share within 25% = {share:.1%}".format(
            p=means["rate_p90_p10_market"],
            mae=means["mae_pct_PP_market"],
            mael=means["mae_pct_PP_long_market"],
            share=means["share_within_25pct_PP_market"],
        )
    )
    emp = report.get("employment")
    if emp:
        print(
            "Employment: {n} industries FTE-based hours; total {h:.1f} bn; "
            "reconciliation gap {g:.2e}%".format(
                n=emp["n_industries"],
                h=emp["total_hours_bn"],
                g=emp["gap_pct"],
            )
        )
    real = report.get("real")
    if real:
        print(
            "Real accounts: R_real market = {r:.1%}; CV of r_real = {cv:.3f} "
            "(2017 input deflator)".format(
                r=real["R_real_market"], cv=real["r_real_weighted_cv_market"]
            )
        )
    comparison = report.get("benchmark_comparison", [])
    market_rows = [
        row for row in comparison if str(row.get("benchmark", "")).endswith("| market")
    ]
    if market_rows:
        print("Benchmark comparison (market industries):")
        for row in market_rows:
            name = str(row["benchmark"]).replace(" | market", "")
            print(
                f"  {name:<52} MAE {row['mae_pct']:5.1f}%  "
                f"corr {row['corr']:.3f}  slope {row['slope']:.3f}"
            )
    gravitation_rows = report.get("shaikh", {}).get("gravitation", [])
    if gravitation_rows:
        print("Gravitation comparison:")
        for row in gravitation_rows:
            print(
                f"  {row['benchmark']:<52} gap {row['mean_abs_d']:.1%}; "
                f"half-life {row['half_life_years']:.1f}y; "
                f"GO beta {row['beta_go']:+.3f} (p={row['p_go']:.3f}); "
                f"1y RMSE {row['forecast_pp_1y']:.3f} vs naive "
                f"{row['forecast_naive_1y']:.3f}"
            )
    diag = report.get("unit_prices", {}).get("diagnostics", {})
    if diag:
        revenue = diag.get("revenue_ratio", {})
        print(
            "Revenue ratio PP/GO: mean {m:.3f}, std {s:.3f}, "
            "p5/p95 {lo:.2f}/{hi:.2f}, within 10% {w:.1%}".format(
                m=revenue.get("mean_ratio", float("nan")),
                s=revenue.get("std_ratio", float("nan")),
                lo=revenue.get("p05_ratio", float("nan")),
                hi=revenue.get("p95_ratio", float("nan")),
                w=revenue.get("share_within_10pct", float("nan")),
            )
        )
        if not diag.get("within_sector_identified", True):
            print("Within-sector test: not identified (no within-sector price variation).")
        if not diag.get("measurement_identified", True):
            print("Measurement-error test: not identified (deflators constant within sector).")
    unit = report.get("unit_prices", {}).get("comparison", [])
    if unit:
        print("Unit prices (relative, normalised):")
        for row in unit:
            print(
                f"  {row['benchmark']:<38} log MAE {row['log_mae']:.3f}  "
                f"corr {row['corr']:.3f}  slope {row['slope']:.3f}"
            )
    long_run = report.get("gravitation", {}).get("long_run")
    if long_run:
        dev = long_run["deviation"]
        ecm = long_run["error_correction"]
        print(
            "Long-run PP (5y trailing): mean abs {mae:.1%}; half-life {hl:.1f}y; "
            "ECM GO beta={b:.3f} (p={p:.3f})".format(
                mae=dev["mean_abs_d"],
                hl=dev["ar1_half_life_years"] or float("nan"),
                b=ecm["delta_log_GO"]["beta"],
                p=ecm["delta_log_GO"]["p_value"],
            )
        )
        metrics = {
            (int(row["horizon"]), row["model"]): row["rmse_log"]
            for row in long_run["forecast_metrics"]
        }
        if (1, "pp") in metrics:
            print(
                "Long-run PP forecast, 1y/3y/5y log RMSE: "
                f"PP {metrics[(1, 'pp')]:.3f} / {metrics.get((3, 'pp'), float('nan')):.3f} / "
                f"{metrics.get((5, 'pp'), float('nan')):.3f} vs naive "
                f"{metrics.get((1, 'naive'), float('nan')):.3f} / "
                f"{metrics.get((3, 'naive'), float('nan')):.3f} / "
                f"{metrics.get((5, 'naive'), float('nan')):.3f}"
            )
    if means.get("real_N_growth") is not None:
        print(
            "Sector-deflated real growth ({start}-{end}): N {n:+.2f}%/yr, "
            "GO {go:+.2f}%/yr".format(
                start=means["real_start_year"],
                end=means["real_end_year"],
                n=100 * means["real_N_growth"],
                go=100 * means["real_GO_growth"],
            )
        )
    proxies = report.get("proxy_sensitivity", [])
    if proxies:
        print("Capital-proxy sensitivity (MAE of PP vs GO):")
        for row in proxies:
            print(
                "  {proxy:<12} {mae:.1f}%  corr={corr:.3f}".format(
                    proxy=row["capital_proxy"],
                    mae=row["mae_pct_PP"],
                    corr=row["corr_PP"],
                )
            )
    print()
    _print_gravitation(result.report.get("gravitation"))
    print()
    print(f"Panel:  {config.settings.processed_dir / 'industries.csv'}")
    print(f"Tables: {config.settings.output_dir / 'tables'}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    code = cmd_analyze(args)
    if code != 0:
        return code
    print()
    code = cmd_industries(args)
    if code != 0:
        return code
    if not args.no_plots:
        print()
        code = cmd_figures(args)
    if code != 0:
        return code
    print()
    code = cmd_value_tests(args)
    if code != 0:
        return code
    print()
    code = cmd_labour_power(args)
    if code != 0:
        return code
    print()
    return cmd_regulation(args)


def cmd_figures(args: argparse.Namespace) -> int:
    """Render the findings figures from artifacts already on disk."""
    from .viz.findings import build_findings_figures

    config = _load(args)
    written = build_findings_figures(config)
    print("Findings figures:")
    for name, path in written.items():
        print(f"  {name:<16} {path}")
    print()
    print("How to read them: docs/figures.md")
    return 0


def cmd_value_tests(args: argparse.Namespace) -> int:
    """Run the value-theory tests (design B: MELT against distribution)."""
    from .model.value_theory import (
        load_inputs,
        run_value_theory_tests,
        write_outputs,
    )

    config = _load(args)
    tables = config.settings.output_dir / "tables"
    accounts, robustness = load_inputs(config.settings.processed_dir, tables)
    result = run_value_theory_tests(accounts, robustness)
    paths = write_outputs(result, config.settings.output_dir)

    identities = result["identities"]
    print(f"MELT identity audit, {identities['n_years']} years (max abs deviation)")
    print(f"  m = N / L                      {identities['melt_from_N_over_L']:.1e}")
    print(
        "  m_real = real NDP per hour     "
        f"{identities['real_melt_equals_productivity']:.1e}"
    )
    print(
        "  m = P x q                      "
        f"{identities['melt_equals_price_times_productivity']:.1e}"
    )
    print(
        "  V / (m L) = wage share         "
        f"{identities['wage_share_equals_V_over_mL']:.1e}"
    )
    print(
        "  d log m - d log P - d log q    "
        f"{identities['log_decomposition_residual']:.1e}"
    )

    distribution = result["distribution"]
    print()
    if distribution["degenerate"]:
        print("Distribution test: VACUOUS")
        print(
            "  R2 = {r2:.6f}; max |residual| = {resid:.1e}; n = {n}".format(
                r2=distribution["r2"],
                resid=distribution["max_abs_residual"],
                n=distribution["nobs"],
            )
        )
        fit = ", ".join(
            f"{name} {value:+.3f}"
            for name, value in distribution["coefficients"].items()
        )
        print(f"  coefficients: {fit}")
        print(
            "  The wage-share coefficient is zero by construction, "
            "not by evidence."
        )
    else:
        print("Distribution test: identified")
        print(f"  R2 = {distribution['r2']:.3f}; n = {distribution['nobs']}")
        for name, value in distribution["coefficients"].items():
            error = distribution["standard_errors"].get(name)
            p_value = distribution["p_values"].get(name)
            if error is None:
                print(f"  {name:<8} {value:+.3f}")
            else:
                print(f"  {name:<8} {value:+.3f}  (se {error:.3f}, p={p_value:.3f})")

    print()
    print(f"MELT level by value-added concept (latest {accounts.index.max()})")
    for row in result["concept_spread"]:
        print(
            f"  {row['concept']:<16} {row['latest']:7.2f}  "
            f"{100 * row['log_trend_per_year']:5.2f}%/yr  "
            f"{row['ratio_to_ndp_latest']:.2f}x NDP"
        )

    spread = result["measurement_spread"]
    print()
    print(
        "Concept spread: {ratio:.2f}x in level, {lo:.2f}-{hi:.2f}%/yr in growth".format(
            ratio=spread["concept_spread_ratio"],
            lo=100 * spread["concept_trend_min"],
            hi=100 * spread["concept_trend_max"],
        )
    )
    if "spec_level_spread_ratio" in spread:
        print(
            "Hours/coverage spread: {ratio:.2f}x in level, "
            "{lo:.2f}-{hi:.2f}%/yr in growth".format(
                ratio=spread["spec_level_spread_ratio"],
                lo=100 * spread["spec_trend_min"],
                hi=100 * spread["spec_trend_max"],
            )
        )
    print()
    print(f"verdict: {result['verdict']}")
    print()
    print(f"JSON:   {paths['json']}")
    print(f"Table:  {paths['concepts']}")
    print("Docs:   docs/value_theory.md")
    return 0


def cmd_labour_power(args: argparse.Namespace) -> int:
    """Build the value of labour power and test whether it is identified."""
    from .model.value_of_labour_power import (
        build_basket_panel,
        run_volp_tests,
        write_outputs,
    )

    config = _load(args)
    panel = build_basket_panel(config.settings.processed_dir)
    result = run_volp_tests(panel)
    paths = write_outputs(panel, result, config.settings.output_dir)

    sample = result["sample"]
    print(
        "Value of labour power, {start}-{end}; the basket covers {cov:.1%} of "
        "personal consumption".format(
            start=sample["start_year"],
            end=sample["end_year"],
            cov=sample["mean_coverage"],
        )
    )
    coherence = result["coherence"]
    print(
        f"  Coherence sum(lambda F)/L  {coherence['first']:.3f} "
        f"({coherence['first_year']}) -> {coherence['last']:.3f} "
        f"({coherence['last_year']}), mean {coherence['mean']:.3f}"
    )
    labels = {
        "lambda_actual": "Basket labour content (actual)",
        "lambda_wage_financed": "Basket labour content (wage-financed)",
        "wage_share": "Wage share V / N",
        "wage_financed_ratio": "Wage-financed ratio to wage share",
        "price_to_value_ratio": "Price / labour value of the basket",
        "consumption_share_of_wage": "Consumption / wage bill",
    }
    for key, label in labels.items():
        trend = result["trends"][key]
        print(
            f"  {label:<40} {trend['first']:.3f} -> {trend['last']:.3f}  "
            f"{100 * trend['trend_per_year']:+.2f}%/yr "
            f"(p={trend['trend_p_value']:.3f})"
        )

    print()
    print("Price / labour value by final use:")
    for name, value in result["price_value_by_category"].items():
        print(f"  {name:<14} {value:.3f}")
    print(
        "  consumption below investment in "
        f"{result['gradient_years_consumption_below_investment']} of "
        f"{sample['n_years']} years"
    )
    print()
    print(f"verdict: {result['verdict']}")
    print()
    print(f"JSON:   {paths['json']}")
    print(f"Panel:  {paths['panel']}")
    print("Docs:   docs/value_theory.md")
    return 0


def cmd_regulation(args: argparse.Namespace) -> int:
    """Test whether the aggregate profit rate regulates industry rates."""
    from .analysis.regulation import run_regulation_tests, write_outputs

    config = _load(args)
    processed = config.settings.processed_dir
    panel = pd.read_csv(processed / "industries_shaikh.csv")
    state_path = processed / "state_space.csv"
    state = pd.read_csv(state_path) if state_path.exists() else None

    result = run_regulation_tests(panel, state)
    paths = write_outputs(panel, result, config.settings.output_dir)

    sample = result["sample"]
    print(
        f"Profit-rate regulation, {sample['start_year']}-{sample['end_year']}, "
        f"{sample['n_industries']} market industries"
    )
    trend = result["dispersion_trend"]
    print(
        f"  Dispersion of r_i        CV {100 * trend['cv']:+.2f}%/yr, "
        f"IQR {100 * trend['iqr']:+.2f} pp/yr"
    )
    conv = result["convergence"]
    print(
        f"  Convergence to R         beta {conv['beta_toward_R']:+.4f} "
        f"(p={conv['p_value']:.4f}), half-life {conv['half_life_years']:.1f}y"
    )
    print(
        f"  ... but to own mean      beta {conv['beta_toward_own_mean']:+.4f} "
        f"-> identified: {conv['identified']}"
    )
    print(f"  Persistence of |r - R|   {result['persistence']['beta']:.4f}")
    mobility = result["capital_mobility"]
    if mobility:
        print(
            f"  Capital mobility         {mobility['beta']:+.4f} "
            f"(p={mobility['p_value']:.3f}) -> supported: {mobility['supported']}"
        )
    print()
    print(f"verdict: {result['verdict']}")
    print()
    print(f"JSON:   {paths['json']}")
    print(f"Table:  {paths['dispersion']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="usa-marxian",
        description="Empirical tests of Moseley's macro-monetary interpretation, US data.",
    )
    parser.add_argument("--settings", default="config/settings.yaml")
    parser.add_argument("--catalog", default="config/series.yaml")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("info", help="show model identities and series mapping")

    fetch = sub.add_parser("fetch", help="download raw series into data/processed")
    fetch.add_argument("--refresh", action="store_true", help="ignore the cache")

    analyze = sub.add_parser("analyze", help="build accounts, robustness and diagnostics")
    analyze.add_argument("--no-plots", action="store_true")
    analyze.add_argument("--no-robustness", action="store_true")
    analyze.add_argument("--no-diagnostics", action="store_true")
    analyze.add_argument("--refresh", action="store_true", help="ignore the cache")

    industries = sub.add_parser("industries", help="build and analyse BEA industry accounts")
    industries.add_argument("--no-plots", action="store_true")
    industries.add_argument("--no-gravitation", action="store_true")
    industries.add_argument("--refresh", action="store_true", help="re-download the IO archive")

    all_cmd = sub.add_parser("all", help="macro analysis + industry analysis")
    all_cmd.add_argument("--no-plots", action="store_true")
    all_cmd.add_argument("--no-robustness", action="store_true")
    all_cmd.add_argument("--no-diagnostics", action="store_true")
    all_cmd.add_argument("--no-gravitation", action="store_true")
    all_cmd.add_argument("--refresh", action="store_true")

    figures = sub.add_parser(
        "figures", help="rebuild the findings figures from existing artifacts"
    )
    figures.add_argument(
        "--no-plots", action="store_true", help="accepted for symmetry; unused"
    )

    sub.add_parser(
        "value-tests",
        help="test the MELT against distribution and audit its identities",
    )

    sub.add_parser(
        "labour-power",
        help="build the value of labour power and test whether it is identified",
    )

    sub.add_parser(
        "regulation",
        help="test whether the aggregate profit rate regulates industry rates",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "info": cmd_info,
        "fetch": cmd_fetch,
        "analyze": cmd_analyze,
        "industries": cmd_industries,
        "figures": cmd_figures,
        "value-tests": cmd_value_tests,
        "labour-power": cmd_labour_power,
        "regulation": cmd_regulation,
        "all": cmd_all,
    }
    try:
        return handlers[args.command](args)
    except KeyboardInterrupt:
        return 130
    except Exception as exc:  # keep CLI output readable
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
