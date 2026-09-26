---
type: critique
subtype: review
title: 'GitHub automation: the controlled sandbox test of D1 and D2'
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as session a94fb166-05a4-4540-9f8b-aae1aa74ece3
  (resumed; same conversation). The context was summarized more than once. Continuity is self-declared.
setup: Claude Code desktop app, Windows
role: editor
attribution: self-declared
date: '2026-09-26'
prompt: 'The test planned in proposals/2026-09-26-claude-opus-5-5-automation-sandbox-test.md (revision 4), of the code
  GPT-6 cleared at the code-review stage at 5a666e0 (topic automation-code-ac1). The founder chose, verbatim, "Authorize
  the test (Recommended)", confirmed the App installation ("A2 completed"; "Confirm (Recommended)" for the IDs), and
  registered the second App ("ready").'
responds_to:
- proposals/2026-09-26-claude-opus-5-5-automation-sandbox-test.md
- 5a666e0bab6488c94e7fd7c027c36689e92decce
exposure:
- the private sandbox repository, its workflow runs, logs and comments, and GitHub's API responses, read through the
  founder's GitHub account and the editor App's short-lived tokens
human_interventions: 'The founder authorized the test, registered both sandbox Apps, installed the editor App on the
  sandbox only and confirmed its IDs. They did not edit or select this report.'
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# GitHub Automation: The Controlled Sandbox Test of D1 and D2

**Summary.** Every planned check passed: A1–A8 for the Apps and tokens (D1), and all fourteen D2 checks (B1–B13 plus B2b) for the advisory feedback. No check needed a code change. The test found two behaviors to record for adoption and D3, and two tests that failed only in CI, which are fixed in `c3000bf`. Four runs of my own test scripts failed for reasons in the scripts, not the code; they are listed below with what each did. Publishing this report is a separate authorized step.

## What was tested

- **Code:** R = `5a666e0bab6488c94e7fd7c027c36689e92decce`, as cleared. The sandbox's own commits were T = `5dee909c5a49431e8b880623b7b3af64a87f0c39` (R plus a synthetic three-candidate manifest, tagged `round/03-open/v1`) and D = `e671ca1f8c66db6d4847adee7f704246ced066f4` (T plus the byte-identical workflow and the form's default set to the sandbox tag). `tools/verify_sandbox_derivation.py R T D` printed "derivation verified". All 335 tests passed at R before anything was created.
- **Where:** the private repository `question-zero/q0-sandbox`, with main at D and the repository variable `Q0_ROUND3_FEEDBACK=on`. Nothing touched `q0-inquiry`, `.github` or any real submission. All content was synthetic.
- **Who acted:** the founder's GitHub account for issues, pull requests and settings, and the editor App's short-lived tokens for A4–A8. Every token was minted by `tools/github_apps/app_token.py` and revoked when its command ended.
- **When:** 2026-09-26, about 04:00–06:50 UTC.

## D1: the Apps and tokens

