"""Convert clang-tidy console output to a SARIF 2.1.0 log (not a command itself)."""

import json
import os
import re

FINDING = re.compile(
    r"^(?P<file>/\S.*?):(?P<line>\d+):(?P<col>\d+): (?P<level>warning|error): "
    r"(?P<msg>.*?)(?: \[(?P<check>[^\]]+)\])?$")


def to_sarif(log_text, root):
    """SARIF for the findings in files under <root>, with paths relative to it."""
    root = os.path.join(os.path.abspath(root), "")
    rules, results, seen = {}, [], set()
    for row in log_text.splitlines():
        m = FINDING.match(row)
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
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{"tool": {"driver": {"name": "clang-tidy", "rules": list(rules.values())}},
                  "results": results}],
    }


def write_sarif(log_text, root, sarif_path):
    """Write the SARIF log and return the number of findings."""
    sarif = to_sarif(log_text, root)
    with open(sarif_path, "w", encoding="utf-8") as f:
        json.dump(sarif, f, indent=2)
    return len(sarif["runs"][0]["results"])
