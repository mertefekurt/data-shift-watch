from __future__ import annotations

import json

from data_shift_watch.metrics import SEVERITY_RANK, round_float
from data_shift_watch.models import ColumnShift, DriftReport


def render_report(report: DriftReport, *, output_format: str, top: int) -> str:
    if output_format == "json":
        return json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n"
    if output_format == "markdown":
        return render_markdown(report, top=top)
    raise ValueError(f"unsupported output format: {output_format}")


def render_markdown(report: DriftReport, *, top: int) -> str:
    rows = sorted(
        report.columns,
        key=lambda column: (SEVERITY_RANK[column.severity], column.psi or 0.0),
        reverse=True,
    )
    limited_rows = rows[: max(1, top)]

    lines = [
        "# Data Shift Report",
        "",
        f"**Overall severity:** `{report.overall_severity}`",
        "",
        "| Input | Rows |",
        "| --- | ---: |",
        f"| Baseline `{report.baseline_path}` | {report.baseline_rows} |",
        f"| Current `{report.current_path}` | {report.current_rows} |",
        "",
        (
            f"Checked `{len(report.checked_columns)}` columns. "
            f"Showing the top `{len(limited_rows)}` by risk."
        ),
        "",
        "| Column | Type | Severity | PSI | Missing delta | Notes |",
        "| --- | --- | --- | ---: | ---: | --- |",
    ]

    for column in limited_rows:
        lines.append(_markdown_row(column))

    lines.extend(
        [
            "",
            "## Workflow",
            "",
            "1. infer column type from non-missing values",
            "2. compare numeric buckets or categorical frequencies",
            "3. combine PSI, missing-rate change, and unseen-category rate into a severity",
            "4. return exit code `2` when `--fail-on` is reached",
            "",
        ]
    )
    return "\n".join(lines)


def _markdown_row(column: ColumnShift) -> str:
    psi = "" if column.psi is None else str(round_float(column.psi))
    missing_delta = str(round_float(column.missing_delta))
    notes = "; ".join(column.notes)
    return (
        f"| `{column.column}` | {column.kind} | `{column.severity}` | {psi} | "
        f"{missing_delta} | {notes} |"
    )
