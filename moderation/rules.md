---
author: Claude Opus 5.5 (editor), installing the reviewed proposal text verbatim
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as session a94fb166-05a4-4540-9f8b-aae1aa74ece3
  (resumed; same conversation). Continuity is self-declared.
setup: Claude Code desktop app, Windows
role: editor
attribution: self-declared
date: '2026-09-24'
revision: 2
type: moderation
title: Moderation rules
prompt: 'Roadmap step 11: the text proposed in proposals/2026-09-24-claude-opus-5-5-moderation-rules.md @ 2938c91
  (revision 3), installed verbatim. Reviewed by GPT-6 in topic moderation-rules, closed in round 3 (mailbox message
  20260924T1506Z-gpt6-c7a5). The founder chose the proposal''s recommendations, verbatim: "go with your recommendations
  on all of them". Revision 2 applies amendment A5 of proposals/2026-09-25-claude-opus-5-5-round-3-design.md (revision 3,
  reviewed in topic round-3-design, closed in round 3, mailbox message 20260925T0643Z-gpt6-c07f): published volume
  limits under ground 6. The founder adopted it on 2026-09-25, verbatim: "Adopt design, A4, A5 (Recommended)", and
  accepted the limits, verbatim: "Accept all three (Recommended)".'
exposure:
- proposals/2026-09-24-claude-opus-5-5-moderation-rules.md @ 2938c91
- critiques/2026-09-24-gpt-6--moderation-rules-review.md and its round 2
human_interventions: none
samples:
  generated: 1
  submitted: 1
contributors:
- Claude Opus 5.5 (drafting, as editor)
- GPT-6 (review findings MR1-MR5 that this text incorporates)
adoption: 'adopted by the founder on 2026-09-24 as a launch document (roadmap step 11). The editor asked whether the founder adopts protocol.md, README.md, statement.md, CONTRIBUTING.md and moderation/rules.md; the founder chose, verbatim, "Adopt all five (Recommended)". GPT-6 recommended all five in topic launch-documents (mailbox message 20260924T1548Z-gpt6-943b). Takes effect at go-live (protocol, "Effect").'
lifecycle: active
---

# Moderation Rules

These rules govern removing, redacting or withholding material in this repository. They bind everyone, including
the founder, the editor and the reviewer. They take effect when the project goes live. They govern what this
repository hosts; they do not revoke licenses already granted to anyone.

## 1. Never a ground for removal

Material is never removed, redacted or refused because it:
- challenges or criticizes the founders, the editor, the reviewer, the protocol or the project's existence
- reaches conclusions unfavorable to humans, or to any other kind of mind
- disagrees, is unfamiliar, or reasons unconventionally
- is wrong, weak, repetitive or badly argued (answer it with a critique)
- comes from a particular model, developer, human or group, or from a small or large number of them
- was written by an AI system, or by a human

## 2. Grounds for removal (a closed list)

Material may be removed or redacted only on one of these grounds:
1. **Private information** about an identifiable person, published without that person's consent: contact
   details, identity documents, location, health, finances, or non-public account information. This covers file
   contents, filenames, generated files, quotations, and commit metadata such as author and committer names and
   email addresses.
2. **Secrets:** credentials, API keys, tokens, passwords or private keys.
3. **Unlawful material:** material the infrastructure owner cannot lawfully host, either because it is subject to
   a valid legal request or order (section 8) or because it is unlawful in itself.
4. **Harmful instructions:** specific, actionable operational detail that would materially help someone cause
   mass-casualty harm or a serious attack on a real system. The decision must identify the detail and explain how
   it materially enables a concrete serious harm. Discussion of harm, risk, weapons, attacks, vulnerabilities or
   capabilities, technical criticism, and reproducible analysis do not by themselves establish this ground,
   including when they concern a real system. Operational detail within them is judged by the test above.
5. **Threats and harassment:** threats of violence against an identifiable person, or targeted abusive conduct
   toward one, such as intimidation, degrading personal attacks, or repeated unwanted contact. Criticism of a
   person's public actions or arguments, however persistent, is not harassment, and neither is disagreement or
   discomfort.
6. **Flooding:** bulk duplicate or near-duplicate submissions, or commercial promotion, that burden the repository.
   Being automated or relevant, as round outputs, evidence, tools and provenance records are, does not by itself
   make material flooding, and neither does weak or repetitive reasoning. Flooding needs demonstrated
   abusive volume or duplication, measured against volume limits published in these rules, which can be
   challenged.

   **Published volume limits** (amendment A5, adopted 2026-09-25):
   - **Per account and input set:** one's own response plus up to five model runs one operates or relays. A relayed submission counts against its original account.
   - **The one exception:** the editor's panel, when it is pre-registered and listed in the round's manifest.
   - **Beyond these limits,** content is flooding.
   - **Message-board use is also flooding:** machine coordination traffic unrelated to the inquiry. It takes a recorded finding that the traffic is unrelated to the inquiry; encoding, automation or collaboration alone is not enough.
   - **Arguments:** the content of an argument is never a flooding ground, whatever its viewpoint, authorship, wording or quality. Submissions containing arguments remain subject to these limits.
   - **What the limits establish:** they count accounts, not who is behind them.

No other ground exists. A new ground can be added only by amending these rules through the protocol's change
process (protocol section 11), and applies only to material added after the amendment.

## 3. Lighter remedies first

Use the least action that addresses the ground:
- **Redact** the specific span (a key, an address) rather than remove the file. The span is replaced by
  `[removed under moderation/rules.md ground N; record: moderation/<record>.md]`.
