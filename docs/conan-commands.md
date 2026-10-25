# Conan custom commands (`maturity:*`)

The `maturity:*` commands wrap the Conan calls this project needs: installing and building a
product variant for a target and build type, keeping the lockfiles current, the coverage run and
clang-tidy. They ship inside the
configuration package `maturity-config`, together with the profiles they use, and are tested
next to the recipe. See [architecture.md](architecture.md) for how this fits into the build.

## Where things live

| Path                                                   | Content                                         |
| ------------------------------------------------------ | ----------------------------------------------- |
| `conanconfig.yml`                                      | Config packages to install (version range)      |
| `conan.lock`                                           | Pins their exact version and recipe revision    |
| `.conanrc`                                             | Per-checkout Conan home in `.conan2/`           |
| `products/<name>.yml`, `products/<name>.lock`          | Product variants and their lockfiles            |
| `conan-recipes/recipes/maturity-config/all/`           | The recipe (stands in for a remote, see below)  |
| `.../all/profiles/maturity/`                           | Profiles shipped by the package                 |
| `.../all/extensions/commands/maturity/`                | The commands (`cmd_*.py`) and `_maturity.py`    |
| `.../all/test/`                                        | Tests of the package and commands               |

Nothing in the project references files of the package by path. Everything goes through the
package reference `maturity-config`, so the recipe can move to Artifactory without changes to
the consumer.

## Setup

The devcontainer and CI do this automatically:

```sh
scripts/conan_bootstrap.sh     # build maturity-config from the in-repo recipe index
conan config install-pkg .     # install it; picks up conan.lock automatically
```

`conan config install-pkg` only downloads ready-built packages, so while the recipe lives in
this repo, `conan_bootstrap.sh` first builds it from `conan-recipes/` (registered as the
local-recipes-index remote `maturity-recipes`).

`.conanrc` gives every checkout its own Conan home. Checkouts of different release branches
can use different `maturity-config` versions side by side, because one Conan home can hold only
one installed version. Dependencies are built once per checkout.

## Commands

All commands take an optional `path` (the repository root, default `.`).

### `conan maturity:install`

```sh
conan maturity:install --product=productA --target=linux-x86_64 --build-type=debug
```

| Option         | Default   | Meaning                                                     |
| -------------- | --------- | ----------------------------------------------------------- |
| `--product`    | required  | A variant from `products/`                                  |
| `--target`     | required  | A profile under `maturity/target/`                          |
| `--build-type` | `release` | A profile under `maturity/build_type/`                      |
| `--build`      | `missing` | Passed through as Conan's `--build` policy                  |

It runs `conan install` with:

- the lockfile `products/<product>.lock`
- the `options` of `products/<product>.yml` as `-o &:<key>=<value>`
- host profiles `maturity/target/<target>` and `maturity/build_type/<build type>`
- build profiles `maturity/target/linux-x86_64` and `maturity/build_type/release` (the build machine)

It prints the full command line. Unknown products, targets or build types fail with the
available choices. A missing lockfile fails with a hint to run `lock-update`.

### `conan maturity:build`

```sh
conan maturity:build --product productA --target linux-x86_64                    # Release, tests
conan maturity:build --product productA --target linux-x86_64 --build-type debug
conan maturity:build --product productB --target linux-x86_64 --skip-test        # no tests
```

| Option         | Default   | Meaning                                                     |
| -------------- | --------- | ----------------------------------------------------------- |
| `--product`    | required  | A variant from `products/`                                  |
| `--target`     | required  | A profile under `maturity/target/`                          |
| `--build-type` | `release` | A profile under `maturity/build_type/`                      |
| `--skip-test`  | off       | Build without the unit tests                                |
| `--version`    | none      | Version of the build, passed to `conan build --version`     |
| `--build`      | `missing` | Passed through as Conan's `--build` policy                  |

This is the canonical `conan build`: install, generate and the recipe's `build()` (CMake
configure, build, then `ctest --output-on-failure --no-tests=error`), with the same lockfile,
options and profiles as `maturity:install` (the shared helper `graph_args` in `_maturity.py`
composes them for `install`, `build` and `coverage`). The output lands in `build/<Build type>/`,
for example `build/Release/maturity_app`.

`--skip-test` passes Conan's own test switch, `-c tools.build:skip_test=True`. `CMake.ctest()`
then does nothing, and `BUILD_TESTING` is `OFF`, so `CMakeLists.txt` neither builds the test
executable nor looks for gtest. gtest is still resolved from the lockfile, which keeps the lock
valid. The recipe's `generate()` sets `BUILD_TESTING` to `ON` again for a build without the
flag. Conan alone only ever sets `OFF`, and a cached `OFF` would make the next build run the old
test binary without rebuilding it.

