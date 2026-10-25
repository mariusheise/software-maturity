#!/usr/bin/env bash
# Regenerate the per-product lockfiles in locks/ from conanfile.py (newest allowed versions).
set -euo pipefail

cd "$(dirname "$0")/.."
for product in productA productB; do
  conan lock create . --lockfile-out="locks/${product}.lock" -o "&:product=${product}" \
    -s build_type=Release -s compiler.cppstd=20
  echo >>"locks/${product}.lock"
done
