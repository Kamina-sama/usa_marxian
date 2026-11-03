"""Command line interface.

Examples
--------
    usa-marxian info
    usa-marxian fetch
    usa-marxian analyze
    usa-marxian all
"""

from __future__ import annotations

import argparse
import sys

from .config import ProjectConfig
from .data.build import build_raw_panel, report_series_map
from .pipeline import run


def _load(args: argparse.Namespace) -> ProjectConfig:
    return ProjectConfig.load(settings_path=args.settings, catalog_path=args.catalog)


def _print_report(report: dict) -> None:
    sample = report["sample"]
    print(f"Sample: {sample['start_year']}-{sample['end_year']} "
          f"({sample['n_years']} years, hours_method={sample['hours_method']})")

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


def cmd_info(args: argparse.Namespace) -> int:
    config = _load(args)
    print("Moseley's aggregate identities")
    print("  P = C + N          value-price = constant capital + new value")
    print("  S = N - V          surplus-value = new value - variable capital")
    print("  R = S / M          general rate of profit")
    print("  N = m * L          new value = MELT * labour hours")
    print()
    print("Series mapping")
    mapping = report_series_map(config)
    for row in mapping.itertuples(index=False):
        optional = " (optional)" if row.optional else ""
        print(f"  {row.role:<22} {row.provider}:{row.series_id:<18} {row.units}{optional}")
    print()
    print("Data access: keyless by default (FRED CSV, BLS v1, BEA flat file).")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    config = _load(args)
    config.settings.ensure_directories()
    panel = build_raw_panel(config)
    path = config.settings.processed_dir / "raw_panel.csv"
    panel.to_csv(path, index_label="year")
    print(f"Raw panel: {panel.shape[0]} years x {panel.shape[1]} series -> {path}")
    print(panel.tail(3).to_string())
    return 0


def cmd_analyze(args: argparse.Namespace) -> int:
    config = _load(args)
    result = run(config=config, save=True, make_plots=not args.no_plots)
    _print_report(result.report)
    print()
    print(f"Accounts: {config.settings.processed_dir / 'accounts.csv'}")
    print(f"Tables:   {config.settings.output_dir / 'tables'}")
    if not args.no_plots:
        print(f"Figures:  {config.settings.output_dir / 'figures'}")
    return 0


def cmd_all(args: argparse.Namespace) -> int:
    return cmd_analyze(args)


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
    fetch.add_argument("--no-plots", action="store_true", help=argparse.SUPPRESS)

    analyze = sub.add_parser("analyze", help="build accounts and run the analysis")
    analyze.add_argument("--no-plots", action="store_true")

    all_cmd = sub.add_parser("all", help="fetch + analyze")
    all_cmd.add_argument("--no-plots", action="store_true")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "info": cmd_info,
        "fetch": cmd_fetch,
        "analyze": cmd_analyze,
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
