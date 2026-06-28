from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from math import log
from statistics import fmean, pstdev

from data_shift_watch.models import ColumnShift, Severity, Thresholds

MISSING_VALUES = {"", "na", "n/a", "nan", "none", "null"}
SEVERITY_RANK: dict[Severity, int] = {"ok": 0, "low": 1, "medium": 2, "high": 3}


def analyze_column(
    column: str,
    baseline_values: list[str | None] | None,
    current_values: list[str | None] | None,
    *,
    thresholds: Thresholds,
    numeric_bins: int,
    max_categories: int,
) -> ColumnShift:
    if baseline_values is None or current_values is None:
        return _schema_shift(column, baseline_values, current_values)

    baseline_missing = missing_rate(baseline_values)
    current_missing = missing_rate(current_values)
    missing_delta = abs(current_missing - baseline_missing)
    kind = infer_kind(baseline_values, current_values)

    if kind == "numeric":
        return _numeric_shift(
            column,
            baseline_values,
            current_values,
            thresholds=thresholds,
            numeric_bins=numeric_bins,
            baseline_missing=baseline_missing,
            current_missing=current_missing,
            missing_delta=missing_delta,
        )

    return _categorical_shift(
        column,
        baseline_values,
        current_values,
        thresholds=thresholds,
        max_categories=max_categories,
        baseline_missing=baseline_missing,
        current_missing=current_missing,
        missing_delta=missing_delta,
    )


def infer_kind(baseline_values: Iterable[str | None], current_values: Iterable[str | None]) -> str:
    baseline_clean = non_missing_values(baseline_values)
    current_clean = non_missing_values(current_values)
    if not baseline_clean or not current_clean:
        return "categorical"
    baseline_numeric = _numeric_ratio(baseline_clean) >= 0.95
    current_numeric = _numeric_ratio(current_clean) >= 0.95
    return "numeric" if baseline_numeric and current_numeric else "categorical"


def non_missing_values(values: Iterable[str | None]) -> list[str]:
    clean: list[str] = []
    for value in values:
        normalized = normalize_value(value)
        if normalized is not None:
            clean.append(normalized)
    return clean


