"""Layer 1: the audit summary in _audit.py, without a Conan home."""

import json
import os

import _audit

RESULT = {"data": {
    "zlib/1.3.1": {"vulnerabilities": {"totalCount": 2, "edges": [
        {"node": {"name": "CVE-1", "severity": "Medium", "cvss": {"preferredBaseScore": 5.0}}},
        {"node": {"name": "CVE-2", "severity": "Critical", "cvss": {"preferredBaseScore": 9.8}}},
    ]}},
    "gtest/1.14.0": {"vulnerabilities": {"totalCount": 0, "edges": []}},
    "own|lib/1.0": {"error": {"details": "Not found."}},
}, "provider_url": "https://audit.example"}


def test_findings_are_sorted_worst_first_and_list_unscanned_packages():
    rows, unscanned = _audit.findings(RESULT)
    assert [(r["id"], r["score"]) for r in rows] == [("CVE-2", 9.8), ("CVE-1", 5.0)]
    assert unscanned == [("own|lib/1.0", "Not found.")]


def test_summary_counts_against_the_gate():
    rows, unscanned = _audit.findings(RESULT)
    text = _audit.summary_markdown("Audit: a", 3, rows, unscanned, 7.0)
    assert "**2 known vulnerabilities** in 3 package(s), 1 at or above the gate of CVSS 7." in text
    assert "| zlib/1.3.1 | CVE-2 | Critical | 9.8 |" in text
    assert "Not scanned: own\\|lib/1.0 (Not found.)" in text


def test_summary_without_vulnerabilities_has_no_table():
    text = _audit.summary_markdown("Audit: a", 1, [], [], 7.0)
    assert "**0 known vulnerabilities**" in text and "| Package |" not in text


def test_write_report_writes_json_html_markdown_and_the_job_summary(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    stem = str(tmp_path / "out" / "a-linux")
    above, text = _audit.write_report(RESULT, stem, "Audit: a", 9.8)
    assert [r["id"] for r in above] == ["CVE-2"]
    with open(stem + ".json", encoding="utf-8") as f:
        assert json.load(f) == RESULT
    with open(stem + ".html", encoding="utf-8") as f:
        assert "CVE-2" in f.read()
    assert os.path.isfile(stem + ".md")
    assert summary.read_text(encoding="utf-8") == text
