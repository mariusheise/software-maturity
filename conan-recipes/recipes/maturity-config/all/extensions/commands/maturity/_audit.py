"""Summaries of 'conan audit scan' results for maturity:audit (not a command itself)."""

import contextlib
import io
import json
import os

from conan.cli.formatters.audit.vulnerabilities import html_vuln_formatter

from _tests import md


def findings(result):
    """One row per vulnerability in a scan result, worst first, and the packages not scanned."""
    rows, unscanned = [], []
    for ref, info in result.get("data", {}).items():
        if "error" in info:
            unscanned.append((ref, info["error"].get("details", "")))
            continue
        for edge in info.get("vulnerabilities", {}).get("edges", []):
            node = edge["node"]
            rows.append({"package": ref, "id": node.get("name", "?"),
                         "severity": node.get("severity", "?"),
                         "score": float(node.get("cvss", {}).get("preferredBaseScore", 0.0))})
    rows.sort(key=lambda r: (-r["score"], r["package"], r["id"]))
    return rows, unscanned


def summary_markdown(title, scanned, rows, unscanned, threshold):
    failing = [r for r in rows if r["score"] >= threshold]
    lines = [f"### {title}", "",
             f"**{len(rows)} known vulnerabilities** in {scanned} package(s), {len(failing)} at or "
             f"above the gate of CVSS {threshold:g}.", ""]
    if rows:
        lines += ["| Package | Vulnerability | Severity | CVSS |", "| --- | --- | --- | --- |"]
        lines += [f"| {md(r['package'])} | {md(r['id'])} | {r['severity']} | {r['score']:g} |"
                  for r in rows]
        lines.append("")
    if unscanned:
        lines += ["Not scanned: " + ", ".join(f"{md(ref)} ({md(details)})"
                                              for ref, details in unscanned), ""]
    return "\n".join(lines) + "\n"


def write_report(result, stem, title, threshold):
    """Write <stem>.json (the raw scan), <stem>.html (Conan's report) and <stem>.md, and append
    the markdown to the GitHub job summary. Returns (rows at or above the gate, markdown)."""
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    with open(stem + ".json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    html = io.StringIO()
    with contextlib.redirect_stdout(html):
        html_vuln_formatter(result)
    with open(stem + ".html", "w", encoding="utf-8") as f:
        f.write(html.getvalue())
    rows, unscanned = findings(result)
    text = summary_markdown(title, len(result.get("data", {})), rows, unscanned, threshold)
    with open(stem + ".md", "w", encoding="utf-8") as f:
        f.write(text)
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(target, "a", encoding="utf-8") as f:
            f.write(text)
    return [r for r in rows if r["score"] >= threshold], text
