import json

from data_shift_watch.cli import main


def test_cli_writes_markdown_report(tmp_path) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    output = tmp_path / "report.md"
    baseline.write_text("id,score\n1,10\n2,11\n3,10\n", encoding="utf-8")
    current.write_text("id,score\n4,40\n5,42\n6,41\n", encoding="utf-8")

    exit_code = main([str(baseline), str(current), "--output", str(output)])

    assert exit_code == 0
    assert "# Data Shift Report" in output.read_text(encoding="utf-8")


def test_cli_json_respects_include_and_exclude(tmp_path, capsys) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    baseline.write_text("id,score,segment\n1,10,a\n2,11,b\n", encoding="utf-8")
    current.write_text("id,score,segment\n3,12,a\n4,13,c\n", encoding="utf-8")

    exit_code = main(
        [
            str(baseline),
            str(current),
            "--format",
            "json",
            "--include",
            "score,segment",
            "--exclude",
            "score",
        ]
    )

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["checked_columns"] == ["segment"]


def test_cli_fail_on_high_returns_two(tmp_path) -> None:
    baseline = tmp_path / "baseline.csv"
    current = tmp_path / "current.csv"
    baseline.write_text("id,plan\n1,basic\n2,basic\n3,basic\n", encoding="utf-8")
    current.write_text("id,plan\n4,new\n5,new\n6,new\n", encoding="utf-8")

    exit_code = main([str(baseline), str(current), "--fail-on", "high"])

    assert exit_code == 2


def test_cli_reports_invalid_input(tmp_path, capsys) -> None:
    missing = tmp_path / "missing.csv"
    current = tmp_path / "current.csv"
    current.write_text("id,score\n1,10\n", encoding="utf-8")

    exit_code = main([str(missing), str(current)])

    assert exit_code == 1
    assert "file not found" in capsys.readouterr().err
