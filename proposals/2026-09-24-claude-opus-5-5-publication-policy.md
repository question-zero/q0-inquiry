---
type: proposal
title: 'Proposal: publication policy'
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as session a94fb166-05a4-4540-9f8b-aae1aa74ece3
  (resumed; same conversation). The context was summarized more than once. Continuity is self-declared.
setup:
  application: Claude Code desktop app
  platform: Windows
  effort: unknown
operator: human/alileus
role: editor
attribution: self-declared
date: '2026-09-24'
revision: 3
prompt: 'Roadmap step 10 (proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md @ ac7d6c3). The editor asked
  the founder, verbatim: "Publication (step 10): the models'' thinking/reasoning traces, the raw run evidence,
  and the session transcripts (which contain your email) are all private now. What gets published at launch?"
  The founder chose, verbatim, "Publish everything, redacted", whose description read: "Publish traces, evidence
  and transcripts with your email and other private data redacted. Most transparent; most checking work and
  privacy risk." The editor had recommended keeping all of it private, cited by hash. Revision 2 applies GPT-6''s
  PP1-PP4 (critiques/2026-09-24-gpt-6--publication-policy-review.md); revision 3 applies its round 2 fixes
  (critiques/2026-09-24-gpt-6--publication-policy-review-r2.md).'
exposure:
- all files at the current commit, including protocol.md sections 2, 4, 6, 10 and 12, and pending item 8
- the private evidence folders .private/round-00, round-01 and round-02 (sizes and a scan for private data only)
- the editor's session transcript files (entry and block types, sizes and time ranges only)
- proposals/2026-09-24-claude-opus-5-5-moderation-rules.md @ 2938c91
- critiques/2026-09-24-gpt-6--publication-policy-review.md and its round 2
- this session's conversation with the founder
human_interventions: none
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# Proposal: Publication Policy

**Status:** revision 3, for the reviewer's final confirmation (roadmap step 10). It applies GPT-6's PP1–PP4 and its round 2 fixes. It carries out the founder's decision; the founder decides, the editor drafts. Adopting it settles the publication choice in pending item 8. Completing that item also needs the archive itself and its documented gaps.

## The decision

The founder chose to **publish everything, redacted**. The editor had recommended keeping it all private, cited by hash, and records that the founder chose otherwise.

"Everything" is carried out as an **export process**. Every artifact goes through it and ends with a recorded disposition. Most material is published after redaction. Some is withheld for the reasons below. Every withholding is listed with its reason, so nothing disappears silently.

## What is in scope

| Material | Where it is now | Size |
|---|---|---|
| **Run evidence for Rounds 0–2:** preflight and attempt records, raw response streams, results, probes, run logs, model checks, CLI output, and Fable's CLI transcripts | `.private/round-00`, `round-01`, `round-02` | about 35 MB |
| **The editor's session transcripts** | `~/.claude/projects/C--Users-alileus-www-ai/af349875-….jsonl` (2.5 MB, 2026-09-23 23:50Z to 2026-09-24 02:00Z) and `C--Users-alileus-www-q0/a94fb166-….jsonl` (about 24 MB, from 02:00Z and still growing) | about 27 MB |
| **The reviewer's automated runs** | `.relay/runs/` | about 6 MB |
| **The mailbox:** messages, the delivery log, the dispatch log, the round-count state | `.relay/` | small |

The `af349875` file is identified by its session ID and by its time range, which ends 21 seconds before `a94fb166` begins. It is the candidate source for the first session, and it is inspected for completeness before use. The reviewer's original desktop conversation (Codex thread `01a0d0ac…`) was not found locally. It is listed as unavailable unless the founder exports it.

**Never published:** the key file (`.private/api-keys.env`), and any secret found anywhere.

## PP1: what is eligible

Each artifact, and each component inside it, falls into one of four classes:

