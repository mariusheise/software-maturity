# Maturity Checklist Status

Based on the 28-practice GitHub CI checklist. Rollout order: categories 1, 2, 5
first, then 3 and 4, then 6.

| #     | Practice                                  | Status                                           |
| ----- | ----------------------------------------- | ------------------------------------------------ |
| 1     | Automated build on push/PR                | In place (Release/Debug matrix, Conan cache)     |
| 4     | Required tests                            | In place (GoogleTest; 90% line-coverage gate) |
| 5     | Static analysis and linting               | In place (clang-format, CodeQL, -Werror)          |
| 6     | prek hooks                                | In place (local and required CI check)           |
| 11    | Dependency scanning                       | Partial (Dependabot; dependency review planned)  |
| 12    | Secrets scanning                          | In place (gitleaks, betterleaks, history scan)   |
| 13    | Workflow hardening                        | In place (zizmor, actionlint, SHA pins, read-only token) |
| 17    | Reproducible environment                  | In place (devcontainer, Conan lockfile)          |
| 20    | Branch protection and rulesets            | In place (`protect-main`; owner bypass via PR)   |
| 21    | CODEOWNERS                                | In place (code owner review required)            |
| 2-3   | Runners and reusable workflows            | Planned                                          |
| 7-10  | Fuzzing, performance, E2E, mutation       | Planned                                          |
| 14-16 | Provenance, IaC scanning, Scorecard       | Partial (SBOM, attestations, Scorecard; no IaC)                                        |
| 18-19 | Release and deployment                    | Partial (tag-triggered release workflow)                                        |
| 22-24 | Governance docs and access                | Partial (SECURITY.md, CONTRIBUTING.md)                                        |
| 25-28 | Measurement and improvement               | Planned                                          |
