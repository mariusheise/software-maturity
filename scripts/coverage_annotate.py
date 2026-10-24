#!/usr/bin/env python3
"""Turn a gcovr JSON report into GitHub annotations and a job summary."""
import json
import os
import sys


def uncovered_ranges(lines):
    missed = sorted(l["line_number"] for l in lines if l["count"] == 0 and not l.get("gcovr/excluded"))
    ranges = []
    for n in missed:
        if ranges and n == ranges[-1][1] + 1:
            ranges[-1][1] = n
        else:
            ranges.append([n, n])
    return ranges


def main(path):
    with open(path) as f:
        files = json.load(f)["files"]

    rows, total, covered = [], 0, 0
    for entry in sorted(files, key=lambda e: e["file"]):
        lines = [l for l in entry["lines"] if not l.get("gcovr/excluded")]
        hit = sum(1 for l in lines if l["count"] > 0)
        total += len(lines)
        covered += hit
        ranges = uncovered_ranges(lines)
        for start, end in ranges:
            title = "Not covered by tests"
            span = f"Line {start} is" if start == end else f"Lines {start}-{end} are"
            print(f"::warning file={entry['file']},line={start},endLine={end},title={title}::"
                  f"{span} not executed by any test")
        missing = ", ".join(f"{a}-{b}" if a != b else str(a) for a, b in ranges) or "-"
        pct = 100.0 * hit / len(lines) if lines else 100.0
        rows.append(f"| `{entry['file']}` | {hit}/{len(lines)} | {pct:.1f}% | {missing} |")

    pct = 100.0 * covered / total if total else 100.0
    summary = ["## Line coverage", "", f"**{pct:.1f}%** ({covered}/{total} lines)", "",
               "| File | Lines | Cover | Missing |", "| --- | --- | --- | --- |", *rows, ""]
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a") as f:
            f.write("\n".join(summary))
    else:
        print("\n".join(summary))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "coverage.json")