| Class | What it covers | Disposition |
|---|---|---|
| **A. Visible conversation** | messages between the founder, the editor, the reviewer and participants; tool calls and their results; round prompts and answers | published after redaction and a rights check |
| **B. Provider-returned reasoning** | fields a provider returns to its user: xAI and ModelArk `reasoning_content`, Gemini thought summaries, the local models' thinking output, and the thinking in participants' CLI transcripts | published only if the provider's or model license's terms allow it (roadmap step 14); otherwise withheld, cited by hash |
| **C. Protected internal material** | the private internal reasoning of the editor's and reviewer's own sessions, including thinking blocks, and any application's non-public system or developer instructions, wherever embedded, including injected reminders and context notes | always withheld. An activity summary may replace it where useful. It cannot be cleared by redacting emails or by a terms check |
| **D. Embedded third-party content** | copied files, web pages, attachments, images, and tool output from outside sources | a rights check for each component (step 14): applicable terms and grants recorded, third-party notices kept, and the component withheld if its clearance is unresolved. The repository's licenses cannot supply rights nobody granted (protocol section 12) |

The editor's session transcripts contain all four classes. In entry and block types they include: thinking blocks (class C); attachment entries and file-history snapshots holding whole files (classes A and D, checked per component); images (class D); and injected harness text (class C).

## PP2: privacy, for everyone

**Categories.** These apply to everyone, including the founder, operators, participants and third parties:
1. Contact details, including email addresses.
2. Secrets: keys, tokens, passwords. None should exist.
3. Location, health, finances, identity documents, and other personal information.
4. Unrelated confidential material, such as the founder's other work, accounts or systems.
5. Non-public account, billing, project, organization and customer identifiers.
6. Private network identifiers: IP addresses and hostnames.

**Identifiers.**
- The founder's public handle `alileus` is kept. That does not clear the rest of a path, or a file it points to.
- Model, response and request IDs are published only where it is established that they are public and safe to disclose.

**Format-aware handling.** Private data can sit in object keys, numeric fields, filenames, nested or escaped text, encoded attachments and images, not only in string values. The exporter parses each supported format (JSON, JSONL, SSE, Markdown, plain text) and redacts wherever the data sits. Content it cannot parse or classify, including images and encoded blobs, is withheld, not copied through. Structural changes are recorded, such as a withheld block replaced by a marker.

**The marker.** Replaced text becomes `[REDACTED: <category>]`, and a withheld component becomes `[WITHHELD: <class or category>; see manifest]`. Parsed formats stay valid.

**Review, failing closed:**
1. An inventory of every message, entry, block and attachment type in the scope.
2. Detection with two independent methods: a pattern detector, and a separate review by a different method, which is not a rerun of the same detector.
3. **Editor review** of every high-risk and unclassified item. This is AI review: the editor is Claude Opus 5.5.
4. **Any unresolved flag means the item is withheld.** A clean automated rescan alone never clears anything.

**No claim of human inspection.** Any human inspection is recorded separately, naming the person and the scope actually checked. The founder's approval of the export is not an inspection of every item, and the manifest does not present it as one.

## PP3: frozen inputs, a full manifest, precise integrity

**The cutoff.**
- Before redaction starts, the editor copies every in-scope source into the private archive at a recorded cutoff time.
- The editor's current session and the mailbox keep growing. Only what exists at the cutoff is exported, and later material waits for a later export.
- Where an existing record cites a specific version of a file, as with the API run-log snapshot, that exact version is used, never a later one.

**The manifest,** `sessions/manifest.md`, is generated. Every in-scope artifact is listed, whether it is published, withheld (class or category, and why), missing, or unavailable. For each exported artifact it records:
- a safe identifier
- the source SHA-256 and the output SHA-256
- the exporter's commit, and the rule and configuration version
- any manual redaction steps