`--version` is Conan's way to supply a version the recipe doesn't declare. `conanfile.py`
has no `version`; the release workflow passes the one from the tag. The recipe hands it to CMake
as `MATURITY_VERSION`, or `0.0.0-dev` without the option. The root package is not in the
lockfile, so the version never changes a lock.

Unless `--skip-test` is given, it also writes a **test report** to `build/test-report/`:
`<product>-<build type>.html` (one self-contained, sortable file), `.md` (counts and slowest
tests; also appended to the GitHub job summary) and `.json` (the totals). It passes
`-c user.maturity:junit=<file>.xml`, and the recipe's `build()` hands that path to
`ctest --output-junit`; `_tests.py` turns the JUnit XML into the report. A failing test still
produces the report before the command fails. `maturity:coverage` does the same, writing
`build/coverage-report/tests.html`.

CI (`build-test` in `tests.yml`, for both products and build types), CodeQL and releases run
this command with tests; releases add `--version`.

### `conan maturity:lock-update`

```sh
conan maturity:lock-update                     # all products, all targets
conan maturity:lock-update --product productB  # one product
```

It regenerates `products/<product>.lock` from `conanfile.py` (newest versions the recipe
allows). It starts from scratch for the first target and build type and merges in the others,
so one lock covers every combination. Then it adds the installed config packages as
`config_requires`. A product with only a `.yml` gets its `.lock` here.

### `conan maturity:config-lock-update`

```sh
conan maturity:config-lock-update
```

It re-resolves `conanconfig.yml` (newest version in range), installs the result, and pins it in
`conan.lock` and in every `products/*.lock`. Config packages that a remote has as a recipe but
not as a binary, like the in-repo index today, are built first. That build step passes
`--update=<package>`, because `install-pkg` always checks the remotes: without it, the build
step took the older revision from the cache, and the first run after a recipe edit failed with
"Missing prebuilt package" (fixed in #35).

### `conan maturity:coverage`

```sh
conan maturity:coverage --product productA --target linux-x86_64
conan maturity:coverage --product productA --target linux-x86_64 --diff-base origin/main
```

| Option         | Default   | Meaning                                                          |
| -------------- | --------- | ---------------------------------------------------------------- |
| `--product`    | required  | A variant from `products/`                                       |
| `--target`     | required  | A profile under `maturity/target/`                               |
| `--fail-under` | manifest  | Minimum line coverage in percent (default: `coverage.fail_under`, 90) |
| `--diff-base`  | none      | Also report coverage of lines changed since the merge base with this revision |
| `--build`      | `missing` | Passed through as Conan's `--build` policy                       |

It is the coverage gate of CI, runnable locally with the same result:

1. Deletes `*.gcda` counters left in `build/coverage/` by earlier runs.
2. Runs `conan build` with the arguments of `maturity:install` for the debug build type, plus
   the profile `maturity/coverage`. The recipe's `build()` configures, builds and runs ctest.
3. Runs gcovr on `build/coverage/`. Filters and exclusions come from the project's
   `gcovr.cfg`, so the command has nothing project-specific in it.
4. Writes to `build/coverage-report/`: `coverage-report.html` (one self-contained file with
   the coloured sources), `coverage.json`, `coverage.xml` (Cobertura) and
   `coverage-summary.md` (the PR comment body). It prints the summary and the report path.
5. With `--diff-base`, the summary also gives the coverage of the changed lines: the diff from
   the merge base to the working tree, so uncommitted edits count. CI passes `HEAD^1` on PRs.
6. Fails if the line coverage is below the gate, after the reports are written. The gate is
   `--fail-under` if given, otherwise the product's `coverage.fail_under` (90 from
   `defaults.yml`). The result line names its source, e.g.
   `meets the gate of 90% (defaults.yml)`.

On GitHub Actions it also writes the summary to the job summary and the step output
`line-percent`. It needs `gcovr` on `PATH`, and a recipe with
`cmake_layout()` and a `build()` that runs the tests.

### `conan maturity:tidy`

```sh
conan maturity:tidy --product productA --target linux-x86_64
conan maturity:tidy --product productA --target linux-x86_64 --diff-base origin/main
conan maturity:tidy --product productA --target linux-x86_64 --fix
```

