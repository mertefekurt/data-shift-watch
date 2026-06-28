from data_shift_watch.core import analyze_shift
from data_shift_watch.metrics import (
    categorical_counts,
    infer_kind,
    numeric_bucket_counts,
    numeric_edges,
    population_stability_index,
)


def test_numeric_column_inference() -> None:
    assert infer_kind(["1", "2", "3"], ["4.5", "5.5"]) == "numeric"


def test_numeric_buckets_cover_out_of_range_values() -> None:
    edges = numeric_edges([1, 2, 3, 4, 5], 3)
    counts = numeric_bucket_counts([-10, 1, 3, 99], edges)
    assert sum(counts) == 4
    assert counts[0] >= 2
    assert counts[-1] >= 1


def test_population_stability_index_is_zero_for_same_distribution() -> None:
    assert population_stability_index([10, 20, 30], [10, 20, 30]) == 0


def test_categorical_counts_group_other_values() -> None:
    counts = categorical_counts({"basic": 3, "pro": 2, "team": 1}, ["basic", "pro"])
    assert counts == [3, 2, 1]


def test_analyze_shift_marks_missing_column_high(tmp_path) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    baseline.write_text("id,score,label\n1,10,a\n2,11,b\n", encoding="utf-8")
    current.write_text("id,score\n3,12\n4,13\n", encoding="utf-8")

    report = analyze_shift(baseline, current)
    label = next(column for column in report.columns if column.column == "label")

    assert label.kind == "schema"
    assert label.severity == "high"
    assert report.overall_severity == "high"


def test_analyze_shift_skips_identifier_like_columns_by_default(tmp_path) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    baseline.write_text(
        "customer_id,score\nc1,10\nc2,11\nc3,10\nc4,12\nc5,10\n",
        encoding="utf-8",
    )
    current.write_text(
        "customer_id,score\nc6,10\nc7,11\nc8,10\nc9,12\nc10,10\n",
        encoding="utf-8",
    )

    report = analyze_shift(baseline, current)

    assert "customer_id" not in report.checked_columns
    assert report.checked_columns == ("score",)
