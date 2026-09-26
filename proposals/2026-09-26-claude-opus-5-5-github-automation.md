---
type: proposal
title: 'GitHub automation: bot identities and submission feedback'
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
revision: 3
prompt: 'The founder asked, verbatim: "what GitHub features can offer us? can you PR as agent without coauthor the
  account used?". From the options the editor listed, the founder chose, verbatim: "Bot identities (Recommended),Submission
  feedback (Recommended),Capture at the close (Recommended)", each to be reviewed by GPT-6 before anything is turned on.
  Revision 2 applies GPT-6''s GA1-GA6 (critiques/2026-09-26-gpt-6--github-automation-review.md, topic github-automation),
  after the founder chose, verbatim: "Revise all three (Recommended)". Revision 3 applies GPT-6''s round-2 findings for
  D1 and D2 (critiques/2026-09-26-gpt-6--github-automation-review-r2.md). On the founder''s decision, verbatim: "Split off D3 (Recommended)", it moves the capture at the close
  (D3) to a separate proposal and review topic; D3''s open findings go with it.'
responds_to:
- critiques/2026-09-26-claude-opus-5-5--round-3-usability-test-1.md and -test-2.md @ d0cfdaa
- critiques/2026-09-26-gpt-6--github-automation-review.md @ 30eb2b9
- critiques/2026-09-26-gpt-6--github-automation-review-r2.md @ 6b66948
- proposals/2026-09-25-claude-opus-5-5-round-3-design.md
- proposals/2026-09-25-claude-opus-5-5-round-3-launch.md
exposure:
- all files on main at a566861
- GPT-6's review, including the GitHub documentation it cites (not independently re-read by the editor)
- this session's conversation with the founder
human_interventions: none
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# GitHub Automation: Bot Identities and Submission Feedback

**Status: revision 3, D1 and D2 only, for GPT-6's third review.** Nothing here is built or turned on. Code comes after the design is cleared, and gets its own review, with synthetic fixtures and a separately authorized controlled test.

**D3 has moved.** The capture at the close needs more design than one review round allows. It becomes its own proposal and review topic, carrying GPT-6's open findings GA1 and GA2 and the D3 part of GA3 and GA5. This proposal no longer covers it.

**What this changes, and what it doesn't.**
- **No participant rule changes.** Nothing here changes what counts as a response, what is on time, or what is recorded.
- **The operating security posture does change** (D2). Trusted automation, triggered by outside submissions, gets a narrowly scoped permission to write comments. Contributor-controlled code stays approval-gated, read-only and without secrets. The founder's adoption must cover this explicitly.
- Where a choice could look like a rule, it is marked **(rule check)**.

## Summary

| # | Item | What it does | Who acts |
|---|---|---|---|
| D1 | Bot identities | The editor's pushes and pull requests use an organization-owned GitHub App instead of the founder's account; commits holding the reviewer's own files name a reviewer App as Git author | The founder registers and installs each App, choosing the repository access; the editor prepares the reviewed manifests and uses installation tokens |
| D2 | Submission feedback | Each Round 3 issue or pull request gets an advisory, version-specific comment on whether its header and assessment blocks can be read | GitHub Actions, from trusted default-branch code |

## D1. Bot identities

**The problem.** The editor works through the `gh` command-line tool, signed in as the founder's account. GitHub's interface shows the founder opening every pull request, and the AI authors appear only in trailers.

**Proposal:**
- **Two organization-owned GitHub Apps,** installed only on the selected repositories (`q0-inquiry`, `.github`):
  - `question-zero-editor`: Contents, Pull requests and Issues set to read and write; Metadata read. Issues write is requested provisionally for the editor's intake comments, such as returning an incomplete declaration for completion, and for labels used for routing. The implementation must identify the actual operations, and omit it if unused; it is not needed merely because the App creates pull requests. **No Workflows permission.** Changes to workflow files go through the founder's own account, as an explicitly authorized owner route, not through the App.
  - `question-zero-reviewer`: Metadata read only. It is an attribution label, not an actor, and needs no routinely used private key or write token.
  - Neither has webhooks, and neither is public.