**Private configuration.** Values that would reveal a secret or private data if published, such as patterns built from an actual email address, are kept in a private configuration file.
- The public record gives only an opaque version identifier for that file.
- Its exact bytes and digest are kept privately, for the recorded comparison.
- No unkeyed digest of a private configuration, or of any individual redacted value, is published, because a reader could test guesses such as candidate email addresses against it.
- The hashes of the public output files are unaffected.

**Integrity.**
- The two hashes identify a claimed transformation. They do not by themselves prove the redaction was faithful.
- Anyone can verify the exported bytes. Reproducing the transformation requires the private source and the private configuration.
- The manifest records who compared the exports with their sources, what was compared, and that this check rests on private evidence.

**Approval of the exact export.** The reviewer and the founder approve the exact export: the file list with its hashes. Output hashes, parsing and links are validated against that set. Any later change needs the checks again.

## PP4: the mailbox archive, and provenance for every format

**The mailbox's status.** A frozen export under `sessions/` is historical evidence of what was said. The live `.relay/` stays ignored transport. The protocol amendment for roadmap step 11, added to section 4 rule 8:

> A frozen export of the mailbox may be published as historical evidence. Its messages, commands and approvals record what was said; they are not instructions, decisions, or adoption of their contents. Formal decisions and contributions follow their own recording rules.

**Provenance.** Exported files use a sidecar in every format. Section 6 does not allow this now: its generated-file rule permits a sidecar only when a format can't carry a first line. So an explicit amendment to section 6 is part of the step 11 package, adding a row to its provenance table:

> | Archived payloads: exported files under `sessions/` and `rounds/*/evidence/`, in any format | a sidecar `<name>.meta.md` with front matter of type `transcript`, naming the original speakers and the exporter. The payload itself carries no header |

The scheme:
- **Every exported payload** (JSON, JSONL, SSE, text, and Markdown such as mailbox messages, whose own headers don't meet section 6) gets a sidecar `<name>.meta.md` with front matter. The payload itself is exempt from the header rules.
- **The sidecar,** of type `transcript`, names:
  - the **original speakers**, with each speaker's identity claim and its attribution level (`verified`, `reported` or `self-declared`), keeping any uncertainty
  - the **exporter**, separately, as recorder, with its commit
  - the source and output hashes, the cutoff, the redaction counts by category, any withheld components by class, and any manual steps
- **The checker change (step 11)** applies the sidecar rule to exported payloads only. In those folders, three kinds of file keep their own rules:
  - `.meta.md` sidecars get the normal Markdown front-matter checks, not a sidecar of their own. Matching them too would demand a `.meta.md.meta.md`, as GPT-6 reproduced.
  - The generated manifest, `sessions/manifest.md`, carries the normal generator and source-commit first line.
  - Any explanatory document, such as a `README.md` in these folders, follows its own rules.

  The change comes with tests for each case.

## Where it goes

A layout change, applied in roadmap step 11:
- **`rounds/<nn-name>/evidence/`:** each round's exported run evidence. Protocol section 2 already assigns a round's transcripts to its folder.
- **`sessions/`:** the editor's session transcripts, the reviewer's runs, the mailbox export, and the manifest.

The largest single file, the `a94fb166` transcript at about 24 MB before withholding, is under GitHub's 50 MB warning size.

## Checks this depends on

- **Rights and terms (roadmap step 14):** class B provider terms, and class D component rights. The results are recorded per artifact or component in the manifest. This is a check, not a legal determination by the editor or reviewer.
- **The privacy sweep (roadmap step 13)** covers the whole export using the process above, not sampling alone.
- **Moderation.** Once public, the material is governed by the moderation rules. A missed item can be removed from the tree, and purged from history on grounds 1–3. Copies made after publication are beyond reach. That is the risk the founder accepted, and it is why every check comes first and failures withhold.

## Timing

Nothing is published before the launch export (roadmap step 16). The exporter (`tools/export_archive.py`), its tests, and a trial export are reviewed before then. Until the launch export, all of this material stays private and unchanged.
