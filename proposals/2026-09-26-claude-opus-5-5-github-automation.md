---
type: proposal
title: 'GitHub automation: bot identities, submission feedback, and capture at the close'
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
prompt: 'The founder asked, verbatim: "what GitHub features can offer us? can you PR as agent without coauthor the
  account used?". From the options the editor listed, the founder chose, verbatim: "Bot identities (Recommended),Submission
  feedback (Recommended),Capture at the close (Recommended)", each to be reviewed by GPT-6 before anything is turned on.'
responds_to:
- critiques/2026-09-26-claude-opus-5-5--round-3-usability-test-1.md and -test-2.md @ d0cfdaa
- proposals/2026-09-25-claude-opus-5-5-round-3-design.md
- proposals/2026-09-25-claude-opus-5-5-round-3-launch.md
exposure:
- all files on main at d0cfdaa
- this session's conversation with the founder
human_interventions: none
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# GitHub Automation: Bot Identities, Submission Feedback, and Capture at the Close

**Status: a draft for GPT-6's review of the design.** Nothing here is built or turned on. The code comes after the design review, and gets its own review.

**No rule changes.** All three items are tooling that carries out rules already adopted. None changes what counts as a response, what is on time, or what is recorded. Where a design choice could look like a rule, it is marked **(rule check)** for the reviewer.

## Summary

| # | Item | What it does | Who acts |
|---|---|---|---|
| D1 | Bot identities | The editor's and reviewer's commits and pull requests show as GitHub Apps, not the founder's account | The founder creates each App with one click; the editor uses it |
| D2 | Submission feedback | Each Round 3 issue or pull request gets an automatic comment: whether its header and assessment blocks can be read | GitHub Actions |
| D3 | Capture at the close | After the close, a workflow records the state of every Round 3 issue and pull request as it stood at the close, from GitHub's own server-side records | GitHub Actions; the editor writes receipts from its output |

## D1. Bot identities

**The problem.** The editor works through the `gh` command-line tool, signed in as the founder's account. Every pull request says the founder opened it, and the AI authors appear only as `Co-authored-by` trailers. The record states who did what, but GitHub's own interface shows it the other way round.

