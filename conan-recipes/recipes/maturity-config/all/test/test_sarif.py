"""Layer 1: the clang-tidy to SARIF conversion in _sarif.py, without a Conan home."""

import json

import _sarif

LOG = """\
/repo/src/a.cpp:3:5: error: use 'using' instead of 'typedef' [modernize-use-using,-warnings-as-errors]
/repo/src/a.cpp:3:5: error: use 'using' instead of 'typedef' [modernize-use-using,-warnings-as-errors]
/repo/include/b.hpp:7:1: warning: something [performance-x]
/elsewhere/c.cpp:1:1: warning: outside the root [performance-x]
/repo/src/d.cpp:2:2: error: unknown type name 'foo'
42 warnings generated.
"""


def test_to_sarif_dedups_and_keeps_files_under_the_root():
    run = _sarif.to_sarif(LOG, "/repo")["runs"][0]
    found = [(r["locations"][0]["physicalLocation"]["artifactLocation"]["uri"],
              r["locations"][0]["physicalLocation"]["region"]["startLine"], r["ruleId"],
              r["level"]) for r in run["results"]]
    assert found == [
        ("src/a.cpp", 3, "modernize-use-using,-warnings-as-errors", "error"),
        ("include/b.hpp", 7, "performance-x", "warning"),
        ("src/d.cpp", 2, "clang-diagnostic", "error"),
    ]
    assert [r["id"] for r in run["tool"]["driver"]["rules"]] == [
        "modernize-use-using,-warnings-as-errors", "performance-x", "clang-diagnostic"]


def test_write_sarif_returns_the_number_of_findings(tmp_path):
    path = tmp_path / "out.sarif"
    assert _sarif.write_sarif(LOG, "/repo", str(path)) == 3
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == "2.1.0"
    assert _sarif.write_sarif("", "/repo", str(path)) == 0
