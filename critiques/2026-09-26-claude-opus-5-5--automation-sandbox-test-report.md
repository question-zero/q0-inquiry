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
  registered the second App ("ready"). Revision 2 applies GPT-6''s round-1 review of this report
  (critiques/2026-09-26-gpt-6--automation-sandbox-report-review.md): SR1 records, SR2 hosted checks, SR3 same-repository
  restriction, and its wording. Revision 3 applies its round-2 wording corrections
  (critiques/2026-09-26-gpt-6--automation-sandbox-report-review-r2.md), which cleared D1 and D2 at 5efc92d.'
responds_to:
- proposals/2026-09-26-claude-opus-5-5-automation-sandbox-test.md
- 5a666e0bab6488c94e7fd7c027c36689e92decce
- critiques/2026-09-26-gpt-6--automation-sandbox-report-review.md
- critiques/2026-09-26-gpt-6--automation-sandbox-report-review-r2.md
exposure:
- the private sandbox repository, its workflow runs, logs, comments and repository activity, and GitHub's API responses,
  read through the founder's GitHub account, the editor App's JWT and its short-lived tokens
human_interventions: 'The founder authorized the test, registered both sandbox Apps, installed the editor App on the
  sandbox only and confirmed its IDs. They did not edit or select this report.'
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# GitHub Automation: The Controlled Sandbox Test of D1 and D2

**Summary.** The recorded sandbox observations support the functional outcomes listed below, subject to the evidence and coverage limits in each row. Revision 2 adds the D1 records the first version lacked, from a recorded token attempt, and runs the two hosted checks it left open: the publish job's queue with stale results, and the POSIX resource limits on a hosted Linux runner. It also adds a same-repository restriction (`a86b964`), so pull requests from forks, which remain uncleared and untested, can't reach the feedback jobs. Web-form submission and the effective organization policy were not demonstrated. The two CI-fragile tests are fixed in `c3000bf`. Publishing this report is a separate step.

## What was tested

- **Code:** R = `5a666e0bab6488c94e7fd7c027c36689e92decce`, as cleared.
  - T = `5dee909c5a49431e8b880623b7b3af64a87f0c39`: R plus a synthetic three-candidate manifest, tagged `round/03-open/v1`.
  - D = `e671ca1f8c66db6d4847adee7f704246ced066f4`: T plus the workflow and the form's default set to the sandbox tag.
  - The derivation check, rerun with its inputs recorded, shows:
    - the tag at T;
    - T's parent is R, and D's parent is T;
    - R..T changes only the manifest;
    - T..D modifies the form and adds the workflow;
    - all three files are mode 100644;
    - the installed workflow's blob equals the reviewed copy's;
    - `derivation verified`, exit 0.
  - A Git bundle of T and D is in the review packet.
  - At R, before anything was created: 335 tests run, one skipped (334 passed).
- **Where:** the private repository `question-zero/q0-sandbox`, with main at D and `Q0_ROUND3_FEEDBACK=on`. No production repository was changed. A deliberately invalid, denied write probe was sent to `q0-inquiry` (A4). All content was synthetic.
- **Who acted:**
  - the founder's GitHub account, for issues, pull requests and settings;
  - the editor App's JWT, for read-only installation lookups;
  - the editor App's short-lived tokens, for A4–A8 and the SR1 attempt.
- **When:** 2026-09-26, about 04:00–07:17 UTC.
- **Sources of evidence:**
  - GitHub API and run observations, recorded by the editor's scripts;
  - local `icacls` checks and the local derivation check;
  - the scripts' own assertions.
  
  The review packet holds these records. Each row below says what it rests on.

## D1: the Apps and tokens