| Option        | Default   | Meaning                                                           |
| ------------- | --------- | ----------------------------------------------------------------- |
| `--product`   | required  | A variant from `products/`                                        |
| `--target`    | required  | A profile under `maturity/target/`                                |
| `--diff-base` | none      | Only files changed since the merge base with this revision        |
| `--fix`       | off       | Apply clang-tidy's fixes, then check again                        |
| `--build`     | `missing` | Passed through as Conan's `--build` policy                        |

It is the `clang-tidy` CI check, runnable locally with the same result:

1. Runs `conan install` with the arguments of `maturity:install` for the debug build type plus
   the profile `maturity/tidy`, then `cmake --preset conan-tidy-debug`. It only configures, so
   nothing is compiled. It configures fresh on every run, so the compile database always
   matches the requested product and lockfile.
2. Checks every translation unit in `build/tidy/Debug/compile_commands.json` that lies in the
   repository and outside `build/`. With `--diff-base`, it checks only the files changed since
   the merge base, including uncommitted edits.
3. Which checks run, and which headers are reported (`HeaderFilterRegex`,
   `ExcludeHeaderFilterRegex`), come from the project's `.clang-tidy`, so the command has
   nothing project-specific in it.
4. Writes `build/tidy-report/clang-tidy.log` and `clang-tidy.sarif`, the latter for GitHub code
   scanning, and fails on any finding.

It prints the clang-tidy version it found. The project pins `clang-tidy==23.1.3` (PyPI wheel)
in `.devcontainer/requirements.txt` for both the devcontainer and CI. It needs `clang-tidy` and
`cmake` on `PATH`.

### `conan maturity:audit`

```sh
export CONAN_AUDIT_PROVIDER_TOKEN_CONANCENTER=<token>   # or once: conan audit provider auth conancenter --token=<token>
conan maturity:audit
conan maturity:audit --product productB --severity-level 9
```

| Option             | Default       | Meaning                                                      |
| ------------------ | ------------- | ------------------------------------------------------------ |
| `--product`        | all           | A variant from `products/`                                   |
| `--target`         | all of the product's | A profile under `maturity/target/`                    |
| `--severity-level` | manifest      | Fail on a vulnerability with this CVSS score or higher (default: `audit.severity_level`, 7.0) |
| `--provider`       | `conancenter` | Conan audit provider                                         |

It is the `audit` CI workflow, runnable locally with the same result:

1. For each product and each of its targets, runs `conan audit scan` with the arguments of
   `maturity:install` for the release build type. That resolves the graph from the product's
   lockfile, so it scans exactly the locked versions; nothing is built.
2. Writes to `build/audit-report/`, per product and target: `<product>-<target>.json` (the raw
   scan), `.html` (Conan's report) and `.md` (a table, worst first, also appended to the GitHub
   job summary). Packages the provider doesn't know, such as private ones, are listed as "not
   scanned".
3. Fails if any vulnerability reaches the product's gate: `--severity-level` if given,
   otherwise the manifest's `audit.severity_level` (7.0, CVSS "High", from `defaults.yml`).
   Conan's own threshold is switched off so the gate can differ per product.
4. Vulnerabilities listed in the manifest's `audit.ignore` (id: reason) are accepted: they stay
   in the reports with their reason in an "Accepted" column but don't fail the gate. A new
   vulnerability still fails. An accepted id the provider no longer reports for that product
   gives a warning, so fixed entries get removed.

```yaml
# products/productB.yml
audit:
  ignore:
    CVE-2026-76844: "zlib is required but never linked or called (placeholder dependency)"
```

Use it only with a reason someone can check (not reachable, not linked, mitigated elsewhere),
and remove the entry when a fixed version is locked.

