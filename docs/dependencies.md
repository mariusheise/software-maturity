# Tooling and dependencies

Everything the repository needs to build, test and check itself: where each tool comes from,
how its version is fixed, and what updates it. The devcontainer installs all of it; CI installs
the same pins on GitHub-hosted `ubuntu-24.04` runners. See [architecture.md](architecture.md) for
how the pieces fit together.

## System packages (devcontainer)

From [.devcontainer/Dockerfile](../.devcontainer/Dockerfile), base image `ubuntu:26.04`. Versions
are whatever that Ubuntu release ships; Dependabot (`docker`) proposes new base images.

| Package | Used for |
| --- | --- |
| `build-essential` (gcc, g++, make) | Compiling; the target profile `linux-x86_64` detects this gcc |
| `cmake`, `ninja-build` | The CMake build driven by the recipe's `build()` |
| `gdb` | Debugging |
| `git` | Version control; `maturity:coverage` and `maturity:tidy` use it for `--diff-base` |
| `jq` | Reading `conan maturity:list --format=json` in a shell, as CI does |
| `python3`, `python3-venv` | The virtual environment `/opt/venv` for the Python tools below |
| `ca-certificates` | TLS for downloads (pip, Conan remotes) |

The devcontainer feature `ghcr.io/devcontainers/features/github-cli` adds `gh`
([devcontainer.json](../.devcontainer/devcontainer.json); Dependabot `devcontainers`, with
[devcontainer-lock.json](../.devcontainer/devcontainer-lock.json) pinning the feature).

On CI runners, `jq`, `gh` and `git` are preinstalled by the GitHub runner image.

## Python tools (devcontainer and CI)

From [.devcontainer/requirements.txt](../.devcontainer/requirements.txt), installed into
`/opt/venv` in the image and with `pip install -r .devcontainer/requirements.txt` in every CI job.
Dependabot (`pip`) bumps them; `conan` and `conan-server` are grouped because they must match.

| Package | Pin | Used for |
| --- | --- | --- |
| `conan` | `==2.33.0` | Package manager and the `maturity:*` custom commands |
| `conan-server` | `==2.33.0` | Test harness of the command tests (in-memory remote); must equal `conan` |
| `clang-tidy` | `==23.1.3` | Static analysis (`maturity:tidy`); the PyPI wheel, so devcontainer and CI run the same version |
| `gcovr` | `==8.7` | Coverage reports and gate (`maturity:coverage`) |
| `prek` | `>=0.5.5` | Git hooks and the `prek` CI check (lower bound only, see "Gaps") |
| `pytest` | `==9.1.1` | Tests of the `maturity-config` package |
| `WebTest` | `==3.0.7` | Needed by Conan's test server in those tests |

`/opt/venv` belongs to root because the image builds it. After changing `requirements.txt`, rebuild
the devcontainer; `pip install` inside the running container fails.

CI uses Python 3.12 (`actions/setup-python`), the devcontainer the Python of Ubuntu 26.04 (3.14).
The tools above support both.

## Git hooks (prek)

From [.pre-commit-config.yaml](../.pre-commit-config.yaml), each pinned to a tag. prek downloads
them on first use, locally and in the `prek` CI job.

| Hook | Pin | Checks |
| --- | --- | --- |
| `pre-commit-hooks` | `v5.0.0` | Large files, merge markers, shebangs, YAML, end of file, line endings, whitespace |
| `mirrors-clang-format` | `v18.1.8` | C++ formatting (`.clang-format`); separate from clang-tidy 23.1.3 |
| `gitleaks` | `v8.21.2` | Secrets in staged changes |
| `betterleaks` | `v1.9.0` | Secrets in staged changes (second scanner) |
| `actionlint` | `v1.7.12` | Workflow syntax and shell in workflows |
| `zizmor` | `v1.31.1` | Workflow security (pinning, permissions, injection) |

## CI-only tools

| Tool | Where | Pin | Used for |
| --- | --- | --- | --- |
| GitHub Actions | all workflows | commit SHA (tag in a comment) | Checkout, Python, cache, artifacts, attestations, SBOM, CodeQL |
| Go | `ci.yml` `secrets` | `1.25` (`actions/setup-go`) | Building betterleaks |
| betterleaks | `ci.yml` `secrets` | `v1.9.0` (`go install …@v1.9.0`) | Secret scan of the full git history |
| syft (via `anchore/sbom-action`) | `release.yml` | the action's SHA | CycloneDX SBOM from the product lockfile |

Dependabot (`github-actions`, all actions in one group) bumps the action SHAs weekly, with a 7-day
cooldown for new releases.

## Conan packages

| Package | Pinned in | Updated by | Used for |
| --- | --- | --- | --- |
| `gtest/1.14.0` (test requirement) | `products/<name>.lock` | `conan maturity:lock-update` | Unit tests |
| `zlib/1.3.1` (productB only) | `products/productB.lock` | `conan maturity:lock-update` | Placeholder product difference |
| `maturity-config` (configuration package) | `conan.lock` and every product lock | `conan maturity:config-lock-update` | Profiles and the `maturity:*` commands |

Dependencies come from conancenter; `maturity-config` from the in-repo recipe index
`conan-recipes/` (see [conan-commands.md](conan-commands.md)). Locks store exact versions and
recipe revisions, so a build is reproducible until someone runs `lock-update` and commits the
result. Dependabot does not cover Conan.

## Gaps

- **prek hooks**: no Dependabot coverage. Update with `prek autoupdate` and commit the new
  `rev:` values (review the diffs; they run on every commit).
- **`prek`**: only a lower bound (`>=0.5.5`), so a new prek release reaches CI without a PR. Pin it
  exactly if that ever causes trouble.
- **Conan dependencies**: no automatic update PRs; run `conan maturity:lock-update` periodically.
- **Two clang versions**: clang-format comes from the `v18.1.8` hook, clang-tidy from the
  `23.1.3` wheel. They don't interact, but bumping one doesn't bump the other.
