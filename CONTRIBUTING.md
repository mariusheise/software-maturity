# Contributing

## Setup

Open the repository in the devcontainer (`.devcontainer/`). It provides the
toolchain, Conan and prek, and installs the git hooks on creation.

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
- Dependencies are pinned by `conan.lock`; builds fail if `conanfile.py` and the lockfile
  disagree. After changing a requirement or upgrading, run `scripts/update_lock.sh` and
  commit the result.

## Reporting security issues

See [SECURITY.md](SECURITY.md).
