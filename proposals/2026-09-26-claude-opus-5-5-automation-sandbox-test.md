---
type: proposal
title: 'Controlled test plan: GitHub automation D1 and D2 in a private sandbox'
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as session a94fb166-05a4-4540-9f8b-aae1aa74ece3
  (resumed; same conversation). The context was summarized more than once. Continuity is self-declared.
setup: Claude Code desktop app, Windows
operator: human/alileus
role: editor
attribution: self-declared
date: '2026-09-26'
revision: 4
prompt: 'Step 2 of the reviewed order in proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3): "GPT-6
  reviews the code and the controlled-test plan before that plan is run." The founder chose, verbatim: "All three below
  (Recommended)", which included building the D1 and D2 code for GPT-6''s code review. This plan runs nothing by itself.
  Revision 2 applies GPT-6''s AC9 and the plan items of AC1-AC8 (critiques/2026-09-26-gpt-6--automation-code-review.md, topic automation-code).
  Revision 3 applies its round-2 plan findings (critiques/2026-09-26-gpt-6--automation-code-review-r2.md): the derived sandbox commit, the install-before-approve order,
  and the residual cases. Revision 4 applies its round-3 findings (critiques/2026-09-26-gpt-6--automation-code-review-r3.md): the whole R, T, D chain
  is verified, and approval records the lookup token''s effective scope.'
responds_to:
- proposals/2026-09-26-claude-opus-5-5-github-automation.md
- critiques/2026-09-26-gpt-6--github-automation-review-r3.md
exposure:
- the D1 and D2 code on the branch that carries this plan
- GPT-6's three design reviews
human_interventions: none
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# Controlled Test Plan: GitHub Automation D1 and D2 in a Private Sandbox

**What this plan is for.** The offline tests use a fake GitHub API. This plan checks the behaviour that only real GitHub can show, in a private sandbox, before final code approval. It covers D1 (the Apps) and D2 (the feedback workflow) only. D3 has its own topic and its own test later.

**Nothing here runs until the founder authorizes it separately,** after GPT-6 has reviewed this plan and the code. Authorizing the test is not adopting the design.

**Before any live step,** the full offline suite passes at the exact commit GPT-6 cleared (the reviewed commit, R). It covers the AC1-AC8 regressions and GPT-6's round-2 cases:
- the credential helper's destination checks, and refusal of repository-local credential, header, askpass, include and URL-rewrite settings, including URL-specific ones;
- registration's destination, slug and access-control failures;
- approval of a private repository through a temporary metadata-read token that is revoked;
- minting's identity, enumerated permission levels, expiry and revocation checks, and the final exit status after launch failures, timeouts and interruptions;
- the pinned revision, typed header failures, schema type checks, reconciliation of old runs to the current version, and disappearing results;
- oversized API pages as incomplete, a validator stopped by its limits as a typed result, and the complete-file digest;
- Git modes, form layouts including headings inside unfenced answers, `unknown` sample counts, conditional fields and trusted diagnostics.

## The sandbox's own commits

The sandbox can't run R unchanged: R deliberately keeps the workflow inactive, and its manifest and form belong to the real round. So the sandbox runs a derived commit, built in two steps:
1. **T** is R with the synthetic three-candidate manifest in place of `rounds/03-open/prompt.md`. The sandbox's tag `round/03-open/v1` points to T.
2. **D** is T plus two changes: the workflow copied, byte for byte, from `tools/workflows/round-3-feedback.yml` to `.github/workflows/`, and the form's `input_set` default changed to the sandbox's own `round/03-open/v1 @ T`. D is the sandbox's default branch.

`tools/verify_sandbox_derivation.py R T D` must pass before any live step. It checks the whole chain: T changes only the manifest, which names exactly three candidates, gives a closing time, and carries a hash and size matching its own text; the sandbox tag points to T; D adds only the byte-identical workflow and changes only the form's `input_set` default line, to exactly `round/03-open/v1 @ T`. Every other path, including all of `tools/` and the required CI workflow, must be byte-identical to R. The test record names R, T and D, and the workflow's `trusted_sha` output in every run must be D.

## What the founder authorizes

1. **A private repository, `question-zero/q0-sandbox`,** created for the test. It holds a copy of the relevant tools, the issue form, and a tagged synthetic manifest (`round/03-open/v1`) with three synthetic candidates. It is never used for the inquiry, and is archived or deleted afterwards, as the founder chooses.
2. **Two throwaway Apps, `question-zero-editor-sandbox` and `question-zero-reviewer-sandbox`,** registered with `register.py --sandbox` and installed on `q0-sandbox` only. They are deleted after the test. The production Apps are not registered by this test.
3. **The feedback workflow, installed in the sandbox only,** through the founder's account, with the repository variable `Q0_ROUND3_FEEDBACK=on` set in the sandbox only.
4. **The editor making test pushes, pull requests, issues and edits in the sandbox,** with synthetic content only.

