#!/usr/bin/env bash
# Build Debug with coverage instrumentation, run the tests and enforce the line-coverage gate.
set -euo pipefail

cd "$(dirname "$0")/.."
min_line_coverage="${1:-90}"

conan install . --build=missing -s build_type=Debug -s compiler.cppstd=20
cmake --preset conan-debug -DMATURITY_COVERAGE=ON
cmake --build --preset conan-debug
ctest --preset conan-debug --output-on-failure

gcovr --root . --filter "src/" --filter "include/" --exclude "src/main.cpp" \
  --print-summary --xml-pretty --output coverage.xml \
  --fail-under-line "${min_line_coverage}" build/Debug
