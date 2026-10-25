# Contributing

## Setup

Open the repository in the devcontainer (`.devcontainer/`). It provides the
toolchain, Conan and prek, installs the git hooks and the Conan configuration on creation.
Conan uses a per-checkout home in `.conan2/` (set by `.conanrc`), so checkouts of different
release branches do not share commands, profiles or packages.

## Workflow

1. Branch from `main`; direct pushes to `main` are blocked.
2. Make the change and run the checks locally:
   - `prek run --all-files` for formatting, secret scanning and workflow linting
   - `conan maturity:build --product productA --target linux-x86_64 [--build-type debug]` to
     build and run the unit tests (`--skip-test` builds without them)
   - `conan maturity:coverage --product productA --target linux-x86_64 --diff-base origin/main`
     for the coverage gate (see [Coverage](#coverage))
   - `conan maturity:tidy --product productA --target linux-x86_64` for clang-tidy (see
     [Static analysis](#static-analysis))
   - `python -m pytest conan-recipes/recipes/maturity-config/all/test` after changing the
     `maturity:*` commands or profiles (see [docs/conan-commands.md](docs/conan-commands.md))
3. Open a pull request. Required checks must pass: `prek`, `tests`, `coverage`,
   `conan-commands`, `secrets (betterleaks)`, `analyze (c-cpp)` and `clang-tidy`. `tests` and
   `coverage` pass only when every product's `build-test` and `coverage` jobs pass.
4. Code Owners review is required for paths listed in `.github/CODEOWNERS`.
   Changes to secret-scan exclusions (`.betterleaks.toml`) always need it.
5. Pull requests are squash-merged; commits must be signed.

## Standards

- New behaviour comes with unit tests; coverage must stay at or above the gate.
- The library builds with `-Wall -Wextra -Wpedantic -Werror`.
- Never commit real secrets. If a test needs a dummy credential, exclude that
  exact path, rule and value in `.betterleaks.toml`, as `tests/password_test.cpp` does.
- GitHub Actions are pinned to commit SHAs with least-privilege `permissions`.
- Dependencies are pinned per product in `products/<product>.lock`; builds fail if `conanfile.py`
  and the lockfile disagree. After changing a requirement or upgrading, run
  `conan maturity:lock-update` and commit the result.
- Shared Conan configuration (profiles and the `maturity:*` commands) is the configuration
  package `maturity-config`, pinned in `conan.lock`. Its recipe lives in `conan-recipes/`, a
  local-recipes-index that stands in for a remote. After changing it, run
  `conan maturity:config-lock-update` and commit the recipe, `conan.lock` and `products/*.lock`.
- Product variants live in `products/`. To add one, create `products/<name>.yml` with its
  `options` (the manifest keys are listed in [docs/conan-commands.md](docs/conan-commands.md);
  `conan maturity:list` validates and shows them), run `conan maturity:lock-update --product <name>`, and add a
  `release-<name>.yml` caller (tag triggers cannot be discovered). CI picks the new product up
  from `maturity:list` and gates it automatically; no workflow or ruleset change is needed. Build one with
  `conan maturity:build --product productB --target linux-x86_64`. Releases are cut by pushing a tag `<product>_v<version>`
  (for example `productA_v1.0.0`); a hyphen in the version makes it a pre-release. The tag is
  the only source of the version: there is none in `conanfile.py` or `CMakeLists.txt`, and
  local builds report `0.0.0-dev`. Each tag is handled
  by `release-<product>.yml`, which calls the shared `release.yml`. Verify assets with
  `gh attestation verify <file> --repo mariusheise/software-maturity --signer-workflow mariusheise/software-maturity/.github/workflows/release.yml`.

## Test report

Every `conan maturity:build` that runs the tests also writes a test report:

- `build/test-report/<product>-<build type>.html`: one self-contained file, no server needed.
  It shows tiles with the counts (passed, failed, skipped, disabled) and the total time, and a
  table with one row per test, its status and its time. Click a column to sort it and a tile
  to filter. Failed and skipped tests have their output in the row.
- The console, and on CI the job summary, show the counts and the slowest tests.
- The report is written even when a test fails, so you can see what failed. `--skip-test`
  writes none.
- A gtest `GTEST_SKIP()` shows as skipped and a `DISABLED_` test as disabled.

On a pull request, CI builds both products in Release and Debug. Each combination links its
HTML report from the run summary, and one sticky comment summarises all four. Releases attach
the report of the released product.

## Coverage

The `coverage` check fails a pull request below 90% line coverage. Run the same check locally
before opening a pull request:

```sh
conan maturity:coverage --product productA --target linux-x86_64 --diff-base origin/main
```

- It builds with coverage instrumentation in `build/coverage/Debug`, runs the unit tests,
  and checks the gate. Your normal `build/Debug` is not touched.
- It prints the total, the coverage of the lines you changed since you branched from
  `origin/main` (uncommitted edits included), and a table of files with their uncovered lines.
  Run `git fetch` first so `origin/main` is current.
- Open `build/coverage-report/coverage-report.html` for the coloured source view; red lines
  are not executed by any test.
- The reports are written even when the gate fails, so you can see what is missing.
- Every run starts from zero, so you can rerun it after adding tests.
- Leave out `--diff-base` for the total only. The gate comes from the product's manifest
  (`coverage.fail_under`, 90 by default); `--fail-under <percent>` changes it for a
  local experiment; CI uses the manifest's gate.
- `gcovr.cfg` decides which files count (`src/` and `include/`, without `src/main.cpp`).
  Change it only with a reason in the pull request.

On a pull request, CI posts the same summary as a comment (same-repo, non-Dependabot pull
requests) and links the HTML report from the run summary.

## Static analysis

The `clang-tidy` check fails a pull request on any finding. Run the same check locally:

```sh
conan maturity:tidy --product productA --target linux-x86_64
conan maturity:tidy --product productA --target linux-x86_64 --diff-base origin/main  # changed files
conan maturity:tidy --product productA --target linux-x86_64 --fix                    # apply fixes
```

- It checks every source file of the project (`src/` and `tests/`) and the project's headers,
  with the checks in `.clang-tidy`. Findings in dependencies are never reported.
- clang-tidy is pinned in `.devcontainer/requirements.txt` (23.1.3), so the devcontainer and CI
  give the same result. The command prints the version it uses. Dependabot proposes upgrades;
  fix any new findings in that pull request.
- The log and SARIF land in `build/tidy-report/`; CI uploads the SARIF to code scanning.
- `--fix` applies clang-tidy's fixes and then checks again; review the diff before committing.

## Reporting security issues

See [SECURITY.md](SECURITY.md).