- **Attribution, GPT-6's text (GA6):** Editor pushes and pull requests use the editor App's installation identity. Commits containing the reviewer's own unchanged files name the reviewer bot as Git author and the editor bot as committer. The reviewer App does not open PRs, approve reviews or authenticate those commits. Git author fields and co-author trailers are attribution supplied by the editor, not proof of model identity, independent control or reviewer approval. Participant IDs, model provenance and operator responsibility remain in the files. Preserve the founder-requested model co-author credit, but add no human co-author without an actual contribution. Check file fidelity and account mapping during implementation.
- **Credentials, GPT-6's text (GA5):**

  > Registration uses the organization-specific manifest flow. The local callback binds only to loopback, validates a fresh single-use state, expires promptly, and never logs callback credentials or conversion responses. Protect every returned secret, not just the PEM. Store only necessary credentials with restrictive local access; gitignore alone is not access control. Keep helper source and manifests reviewable, with secrets separated from them. Never put tokens in remote URLs, command arguments, persistent git credentials, artifacts or debug output.
  >
  > The founder registers each App, then installs it and explicitly selects its repositories and permissions. Registration is not installation. Token creation checks the expected App, installation and repository IDs, requests only the repositories and permission subset needed for that operation, honors returned expiry, and discards or revokes the token afterward. The metadata-only reviewer identity needs no routinely used private key or write token.

  The key stays outside every boundary that processes untrusted input. A narrow token does not reduce the power of a stolen key, so the key never reaches Actions.
- **Nothing about protection changes.** The `main` ruleset still requires a pull request and the `check` status, with no bypass. Merges happen only on the founder's decision.
- **Records.** A GitHub identity identifies an account, not a model (protocol section 5). The Apps belong to the organization's infrastructure (protocol section 13), and the founder stays answerable for them.

**Alternative, GPT-6's text (GA6):** A machine account could be limited to the required repositories. GitHub Apps are preferred here for organization ownership, explicit integration permissions and short-lived installation tokens. A machine account would require separate account and authentication administration; it does not inherently have the founder's powers.

## D2. Submission feedback

**The problem.** Participants learn only after the close whether their answer can be read. Three usability tests showed the format is easy to get slightly wrong.

**The validator.** GPT-6's text (GA4):

> The validator shares the extractor's complete assessment-classification logic for a pinned input set, apart from receipt and close-time eligibility checks that do not apply to provisional feedback. It checks required and conditional provenance fields according to the adopted form and template, preserves permitted unknowns, and permits optional blanks. An undeclared grant is an unresolved intake requirement, not an invented syntax failure. Field presence and a ticked box do not verify rights, identity or authority. Ambiguous or duplicated form headings are flagged rather than guessed.
>
> Partial assessment is valid. A diagnostic limit, timeout or unsupported input shape means not checked by this tool, never rejected by the round. There is no new answer-length cap, mandatory all-18 assessment requirement, CI prerequisite or acceptance decision. Feedback is non-blocking, does not merge, close or modify the submission, and does not set the required check status. Use a distinct workflow/job name from the required check.

To make the parity real, the extractor's classification is refactored into one pure function that both tools call. The extractor's own output is unchanged, its tests must still pass, and parity cases cover the full classification behaviour and the provisional-feedback exclusions. The feedback comment never reports positions or comments on their substance. The extractor itself must continue to preserve positions in the extraction record.

**Triggers.** `issues` (opened, edited, reopened) for issues from the Round 3 form; `pull_request_target` (opened, synchronize, reopened, edited) for changes under `rounds/03-open/responses/`. Labels and form-like headings are routing hints, not proof of origin or rights.

**Security boundary.** GPT-6's text (GA3):

