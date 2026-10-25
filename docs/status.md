# Status and handover

Last updated 2026-10-25. Working method and per-item plans: [agent-handover.md](agent-handover.md). The repo has no GitHub issues; work was tracked as PRs. This file
is the source of truth for what is done and what is open.

## Done (PR numbers)

| Area                | Work                                                                 |
| ------------------- | -------------------------------------------------------------------- |
| CI and hooks        | CI with prek and build/test matrix (#1); workflow linting, betterleaks, Dependabot, history secret scan (#2) |
| Security scanning   | CodeQL and Scorecard (#7, #9); dummy-secret test excluded on purpose (#8) |
| Coverage            | 90% gate (#10); annotations and summary (#13); sticky PR comment, coloured HTML (#14); Pages tried, replaced by expiring artifact (#15, #16); inline annotations added, then removed (#17, #19); run-summary link (#24); gist badge on main (#23) |
| Coverage (local)    | (#34) `conan maturity:coverage` in `maturity-config`: coverage profile with its own build folder, gcovr via `gcovr.cfg`, reports in `build/coverage-report/`, changed-lines figure via `--diff-base`; same command in CI (own `coverage.yml`) and releases; replaces `scripts/coverage.sh` and `coverage_annotate.py` |
| Static analysis     | clang-tidy with SARIF to code scanning (#20); findings fail the build, required check (#26); `conan maturity:tidy` with clang-tidy pinned at 23.1.3 (PyPI) for devcontainer and CI, own configure-only folder, `tests/` now checked too (#37) |
| Conan build         | `conan maturity:build` (canonical `conan build`, `--skip-test` maps to `tools.build:skip_test`) replaces `scripts/build.sh` in CI, CodeQL and releases; `BUILD_TESTING` set both ways in `generate()`; shared `graph_args` helper (#36) |
| Conan commands      | `maturity:config-lock-update` first-run failure after a recipe edit fixed with a scoped `--update` (#35) |
| Reproducibility     | Conan lockfile (#21); per-product lockfiles (#28); config package via `conanconfig.yml` and a local recipe index, pinned in `conan.lock`, with `maturity:*` custom commands and `products/` discovery, per-checkout Conan home via `.conanrc`, command tests in the `conan-commands` CI job (#31) |
| Test report         | Sortable single-file HTML test report from `maturity:build`/`maturity:coverage` (ctest JUnit, `_tests.py`); `tests.yml` with `build-test` for both products and build types, artifacts, sticky PR comment; coverage for both products; release asset per product (#41) |
| Product manifests   | `products/<name>.yml` validated against a schema with shipped `defaults.yml`; `conan maturity:list` (text, JSON) (#43); `conf:` as `user.maturity.product:*`, `targets`, `coverage.fail_under` as the gate (#44); CI matrices from `maturity:list`, gate jobs `tests` and `coverage` so new products need no ruleset change (7 required checks), `release.latest` in `release.yml`, per-product release links; badges dropped (#45) |
| Versioning          | Version only from the release tag: no `version` in `conanfile.py`/`CMakeLists.txt`, `maturity:build --version`, `MATURITY_VERSION` into `version.hpp`, `maturity_app --version`, checked by ctest and in `release.yml` (#40) |
| Releases            | Tag-triggered release with SBOM and attestations (#12); coverage report as asset (#25); auto pre-release flag and `actions/attest` (#27); reusable workflow with per-product tags (#28); version from the tag (#40); attested test report of the released product (#41) |
| Governance docs     | SECURITY.md, CONTRIBUTING.md (#11); checklist status (#3)            |
| Dependency scanning | `dependency-review` on PRs (actions, pip); `conan maturity:audit` wraps `conan audit scan` per product, gate `audit.severity_level` (CVSS 7.0) and accepted ids with reasons (`audit.ignore`) in the manifest; zlib bumped to 1.3.2 after the first scan, its two remaining High CVEs accepted for productB (zlib is never linked); reports in `build/audit-report/`; `audit.yml` daily and on dependency changes, token in secret `CONAN_AUDIT_TOKEN` (#46) |
| Dependency updates  | Dependabot bumps for ubuntu, conan, prek (#4 to #6); pytest 9.1.1, gcovr 8.7 (#32, #33) |

Closed without merging: #18 (demo PR for uncovered code), #22 (code coverage API upload,
needs a paid plan).

Releases published: `v0.1.0` (plus rc.1, rc.2), `productA_v0.1.0`, `productB_v0.1.0`
(plus `-rc.1` pre-releases), and the pre-releases `productA_v0.2.0-rc.1` (first tag-driven
version), `productA_v0.2.0-rc.2` and `productB_v0.2.0-rc.1` (first with the test report; each
contains only its own product's tests, coverage and SBOM). `productA_v0.1.0` still carries the
Latest marker.

The README has no badges (dropped in #45: shields.io and the unlisted gist leak data and don't
work for private repositories). A private-safe design is planned in
[architecture.md](architecture.md#badges-planned-not-built).

## Open

1. Make `dependency-review` a required check once it has run on `main`'s PRs (ruleset
   `protect-main`). `audit` stays optional (path filter, daily schedule).
2. Build both products in CI: done for tests and coverage (#41); clang-tidy and CodeQL stay on
   productA (same sources).
3. Give productB a real difference, or replace the placeholder zlib dependency. Removing zlib
   also removes the two accepted CVEs in `products/productB.yml` (`audit.ignore`).
4. Fuzzing, performance benchmarks, E2E and mutation testing (checklist 7 to 10).
5. Runner strategy and more reusable workflows (checklist 2 and 3).
6. IaC scanning (checklist 15) if infrastructure code appears.
7. Governance and access documents beyond SECURITY and CONTRIBUTING (checklist 22 to 24).
8. Measurement and improvement loop (checklist 25 to 28).
9. Private-safe badges (coverage, tests, release version per product) on an orphan `badges`
   branch, as designed in [architecture.md](architecture.md#badges-planned-not-built). The old
   gist-based setup is fully deleted.
10. "Latest" marker: the mechanism exists (`release.latest` in each manifest, #45); both
    products use the default (GitHub decides). Decide a policy when a final release is due.
11. Add C, Python and Rust variants.

## Conventions for the next session

- Work on a branch, open a PR, wait for the 7 required checks, then admin-merge own PRs
  (authorised for this repo only).
- Run `prek run --all-files` before committing; new scripts need `git add --chmod=+x`.
- Never paste tokens in chat. The repo currently holds no secrets of its own.
- Do not push release tags without asking; each tag publishes a public release.
