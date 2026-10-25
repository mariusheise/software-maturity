# Software Maturity Demonstrator

[![OpenSSF Scorecard](https://api.scorecard.dev/projects/github.com/mariusheise/software-maturity/badge)](https://scorecard.dev/viewer/?uri=github.com/mariusheise/software-maturity) [![Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/mariusheise/9a670b7c3e531f53dabb7e1f6012e1a3/raw/coverage-main.json)](https://github.com/mariusheise/software-maturity/actions/workflows/ci.yml?query=branch%3Amain)

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
| `conan-recipes/`          | Local recipe index standing in for a Conan remote |
| `CMakeLists.txt`          | Build definition                                  |
| `.pre-commit-config.yaml` | Hooks run by prek                                 |
| `.github/workflows/`      | CI, clang-tidy, CodeQL, Scorecard, releases       |
| `.github/CODEOWNERS`      | Required reviewers per path                       |
| `.devcontainer/`          | Reproducible dev environment (Docker)             |
| `scripts/`                | build, coverage, clang-tidy, lockfile, CI helpers |

## Usage

Open the folder in VS Code and choose **Reopen in Container**
(requires Docker and the Dev Containers extension). Then, in the container:

```sh
scripts/build.sh                     # or: scripts/build.sh Debug
conan maturity:install --product=productA --target=linux-x86_64 --build-type=debug
PRODUCT=productB scripts/build.sh    # build the other product variant
prek run --all-files
./build/Release/maturity_app
```

The git hook and the Conan configuration are installed automatically (`prek install`,
`scripts/conan_bootstrap.sh`, `conan config install-pkg .`).

## Releases

Push a tag `<product>_v<version>` (for example `productA_v1.0.0`). A hyphen in the
version (`productA_v1.0.0-rc.1`) makes it a pre-release. Assets (tarball, coverage
report, CycloneDX SBOM) are attested; see [SECURITY.md](SECURITY.md) to verify them.
