from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

from data_shift_watch.errors import DataShiftError


@dataclass(frozen=True)
class CsvDataset:
    path: Path
    columns: tuple[str, ...]
    rows: tuple[dict[str, str | None], ...]

    def values_for(self, column: str) -> list[str | None]:
        if column not in self.columns:
            raise KeyError(column)
        return [row.get(column) for row in self.rows]


def load_csv(path: str | Path) -> CsvDataset:
    csv_path = Path(path)
    if not csv_path.exists():
        raise DataShiftError(f"file not found: {csv_path}")
    if not csv_path.is_file():
        raise DataShiftError(f"not a file: {csv_path}")

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise DataShiftError(f"csv has no header row: {csv_path}")

            original_columns = tuple(reader.fieldnames)
            columns = tuple(column.strip() for column in original_columns)
            _validate_columns(columns, csv_path)

            rows: list[dict[str, str | None]] = []
            for raw_row in reader:
                row = {
                    clean_name: raw_row.get(original_name)
                    for original_name, clean_name in zip(original_columns, columns, strict=True)
                }
                rows.append(row)
    except UnicodeDecodeError as exc:
        raise DataShiftError(f"csv is not valid utf-8: {csv_path}") from exc
    except OSError as exc:
        raise DataShiftError(f"could not read csv: {csv_path}") from exc

    return CsvDataset(path=csv_path, columns=columns, rows=tuple(rows))


def _validate_columns(columns: tuple[str, ...], path: Path) -> None:
    if not columns:
        raise DataShiftError(f"csv has no columns: {path}")
    blank_columns = [index + 1 for index, column in enumerate(columns) if not column]
    if blank_columns:
        joined = ", ".join(str(index) for index in blank_columns)
        raise DataShiftError(f"csv has blank column names at positions: {joined}")

    seen: set[str] = set()
    duplicates: set[str] = set()
    for column in columns:
        if column in seen:
            duplicates.add(column)
        seen.add(column)
    if duplicates:
        joined = ", ".join(sorted(duplicates))
        raise DataShiftError(f"csv has duplicate columns: {joined}")
