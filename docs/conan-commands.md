# Conan custom commands (`maturity:*`)

The `maturity:*` commands wrap the Conan calls this project needs: installing a product variant
for a target and build type, and keeping the lockfiles current. They ship inside the
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
available choices. A missing lockfile fails with a hint to run `lock-update`. `scripts/build.sh`,
`coverage.sh` and `clang_tidy.sh` call this command, reading `PRODUCT` and `TARGET` from the
environment.

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
not as a binary, like the in-repo index today, are built first.

## Products and profiles

A product variant is a pair of files with the same name in `products/`:

```yaml
# products/productB.yml
description: Base product plus zlib
options:
  product: productB
```

A `.lock` without a `.yml` is ignored with a warning.

Profiles live on two axes, so new variants are new files rather than combinations:

- `maturity/target/<os>-<arch>[-<compiler>]`: OS, architecture and compiler. `linux-x86_64`
  uses gcc, finds its version with `detect_api` and sets C++20. No default profile is needed.
- `maturity/build_type/<cmake build type, lowercase>`: `release`, `debug`.

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
| Upgrade dependencies          | `conan maturity:lock-update`; commit `products/*.lock`                   |
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
| 2     | `test_commands.py`         | Each command through the real Conan CLI, loaded straight from the source folder into a throwaway Conan home with the recipe's profiles. Checks the generated command lines, lockfile contents, error messages and the config pin check. |
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
