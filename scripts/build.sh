#!/usr/bin/env bash
# Install dependencies, configure, build and test (Release by default).
set -euo pipefail

cd "$(dirname "$0")/.."
product="${PRODUCT:-productA}"
build_type="${1:-Release}"
preset="conan-${build_type,,}"

conan install . --lockfile="locks/${product}.lock" -o "&:product=${product}" --build=missing -s build_type="${build_type}" -s compiler.cppstd=20
cmake --preset "${preset}"
cmake --build --preset "${preset}"
ctest --preset "${preset}" --output-on-failure
