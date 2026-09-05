"""The tests this project already had before anyone had heard of Converge."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sensorlog.cli import main  # noqa: E402
from sensorlog.readings import Reading, parse_line, read_log  # noqa: E402
from sensorlog.report import render_report, render_summary  # noqa: E402

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "day.log"


def test_comments_and_blanks_are_skipped():
    assert parse_line("# a comment") is None
    assert parse_line("   ") is None


def test_a_reading_without_a_unit_still_parses():
    assert parse_line("panel_temperature 31.5") == Reading("panel_temperature", 31.5, "")


def test_the_sample_log_parses():
    readings = read_log(SAMPLE)
    assert len(readings) == 4
    assert readings[0].name == "ambient_light"


def test_report_marks_a_missing_unit():
    line = render_report([Reading("panel_temperature", 31.5)])
    assert line == "panel_temperature: 31.5 ?"


def test_summary_averages_the_commonest_unit():
    out = render_summary(read_log(SAMPLE))
    assert out.startswith("4 readings, mean ")
    assert out.endswith("lux over 2")


def test_cli_reports(capsys):
    assert main(["report", str(SAMPLE)]) == 0
    assert "ambient_light" in capsys.readouterr().out


def test_cli_rejects_a_bad_command(capsys):
    assert main(["frobnicate", str(SAMPLE)]) == 2
