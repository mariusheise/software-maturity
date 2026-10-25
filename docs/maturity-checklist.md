# Maturity Checklist Status

See [status.md](status.md) for the open work list.

Based on the 28-practice GitHub CI checklist. Rollout order: categories 1, 2, 5
first, then 3 and 4, then 6.

| #     | Practice                                  | Status                                           |
| ----- | ----------------------------------------- | ------------------------------------------------ |
| 1     | Automated build on push/PR                | In place (both products × Release/Debug, Conan cache) |
| 4     | Required tests                            | In place (GoogleTest for both products; sortable test report; 90% line-coverage gate, runnable locally with `conan maturity:coverage`) |
| 5     | Static analysis and linting               | In place (clang-format, CodeQL, -Werror, clang-tidy gate with a pinned version, runnable locally with `conan maturity:tidy`) |
| 6     | prek hooks                                | In place (local and required CI check)           |
| 11    | Dependency scanning                       | In place (Dependabot, dependency review on PRs, daily `conan maturity:audit` of the Conan locks) |
| 12    | Secrets scanning                          | In place (gitleaks, betterleaks, history scan)   |
| 13    | Workflow hardening                        | In place (zizmor, actionlint, SHA pins, read-only token) |
| 17    | Reproducible environment                  | In place (devcontainer, Conan lockfile)          |
| 20    | Branch protection and rulesets            | In place (`protect-main`; owner bypass via PR)   |
| 21    | CODEOWNERS                                | In place (code owner review required)            |
| 2-3   | Runners and reusable workflows            | Planned                                          |
| 7-10  | Fuzzing, performance, E2E, mutation       | Planned                                          |
| 14-16 | Provenance, IaC scanning, Scorecard       | Partial (SBOM, attestations, Scorecard; no IaC scanning)                                        |
| 18-19 | Release and deployment                    | In place (per-product tag releases, version from the tag, attested tarball, test report, coverage report and SBOM) |
| 22-24 | Governance docs and access                | Partial (SECURITY.md, CONTRIBUTING.md)                                        |
| 25-28 | Measurement and improvement               | Planned                                          |
