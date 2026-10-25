"""Layer 1: the coverage summary in _coverage.py, without a Conan home."""

import json
import subprocess

import _coverage

REPORT = {"files": [
    {"file": "src/b.cpp", "lines": [
        {"line_number": 1, "count": 1},
        {"line_number": 2, "count": 0},
        {"line_number": 3, "count": 0},
        {"line_number": 5, "count": 0},
        {"line_number": 9, "count": 0, "gcovr/excluded": True},
    ]},
    {"file": "src/a.cpp", "lines": [{"line_number": 4, "count": 3}]},
]}


def git(root, *args):
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def test_ranges_and_fmt():
    assert _coverage.fmt(_coverage.ranges_of({5, 1, 2, 3, 7})) == "1-3, 5, 7"
    assert _coverage.fmt([]) == "-"


def test_summarize_counts_lines_and_skips_excluded():
    pct, text = _coverage.summarize(REPORT)
    assert pct == 40.0
    assert "**40.0%** (2/5 lines)" in text
    assert text.index("src/a.cpp") < text.index("src/b.cpp")
    assert "| `src/b.cpp` | 1/4 | 25.0% | 2-3, 5 |" in text
    assert "Changed lines" not in text


def test_summarize_reports_changed_lines():
    _, text = _coverage.summarize(REPORT, {"src/b.cpp": {1, 2, 9}, "README.md": {1}})
    assert "Changed lines: **50.0%** (1/2 executable lines covered)" in text


def test_summarize_empty_report_is_fully_covered():
    pct, _ = _coverage.summarize({"files": []})
    assert pct == 100.0


def test_changed_lines_include_uncommitted_edits_since_the_merge_base(tmp_path):
    git(tmp_path, "init", "-q", "-b", "main")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "a.cpp").write_text("1\n2\n3\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    git(tmp_path, "checkout", "-q", "-b", "feature")
    (tmp_path / "a.cpp").write_text("1\nchanged\n3\n", encoding="utf-8")
    git(tmp_path, "commit", "-q", "-am", "committed change")
    (tmp_path / "a.cpp").write_text("1\nchanged\n3\nuncommitted\n", encoding="utf-8")
    assert _coverage.changed_lines(str(tmp_path), "main") == {"a.cpp": {2, 4}}


def test_write_summary_writes_markdown_and_github_outputs(tmp_path, monkeypatch):
    report = tmp_path / "coverage.json"
    report.write_text(json.dumps(REPORT), encoding="utf-8")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(tmp_path / "step-summary"))
    monkeypatch.setenv("GITHUB_OUTPUT", str(tmp_path / "output"))
    pct, text = _coverage.write_summary(str(report), str(tmp_path / "summary.md"), str(tmp_path))
    assert pct == 40.0
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == "<!-- coverage-comment -->\n" + text
    assert (tmp_path / "step-summary").read_text(encoding="utf-8") == text
    assert (tmp_path / "output").read_text(encoding="utf-8") == "line-percent=40.0\n"
