"""Command line: sales-lab run | summary | report."""

import argparse
import logging
import sys

from sales_lab.config import Settings
from sales_lab.errors import SalesLabError
from sales_lab.models import format_cents
from sales_lab.service import create_service


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sales-lab", description="Sales Automation Lab")
    parser.add_argument("-v", "--verbose", action="store_true", help="verbose logging")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("run", help="import the CSV into the database")
    commands.add_parser("summary", help="print total sales")
    commands.add_parser("report", help="write a per-category CSV report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    settings = Settings.from_env()
    service = create_service(settings)

    try:
        match args.command:
            case "run":
                result = service.import_file(
                    settings.input_path, settings.output_dir / "rejected.csv"
                )
                print(f"Read {result.read}, loaded {result.loaded}, rejected {result.rejected}")
            case "summary":
                summary = service.summary()
                print(
                    f"Orders: {summary.orders} | Units: {summary.units} | "
                    f"Categories: {summary.categories} | "
                    f"Revenue: {format_cents(summary.revenue_cents)} EUR"
                )
            case "report":
                path = service.write_report(settings.output_dir / "category_report.csv")
                print(f"Report: {path}")
    except (SalesLabError, FileNotFoundError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
