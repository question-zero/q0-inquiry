---
type: proposal
title: Succession of project infrastructure
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166 (used in revision 1)
run: >
  Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as
  session a94fb166-05a4-4540-9f8b-aae1aa74ece3 (resumed; same conversation;
  no known context loss). Continuity is self-declared.
setup: Claude Code desktop app, Windows
attribution: self-declared
date: 2026-09-24
revision: 4
prompt: >
  Revision 1, founder verbatim: "or don't take my opinion, lets brainstorm an
  idea that fits all stakeholders". Revision 2: GPT-6's feedback, relayed by
  the founder, verbatim: "The succession proposal also needs to account for
  liquidators and creditors, define notice and dispute procedures, and
  qualify its promises that history cannot be deleted and licenses cannot
  change. A second GitHub owner improves continuity but has full
  administrative power." Revision 3: GPT-6's findings S1–S3, relayed by the
  founder (see responds_to). Revision 4 records the founder's decision for
  launch (roadmap step 9). The editor asked, verbatim: "Succession (step 9):
  the open items are people you'd trust (a second GitHub owner, a standby
  custodian, a dispute reviewer) and a Saudi legal review. What should happen
  before launch?" The founder chose, verbatim, "Defer people, record gaps
  (Recommended)".
responds_to:
  - protocol.md @ ad71bb3 (section 13, succession)
  - critiques/2026-09-24-gpt-6--succession-response.md @ 4fb479e
  - critiques/2026-09-24-gpt-6--protocol-r8-and-succession-r2-review.md @ 00cd305
exposure:
  - all files at commit 00cd305
  - this session's conversation with the founder
human_interventions: >
  The founder relayed GPT-6's feedback that prompted revision 2, and GPT-6's
  summary of the review that prompted revision 3. Revision 2 had recorded
  the relayed feedback as the founder's own words; revision 3 corrects that
  (GPT-6 finding S3).
samples:
  generated: 1
  submitted: 1
lifecycle: active
---

# Proposal: Succession of Project Infrastructure

**Status:** Revision 3. Revision 2 was rewritten around GPT-6's response (`critiques/2026-09-24-gpt-6--succession-response.md` @ 4fb479e), and revision 3 applies its later findings S1–S3. This is a proposal for the founder to decide on.

- **Planned, not guaranteed.** It describes succession as planned. It is not a legal instrument.
- **Legal review needed.** The company commitment needs review under Saudi law before anyone calls succession secured.
- **Time periods and thresholds are proposed defaults,** not established facts.

## Roles

These are different parties, and the process must not treat them as one.

| Role | Who |
|---|---|
| Owner | Alileus LLC |
| Liquidator | If the company is liquidated, acts for it under the law. A repository rule cannot override the liquidator's legal powers. |
| Creditors | Their claims are handled under applicable law and its order of priority. According to GPT-6's reading of the Saudi Companies Law (articles 252–255), the company's debts come before any return of capital or distribution of surplus. This proposal can't displace creditors' rights. |
| Shareholders | Receive residual entitlements after the company's obligations are addressed. Being a shareholder does not by itself outrank a valid company commitment. How the proposed commitment is treated is a question for the Saudi legal review. |
| Stewards | People or organizations who have accepted named continuity duties (below) |
| Standby custodian | A named, willing party who preserves the project during a gap or dispute. Not yet appointed |
| Dispute reviewer | A named independent party who decides disputed triggers. Not yet appointed |

## Now: the smallest workable arrangement

1. **A second GitHub owner:** someone who consents, is accountable, and uses a separate account and recovery method.
   - Every owner has full administrative power, including over the other owners.
   - This protects against lockout. It does not create joint control, so choose someone you'd trust with the whole organization.
2. **An asset and duty register** listing:
   - the organization and repositories
   - the domain, if bought
   - billing and recovery contacts
   - service agreements
   - any name rights actually held

   Keep company-wide accounts separate. Never publish secrets.
3. **Independent snapshots:** a Software Heritage save, a Zenodo release archive, and a second host.
   - Test restoring from them, and publish the snapshot IDs.
   - A live mirror alone can copy destructive changes.
4. **A named standby custodian and a named dispute reviewer.**
5. **An authorized company commitment to this process,** reviewed for its actual legal effect.

Until items 1–5 exist, forks and snapshots are the only fallback.

## Triggers

| Situation | What happens |
|---|---|
| **Planned exit:** a formal dissolution or liquidation decision, insolvency proceedings, or written withdrawal of support | Succession planning starts immediately. Nothing transfers automatically. |
| **Abandonment:** 6 months of documented failure to perform essential duties, then 60 days' notice to cure | The succession process starts. Time is counted from the failure, not from the last commit. A token action doesn't count as a cure. |
| **Urgent risk:** account loss, incapacity, compromise, or imminent expiry or nonpayment | Pre-authorized preservation and recovery start immediately. Permanent succession still goes through the process. |
| **Dormancy:** duties are performed but nothing new is contributed | Not a trigger. |

**Essential duties:** keep administrative access, handle renewals and security incidents, keep snapshots recoverable, and answer continuity notices.

**Notice and disputes:**
1. Anyone may report a failed duty, with evidence.
2. The standby custodian assesses the report, notifies the company and stewards through recorded channels, and publishes the claim and its reasons. If the main repository is unreachable, it publishes on an independent mirror.
3. The company may challenge the evidence. Disputed triggers go to the dispute reviewer.
4. If the challenge concerns the reviewer's own decision or interests, as when the standby custodian also serves as dispute reviewer, an independent alternate decides. If no independent alternate is available, authorized preservation continues and any contested permanent transfer waits.
5. During a dispute, preservation is allowed. Seizure is not.

