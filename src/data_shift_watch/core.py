from __future__ import annotations

from pathlib import Path

from data_shift_watch.csv_loader import CsvDataset, load_csv
from data_shift_watch.errors import DataShiftError
from data_shift_watch.metrics import SEVERITY_RANK, analyze_column, non_missing_values
from data_shift_watch.models import DriftReport, Severity, Thresholds


def analyze_shift(
    baseline_path: str | Path,
    current_path: str | Path,
    *,
    include: set[str] | None = None,
    exclude: set[str] | None = None,
    thresholds: Thresholds | None = None,
    numeric_bins: int = 10,
    max_categories: int = 12,
    ignore_id_like: bool = True,
) -> DriftReport:
    if numeric_bins < 2:
        raise DataShiftError("numeric_bins must be at least 2")
    if max_categories < 1:
        raise DataShiftError("max_categories must be at least 1")

    baseline = load_csv(baseline_path)
    current = load_csv(current_path)
    checked_columns = _selected_columns(
        baseline,
        current,
        include=include,
        exclude=exclude,
        ignore_id_like=ignore_id_like,
    )
    if not checked_columns:
        raise DataShiftError("no columns selected for analysis")

    active_thresholds = thresholds or Thresholds()
    column_reports = tuple(
        analyze_column(
            column,
            baseline.values_for(column) if column in baseline.columns else None,
            current.values_for(column) if column in current.columns else None,
            thresholds=active_thresholds,
            numeric_bins=numeric_bins,
            max_categories=max_categories,
        )
        for column in checked_columns
    )
    overall = _overall_severity(column.severity for column in column_reports)

    return DriftReport(
        baseline_path=str(Path(baseline_path)),
        current_path=str(Path(current_path)),
        baseline_rows=len(baseline.rows),
        current_rows=len(current.rows),
        checked_columns=tuple(checked_columns),
        overall_severity=overall,
        columns=column_reports,
    )


def _selected_columns(
    baseline: CsvDataset,
    current: CsvDataset,
    *,
    include: set[str] | None,
    exclude: set[str] | None,
    ignore_id_like: bool,
) -> list[str]:
    ordered = list(baseline.columns)
    ordered.extend(column for column in current.columns if column not in baseline.columns)

    if include is not None:
        requested = [column for column in ordered if column in include]
        unknown = sorted(include.difference(ordered))
        if unknown:
            joined = ", ".join(unknown)
            raise DataShiftError(f"include references unknown columns: {joined}")
        ordered = requested

    if exclude:
        ordered = [column for column in ordered if column not in exclude]

    if include is None and ignore_id_like:
        ordered = [
            column for column in ordered if not _looks_like_identifier(column, baseline, current)
        ]

    return ordered


def _overall_severity(severities: object) -> Severity:
    return max(severities, key=lambda severity: SEVERITY_RANK[severity])


def _looks_like_identifier(column: str, baseline: CsvDataset, current: CsvDataset) -> bool:
    normalized = column.lower().replace("-", "_").replace(" ", "_")
    name_matches = (
        normalized in {"id", "uuid", "guid"}
        or normalized.endswith("_id")
        or normalized.endswith("_uuid")
        or normalized.endswith("_guid")
    )
    if not name_matches or column not in baseline.columns or column not in current.columns:
        return False

    baseline_values = non_missing_values(baseline.values_for(column))
    current_values = non_missing_values(current.values_for(column))
    return _unique_ratio(baseline_values) >= 0.9 and _unique_ratio(current_values) >= 0.9


def _unique_ratio(values: list[str]) -> float:
    if len(values) < 5:
        return 0.0
    return len(set(values)) / len(values)
