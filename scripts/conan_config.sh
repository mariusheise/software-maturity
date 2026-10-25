#!/usr/bin/env bash
# Install the Conan configuration packages listed in conanconfig.yml into the Conan home.
# conan-recipes/ is a local-recipes-index that stands in for a remote such as Artifactory.
# Once the recipes move there, replace the remote and drop the build loop; the references
# in conanconfig.yml stay as they are.
set -euo pipefail

cd "$(dirname "$0")/.."
remote="maturity-recipes"

conan profile detect --exist-ok
conan remote add "${remote}" "${PWD}/conan-recipes" --type=local-recipes-index --force

# install-pkg only downloads binaries, so build the config packages from the index first.
sed -n 's/^  - //p' conanconfig.yml | while read -r ref; do
  conan install --requires="${ref}" -r "${remote}" --build=missing --output-folder=build/conan-config
done
conan config install-pkg .
