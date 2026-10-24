#!/usr/bin/env python3
"""Turn a gcovr JSON report into GitHub annotations and a job summary.

With COVERAGE_DIFF_BASE set (e.g. HEAD^1), annotations are limited to lines
changed relative to that revision, so "Files changed" shows what the PR covers.
"""
import json
import os
import re
import subprocess
import sys

HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@")


def changed_lines(base):
    out = subprocess.run(["git", "diff", "-U0", "--no-color", base, "HEAD"],
                         check=True, capture_output=True, text=True).stdout
    changed, current = {}, None
    for row in out.splitlines():
        if row.startswith("+++ "):
            current = row[6:] if row.startswith("+++ b/") else None
            if current:
                changed[current] = set()
        elif current and (m := HUNK.match(row)):
            start, count = int(m.group(1)), int(m.group(2) or 1)
            changed[current].update(range(start, start + count))
    return changed


def ranges_of(numbers):
    ranges = []
    for n in sorted(numbers):
        if ranges and n == ranges[-1][1] + 1:
            ranges[-1][1] = n
        else:
            ranges.append([n, n])
    return ranges


def fmt(ranges):
    return ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in ranges) or "-"


def annotate(level, path, ranges, title, verb):
    for start, end in ranges:
        span = f"Line {start} is" if start == end else f"Lines {start}-{end} are"
        print(f"::{level} file={path},line={start},endLine={end},title={title}::{span} {verb}")


def main(path, markdown_out=None):
    with open(path) as f:
        files = json.load(f)["files"]
    base = os.environ.get("COVERAGE_DIFF_BASE")
    diff = changed_lines(base) if base else None

    rows, total, covered = [], 0, 0
    patch_total, patch_hit = 0, 0
    for entry in sorted(files, key=lambda e: e["file"]):
        lines = [l for l in entry["lines"] if not l.get("gcovr/excluded")]
        hit = {l["line_number"] for l in lines if l["count"] > 0}
        miss = {l["line_number"] for l in lines if l["count"] == 0}
        total += len(lines)
        covered += len(hit)
        if diff is None:
            annotate("warning", entry["file"], ranges_of(miss), "Not covered by tests",
                     "not executed by any test")
        else:
            touched = diff.get(entry["file"], set())
            annotate("warning", entry["file"], ranges_of(miss & touched),
                     "Not covered by tests", "changed here but not executed by any test")
            annotate("notice", entry["file"], ranges_of(hit & touched),
                     "Covered by tests", "changed here and executed by tests")
            patch_total += len((hit | miss) & touched)
            patch_hit += len(hit & touched)
        pct = 100.0 * len(hit) / len(lines) if lines else 100.0
        rows.append(f"| `{entry['file']}` | {len(hit)}/{len(lines)} | {pct:.1f}% | {fmt(ranges_of(miss))} |")

    pct = 100.0 * covered / total if total else 100.0
    summary = ["## Line coverage", "", f"**{pct:.1f}%** ({covered}/{total} lines)"]
    if diff is not None:
        ppct = 100.0 * patch_hit / patch_total if patch_total else 100.0
        summary += ["", f"Changed lines in this PR: **{ppct:.1f}%** "
                        f"({patch_hit}/{patch_total} executable lines covered)"]
    summary += ["", "| File | Lines | Cover | Missing |", "| --- | --- | --- | --- |", *rows, ""]
    text = "\n".join(summary)
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a") as f:
            f.write(text)
    else:
        print(text)
    if markdown_out:
        with open(markdown_out, "w") as f:
            f.write("<!-- coverage-comment -->\n" + text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage.json",
         sys.argv[2] if len(sys.argv) > 2 else None)