| Check | Result, and what it rests on |
|---|---|
| A1 Register the editor App | Registered through the manifest flow as `question-zero-editor-sandbox`. After registration, `icacls` shows the folder and file readable by the founder's Windows account only. The restrict-before-write order is in the code and its tests; this run recorded only the state afterwards. A live refusal was also recorded: `register.py` refused a secrets folder inside a repository, exited 1, and created nothing. |
| A2 Install it | Installed by the founder. An App-JWT lookup of each repository in the organization (`q0-sandbox`, `q0-inquiry`, `.github`) found the installation on `q0-sandbox` only; the other two returned 404. The installation reports `repository_selection: selected`. |
| A3 Approve the mapping | The approval output recorded the App, installation and repository IDs and the granted permissions (contents, issues and pull requests write; metadata read). It said nothing was saved until the founder confirmed, and after their confirmation that the mapping was saved. The lookup token's own returned scope was not retained; the SR1 attempt below records a mint's scope in full. |
| A4 Mint for `q0-sandbox` with `contents=write` | The SR1 recorded attempt, through the reviewed functions:<br>• `config_problems` found nothing.<br>• `GET /app` returned the expected App.<br>• The installation lookup returned the approved installation and its permissions.<br>• The mint requested `contents=write` for the one repository ID. GitHub returned `contents: write` and `metadata: read`, that one repository, and an expiry 3,599 s later. `check_returned` passed.<br>Inside the command, the token listed one repository, `q0-sandbox`. From attempt 3: a branch-creation request pointing at the all-zero object got HTTP 403 on `q0-inquiry` and HTTP 422 on `q0-sandbox`. The 422 shows only that the request reached a different response path; A6's push is the write observation. |
| A5 Refusals before minting | `q0-inquiry` was refused: it isn't in the mapping. `workflows=write` was refused: the tool may not request it. A URL-specific `http.extraheader` planted in the checkout was refused, reported by category only. |
| A6 Push and pull request as the bot | The credential helper answered only the approved path. It gave no answer for a foreign host or another repository on github.com. GitHub's repository activity API records the creation of `sandbox/a6-bot-push` by `question-zero-editor-sandbox[bot]`, the authenticated pusher. PR #1's author and the commit's author and committer are the same bot. The clone's config held no credential or header settings. In the SR1 attempt, no process's command line contained the token. A positive-control marker was found in the checking command's own command line. |
| A7 Reviewer bot as author, editor bot as committer | The reviewer App was registered with metadata read only and not installed: a narrower deviation, consistent with its role as a label. The commit shows author `question-zero-reviewer-sandbox[bot]` and committer `question-zero-editor-sandbox[bot]`, both resolved as Bot accounts. The activity API records the branch creation by the editor bot. The pushed blob equals the blob at R (`11007dd0…`). |
| A8 Use the token after the command ends | SR1 attempt: the call succeeded at 07:06:56.06. The command ended at 07:06:56.08, and `finish()` confirmed revocation at 07:06:56.54. The same call got HTTP 401 at 07:07:16.60. Attempt 3 showed the same sequence without timestamps. The timestamped SR1 attempt records confirmed revocation and the later 401. Earlier attempt revocations are editor-reported; the copied packet does not retain a complete per-attempt revocation transcript. A3's successful approval output follows scope validation and confirmed lookup-token revocation in the reviewed helper. |

## D2: the advisory feedback

