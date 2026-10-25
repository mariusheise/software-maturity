# Agent handover

For an agent (or person) continuing this work with no prior context. Read
[README.md](../README.md), [architecture.md](architecture.md) and [status.md](status.md) first;
this file adds the working method, pitfalls and a concrete plan per open item.
Written 2026-10-25 against `main` after PR #31; updated after PR #45.

## 1. Goal

`mariusheise/software-maturity` (public) is a reference repo demonstrating a high software
maturity level with Git and GitHub only, measured against a 28-practice "GitHub CI Software
Maturity Checklist". The checklist text itself is not in the repo; `maturity-checklist.md`
holds only the practice numbers, names and status. Ask the user for the full text before
working on practices 7-10 and 22-28. The code is a tiny C++ library; the value is the system
around it. C, Python and Rust variants are planned.

## 2. Current state (verified at handover)

- 45 PRs merged or closed, no GitHub issues. 7 required checks on `main`: prek, tests,
  coverage, conan-commands, secrets (betterleaks), analyze (c-cpp), clang-tidy. `tests` and
  `coverage` are gate jobs over all products' matrix jobs.
- Releases: `v0.1.0` (+ rc.1, rc.2), `productA_v0.1.0`, `productB_v0.1.0` (+ `-rc.1` each),
  `productA_v0.2.0-rc.1`, `productA_v0.2.0-rc.2`, `productB_v0.2.0-rc.1`. The 0.2.0
  pre-releases prove the tag-driven version (`maturity_app --version` in the tarball) and the
  per-product test report. All assets (tarball, tests, coverage, SBOM) are attested and
  verified. `productA_v0.1.0` is still Latest.
- No README badges since #45 (see open item 9).

## 3. How to work here

- The real repo and tooling live in the devcontainer, not the host checkout. The host folder
  (`C:\Data\Development\SoftwareMaturity`) can be a stale snapshot with no commits. From the
  host shell the container is reached through WSL, for example:
  `wsl.exe -e docker exec -i -w /workspaces/SoftwareMaturity <container-id> <cmd>`.
  The container id changes; find it with `wsl.exe -e docker ps`. Set `MSYS_NO_PATHCONV=1`.