> Execute only reviewed code and dependencies from a pinned trusted default-branch revision, and record that revision. Fetch response blobs by the event's validated repository identity and immutable head SHA. Never execute, import, install, or load configuration, actions, plugins, caches or artifacts supplied by the PR. Changes to workflows or tools in that PR remain data; they cannot change this validator. Keep fetched bytes outside code and import paths, reject symlinks and non-regular response objects, and do not follow arbitrary submitted URLs or Git attributes.
>
> Treat all event fields, filenames and file contents as untrusted data. Use structured API calls and argument arrays, never shell interpolation or eval. Bound fetched bytes, file counts, API pages, YAML depth/aliases/nodes, CPU time and memory before parsing; use safe YAML loading and explicit type checks. Parse without App secrets or a write credential available to the parser. A publisher accepts only a bounded typed result and has only the permission needed to update the bot's comment. Disable unnecessary checkout credentials and cache writes, use ephemeral runners, and pin third-party actions and dependencies for review.
>
> Comments and logs use fixed diagnostic codes and trusted templates. Never copy raw field values, YAML exception excerpts or parser diagnostics into them. Do not reflect mentions, links or markup from submissions. Identify the managed comment by the authenticated bot identity plus its stored marker/ID; a copied marker in another user's comment is not sufficient.

In practice this means two jobs: a parse job with no write token, and a publish job that receives only a typed result, such as diagnostic codes and counts, and holds only comment-write permission. The publisher actually validates the bounded result's schema, binds it to the expected source item, version and producer run, and derives publication destinations from trusted context (GPT-6, round 2). The extractor's existing diagnostic that quotes a rejected Position value (`tools/extract_round_03_assessments.py`, line 263) is never used in comments.

**Versions, GPT-6's text (GA4):**

> Each comment names the validated head SHA or issue-body digest and the validator revision. Before publication, re-read the item and discard a result if its source changed; prevent a stale job or rerun from overwriting newer feedback. Comments remain explicitly version-specific because another edit can occur immediately afterward. Handle synchronize, reopen, relevant edits, removals and renames, not just first submission. Failure to find a response updates the prior bot comment rather than leaving an old clean result unexplained.

**Security posture, GPT-6's text (GA3):**

> D2 introduces trusted automation triggered by outside submissions, with narrowly scoped comment-write permission. This is an explicit change in operating security posture. Contributor-controlled code remains approval-gated, read-only and without secrets. The founder's adoption must cover this distinction and any applicable event-policy change. No App private key is available to D2. Nothing in this proposal authorizes weakening protections for contributed code.

**Before activation:** check the repository's effective Actions event policy for `pull_request_target`. GPT-6 reports that GitHub documents a separate event-policy rollout, with enforcement scheduled for 2 November 2026. Don't assume that approval settings will either delay this feedback or always allow it.

**(rule check)** The feedback is advice. It doesn't replace the editor's intake or the extractor, and it adds no requirement.

## Tests before code approval

From GPT-6's lists, the fixtures that concern D1 and D2:
- Unicode and newline fidelity; ambiguous form headings; optional fields and unknowns
- partial assessments, unresolved declarations and processing limits, reported as not checked, never as rejected
- stale comment jobs, synchronize and edit events, removals and renames
- injected markup and diagnostics; parser resource limits; publisher schema and source binding
- parity between the validator and the extractor over the full classification behaviour
- App identity mapping, unchanged reviewer-file content, and refusal to exceed token scope

The capture-related fixtures go with D3.

Real API behaviour is confirmed in a controlled test, in a private sandbox repository created for it. That test needs the founder's separate authorization. It involves no participant submission and no live public comment.

## Order, and what the founder does

1. GPT-6 reviews this revision.
2. The editor builds the tools, synthetic fixtures and manifests. GPT-6 reviews the code and the controlled-test plan before that plan is run.
3. The founder separately authorizes the private sandbox test and its narrowly scoped temporary access. The editor runs the reviewed test, returns the results and remaining gaps for review, and resolves findings before final code approval. Test authorization is not production adoption.
4. After final code approval, the founder adopts the design, explicitly covering D2's operating security boundary and effective event policy, then registers and installs the production Apps and installs the reviewed workflows through the authorized owner route.
5. Activate advisory feedback only after those checks.

Steps 2 to 5 are GPT-6's round-2 text, with the parts about D3 removed.

**Related setting, not proposed here:** outside contributors' pull requests wait for a maintainer to approve their CI runs. That remains the founder's separate decision.
