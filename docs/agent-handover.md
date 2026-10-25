# Agent handover

For an agent (or person) continuing this work with no prior context. Read
[README.md](../README.md), [architecture.md](architecture.md) and [status.md](status.md) first;
this file adds the working method, pitfalls and a concrete plan per open item.
Written 2026-10-25 against `main` after PR #31; updated after PR #37.

## 1. Goal

`mariusheise/software-maturity` (public) is a reference repo demonstrating a high software
maturity level with Git and GitHub only, measured against a 28-practice "GitHub CI Software
Maturity Checklist". The checklist text itself is not in the repo; `maturity-checklist.md`
holds only the practice numbers, names and status. Ask the user for the full text before
working on practices 7-10 and 22-28. The code is a tiny C++ library; the value is the system
around it. C, Python and Rust variants are planned.

## 2. Current state (verified at handover)

- 37 PRs merged or closed, no GitHub issues. Required checks on `main`: prek,
  build-test (Release), build-test (Debug), secrets (betterleaks), analyze (c-cpp), coverage,
  clang-tidy, conan-commands.
- Releases: `v0.1.0` (+ rc.1, rc.2), `productA_v0.1.0`, `productB_v0.1.0` (+ `-rc.1` each).
  Release assets are attested and verified. The `actions/attest` swap and the auto
  pre-release flag are proven by the product releases.
- Not verified: the rendered coverage badge after the gist cache delay (the gist JSON itself
  is correct: schemaVersion 1, label coverage, message 100.0%, color brightgreen).
  Check that the README badge renders green.

## 3. How to work here

- The real repo and tooling live in the devcontainer, not the host checkout. The host folder
  (`C:\Data\Development\SoftwareMaturity`) can be a stale snapshot with no commits. From the
  host shell the container is reached through WSL, for example:
  `wsl.exe -e docker exec -i -w /workspaces/SoftwareMaturity <container-id> <cmd>`.
  The container id changes; find it with `wsl.exe -e docker ps`. Set `MSYS_NO_PATHCONV=1`.
- `gh`, `jq`, clang-tidy and gcovr exist only in the container. Run the gates locally exactly
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

- Branch, PR, wait for ALL 8 required checks to be `pass`, then admin-merge own PRs
  (`gh pr merge N --squash --admin --delete-branch`). This is authorised for this repo only.
  Do not merge while any check is pending: read the `gh pr checks N` output for `pending`.
  This was violated once on PR #29 (docs only), so be strict.
- Run `prek run --all-files` before committing. New scripts need `git add --chmod=+x`. Files
  must end with a newline (end-of-file-fixer aborts the commit; restage and recommit).
- Never print or store tokens. `GIST_TOKEN` exists only as an environment secret in
  `coverage-badge`.
- Ask before pushing release tags: each tag publishes a public release. Use a hyphenated
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
2. **Build both products in CI.** Add a `product` dimension to `build-test`
   (`maturity:build --product`), `clang-tidy` (`maturity:tidy --product`) and `coverage` in
   `coverage.yml` (`--product`). This changes check names (for example
   `build-test (Release, productA)`), so update the ruleset's required checks in the same
   session, otherwise PRs block. Alternative that keeps names: a separate job
   `build-test-products`.
3. **Real product difference.** productB adds zlib only as a placeholder. Decide with the user
   what differs (a CMake toolchain variable, an extra source file, a dependency). Regenerate
   locks with `conan maturity:lock-update`.
4. **CI health (checklist 25-28).** Scheduled workflow plus `scripts/ci_health.py` using
   `gh api` for runs and jobs: success rate on main, P50/P95 duration, queue time, flaky
   re-runs (`run_attempt > 1`), time to green per PR, Conan cache hit rate. Write a job
   summary table, upload JSON, persist history (data branch or gist; API history is about 90
   days). Optional issue when thresholds breach. Needs `actions: read`, `contents: read`.
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
9. **Badge for release branches.** When the first `release/**` branch exists: per-branch gist
   file, `release/**` push trigger on `coverage-badge`, extend the environment deployment
   branches and the ruleset. Today the badge tracks `main` only.
10. **Latest marker policy.** `gh release edit <tag> --latest` can pin it; decide the policy
    with the user (for example never mark product releases Latest).
11. **C, Python, Rust variants.** Reuse the same gates: format, lint, test, coverage, SBOM,
    attestation, per-language lockfile. Keep the `protect-main` required checks consistent.
12. **Smaller follow-ups:** verify the badge renders; consider signing tags from a developer
    machine. The Obsidian MCP setup was parked and is unrelated to the repo.

## 6. Known gotchas

- Required-check names must match the job names exactly, including matrix suffixes.
- Reusable workflow callers must grant every permission the callee jobs request.
- A tag filter matches the whole tag: `v*` does not match `productA_v1.0.0`.
- `actions/upload-code-coverage` and Code Quality need a paid plan (PR #22 failed with 404).
- `actions/upload-artifact` `artifact-url` needs a GitHub login to open.
- The coverage PR comment job only runs for same-repo, non-Dependabot PRs.
- clang-tidy findings appear twice on a PR (bot review comment plus check annotation); this is
  GitHub behaviour, not a bug.
- The raw gist URL can serve stale content for minutes; use the gist API to confirm.
- `src/main.cpp` is excluded from coverage (`gcovr.cfg`); the gate is 90% lines. The coverage
  build lives in `build/coverage/Debug` (profile `maturity/coverage`), separate from `build/Debug`.
- The coverage jobs (`coverage`, `coverage-comment`, `coverage-badge`) are in `coverage.yml`,
  not `ci.yml`.
- `conan config install-pkg` checks every enabled remote; an unreachable conancenter can
  fail it once. Rerun before debugging.
- Plain `conan install .` at the root picks up the config-only `conan.lock`; use
  `conan maturity:install`.
