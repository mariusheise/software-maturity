#!/usr/bin/env bash
# Build the config packages listed in conanconfig.yml from the in-repo recipe index
# (conan-recipes/), so that "conan config install-pkg ." can install them afterwards.
# install-pkg only downloads binaries. Remove this script once the recipes are published
# to a real remote; then "conan remote add" plus "conan config install-pkg ." is enough.
set -euo pipefail

cd "$(dirname "$0")/.."
remote="maturity-recipes"

conan profile detect --exist-ok
conan remote add "${remote}" "${PWD}/conan-recipes" --type=local-recipes-index --force
sed -n 's/^  - //p' conanconfig.yml | while read -r ref; do
  conan install --requires="${ref}" -r "${remote}" --build=missing --lockfile="" \
    --output-folder=build/conan-config
done
