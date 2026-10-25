#!/usr/bin/env bash
# Install dependencies, configure, build and test (Release by default).
set -euo pipefail

cd "$(dirname "$0")/.."
product="${PRODUCT:-productA}"
target="${TARGET:-linux-x86_64}"
build_type="${1:-Release}"
preset="conan-${build_type,,}"

conan maturity:install --product="${product}" --target="${target}" --build-type="${build_type,,}"
cmake --preset "${preset}"
cmake --build --preset "${preset}"
ctest --preset "${preset}" --output-on-failure