- `gh`, `jq`, clang-tidy and gcovr exist only in the container (full list with pins:
  [dependencies.md](dependencies.md); `jq` arrives with the rebuild after #45). Run the gates locally exactly
  as CI does: `conan maturity:coverage` and `conan maturity:tidy` (both
  `--product productA --target linux-x86_64`). `/opt/venv` belongs to root: after changing
  `.devcontainer/requirements.txt`, rebuild the container rather than `pip install`.
- Claude Code state (sessions, memory, `.claude.json`, login) lives in the Docker volume
  `software-maturity-claude` at `~/.claude` (`CLAUDE_CONFIG_DIR`), so it survives rebuilds.
  Before that volume existed (until PR #38), a rebuild wiped it.
- Files are written through the shell (`tee` with a quoted heredoc). Avoid backslash escapes
  in generated Python or YAML (they get mangled); use `chr(10)` and check `git diff`. Keep
  long edits in separate tool calls: one giant command with several heredocs failed to parse.
- Conan setup: each checkout has its own Conan home in `.conan2/` (`.conanrc`). Run
  `scripts/conan_bootstrap.sh` and `conan config install-pkg .` once (the devcontainer does it),
  then use the `maturity:*` commands; see [conan-commands.md](conan-commands.md). After
  changing the `maturity-config` recipe, run its tests and `conan maturity:config-lock-update`.
- No GPG key in the container: tags are lightweight, commits are signed by GitHub on squash merge.
- Commit messages end with `Co-Authored-By: Claude Code <noreply@anthropic.com>`; PR bodies
  end with the Claude Code generated line.

## 4. Rules of engagement

- Branch, PR, wait for ALL 7 required checks to be `pass`, then admin-merge own PRs
  (`gh pr merge N --squash --admin --delete-branch`). This is authorised for this repo only.
  Do not merge while any check is pending: read the `gh pr checks N` output for `pending`.
  This was violated once on PR #29 (docs only), so be strict.
- Run `prek run --all-files` before committing. New scripts need `git add --chmod=+x`. Files
  must end with a newline (end-of-file-fixer aborts the commit; restage and recommit).
- Never print or store tokens. The repo has no secrets, variables or environments (the badge
  setup was deleted with the badges).
- Ask before pushing release tags: each tag publishes a public release. The tag is the version;
  there is nothing to bump in the repo. Use a hyphenated
  version (pre-release) for tests; a final release takes over the "Latest" marker.
- Keep responses short; the user prefers concise updates.
- CI hygiene: SHA-pin actions (Dependabot updates them), `permissions: {}` at top level, pass
  untrusted values via `env:`, zizmor and actionlint must pass.

## 5. Open work, with suggested approach

Ordered by value. Update `status.md` and `maturity-checklist.md` as items land.

1. **Dependency review (checklist 11).** Add `actions/dependency-review-action` (SHA-pinned)
   on pull requests with `pull-requests: read`. Free on public repos. Add it as a required
   check in ruleset `protect-main` (id 25796571) only after it has run once, so the check
   name exists.
2. **Build both products in CI.** Done for `build-test` (`tests.yml`) and `coverage` (#41).
   The matrices come from `conan maturity:list` and the gate jobs cover them (#45), so a new
   `products/<name>.yml` needs only a lock and a `release-<name>.yml` caller. `clang-tidy` and
   CodeQL stay on productA.
3. **Real product difference.** productB adds zlib only as a placeholder. Decide with the user
   what differs (a CMake toolchain variable, an extra source file, a dependency). Regenerate
   locks with `conan maturity:lock-update`.
4. **CI health (checklist 25-28).** Scheduled workflow plus `scripts/ci_health.py` using
   `gh api` for runs and jobs: success rate on main, P50/P95 duration, queue time, flaky
   re-runs (`run_attempt > 1`), time to green per PR, Conan cache hit rate. Write a job
   summary table, upload JSON, persist history (a data branch, not a gist, which is readable
   by URL; API history is about 90 days). Optional issue when thresholds breach. Needs
   `actions: read`, `contents: read`.
   DORA-style delivery metrics can come from PR merge times and release tags.
5. **Fuzzing, benchmarks, mutation, E2E (checklist 7-10).** Candidates: a libFuzzer target for
   the password and stats code, Google Benchmark with trend storage, mutation testing with
   mull or dextool. Ask which the user wants first; keep each optional and non-blocking at first.
6. **Reusable workflows and runners (checklist 2-3).** `release.yml` is already reusable.
   Extract the shared setup (checkout, python, Conan config bootstrap, cache) into a reusable workflow
   or composite action; keep `permissions` explicit in callers.
7. **Governance and access docs (checklist 22-24).** Extend CONTRIBUTING, add CODE_OF_CONDUCT,
   issue and PR templates. Needs the checklist text.
8. **IaC scanning (checklist 15).** Only relevant if infrastructure code appears (the
   devcontainer Dockerfile could be linted with hadolint).
9. **Private-safe badges.** Build the design in `architecture.md` ("Badges (planned, not
   built)"): `conan maturity:badge`, SVGs on an orphan `badges` branch, relative README
   paths. The old gist, variable, environment and secret are already deleted. For release
   branches, add per-branch SVGs.
10. **Latest marker policy.** Each manifest's `release.latest` (`true`, `false` or `null`)
    drives `gh release create` (#45); both products use `null` (GitHub decides). Only one
    release per repository can be Latest; per-product lists are linked from the README.
11. **C, Python, Rust variants.** Reuse the same gates: format, lint, test, coverage, SBOM,
    attestation, per-language lockfile. Keep the `protect-main` required checks consistent.
12. **Smaller follow-ups:** consider signing tags from a developer machine; decide on a final
    0.2.0 (it would take the Latest marker, see item 10). The Obsidian MCP setup was parked and is unrelated to the repo.

## 6. Known gotchas

- Required-check names must match the job names exactly, including matrix suffixes.
- Reusable workflow callers must grant every permission the callee jobs request.
- A tag filter matches the whole tag: `v*` does not match `productA_v1.0.0`.
- `actions/upload-code-coverage` and Code Quality need a paid plan (PR #22 failed with 404).
- `actions/upload-artifact` `artifact-url` needs a GitHub login to open.
- The coverage PR comment job only runs for same-repo, non-Dependabot PRs.
- clang-tidy findings appear twice on a PR (bot review comment plus check annotation); this is
  GitHub behaviour, not a bug.
- `src/main.cpp` is excluded from coverage (`gcovr.cfg`); the gate is 90% lines. The coverage
  build lives in `build/coverage/Debug` (profile `maturity/coverage`), separate from `build/Debug`.
- The coverage jobs are in `coverage.yml` and the test jobs (`build-test`, `test-comment`,
  `test-badge`) in `tests.yml`, not `ci.yml`. Matrix job outputs overwrite each other; pass
  data between jobs through artifacts.
- `conan config install-pkg` checks every enabled remote; an unreachable conancenter can
  fail it once. Rerun before debugging.
- Plain `conan install .` at the root picks up the config-only `conan.lock`; use
  `conan maturity:install`.
