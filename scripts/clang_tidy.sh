#!/usr/bin/env bash
# Run clang-tidy on the library and app sources and convert the findings to SARIF.
set -euo pipefail

cd "$(dirname "$0")/.."
build_dir="build/Debug"

if [[ ! -f "${build_dir}/compile_commands.json" ]]; then
  conan install . --build=missing -s build_type=Debug -s compiler.cppstd=20
  cmake --preset conan-debug
fi

status=0
clang-tidy -p "${build_dir}" --header-filter="^${PWD}/(include|src)/" src/*.cpp \
  >clang-tidy.log 2>&1 || status=$?
cat clang-tidy.log
python3 scripts/clang_tidy_to_sarif.py clang-tidy.log clang-tidy.sarif
exit "${status}"
