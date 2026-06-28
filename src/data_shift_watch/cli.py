from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from data_shift_watch import __version__
from data_shift_watch.core import analyze_shift
from data_shift_watch.errors import DataShiftError
from data_shift_watch.metrics import SEVERITY_RANK
from data_shift_watch.reporting import render_report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="data-shift-watch",
        description="Detect distribution shift between a baseline CSV and current CSV.",
    )
    parser.add_argument("baseline", help="baseline CSV used as the reference distribution")
    parser.add_argument("current", help="current CSV to compare against the baseline")
    parser.add_argument(
        "--format",
        choices=("markdown", "json"),
        default="markdown",
        help="report format",
    )
    parser.add_argument("-o", "--output", help="write the report to a file instead of stdout")
    parser.add_argument("--include", help="comma-separated columns to analyze")
    parser.add_argument("--exclude", help="comma-separated columns to skip")
    parser.add_argument(
        "--fail-on",
        choices=("none", "low", "medium", "high"),
        default="none",
        help="exit with code 2 when overall severity is at least this level",
    )
    parser.add_argument("--numeric-bins", type=int, default=10, help="numeric buckets for PSI")
    parser.add_argument(
        "--max-categories",
        type=int,
        default=12,
        help="top baseline categories tracked before grouping into OTHER",
    )
    parser.add_argument(
        "--include-id-like",
        action="store_true",
        help="include high-cardinality identifier-like columns such as id or customer_id",
    )
    parser.add_argument("--top", type=int, default=10, help="number of columns shown in markdown")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        report = analyze_shift(
            args.baseline,
            args.current,
            include=_parse_columns(args.include),
            exclude=_parse_columns(args.exclude),
            numeric_bins=args.numeric_bins,
            max_categories=args.max_categories,
            ignore_id_like=not args.include_id_like,
        )
        output = render_report(report, output_format=args.format, top=args.top)
        _write_output(output, args.output)
    except DataShiftError as exc:
        print(f"data-shift-watch: {exc}", file=sys.stderr)
        return 1

    if _should_fail(report.overall_severity, args.fail_on):
        return 2
    return 0


def _parse_columns(raw_value: str | None) -> set[str] | None:
    if raw_value is None:
        return None
    columns = {column.strip() for column in raw_value.split(",") if column.strip()}
    return columns or None


def _write_output(output: str, output_path: str | None) -> None:
    if output_path is None:
        print(output, end="")
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(output, encoding="utf-8")


def _should_fail(overall_severity: str, fail_on: str) -> bool:
    if fail_on == "none":
        return False
    return SEVERITY_RANK[overall_severity] >= SEVERITY_RANK[fail_on]
