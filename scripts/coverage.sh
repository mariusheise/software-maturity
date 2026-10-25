#!/usr/bin/env bash
# Build Debug with coverage instrumentation, run the tests and enforce the line-coverage gate.
set -euo pipefail

cd "$(dirname "$0")/.."
product="${PRODUCT:-productA}"
target="${TARGET:-linux-x86_64}"
min_line_coverage="${1:-90}"

conan maturity:install --product="${product}" --target="${target}" --build-type=debug
cmake --preset conan-debug -DMATURITY_COVERAGE=ON
cmake --build --preset conan-debug
ctest --preset conan-debug --output-on-failure

gcovr --root . --filter "src/" --filter "include/" --exclude "src/main.cpp" \
  --print-summary --xml-pretty --output coverage.xml --json coverage.json \
  --html-details coverage-report.html --html-single-page --html-self-contained \
  --fail-under-line "${min_line_coverage}" build/Debug