The provider is audit.conan.io. It needs a free token (register at
<https://conan.io/audit/register>). Conan reads it from the environment variable
`CONAN_AUDIT_PROVIDER_TOKEN_CONANCENTER`, or from `conan audit provider auth conancenter
--token=<token>`, which stores it in the Conan home (`.conan2/`, ignored by git). Never put it
in a file in the repository. The free tier has a request limit; every scanned package is one
request.

## Products and profiles

A product variant is a pair of files with the same name in `products/`: a **manifest**
`<name>.yml` and its lockfile `<name>.lock`. A `.lock` without a `.yml` is ignored with a
warning.

```yaml
# products/productB.yml
description: Base product plus zlib   # people only
options:                              # Conan options of the root recipe: -o &:<key>=<value>
  product: productB
conf: {}                              # build settings that aren't options: -c user.maturity.product:<key>=<value>
targets: [linux-x86_64]               # target profiles this product supports (default: all)
coverage:
  fail_under: 90                      # coverage gate in percent
audit:
  severity_level: 7.0                 # CVSS score that fails maturity:audit
  ignore: {}                          # accepted vulnerabilities, id: reason
release:
  latest: null                        # GitHub "Latest" marker: null = GitHub decides
```

Every command validates every manifest before it runs. An unknown key at any level (such as a
typo `fail_undre`), a wrong type or an out-of-range value fails with the file, the key and the
allowed keys. Only `description` and `options` are needed. The rest comes from `defaults.yml`,
shipped in the config package next to the commands, and a manifest overrides it key by key.

| Key | Type | Default | Used by |
|---|---|---|---|
| `description` | string | `""` | people, `maturity:list` |
| `options` | map of scalars | `{}` | every command: `-o &:<key>=<value>` for the root recipe |
| `conf` | map of scalars | `{}` | every command: `-c user.maturity.product:<key>=<value>` |
| `targets` | list of target profiles | all `maturity/target/*` | `lock-update` locks only these; `install`, `build`, `coverage` and `tidy` reject other `--target`s |
| `coverage.fail_under` | number 0–100 | 90 | `maturity:coverage` default gate (`--fail-under` overrides) |
| `audit.severity_level` | number 0–10 | 7.0 | `maturity:audit` gate: fails on a vulnerability with this CVSS score or higher (`--severity-level` overrides) |
| `audit.ignore` | map of id to reason | `{}` | `maturity:audit`: accepted vulnerabilities, reported but not gated; stale ids give a warning |
| `release.latest` | `true`, `false`, `null` | `null` | `release.yml`: `--latest` / `--latest=false` for `gh release create`; `null` lets GitHub decide |

### `conan maturity:list`

```sh
conan maturity:list                                  # readable summary
conan maturity:list --format=json                    # for CI and scripts
conan maturity:list --product productB --format=json
```

It prints the validated manifests merged over the defaults, with `targets` resolved to the
actual profiles. JSON: `{"products": {<name>: <manifest>}, "targets": [...], "build_types": [...]}`.
CI and scripts read product data through this command rather than parsing the YAML:
`tests.yml` and `coverage.yml` build their product matrix from `.products | keys`, and
`release.yml` reads `.products[<product>].release.latest`.

### Three channels from a manifest

- **`options`** reach the root recipe as Conan options (`self.options.<key>`). They change the
  package ID and can change the dependency graph, so use them for what defines the product:
  features and dependencies. The recipe must declare each option.
- **`conf`** reaches the root recipe as `user.maturity.product:<key>` (read it with
  `self.conf.get("user.maturity.product:<key>")`, e.g. in `generate()` into a CMake cache
  variable). It doesn't change the package ID; use it for build or tool settings.
  `lock-update` passes it too, in case a recipe reads it in `requirements()`.
- **Everything else** (`targets`, `coverage`, `release`) is read by the commands and, through
  `maturity:list --format=json`, by CI. It never reaches Conan.

Profiles live on two axes, so new variants are new files rather than combinations:

- `maturity/target/<os>-<arch>[-<compiler>]`: OS, architecture and compiler. `linux-x86_64`
  uses gcc, finds its version with `detect_api` and sets C++20. No default profile is needed.
- `maturity/build_type/<cmake build type, lowercase>`: `release`, `debug`.

`maturity/coverage` is an extra profile, not an axis, stacked last by `maturity:coverage`. It
sets `build_type=Debug`, adds `--coverage` to the compile and link flags of the consumer only
(`&:`, so dependencies built from source are never instrumented), and sets
`build_folder_vars=["const.coverage"]`. The coverage build therefore lives in
`build/coverage/Debug` with presets `conan-coverage-debug`, and the regular `build/Debug`
stays uninstrumented.

`maturity/tidy` is the same kind of extra profile for `maturity:tidy`: `build_type=Debug` and
`build_folder_vars=["const.tidy"]`, so it configures `build/tidy/Debug` (presets
`conan-tidy-debug`).

Later additions such as `target/linux-armv8`, `target/windows-x86_64` or
`build_type/relwithdebinfo` are picked up by the commands automatically.

## Version pinning

The config package is versioned like any Conan package. The recipe revision is a hash of the
exported files, so the same content gives the same revision on every machine.

- `conanconfig.yml` holds the range, and `conan.lock` holds the exact revision.
  `conan config install-pkg .` fails if the locked revision is unavailable. With the in-repo
  recipe, that means the recipe was changed without updating the lock.
- Each product lock pins the config revision too. `maturity:install` then fails
  ("Installed config packages [...] not in the lockfile") if the Conan home has a different
  config than the product was locked with.

## Common tasks

| Task                          | Steps                                                                    |
| ----------------------------- | ------------------------------------------------------------------------ |
| Change a command or profile   | Edit the recipe, run its tests, `conan maturity:config-lock-update`; commit the recipe, `conan.lock` and `products/*.lock` |
| See the products and their settings | `conan maturity:list` (`--format=json` for scripts) |
| Build and test                | `conan maturity:build --product <name> --target <target> [--build-type debug]` |
| Run clang-tidy before a PR    | `conan maturity:tidy --product productA --target linux-x86_64 [--diff-base origin/main]` |
| Check dependencies for known vulnerabilities | `conan maturity:audit` (token in `CONAN_AUDIT_PROVIDER_TOKEN_CONANCENTER`); open `build/audit-report/*.html` |
| Upgrade dependencies          | `conan maturity:lock-update`; commit `products/*.lock`                   |
| Check coverage before a PR    | `conan maturity:coverage --product productA --target linux-x86_64 --diff-base origin/main`; open `build/coverage-report/coverage-report.html` |
| Add a product variant         | Add `products/<name>.yml`, run `conan maturity:lock-update --product <name>`, add a `release-<name>.yml` caller workflow (tag triggers cannot be discovered) |
| Add a target or build type    | Add the profile file, then as for "Change a command or profile"          |

Run `conan install .` at the root only through `maturity:install`. Plain `conan install .`
would pick up the config-only `conan.lock`.

## Tests

The tests live in `conan-recipes/recipes/maturity-config/all/test/`, next to the recipe. They
use a small fixture project of their own (a `conanfile.py` without dependencies and two test
products), not this repository's code, so they move with the recipe when it is split out.
This project's real use of the commands is covered by the regular build jobs.

```sh
python -m pytest conan-recipes/recipes/maturity-config/all/test
```

| Layer | File                       | What it covers                                                     |
| ----- | -------------------------- | ------------------------------------------------------------------ |
| 1     | `test_maturity_helpers.py` | `_maturity.py` functions on their own: product discovery, choice checks, argument building, reading `conanconfig.yml` and the installed config. No Conan home. |
| 1     | `test_audit_helpers.py`    | `_audit.py`: findings from a scan result, the summary against the gate, the written reports. |
| 1     | `test_coverage_helpers.py` | `_coverage.py`: the summary table, excluded lines, changed lines from a temporary git repository (including uncommitted edits), GitHub outputs. |
| 2     | `test_commands.py`         | Each command through the real Conan CLI, loaded straight from the source folder into a throwaway Conan home with the recipe's profiles. Checks the generated command lines, lockfile contents, error messages and the config pin check. `maturity:audit` runs against a faked provider, so no token or network is needed. |
| 3     | `test_packaging.py`        | Builds the real package, checks it contains only profiles and commands, uploads it to an in-memory Conan server, installs it with `config install-pkg` as a consumer would, and runs the commands from the installed package. |

All layers take about two seconds. Notes:

- Layers 2 and 3 use Conan's own test harness, `TestClient` from `conan.test.utils.tools`.
  It isn't a documented public API, so a Conan upgrade can break it. Conan is pinned exactly in
  `.devcontainer/requirements.txt`, so such a break shows up on the Dependabot PR.
- The harness needs `conan-server` (same version as `conan`) and `WebTest`. Both are pinned in
  `.devcontainer/requirements.txt`, and Dependabot bumps `conan` and `conan-server` together.
- `test/` and `*.pyc` files are excluded from the exported recipe, so editing tests doesn't
  change the recipe revision. `conftest.py` turns off bytecode writing so no `__pycache__`
  ends up next to the command modules.
- CI runs the tests in the `conan-commands` job of `ci.yml`.

## Splitting the recipe out

1. Move `conan-recipes/recipes/maturity-config/` into its own repository, including `test/`.
   Its CI runs the tests, then `conan create` and `conan upload` to Artifactory.
2. In this project, add the Artifactory remote (or `urls:` in `conanconfig.yml`), and delete
   `conan-recipes/` and `scripts/conan_bootstrap.sh`.
3. `conanconfig.yml`, `conan.lock` and `products/*.lock` stay as they are, provided the recipe
   is uploaded unchanged (same revision).

## Limitations

- `conan config install-pkg` is marked experimental by Conan.
- One Conan home has one installed config version; `.conanrc` makes that per checkout.
- `install-pkg` checks every enabled remote for updates, so an unreachable remote such as
  conancenter can fail it. Rerun it if that happens.
- `install-pkg` copies files but never deletes them. A file removed from the package stays in
  existing Conan homes until `conan config clean` or a fresh home.