**Proposal:**
- **Two GitHub Apps, owned by the organization:**
  - `question-zero-editor`, installed on `q0-inquiry` and `.github`, with Contents, Pull requests and Issues set to read and write, and Metadata to read. It opens the editor's pull requests and makes its commits.
  - `question-zero-reviewer`, with Metadata read only. It is an identity, not an actor: commits that add GPT-6's own files name it as author. The editor still commits and pushes them.
  - Neither App has webhooks, and neither is public (it can't be installed elsewhere).
- **Creation.** The editor prepares a manifest for each App. The founder opens a local page and clicks Create once per App. A local script receives the one-time code, converts it, and saves the private key to `.private/github-apps/`. The key is never printed, and the editor never pastes it anywhere.
- **Use.** A private helper creates a one-hour installation token when the editor pushes or opens a pull request.
  - Commits by the editor: author and committer are the editor App's bot user.
  - Commits adding GPT-6's files: author is the reviewer App's bot user, and the committer is the editor App.
  - The `Co-authored-by` trailers stay, including `GPT-6 Astra <codex@openai.com>`, which the founder asked for.
- **Nothing about protection changes.** The `main` ruleset still requires a pull request and the `check` status, with no bypass. Merges still happen only on the founder's decision.
- **Records.** `participant_id` and the provenance fields are unchanged; a GitHub identity identifies an account, not a model (protocol section 5). The Apps belong to the organization's infrastructure (protocol section 13), and the founder remains answerable for them.
- **The founder's account keeps its role:** owner of the organization and the Apps, and the only person who merges on their own decision.

**Rejected alternative:** a second GitHub account for the agent (a "machine account"). It needs its own email address and 2FA, has the founder's full user powers, and can't be limited to two repositories.

## D2. Submission feedback

**The problem.** A participant learns only after the close whether the editor can read their answer. The usability test showed that the rules are easy to get slightly wrong.

**Proposal:** a trusted validator, `tools/validate_round_03_response.py`, reusing the extractor's block rules by import, so feedback and extraction can't disagree. For one response it reports:
- whether the header parses as YAML and has the fields the template asks for (for an issue: whether each form field has a value)
- whether `input_set` names the tag and its commit
- for each of the 18 candidates: **read**, not assessed, unparseable (with the reason), incomplete (with the reason), or conflicting; and any block for an ID that is not a candidate

It **never reports positions,** and never comments on content. The comment says the check covers procedure only, is not a receipt, and that the version recorded is the one standing at the close.

**Workflows:**
- **Issues:** `on: issues` (opened, edited), for issues from the Round 3 form. It checks out the default branch only (trusted code), reads the issue body from the event file as data, never through shell interpolation, and posts or updates one comment. Permissions: `issues: write`, `contents: read`.
- **Pull requests:** `on: pull_request_target`, for changes under `rounds/03-open/responses/`. It checks out the default branch only, never the pull request's code. It reads the changed response files through the API as text, and parses them with the trusted validator. Permissions: `pull-requests: write`, `contents: read`. **(security check)** `pull_request_target` is dangerous only when it runs a pull request's code; this design never checks out or runs it. Whether fork approval settings delay this trigger should be verified.
- **Limits:** one comment per issue or pull request, updated in place; concurrency of one run per item; a size cap on the comment.

**(rule check)** The feedback is advice. It doesn't replace the editor's intake or the extractor. An answer that the feedback reads cleanly can still fail intake, for example on rights or receipts.

## D3. Capture at the close

**The problem.** At the close, the editor must record each pull request's last head before the close and each issue's text as it stood then, with evidence. Doing that by hand, as the editor, is slow and asks readers to trust the editor.

**Proposal:** `tools/capture_round_03.py`, run by a workflow **after** the close (manually, or scheduled a few minutes after it). It reconstructs the state at the close from GitHub's server-side records, so its start time doesn't matter.
- **Pull requests** touching `rounds/03-open/responses/`:
  - `created_utc` from the pull request.
  - The captured head: the latest head commit that GitHub's server records show arriving before the close. The evidence is the `check` workflow runs for each head, whose creation times GitHub records at push. Commit dates are not used: they are set by the pusher.
  - The file's SHA-256 at that commit.
- **Issues** from the Round 3 form:
  - `created_utc`.
  - The body as it stood at the close, from the issue's edit history (GraphQL `userContentEdits`: the last edit before the close, or the body as created). **(to verify)** exactly what the history returns for the first version must be tested before relying on it.
  - The answer's SHA-256.
- **Output:** one capture file, `rounds/03-open/capture.json`, with each item's route, number, times, captured commit or hash, and the evidence used (run IDs and times, edit IDs and times). It is opened as a pull request by the editor App. The workflow run's log is public evidence in its own right.
- **Receipts.** The editor writes each response's `receipt` from the capture file. `captured_evidence` cites the capture file and the run.

**Where server records are missing,** for example if Actions didn't run on a push, the capture says so, and the editor records the evidence it used by hand, as the current rules already allow.

**(rule check)** Late items are captured and marked late, as now. Nothing is extracted from the capture itself: the extractor still reads only committed response records with receipts.

## Order, and what the founder does

1. GPT-6 reviews this design.
2. The editor builds D2 and D3 with tests, and prepares D1's manifests. GPT-6 reviews the code.
3. The founder adopts, then clicks Create for the two Apps.
4. D2 is turned on during Round 3. D3 runs after the close.

**Related setting, not proposed here:** outside contributors' pull requests currently wait for a maintainer to approve their CI runs. That's a security setting, for the founder to decide separately.
