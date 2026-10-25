# Contributing

## Setup

Open the repository in the devcontainer (`.devcontainer/`). It provides the
toolchain, Conan and prek, installs the git hooks and the Conan configuration on creation.

## Workflow

1. Branch from `main`; direct pushes to `main` are blocked.
2. Make the change and run the checks locally:
   - `prek run --all-files` for formatting, secret scanning and workflow linting
   - `scripts/build.sh [Release|Debug]` to build and test
   - `scripts/coverage.sh` to enforce the line-coverage gate
3. Open a pull request. Required checks must pass: `prek`, `build-test`,
   `secrets (betterleaks)`, `analyze (c-cpp)` and `coverage`.
4. Code Owners review is required for paths listed in `.github/CODEOWNERS`.
   Changes to secret-scan exclusions (`.betterleaks.toml`) always need it.
5. Pull requests are squash-merged; commits must be signed.

## Standards

- New behaviour comes with unit tests; coverage must stay at or above the gate.
- The library builds with `-Wall -Wextra -Wpedantic -Werror`.
- Never commit real secrets. If a test needs a dummy credential, exclude that
  exact path, rule and value in `.betterleaks.toml`, as `tests/password_test.cpp` does.
- GitHub Actions are pinned to commit SHAs with least-privilege `permissions`.
- Dependencies are pinned per product in `locks/<product>.lock`; builds fail if `conanfile.py`
  and the lockfile disagree. After changing a requirement or upgrading, run
  `scripts/update_lock.sh` and commit the result.
- Shared Conan configuration (the `maturity` profile) is a configuration package listed in
  `conanconfig.yml`. Its recipe lives in `conan-recipes/`, a local-recipes-index that stands in
  for a remote. After changing it, run `scripts/conan_config.sh` to rebuild and reinstall it.
- Product variants are the Conan option `product`. Build one with `PRODUCT=productB scripts/build.sh`
  (default `productA`). Releases are cut by pushing a tag `<product>_v<version>`
  (for example `productA_v1.0.0`); a hyphen in the version makes it a pre-release. Each tag is handled
  by `release-<product>.yml`, which calls the shared `release.yml`. Verify assets with
  `gh attestation verify <file> --repo mariusheise/software-maturity --signer-workflow mariusheise/software-maturity/.github/workflows/release.yml`.

## Reporting security issues

See [SECURITY.md](SECURITY.md).