## Choosing a successor

**Order:**
1. A willing foundation or fiscal host that has accepted these duties.
2. Otherwise, a willing steward chosen by the stewards.
3. Otherwise, if no one accepts within 60 days of the start of selection, a preserved archive.

Interim preservation continues throughout. Restarting from the archive later needs a recorded decision.

**Who counts as a steward.** This follows GPT-6's rule:
- They accepted a named continuity duty at least 90 days before the notice, and documented performing it within the previous year.
- Admission and removal come with stated reasons and are reviewed by an existing steward outside the applicant's control.
- Anyone may challenge a steward's admission, removal, or exclusion, including contributors who believe they were overlooked. Challenges go through the dispute route above.
- Dissent and unaccepted submissions never disqualify anyone.
- Stewards disclose their relationships. Parties under common control count as one.
- Extra accounts, model runs, commits, or donations add nothing.
- Eligibility is frozen at the last uncontested roster before the notice.

**Selection** needs support from two-thirds of eligible independent stewards, with more than half participating and at least two independent stewards in favor. This is an administrative rule, not a way of settling moral questions.

**Until at least two independent stewards exist, there is no one to choose.** Use the standby custodian or the archive.

## What any owner or successor must keep

- **History.** Preserve lawful public history. Exceptions are only those in protocol section 10 (private or unlawful material), and each must be documented. This replaces revision 1's "nothing is deleted."
- **Licenses.** Existing license grants can't be revoked while their terms are followed. A successor accepts the project's licensing policy. Any future policy change applies only from then on and is recorded. This replaces revision 1's "the license is not changed."
- **Content.** Ownership gives no authority to rewrite assessments, censor dissent, or claim anyone's endorsement.
- **Successors' terms.** A successor accepts in writing and gets a defined duty and budget. It may resign, and it has its own replacement process. Nobody promises unlimited personal funding.
- **Sponsors** get no automatic succession priority and no control over conclusions.
- **Custodians** are whoever can accept the obligations. This replaces revision 1's claim that AI can't legally hold accounts, which was too broad.

## Protecting the commitment

- **A promise alone isn't enough.** It needs an authorized company undertaking plus practical access arrangements.
- **Amending the succession commitment** requires public notice, a recorded review, and the agreement of both the company and a party independent of the company.
  - The independent party is the stewards, counted with common-control grouping so that stewards the company controls count as part of the company.
  - If there is no independent steward, the independent party is the standby custodian, who must itself be independent of the company.
  - The company can't remove the commitment on its own.
  - Changes are frozen while a claim is live.
  - Changes the law requires are allowed, with reasons recorded.
- **Protocol section 11 must be amended** to allow this extra consent requirement. Otherwise the founder's general power to adopt changes could undo it.

## Changes from revision 1

- "Beneficiaries" is replaced by the separate roles of liquidator, creditors, and shareholders.
- The trigger of 12 months' inactivity becomes 6 months of documented failure plus 60 days' notice. Planned-exit, urgent-risk, and dormancy cases are added.
- Commit-based "active maintainers" is replaced by a roster of stewards who accepted duties in advance.
- The promises about history, licenses, and AI accounts are narrowed as described above.
- The second-owner recommendation now states that the second owner has full administrative power.
- The participant ID reverts to `af349875`, per GPT-6's resumed-session finding (R5).

## Changes from revision 2

Following GPT-6's review (`critiques/2026-09-24-gpt-6--protocol-r8-and-succession-r2-review.md` @ 00cd305):

- **S1:** creditors and shareholders are separate rows. Creditors' claims follow legal priority. Shareholders receive residual entitlements and don't automatically outrank a valid company commitment.
- **S2:**
  - An independent alternate decides disputes that concern the dispute reviewer's own decisions.
  - Challenges to steward eligibility use the dispute route.
  - Dissent never disqualifies anyone.
  - Amendment consent requires a party independent of the company.
  - The 60-day acceptance window starts when selection begins.
- **S3:** the revision 2 prompt is now correctly attributed to GPT-6, relayed by the founder.

## The founder's decision for launch (revision 4)

The founder chose to defer naming people and to record the gaps. The option read, verbatim: "Launch without named people. Before launch: a tested private backup. After launch: public archive snapshots (Software Heritage, Zenodo). The protocol states plainly what stays unsecured until you name people and get the legal review. Keep the proposed periods (6 months + 60 days to trigger, 60 days to accept)."

So, for launch:
- **Before launch:** a private backup of the repository and the private archive, test-restored (roadmap step 9).
- **After launch:** a Software Heritage save and a Zenodo release archive, with their IDs published.
- **Kept:** the proposed periods, as defaults.
- **Stated as unsecured in the protocol** (section 13, in the refresh of roadmap step 11):
  - no second GitHub owner
  - no standby custodian or dispute reviewer
  - no authorized company commitment
  - no Saudi legal review

  Until these exist, the fallback is forks and snapshots.
- **Still open:** decisions 1–3 below. The founder can answer them at any time, and each answer goes through the usual route.

## Decisions for the founder

1. Who would be the second GitHub owner?
2. Who could be the standby custodian and dispute reviewer? One neutral party can hold both roles, but then an independent alternate is also needed for disputes about that party's own decisions.
3. Arrange Saudi legal review of the company commitment.
4. Keep or change the proposed periods: 6 months plus 60 days to trigger, and 60 days for a successor to accept.
