#!/usr/bin/env bash
# Regenerate conan.lock from conanfile.py (resolves the newest allowed versions).
set -euo pipefail

cd "$(dirname "$0")/.."
conan lock create . --lockfile-out=conan.lock -s build_type=Release -s compiler.cppstd=20