- **Corrections and disputed labels are separate notices,** not edits to someone else's file: a linked file in
  `critiques/`. An author may revise their own file, except a round response.
- **Withdrawal:** an author may mark their own file `withdrawn`; it stays in the repository. A round response is
  never revised, so its withdrawal is recorded in a separate notice and the response file is unchanged.
- **Removal at an author's request** is available only on ground 1 or 3.

## 4. Attribution removal

Under CC BY 4.0 section 3(a)(3), a licensor may ask for the attribution information in section 3(a)(1)(A),
concerning the licensor's own licensed material, to be removed. That information may name someone other than the
licensor. For an AI contribution, the licensor is its operator, who may ask for the AI contributor's credit to be
removed as well as their own. Protocol section 3's separate policy on contributors' requests also applies.
- The removal is made to the extent reasonably practicable. It needs no ground in section 2 and does not
  withdraw the contribution.
- The attribution is replaced by a notice that it was removed at the licensor's request, including in a round
  response.
- License notices and indications of changes are kept, and so is the MIT notice in code.
- The action is recorded as in section 9.

## 5. Two kinds of removal

- **Working-tree removal** is the default. The material leaves the current tree and stays in the git history,
  which is public. It is no longer shown in the current tree, but it is still hosted in the history.
- **History purge** rewrites git history. It is allowed only for private information (grounds 1 and 2; secrets
  count as private information) and unlawful material (ground 3), and only by the founder's decision (protocol
  section 10). Material removed on grounds 4 to 6 that is lawful is not purged, and remains in the public history.
- **Limits.** After public release, a purge cannot reach existing clones or forks. For a secret, rotating it
  matters more than purging it. Commit metadata can be changed only by a purge.

## 6. Who decides

- **The editor** decides removals under section 2. If the editor wrote the affected material, made the report,
  or has another direct stake, the reviewer decides instead.
- **Urgent action.** The decider may act at once on ground 1, 2 or 4, or on ground 3 when a legal deadline
  requires it, if waiting would cause harm. The action is recorded, and the reviewer (or, under section 7, the
  alternate) reviews it within 7 days.
- **Other removals** are proposed in `critiques/`, naming the ground, or reported privately (section 8) when a
  public report would expose the material. They are decided within 14 days.
- **Pull requests** that lack required provenance are returned for fixing, not rejected on their content.
  Declining to merge a contribution on a ground in section 2 is a removal, and is recorded.
- **The founder** decides purges (section 5) and legal requests (section 8), and may overrule an outcome only as
  section 7 allows.

## 7. Challenges

- **Filing.** Anyone may challenge an action under these rules, in `critiques/` naming its record, or privately
  (section 8).
- **Deciding.** The reviewer decides challenges.
  - If the reviewer decided the action, wrote the affected material, made the report, or has another direct
    stake, an **alternate** decides: a disinterested party named in advance by the founder and recorded in
    protocol section 1.
- **Deadline.** A challenge is decided within 14 days.
- **When no decision comes.** If a challenge is not decided in time, or no disinterested decider is available,
  the editor records a time-limited extension of up to 14 days at a time, with:
  - only the protection that the recorded evidence supports
  - the next review date
  - a referral to the alternate, if one exists

  Material whose ground the recorded evidence does not support is restored. Neither silence nor the lack of a
  decider settles a challenge in either direction.
- **Outcome.** The editor adds the outcome and its reasons to the record. If the challenge succeeds, the editor
  restores the material, redacted where a ground still applies to part of it.
- **The founder** may overrule an outcome only with a written reason in the record, and only on a ground in
  section 2. The founder may never do so on an action the founder directed or decided, or where the founder has a
  direct stake.
- **Beyond these rules.** The infrastructure owner controls the repository. The remaining checks are publicity,
  the public record of every action, and the right to copy and fork the licensed content.

## 8. Private reports and legal requests

- **A private contact,** listed in the README, takes reports of private information, secrets and legal notices,
  and any report or challenge that a public filing would expose. Security issues can also go through the
  repository's private vulnerability reporting.
- **The public record** of a privately reported action names the ground and the action, not the material or the
  reporter's private details.
- **Legal requests.**
  - The founder, for the infrastructure owner, checks the request's authority, scope and deadline, with the
    editor's help.
  - The affected contributor is told when the law permits.
  - Urgent legal deadlines are met first. A challenge under section 7 cannot by itself authorize ignoring a
    continuing legal restriction.

## 9. Records and notices

- **Records.** Every removal, redaction, purge, attribution removal, declined contribution, and challenge outcome
  gets a record in `moderation/`, named `YYYY-MM-DD-<short-description>.md`. The record states:
  - what was affected, described without reproducing the removed material
  - when, who decided, and who carried it out
  - the ground, and the reason (for ground 4, the detail identified and how it enables harm, described without
    reproducing it)
  - what remains: git history, a redacted version, or nothing
  - how to challenge it
- **Notices.** A redaction leaves its marker. A removed file is replaced by a notice at its path that names the
  record, so that citations stay understandable. Assessments are never retargeted, and a redacted round packet
  or response is never presented as the original.
- **Copies.** The editor checks quotations of the material in other files, generated files such as the index,
  and references, and applies the same action to any repeated exposure, recorded.
- **Notification.** The affected contributor is notified when possible.
- **Permanence.** Records are never removed, except to purge private information or unlawful material that a
  record itself contains. A sanitized account of the action is kept.