def normalize_value(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return None if normalized.lower() in MISSING_VALUES else normalized


def missing_rate(values: list[str | None]) -> float:
    if not values:
        return 0.0
    missing_count = sum(1 for value in values if normalize_value(value) is None)
    return missing_count / len(values)


def severity_max(*values: Severity) -> Severity:
    return max(values, key=lambda value: SEVERITY_RANK[value])


def severity_from_psi(psi: float | None, thresholds: Thresholds) -> Severity:
    if psi is None:
        return "ok"
    if psi >= thresholds.high_psi:
        return "high"
    if psi >= thresholds.medium_psi:
        return "medium"
    if psi >= thresholds.low_psi:
        return "low"
    return "ok"


def severity_from_missing_delta(delta: float, thresholds: Thresholds) -> Severity:
    if delta >= thresholds.high_missing_delta:
        return "high"
    if delta >= thresholds.medium_missing_delta:
        return "medium"
    if delta >= thresholds.low_missing_delta:
        return "low"
    return "ok"


def severity_from_unseen_rate(rate: float, thresholds: Thresholds) -> Severity:
    if rate >= thresholds.high_unseen_rate:
        return "high"
    if rate >= thresholds.medium_unseen_rate:
        return "medium"
    return "ok"


def population_stability_index(
    expected_counts: list[int],
    actual_counts: list[int],
) -> float | None:
    if len(expected_counts) != len(actual_counts):
        raise ValueError("expected and actual counts must have equal length")
    if not expected_counts:
        return None

    expected_total = sum(expected_counts)
    actual_total = sum(actual_counts)
    if expected_total == 0 or actual_total == 0:
        return None

    smoothing = 1e-6
    bucket_count = len(expected_counts)
    score = 0.0
    for expected, actual in zip(expected_counts, actual_counts, strict=True):
        expected_pct = (expected + smoothing) / (expected_total + smoothing * bucket_count)
        actual_pct = (actual + smoothing) / (actual_total + smoothing * bucket_count)
        score += (actual_pct - expected_pct) * log(actual_pct / expected_pct)
    return score


def _schema_shift(
    column: str,
    baseline_values: list[str | None] | None,
    current_values: list[str | None] | None,
) -> ColumnShift:
    notes: list[str] = []
    if baseline_values is None:
        notes.append("column is new in current data")
    if current_values is None:
        notes.append("column is missing from current data")

    return ColumnShift(
        column=column,
        kind="schema",
        severity="high",
        baseline_count=len(baseline_values or []),
        current_count=len(current_values or []),
        baseline_missing_rate=missing_rate(baseline_values or []),
        current_missing_rate=missing_rate(current_values or []),
        missing_delta=abs(missing_rate(current_values or []) - missing_rate(baseline_values or [])),
        psi=None,
        notes=tuple(notes),
    )


def _numeric_shift(
    column: str,
    baseline_values: list[str | None],
    current_values: list[str | None],
    *,
    thresholds: Thresholds,
    numeric_bins: int,
    baseline_missing: float,
    current_missing: float,
    missing_delta: float,
) -> ColumnShift:
    baseline_numbers = [float(value) for value in non_missing_values(baseline_values)]
    current_numbers = [float(value) for value in non_missing_values(current_values)]
    edges = numeric_edges(baseline_numbers, numeric_bins)
    baseline_counts = numeric_bucket_counts(baseline_numbers, edges)
    current_counts = numeric_bucket_counts(current_numbers, edges)
    psi = population_stability_index(baseline_counts, current_counts)
    severity = severity_max(
        severity_from_psi(psi, thresholds),
        severity_from_missing_delta(missing_delta, thresholds),
    )

    metrics = {
        "baseline_mean": round_float(fmean(baseline_numbers)) if baseline_numbers else None,
        "current_mean": round_float(fmean(current_numbers)) if current_numbers else None,
        "baseline_std": round_float(pstdev(baseline_numbers)) if len(baseline_numbers) > 1 else 0.0,
        "current_std": round_float(pstdev(current_numbers)) if len(current_numbers) > 1 else 0.0,
        "bins": len(baseline_counts),
    }
    notes = _notes_for_missing_delta(missing_delta)

    return ColumnShift(
        column=column,
        kind="numeric",
        severity=severity,
        baseline_count=len(baseline_values),
        current_count=len(current_values),
        baseline_missing_rate=baseline_missing,
        current_missing_rate=current_missing,
        missing_delta=missing_delta,
        psi=psi,
        metrics=metrics,
        notes=notes,
    )


def _categorical_shift(
    column: str,
    baseline_values: list[str | None],
    current_values: list[str | None],
    *,
    thresholds: Thresholds,
    max_categories: int,
    baseline_missing: float,
    current_missing: float,
    missing_delta: float,
) -> ColumnShift:
    baseline_clean = non_missing_values(baseline_values)
    current_clean = non_missing_values(current_values)
    baseline_counts_raw = Counter(baseline_clean)
    current_counts_raw = Counter(current_clean)
    selected_categories = [
        category for category, _count in baseline_counts_raw.most_common(max(1, max_categories))
    ]

    baseline_counts = categorical_counts(baseline_counts_raw, selected_categories)
    current_counts = categorical_counts(current_counts_raw, selected_categories)
    psi = population_stability_index(baseline_counts, current_counts)
    baseline_categories = set(baseline_counts_raw)
    unseen_count = sum(1 for value in current_clean if value not in baseline_categories)
    unseen_rate = unseen_count / len(current_clean) if current_clean else 0.0
    severity = severity_max(
        severity_from_psi(psi, thresholds),
        severity_from_missing_delta(missing_delta, thresholds),
        severity_from_unseen_rate(unseen_rate, thresholds),
    )

    notes = list(_notes_for_missing_delta(missing_delta))
    if unseen_rate:
        notes.append(f"{round_float(unseen_rate)} of current values are unseen categories")

    return ColumnShift(
        column=column,
        kind="categorical",
        severity=severity,
        baseline_count=len(baseline_values),
        current_count=len(current_values),
        baseline_missing_rate=baseline_missing,
        current_missing_rate=current_missing,
        missing_delta=missing_delta,
        psi=psi,
        metrics={
            "baseline_unique": len(baseline_counts_raw),
            "current_unique": len(current_counts_raw),
            "unseen_rate": round_float(unseen_rate),
            "tracked_categories": len(selected_categories),
        },
        notes=tuple(notes),
    )


def numeric_edges(values: list[float], bin_count: int) -> list[float]:
    if not values:
        return []
    sorted_values = sorted(values)
    if sorted_values[0] == sorted_values[-1]:
        return [sorted_values[0], sorted_values[-1]]

    bins = max(2, bin_count)
    edges = [sorted_values[0]]
    for index in range(1, bins):
        position = int(round(index * (len(sorted_values) - 1) / bins))
        edges.append(sorted_values[position])
    edges.append(sorted_values[-1])

    deduped: list[float] = []
    for edge in edges:
        if not deduped or edge > deduped[-1]:
            deduped.append(edge)
    return deduped


def numeric_bucket_counts(values: list[float], edges: list[float]) -> list[int]:
    if not edges:
        return []
    bucket_count = max(1, len(edges) - 1)
    counts = [0 for _ in range(bucket_count)]
    if len(edges) == 1 or edges[0] == edges[-1]:
        counts[0] = len(values)
        return counts

    for value in values:
        bucket_index = _numeric_bucket_index(value, edges)
        counts[bucket_index] += 1
    return counts


def categorical_counts(raw_counts: Counter[str], selected_categories: list[str]) -> list[int]:
    selected = set(selected_categories)
    counts = [raw_counts.get(category, 0) for category in selected_categories]
    other_count = sum(count for category, count in raw_counts.items() if category not in selected)
    counts.append(other_count)
    return counts


def round_float(value: float, digits: int = 4) -> float:
    return round(float(value), digits)


def _numeric_ratio(values: list[str]) -> float:
    if not values:
        return 0.0
    numeric_count = 0
    for value in values:
        try:
            float(value)
        except ValueError:
            continue
        numeric_count += 1
    return numeric_count / len(values)


def _numeric_bucket_index(value: float, edges: list[float]) -> int:
    if value <= edges[0]:
        return 0
    last_bucket = len(edges) - 2
    if value >= edges[-1]:
        return last_bucket

    low = 0
    high = len(edges) - 1
    while low < high - 1:
        midpoint = (low + high) // 2
        if value < edges[midpoint]:
            high = midpoint
        else:
            low = midpoint
    return min(low, last_bucket)


def _notes_for_missing_delta(delta: float) -> tuple[str, ...]:
    if delta == 0:
        return ()
    return (f"missing rate changed by {round_float(delta)}",)