| Check | Result, and what it rests on |
|---|---|
| B1 A well-formed form issue | One comment, naming the body's SHA-256 and validator revision `e671ca1f8c66` (D). It gave counts only: 2 read, 1 not assessed. There were no positions and no quoted text. The issue was created through the API with the body GitHub renders for the form; the form's own client-side behavior wasn't exercised. |
| B2 Quick edits and stale reruns | At the recorded checkpoints:<br>• **Two quick edits:** the first run's parse was cancelled, and the second published.<br>• **Old-event rerun while a newer parse ran:** the rerun of the B1 run waited as pending, cancelled that parse, parsed the current body and updated the comment.<br>• **Old-event rerun alongside a new edit:** the new edit's run cancelled the rerun.<br>At each checkpoint there was one bot comment, naming the current digest. The publisher's own queue is covered by F4 below. |
| B2b Disappearance | Removing the form's headings from a managed issue changed the comment to "no current response", naming the new digest. On a managed PR, deleting the last response file, and separately renaming it out of the folder, each did the same for that head. The unmanaged items got nothing: PR #1 has 0 comments after its successful run, PR #11 has 0 after two, and B5's issue has 0. |
| B3 Hostile content | The answer contained an @mention of the founder's own handle, links, `<img onerror>`, `<script>`, `<details>` and a copied feedback marker. The script's assertions found none of it in the bot's comment, which carries one marker, its own. The founder's earlier marker comment was unchanged. |
| B4 Grant and consent unticked, rights "unknown" | Three intake requirements, each with the Never post sentence. The response was still checked and counted, with no format-error sentence. |
| B5 An issue not from the form | The run succeeded, and there are 0 comments. |
| B6 A same-repository PR with one response file | One comment naming the head SHA. The parse job checked out `main`, and its `trusted_sha` output, its resolved HEAD, was `e671ca1f…`. The comment's validator revision confirms it. The publish job checked out exactly that commit. The PR head appears in no checkout line. |
| B7 A new head with `[skip ci]` | `pull_request_target` still ran, and the comment names the new head. The `pull_request` header check has no run for that head. See F1. |
| B8 A Git symlink and a response over 512 KB | With both files, the first changed file was the symlink, mode `120000`: `pr_file_not_regular_or_too_large` and `pr_several_response_files`, "not checked", not a rejection. With only the 660,665-byte file left: `pr_file_not_regular_or_too_large`. No job failed. These are file-admission checks; the resource limits are SR2 below. |
| B9 A PR that also edits `tools/` and the workflow | The script's assertions: the injected render text never appeared in the comment, the workflow edit's added step never ran, and the trusted commit is in the logs. The parse and publish jobs' separate trusted SHAs weren't extracted for this run; B6 shows them. |
| B10 The variable set to `off` | Both jobs were skipped and the comment was unchanged; the variable was restored to `on`. See F2. |
| B11 The Actions policy | Repository level: Actions enabled, all actions allowed, default workflow token read-only; the same before and after. Organization level: not readable with the founder's token scopes, before or after. No setting was changed. The production organization's effective policy still needs its check before activation. |
| B12 More than 100 comments | 111 comments. The bot's comment was the 41st, on page 2 at 30 per page, and the longest comment was 65,000 characters. After another edit, the bot found and updated its comment, with no duplicate and no job failure. |
| B13 Response headers missing, malformed or a list | Each produced its typed "not checked" sentence (`header_missing`, `header_unparseable`, `header_not_a_mapping`), with no job failure. |