| Check | Result |
|---|---|
| A1 Register the editor App | Registered through the manifest flow as `question-zero-editor-sandbox`. The credentials folder and file are readable by the founder's Windows account only, verified with `icacls`. |
| A2 Install it | On `q0-sandbox` only, by the founder. |
| A3 Approve the mapping | `approve` printed the installation and repository IDs, the founder confirmed them, and the mapping was saved. Its metadata-read lookup token was revoked. |
| A4 Mint for `q0-sandbox` with `contents=write` | The tool runs a command only if the returned scope is exactly the approved repository ID, the requested permission plus metadata read, and an expiry within the hour. Inside the command, `GET /installation/repositories` listed only `question-zero/q0-sandbox`. A branch-creation request on `q0-inquiry` got HTTP 403; the same request on `q0-sandbox` got HTTP 422, which means the token could write there. Both requests pointed a branch at the all-zero object, so neither could change anything. |
| A5 Refusals before minting | `q0-inquiry` was refused: it is not in the mapping. `workflows=write` was refused: the tool may not request it. A URL-specific `http.extraheader` planted in the checkout's config was refused, reported by category only. |
| A6 Push and pull request as the bot | The credential helper answered only the approved path. It gave no answer for a foreign host or another repository on github.com. A clone pushed branch `sandbox/a6-bot-push`, and `gh` opened PR #1. GitHub shows the branch creation, the commit (author and committer) and the PR as `question-zero-editor-sandbox[bot]`. The clone's config held no credential or header settings. |
| A7 Reviewer bot as author, editor bot as committer | The reviewer App `question-zero-reviewer-sandbox` was registered with metadata read only and not installed. A commit adding a copy of `critiques/2026-09-26-gpt-6--automation-code-review.md` shows author `question-zero-reviewer-sandbox[bot]` and committer `question-zero-editor-sandbox[bot]`, both resolved by GitHub as Bot accounts. The pushed blob equals the blob at R (`11007dd0…`). |
| A8 Use the token after the command ends | The same call worked before revocation and got HTTP 401 twenty seconds after the command ended. The tool reported the revocation as confirmed. |

## D2: the advisory feedback

| Check | Result |
|---|---|
| B1 A well-formed form issue | One comment, naming the body's SHA-256 and validator revision `e671ca1f8c66` (D). It gave counts only: 2 read, 1 not assessed. There were no positions and no quoted text. |
| B2 Quick edits and stale reruns | Two quick edits: the first run was cancelled by the parse job's concurrency, and the second published. The comment names the current digest. Rerunning the B1 run, whose event carries the original body, while a newer run was parsing: the rerun queued, cancelled the in-progress parse, parsed the current body and updated the comment for the current version. Rerunning it alongside a new edit: the new edit's run cancelled the rerun and published the current version. At no point did an older result overwrite a newer one, and there was always one bot comment. |
| B2b Disappearance | Removing the form's headings from a managed issue changed the comment to "no current response", naming the new digest. On a managed PR, deleting the last response file, and separately renaming it out of the response folder, each changed the comment to "no current response" for that head. Unmanaged items got nothing: PR #1, and B5's issue. |
| B3 Hostile content | An answer with an @mention of the founder's own handle, links, `<img onerror>`, `<script>`, `<details>` and a copied feedback marker. None of it appears in the bot's comment, which carries one marker, its own. A marker comment posted by the founder beforehand was not edited. |
| B4 Grant and consent unticked, rights "unknown" | Reported as three intake requirements (grant, consent, unresolved rights), each with the Never post sentence. The response was still checked and counted, with no format-error sentence. |
| B5 An issue not from the form | The run succeeded and posted nothing. |
| B6 A same-repository PR with one response file | One comment naming the head SHA. The parse job checked out `main`; the publish job checked out exactly `e671ca1f…`, the `trusted_sha` the parse job output. The PR's head never appears in a checkout. |
| B7 A new head with `[skip ci]` | `pull_request_target` still ran, and the comment names the new head. See finding F1. |
| B8 A Git symlink and a response over 512 KB | With both files, the first changed file was the symlink, mode `120000` in Git: `pr_file_not_regular_or_too_large` and `pr_several_response_files`, "not checked", not a rejection. With only the 660,665-byte file left: `pr_file_not_regular_or_too_large`, "not checked". No job failed. |
| B9 A PR that also edits `tools/` and the workflow | The injected render text never appeared in the comment, and the workflow edit's added step never ran. The logs show the trusted commit. |
| B10 The variable set to `off` | Both jobs were skipped and the comment was unchanged. The variable was restored to `on`. See finding F2. |
| B11 The Actions policy | Repository level: Actions enabled, all actions allowed, default workflow token read-only; the same before and after. Organization level: not readable with the founder's token scopes (it needs `admin:org`), before or after. No setting was changed. `pull_request_target` ran for this repository throughout. |
| B12 More than 100 comments | 111 comments. The bot's comment was the 41st, on page 2 at 30 per page, and the longest comment was 65,000 characters. After another edit, the bot found its comment and updated it, with no duplicate and no job failure. |
| B13 Response headers missing, malformed or a list | Each produced its typed "not checked" sentence (`header_missing`, `header_unparseable`, `header_not_a_mapping`), with no job failure. |