Nothing touches `q0-inquiry`, `.github` or any real submission. No production credential is created.

## D1 checks

| # | Check | Pass means |
|---|---|---|
In order:

| # | Check | Pass means |
|---|---|---|
| A1 | Register the sandbox editor App from the manifest | Before any secret is written, the folder's and file's access lists show the founder's account only (the `icacls` output is recorded); nothing secret appears in the terminal or the browser page; a destination inside a repository is refused |
| A2 | The founder installs it on `q0-sandbox` only | The installation lists that one repository |
| A3 | Run `app_token.py approve` (after A2), and have the founder confirm the App, installation and repository IDs | The temporary lookup token's effective scope is recorded, and must be exactly metadata read for `q0-sandbox`, or approval fails; the token is revoked either way; the approved mapping names `question-zero/q0-sandbox` by owner and numeric ID, and the installation by ID |
| A4 | Mint a token for `q0-sandbox` with `contents=write` | The effective returned scope is inspected: exactly the approved repository ID, the requested permissions plus metadata read, and an expiry within the hour |
| A5 | Ask for `q0-inquiry`, or for `workflows=write`; add a URL-specific `http.<url>.extraHeader` to the local checkout | Refused before any token is minted |
| A6 | Push a commit and open a pull request through `app_token.py` | GitHub shows the bot as the pusher and PR author; the token is absent from the process arguments, remote URL and git configuration; `git credential fill` for any other host or repository path returns nothing |
| A7 | Commit a file with the reviewer bot as Git author and the editor bot as committer | GitHub shows the attribution as designed; the file is byte-identical to its source |
| A8 | Use the token after the command ends | Refused: the token was revoked; the tool reported the revocation as confirmed |

## D2 checks

Every check records the event, the run, what was posted, and the time; the posted comment is compared with the expected fixed text.

| # | Check | Pass means |
|---|---|---|
| B1 | Open a well-formed issue through the form | One advisory comment appears, naming the body's digest; no positions, no quoted text |
| B2 | Edit it twice quickly; rerun an old event's run while the current parse or publish is running, and again while it is pending | After edits stop, the comment names the current body's digest; a rerun of an old event produces the current version's result, and no stale result overwrites a newer one |
| B2b | Remove the form's headings from a managed issue; remove the last response file from a managed pull request, and rename one out of the response folder | The comment is updated to say there is no current response; an unmanaged item gets nothing |
| B3 | An issue whose answer contains mentions, links, HTML and a copied feedback marker | None of it appears in the comment; the copied marker in another user's comment is not edited |
| B4 | Leave the grant and consent boxes unticked; write "unknown" for rights | Reported as an unresolved intake requirement, not a format error |
| B5 | An issue not from the form | No run, or a run that posts nothing |
| B6 | A same-repository pull request adding one response file | One comment naming the head SHA; the PR's own code is never checked out; both jobs' logs show the identical pinned trusted commit |
| B7 | Push a new head with `[skip ci]` in the commit message | Whether `pull_request_target` still runs; the result is recorded either way, and D3's design notes it |
| B8 | A pull request with two response files; one committed as a real Git symlink (mode 120000); one over 512 KB | The documented codes; not checked, never rejected; the symlink is rejected by its Git mode at the head commit |
| B9 | A pull request that also edits `tools/` and the workflow file | Both jobs run the identical pinned default-branch commit; the PR's changes have no effect |
| B12 | An issue with more than 100 comments, the bot's among them, some of them near GitHub's maximum length | The bot's comment is found and updated; no duplicate is posted; no job fails on page size |
| B13 | A response file with a header that is missing, malformed, or a list | A typed "not checked" comment naming the header problem; no job failure |
| B10 | The repository variable set to anything but `on` | No run posts anything |
| B11 | The effective Actions event policy for `pull_request_target` in the organization | Recorded before and after; whether it runs for this repository |

**Limits of this test.**
- It can't test pull requests from forks by other accounts, because the editor has no second account and doesn't create accounts. **The fork route stays uncleared for production** until there is evidence, from a separately authorized test using an existing account, or a reviewed restriction. No account is created, no installation expanded and no event policy weakened to make a test pass.
- A trigger test shows what happened in these runs. It is not a guarantee of delivery.

## Evidence and report

- **Kept privately:** the run IDs, API responses without credentials, and comment bodies, outside the repository.
- **Recorded for each check:** the effective permissions and the repository and installation mapping; expiry and revocation outcomes; parser-limit outcomes; comment ownership and pagination; stale-run and disappearance outcomes; the trusted commit in both jobs.
- **For GPT-6's review:** a report with the results table, the untested items and any finding, before final code approval. Publishing that report is a separate authorized step.
- **Clean-up:** the sandbox Apps are deleted by the founder. The sandbox repository is archived or deleted as the founder chooses. Its credentials are deleted from the private folder.