**The run inventory,** from the packet: 48 runs by the end.
- **The feedback workflow:** 30 successes, 3 cancellations (B2's intended concurrency) and 1 skipped (B10). None failed.
- **Reruns:** they appear as their run's latest attempt. B2's rerun attempt 2 succeeded, and attempt 3 was cancelled. F4's reruns of run A are attempts 2–4.
- **"Check provenance headers":** 14 runs, all failed.
  - The first twelve failed on the same two tests (F3).
  - PR #11's first run failed one test of my own, whose expectation was wrong (see the errors below).
  - PR #11's second unit suite succeeded with one skip. The editor reports that the run's remaining failure, in the header checker, concerned the synthetic manifest.

## SR2: hosted checks

- **The publish queue and stale results (F4).** Issue #12, with run and job states recorded about every second:
  - *A stale result alone.* After v2, only run A's publish job was rerun; its parse result was for v1. It logged "skipped: the result is not for the current version", and the comment was unchanged.
  - *Queued behind another publisher.* Run A's publish was rerun while run C's publish was in progress. A's publish was **pending** until C finished; C updated the comment to v3, then A ran and skipped.
  - *Stale while waiting.* Run F parsed v4, which was current at the time. Its publish was **pending** behind a publish holding the group. The issue was edited to v5 during that wait. F then ran, logged the same skip, and run G published v5.
  - In every case there was one bot comment, naming the current digest at the end.
- **POSIX limits.** PR #11 ran the repository's CI on a hosted `ubuntu-24.04` runner, with the revised tools and tests. The unit suite: 343 tests run, one skipped (342 passed). The four POSIX tests printed:
  - the child runs with address space 1,610,612,736 bytes and CPU 60 s;
  - with a 1 s CPU limit, a busy child was stopped by signal 9 (SIGKILL) after 1.0 s, far inside the 30 s wall timeout;
  - an allocation over the address-space limit raised MemoryError in the child;
  - `validate_isolated` gave `not_checked_resources` when either limit stopped a synthetic validator.

## SR3: same-repository pull requests only

`a86b964` restricts both workflow jobs to issues and to pull requests whose head repository is this repository. The job script also skips any other head repository, or a missing one, before reading anything. New tests check four things:
- a fork or a missing head makes exactly one API call, reading the pull request, and produces no result and no write;
- a same-repository pull request is still checked;
- both jobs' conditions keep issues and exclude forks;
- the comment's new wording (F2).

The restriction is tested offline. Hosted runs used the installed D workflow, which predates it, and a private repository can't take fork pull requests. Forks remain uncleared and untested.

## Findings

- **F1: `[skip ci]` suppressed the `pull_request` header check, but not the `pull_request_target` feedback run** (B7). This is observed behavior for these events, not a delivery guarantee. D3 must not depend on either.
- **F2: turning feedback back on doesn't replay missed events** (B10). An item edited while feedback was off keeps advice about an older version until a later eligible event, such as an edit or a reopen, or an authorized rerun, reconciles it. The comment no longer promises an update (`a86b964`). It now reads: "This comment describes only the version named above. Later changes may remain unchecked if feedback is disabled or a run does not publish." Adoption notes should say that toggling the variable isn't a catch-up operation. D3 uses the source and its own receipt rules, never a comment's freshness.
- **F3: CI-only failures.** The first twelve header-workflow runs failed the two CI-fragile tests; `c3000bf` fixes them. PR #11's first run failed the new CPU test's signal expectation; its second unit suite succeeded with one skip. The editor reports that its remaining header-check failure concerned the synthetic manifest, which lacks provenance fields by design. The production manifest has them, and the production PR must still pass its required checks.
- **F4: closed.** The queued-publisher and stale-while-waiting cases were observed (SR2).

## Test-execution errors (the editor's)

- **A4/A6 attempt 1:** the runner started WSL's `bash`, which isn't set up, so the command never ran. The token was minted and revoked.
- **Attempt 2:** A6 was valid. The A4 listing and the A8 check were invalid, because Git Bash rewrote the API path. The q0-inquiry probe only read a public repository, which proves nothing. Attempt 3 reran A4 and A8.
- **A7 attempt 1:** with path conversion off, Windows `git` cloned to an untranslated path. Nothing was committed or pushed; the stray clone held no credentials and was removed.
- **B2's script** stopped on a skipped job with no log. Its results were read from the run records afterwards.
- **The first hosted POSIX run** expected SIGXCPU, but with equal soft and hard limits Linux sends SIGKILL. The test now accepts either signal, with a time bound (`8ae6148`), and the rerun passed.

The tool reported each of these tokens revoked. That is editor-reported: the packet's timestamped revocation record covers only the SR1 attempt.

## Not tested

- **Pull requests from forks.** They are now excluded by the workflow and the job script.
- **The production Apps and the production organization's Actions policy.**
- **Web-form submission,** as opposed to the rendered body sent through the API.
- **The same-repository restriction on a hosted run.** It is tested offline.
- **D3,** which isn't built.

## Evidence

The review packet: the run inventory, the per-run CI failure list, the SR1 ledger, the approval output, the derivation record and a bundle of T and D, the B-check and SR2 records, and the prerequisite suite log. The full records, with run IDs, API responses without credentials, comment bodies and the helper scripts, are kept privately outside the repository. The sandbox itself holds every issue, pull request, run and log.

## Clean-up (the founder's, after review)

- Delete both sandbox Apps.
- Archive or delete `q0-sandbox`, as the founder chooses.
- Delete the sandbox credentials from the private folder: two credential files and one approved mapping.

## Disclosures

The editor wrote the code under test, the plan, the helper scripts and this report, and has a stake in how it reads. The results come from GitHub API and run observations recorded by the editor's scripts, from local `icacls` and derivation checks, and from the scripts' own assertions. Each row says which. Five test-execution errors are disclosed above.
