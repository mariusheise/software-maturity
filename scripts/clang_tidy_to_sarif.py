#!/usr/bin/env python3
"""Convert clang-tidy console output to a SARIF 2.1.0 log."""
import json
import os
import re
import sys

FINDING = re.compile(
    r"^(?P<file>/\S.*?):(?P<line>\d+):(?P<col>\d+): (?P<level>warning|error): "
    r"(?P<msg>.*?)(?: \[(?P<check>[^\]]+)\])?$")


def main(log_path, sarif_path):
    root = os.getcwd() + os.sep
    rules, results, seen = {}, [], set()
    with open(log_path) as f:
        for row in f:
            m = FINDING.match(row.rstrip("\n"))
            if not m or not m["file"].startswith(root):
                continue
            rel = m["file"][len(root):]
            check = m["check"] or "clang-diagnostic"
            key = (rel, m["line"], m["col"], check)
            if key in seen:
                continue
            seen.add(key)
            rules.setdefault(check, {"id": check, "shortDescription": {"text": check}})
            results.append({
                "ruleId": check,
                "level": m["level"],
                "message": {"text": m["msg"]},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": rel, "uriBaseId": "%SRCROOT%"},
                    "region": {"startLine": int(m["line"]), "startColumn": int(m["col"])}}}],
            })
    sarif = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{"tool": {"driver": {"name": "clang-tidy", "rules": list(rules.values())}},
                  "results": results}],
    }
    with open(sarif_path, "w") as f:
        json.dump(sarif, f, indent=2)
    print(f"{len(results)} clang-tidy finding(s) written to {sarif_path}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
