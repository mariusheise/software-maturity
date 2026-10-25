"""Coverage summary for maturity:coverage (not a command itself).

Turns a gcovr JSON report into a markdown summary (console, GitHub job summary, PR comment
body). With a diff base, it also reports coverage of the lines changed since that revision.
"""

import json
import os
import re
import subprocess

HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@")
COMMENT_MARKER = "<!-- coverage-comment -->"


def changed_lines(root, base):
    """Lines added or changed in the working tree since the merge base of <base> and HEAD."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True,
                              text=True).stdout

    merge_base = git("merge-base", base, "HEAD").strip()
    changed, current = {}, None
    for row in git("diff", "-U0", "--no-color", merge_base).splitlines():
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


def summarize(report, diff=None):
    """Return (line percent, markdown) for a gcovr JSON report, optionally with changed lines."""
    rows, total, covered = [], 0, 0
    patch_total, patch_hit = 0, 0
    for entry in sorted(report["files"], key=lambda e: e["file"]):
        lines = [l for l in entry["lines"] if not l.get("gcovr/excluded")]
        hit = {l["line_number"] for l in lines if l["count"] > 0}
        miss = {l["line_number"] for l in lines if l["count"] == 0}
        total += len(lines)
        covered += len(hit)
        if diff is not None:
            touched = diff.get(entry["file"], set())
            patch_total += len((hit | miss) & touched)
            patch_hit += len(hit & touched)
        pct = 100.0 * len(hit) / len(lines) if lines else 100.0
        rows.append(f"| `{entry['file']}` | {len(hit)}/{len(lines)} | {pct:.1f}% | {fmt(ranges_of(miss))} |")

    pct = 100.0 * covered / total if total else 100.0
    summary = ["## Line coverage", "", f"**{pct:.1f}%** ({covered}/{total} lines)"]
    if diff is not None:
        ppct = 100.0 * patch_hit / patch_total if patch_total else 100.0
        summary += ["", f"Changed lines: **{ppct:.1f}%** "
                        f"({patch_hit}/{patch_total} executable lines covered)"]
    summary += ["", "| File | Lines | Cover | Missing |", "| --- | --- | --- | --- |", *rows, ""]
    return pct, "\n".join(summary)


def write_summary(json_path, markdown_path, root, diff_base=None):
    """Summarize <json_path> into <markdown_path> and, on GitHub Actions, the job summary and
    the step output 'line-percent'. Returns (line percent, markdown)."""
    with open(json_path, encoding="utf-8") as f:
        report = json.load(f)
    diff = changed_lines(root, diff_base) if diff_base else None
    pct, text = summarize(report, diff)
    with open(markdown_path, "w", encoding="utf-8") as f:
        f.write(COMMENT_MARKER + "\n" + text)
    if target := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(target, "a", encoding="utf-8") as f:
            f.write(text)
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as f:
            f.write(f"line-percent={pct:.1f}\n")
    return pct, text
