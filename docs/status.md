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
| Static analysis     | clang-tidy with SARIF to code scanning (#20); findings fail the build, required check (#26) |
| Conan commands      | `maturity:config-lock-update` first-run failure after a recipe edit fixed with a scoped `--update` (#35) |
| Reproducibility     | Conan lockfile (#21); per-product lockfiles (#28); config package via `conanconfig.yml` and a local recipe index, pinned in `conan.lock`, with `maturity:*` custom commands and `products/` discovery, per-checkout Conan home via `.conanrc`, command tests in the `conan-commands` CI job (#31) |
| Releases            | Tag-triggered release with SBOM and attestations (#12); coverage report as asset (#25); auto pre-release flag and `actions/attest` (#27); reusable workflow with per-product tags (#28) |
| Governance docs     | SECURITY.md, CONTRIBUTING.md (#11); checklist status (#3)            |
| Dependency updates  | Dependabot bumps for ubuntu, conan, prek (#4 to #6); pytest 9.1.1, gcovr 8.7 (#32, #33) |

Closed without merging: #18 (demo PR for uncovered code), #22 (code coverage API upload,
needs a paid plan).

Releases published: `v0.1.0` (plus rc.1, rc.2), `productA_v0.1.0`, `productB_v0.1.0`
(plus `-rc.1` pre-releases). `productA_v0.1.0` currently carries the Latest marker.

## Open

1. Add a dependency-review check (checklist 11).
2. Build both products in CI (a product matrix changes required check names; update the ruleset).
3. Give productB a real difference, or replace the placeholder zlib dependency.
4. Fuzzing, performance benchmarks, E2E and mutation testing (checklist 7 to 10).
5. Runner strategy and more reusable workflows (checklist 2 and 3).
6. IaC scanning (checklist 15) if infrastructure code appears.
7. Governance and access documents beyond SECURITY and CONTRIBUTING (checklist 22 to 24).
8. Measurement and improvement loop (checklist 25 to 28).
9. Release-branch support for the coverage badge: per-branch gist file, `release/**`
   trigger, environment and ruleset extension. Do this when the first release branch exists.
10. Decide who owns the GitHub "Latest" marker across products.
11. Add C, Python and Rust variants.

## Conventions for the next session

- Work on a branch, open a PR, wait for the 8 required checks, then admin-merge own PRs
  (authorised for this repo only).
- Run `prek run --all-files` before committing; new scripts need `git add --chmod=+x`.
- Never paste tokens in chat; `GIST_TOKEN` lives only in the `coverage-badge` environment.
- Do not push release tags without asking; each tag publishes a public release.
