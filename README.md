# Software Maturity Demonstrator

## Purpose

A clean reference repository that shows how a codebase reaches a high software
maturity level using only Git and GitHub. The code is deliberately small (a C++
statistics library and a demo app); the point is the engineering system around it:
CI, quality gates, supply-chain security, reproducible builds and releases.

It is benchmarked against a 28-practice "GitHub CI Software Maturity Checklist"
and grows practice by practice. The plan is to add C, Python and Rust variants
later, so the practices stay language-agnostic where possible.

**Where to start**

| Need                                          | Read                                                     |
| --------------------------------------------- | -------------------------------------------------------- |
| What is done, what is open, what is next      | [docs/status.md](docs/status.md)                         |
| How the CI, gates, releases and secrets work  | [docs/architecture.md](docs/architecture.md)             |
| Checklist practice-by-practice status         | [docs/maturity-checklist.md](docs/maturity-checklist.md) |
| `maturity:*` Conan commands and their tests   | [docs/conan-commands.md](docs/conan-commands.md)         |
| Tools and dependencies, pins and updates      | [docs/dependencies.md](docs/dependencies.md)             |
| Workflow and standards for contributors       | [CONTRIBUTING.md](CONTRIBUTING.md)                       |
| Reporting vulnerabilities, verifying releases | [SECURITY.md](SECURITY.md)                               |

## Layout

| Path                      | Purpose                                           |
| ------------------------- | ------------------------------------------------- |
| `include/`, `src/`        | C++ library and demo executable                   |
| `tests/`                  | GoogleTest unit tests                             |
| `conanfile.py`            | Dependencies and the `product` option (Conan 2)   |
| `products/`               | Product variants: `<name>.yml` and `<name>.lock`  |
| `conanconfig.yml`         | Conan configuration packages to install           |
| `conan.lock`              | Pins the configuration package revision           |
| `.conanrc`                | Per-checkout Conan home (`.conan2/`)              |
| `conan-recipes/`          | Local recipe index standing in for a Conan remote |
| `CMakeLists.txt`          | Build definition                                  |
| `gcovr.cfg`               | Which files count for coverage                    |
| `.pre-commit-config.yaml` | Hooks run by prek                                 |
| `.github/workflows/`      | CI, tests, coverage, clang-tidy, CodeQL, Scorecard, releases |
| `.github/CODEOWNERS`      | Required reviewers per path                       |
| `.devcontainer/`          | Reproducible dev environment (Docker)             |
| `scripts/`                | Conan bootstrap                                   |

## Usage

Open the folder in VS Code and choose **Reopen in Container**
(requires Docker and the Dev Containers extension). Then, in the container:

```sh
conan maturity:build --product=productA --target=linux-x86_64                    # Release, with tests
conan maturity:build --product=productA --target=linux-x86_64 --build-type=debug
conan maturity:build --product=productB --target=linux-x86_64 --skip-test        # other variant, no tests
conan maturity:coverage --product=productA --target=linux-x86_64 --diff-base=origin/main
conan maturity:tidy --product=productA --target=linux-x86_64                     # clang-tidy, as in CI
prek run --all-files
./build/Release/maturity_app
```

`maturity:build` writes a sortable single-file test report (counts, status and time per test)
to `build/test-report/<product>-<build type>.html`. The coverage run writes its reports,
including a single-file HTML report, to `build/coverage-report/`, and clang-tidy writes its log and SARIF to `build/tidy-report/`; see
[CONTRIBUTING.md](CONTRIBUTING.md#coverage).

The git hook and the Conan configuration are installed automatically (`prek install`,
`scripts/conan_bootstrap.sh`, `conan config install-pkg .`).

## Releases

Push a tag `<product>_v<version>` (for example `productA_v1.0.0`). A hyphen in the
version (`productA_v1.0.0-rc.1`) makes it a pre-release. The tag is the only place the version
lives: nothing in the repository is bumped, and `maturity_app --version` of the released binary
prints it. Builds without a tag report `0.0.0-dev`.

A release builds, tests and covers only its own product. Its assets are the tarball, the test
report (`-tests.html`), the coverage report (`-coverage.html`) and a CycloneDX SBOM. All of
them are attested; see [SECURITY.md](SECURITY.md) to verify them. Pre-releases do not move the
"Latest" marker.

GitHub marks only one release per repository as "Latest", so each product has its own list:
[productA releases](../../releases?q=productA_v) and
[productB releases](../../releases?q=productB_v). A product's `release.latest` in
`products/<name>.yml` decides whether its final releases may take the marker (default: GitHub
decides).
