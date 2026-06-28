from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal

Severity = Literal["ok", "low", "medium", "high"]
ColumnKind = Literal["numeric", "categorical", "schema"]
MetricValue = float | int | str | None


@dataclass(frozen=True)
class Thresholds:
    low_psi: float = 0.02
    medium_psi: float = 0.10
    high_psi: float = 0.25
    low_missing_delta: float = 0.02
    medium_missing_delta: float = 0.10
    high_missing_delta: float = 0.25
    medium_unseen_rate: float = 0.05
    high_unseen_rate: float = 0.20


@dataclass(frozen=True)
class ColumnShift:
    column: str
    kind: ColumnKind
    severity: Severity
    baseline_count: int
    current_count: int
    baseline_missing_rate: float
    current_missing_rate: float
    missing_delta: float
    psi: float | None
    metrics: dict[str, MetricValue] = field(default_factory=dict)
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class DriftReport:
    baseline_path: str
    current_path: str
    baseline_rows: int
    current_rows: int
    checked_columns: tuple[str, ...]
    overall_severity: Severity
    columns: tuple[ColumnShift, ...]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
