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
    print("  industry:   BEA summary Use table, 71 industries, 1997-2023")
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


def cmd_industries(args: argparse.Namespace) -> int:
    config = _load(args)
    result = run_industries(
        config=config,
        save=True,
        make_plots=not args.no_plots,
        refresh=args.refresh,
    )
    report = result.report
    latest = report["latest"]
    means = report["sample_means"]
    print(
        "Industries: {n} industries, {start}-{end}; latest {year}".format(
            n=report["n_industries"],
            start=report["sample_start"],
            end=report["sample_end"],
            year=report["latest_year"],
        )
    )
    print(
        "Latest: cost-price mark-up = {r:.1%}; CV of r_i = {cv:.3f}; "
        "p90/p10 = {p:.2f}; MAE(PP_K vs GO) = {mae:.1f}%; corr = {corr:.3f}".format(
            r=latest["R_cost"],
            cv=latest["rate_weighted_cv"],
            p=latest["rate_p90_p10"],
            mae=latest["mae_pct_K"],
            corr=latest["corr_K"],
        )
    )
    print(
        "Sample means: CV = {cv:.3f}; MAE(PP_K) = {mae:.1f}%; "
        "MAE(PP_V) = {maev:.1f}%; share within 25% = {share:.1%}".format(
            cv=means["rate_weighted_cv"],
            mae=means["mae_pct_K"],
            maev=means["mae_pct_V"],
            share=means["share_within_25pct_K"],
        )
    )
    print(
        "Market industries only: CV = {cv:.3f}; MAE(PP_K) = {mae:.1f}%; "
        "share within 25% = {share:.1%}".format(
            cv=means["rate_weighted_cv_market"],
            mae=means["mae_pct_K_market"],
            share=means["share_within_25pct_K_market"],
        )
    )
    print(f"Panel:  {config.settings.processed_dir / 'industries.csv'}")
    print(f"Tables: {config.settings.output_dir / 'tables'}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    code = cmd_analyze(args)
    if code != 0:
        return code
    print()
    return cmd_industries(args)


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
    industries.add_argument("--refresh", action="store_true", help="re-download the IO archive")

    all_cmd = sub.add_parser("all", help="macro analysis + industry analysis")
    all_cmd.add_argument("--no-plots", action="store_true")
    all_cmd.add_argument("--no-robustness", action="store_true")
    all_cmd.add_argument("--no-diagnostics", action="store_true")
    all_cmd.add_argument("--refresh", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "info": cmd_info,
        "fetch": cmd_fetch,
        "analyze": cmd_analyze,
        "industries": cmd_industries,
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
