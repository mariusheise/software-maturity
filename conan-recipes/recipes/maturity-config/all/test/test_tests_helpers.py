"""Layer 1: the test report in _tests.py, without a Conan home."""

import json
import re

import _tests

# Shapes taken from real ctest --output-junit output (CMake 4.2).
JUNIT = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Linux-c++" tests="6" failures="2" disabled="1" skipped="1" time="0">
  <testcase name="Mean.SingleValue" classname="Mean.SingleValue" time="0.0015" status="run">
    <properties/><system-out>[       OK ] Mean.SingleValue (0 ms)</system-out>
  </testcase>
  <testcase name="Slow&lt;T&gt; &amp; co" classname="x" time="0.25" status="run">
    <system-out>ok</system-out>
  </testcase>
  <testcase name="Mean.Broken" classname="Mean.Broken" time="0.004" status="fail">
    <failure message="Failed"/><system-out>expected 1 got 2 &lt;&amp;&gt;</system-out>
  </testcase>
  <testcase name="Mean.Skipped" classname="Mean.Skipped" time="0.001" status="notrun">
    <skipped message="SKIP_REGULAR_EXPRESSION_MATCHED"/><system-out>[  SKIPPED ] why</system-out>
  </testcase>
  <testcase name="Mean.Off" classname="Mean.Off" time="0" status="disabled">
    <system-out>Disabled</system-out>
  </testcase>
  <testcase name="Missing" classname="Missing" time="0" status="notrun">
    <skipped message="Unable to find executable"/><system-out>Unable to find executable: /x</system-out>
  </testcase>
</testsuite>
"""


def rows(tmp_path):
    path = tmp_path / "junit.xml"
    path.write_text(JUNIT, encoding="utf-8")
    return _tests.parse_junit(str(path))


def test_parse_junit_maps_ctest_statuses(tmp_path):
    parsed = {r["name"]: r for r in rows(tmp_path)}
    assert {name: r["status"] for name, r in parsed.items()} == {
        "Mean.SingleValue": "passed", "Slow<T> & co": "passed", "Mean.Broken": "failed",
        "Mean.Skipped": "skipped", "Mean.Off": "disabled", "Missing": "failed"}
    assert parsed["Mean.Broken"]["output"] == "expected 1 got 2 <&>"
    assert parsed["Missing"]["message"] == "Unable to find executable"
    assert parsed["Slow<T> & co"]["time"] == 0.25


def test_totals(tmp_path):
    assert _tests.totals(rows(tmp_path)) == {
        "total": 6, "failed": 2, "passed": 2, "skipped": 1, "disabled": 1, "time": 0.2565}


def test_summary_markdown_lists_failures_and_slowest_tests(tmp_path):
    text = _tests.summary_markdown("Tests: productA, release", rows(tmp_path), slowest=2)
    assert text.startswith("### Tests: productA, release")
    assert "**2 passed**, 2 failed, 1 skipped, 1 disabled (6 tests, 0.26 s)" in text
    assert "Failed: `Mean.Broken`, `Missing`" in text
    slowest = text.split("Slowest")[1]
    assert slowest.index("Slow<T> & co") < slowest.index("Mean.Broken")
    assert "Mean.SingleValue" not in slowest


def test_summary_markdown_escapes_pipes():
    row = {"name": "a|b", "status": "passed", "time": 0.1, "message": "", "output": ""}
    assert "| `a\\|b` | 100.0 ms |" in _tests.summary_markdown("T", [row])


def test_html_is_one_self_contained_sortable_file(tmp_path):
    path = tmp_path / "r.html"
    _tests.write_html("Tests: productA, release", "linux-x86_64", rows(tmp_path), str(path))
    page = path.read_text(encoding="utf-8")
    assert not re.search(r'(src|href)="(https?:)?//', page)
    assert "<script>" in page and "aria-sort" in page and "data-filter" in page
    assert 'data-name="Slow&lt;T&gt; &amp; co"' in page and "Slow<T>" not in page
    assert page.count("<tr data-name=") == 6
    assert 'data-status="disabled"' in page and 'data-time="0.25"' in page
    assert "expected 1 got 2 &lt;&amp;&gt;" in page  # failure output, escaped
    assert "<b>2</b>failed" in page and "<b>0.26 s</b>" in page


def test_write_report_writes_html_md_json_and_job_summary(tmp_path, monkeypatch):
    junit = tmp_path / "t.xml"
    junit.write_text(JUNIT, encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "summary"))
    stem = str(tmp_path / "productA-release")
    totals, text = _tests.write_report(str(junit), stem, "T", "m")
    assert json.loads((tmp_path / "productA-release.json").read_text())["failed"] == 2
    assert (tmp_path / "productA-release.md").read_text() == text
    assert (tmp_path / "productA-release.html").is_file()
    assert (tmp_path / "summary").read_text() == text + "\n"
    assert totals["total"] == 6