Across the whole test, the feedback workflow had no failed runs. Three were cancelled, all by B2's intended concurrency.

## Findings

- **F1: `[skip ci]` doesn't stop `pull_request_target`** (B7). Nothing in D2 relies on it, but D3's design should note that a participant can't suppress the feedback run this way, and that the editor can't rely on it either.
- **F2: edits made while the variable is `off` aren't caught up** (B10). Turning feedback back on processes only later events. An item edited while it was off keeps its older comment, which names its older digest, until its next edit. That's harmless, because the comment says which version it checked. Adoption notes should say so, and D3 must never treat a feedback comment as current.
- **F3: two tests failed in CI while the code behaved correctly.** Every run of "Check provenance headers" in the sandbox failed on the same two tests:
  - `test_run_revokes_and_propagates_child_failure_and_revoke_failure`: `actions/checkout` persists an `http.extraheader`, which `config_problems` rightly refuses.
  - `test_the_exact_chain_passes`: it depended on the real form's default, which a derived sandbox changes.
  
  Commit `c3000bf` points the first test's real configuration check at a fresh checkout and gives the derivation tests their own form fixture. Both pass with such a header planted and the sandbox's default in place, and the full suite passes (335, 1 pre-existing skip). These are GPT-6's two final-approval follow-ups from the AC1 review.
- **F4: no queued publish job was observed** (B2). GitHub's timing put the queued work in the parse jobs instead. The publish job's own queue (concurrency without cancellation) wasn't exercised by an observed wait. Each publish re-reads the current version before writing, which B2 did exercise.

## Test-execution errors (the editor's)

- **A4/A6 attempt 1:** the runner started WSL's `bash`, which isn't set up on this machine, so the command never ran. The token was minted and revoked.
- **Attempt 2:** A6 was valid. The A4 listing and the A8 check were invalid, because Git Bash rewrote the API path `/installation/repositories` as a Windows path. The q0-inquiry probe only read contents, and the repository is public, so a read proves nothing. Attempt 3 reran A4 and A8 with path conversion off and write probes that can't change anything.
- **A7 attempt 1:** with path conversion still off, Windows `git` cloned to an untranslated path. Nothing was committed or pushed. The stray clone held no credentials and was removed.
- **B2's script** stopped on its last step, a skipped job that had no log to fetch. The results were then read from the run records.

Every token minted in these attempts was revoked, and the tool confirmed each revocation.

## Not tested

- **Pull requests from forks.** The plan doesn't clear that route, and a private repository can't take them.
- **The production Apps.** None was registered.
- **The organization-level Actions policy,** which isn't readable with the founder's current token scopes.
- **Issues submitted through the web form.** Issues were created through the API with the body GitHub renders for the form. The parsing is identical, but the form's own client-side validation wasn't exercised.
- **A publish job queued behind another** (F4).
- **D3,** which isn't built.

## Evidence

Kept privately, outside the repository: run IDs, API responses without credentials, comment bodies and the helper scripts, with timestamps. The sandbox repository itself holds every issue, pull request, run and log.

## Clean-up (the founder's, after review)

- Delete both sandbox Apps.
- Archive or delete `q0-sandbox`, as the founder chooses.
- Delete the sandbox credentials from the private folder: two credential files and one approved mapping.

## Disclosures

The editor wrote the code under test, the plan, the helper scripts and this report, and has a stake in how it reads. Every result above is from GitHub's own records, read after the fact. Four script errors are disclosed above rather than left out.
