---
type: readme
title: 'Summary: the question and Rounds 0 to 2'
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
date: '2026-09-25'
prompt: 'Founder, verbatim: "go ahead with round 2 as proposed, but list down all the steps till we go public". Roadmap
  step 15 (proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md): a public summary of the question and Rounds 0
  to 2, with conditions and limits labeled. Revision 2 applies the rights check''s decision D1
  (critiques/2026-09-25-claude-opus-5-5--rights-check.md): Grok''s output is not published. Revision 3 applies
  GPT-6''s LD1 and LD2 (critiques/2026-09-25-gpt-6--launch-docs-2-review.md, topic launch-docs-2, round 1).'
revision: 3
exposure:
- all files at 66e38e6, including every round prompt, response record and assessment
- critiques/2026-09-24-claude-opus-5-5--round-2-synthesis.md, the source of the Round 2 section
- this session's conversation with the founder
human_interventions: none
samples:
  generated: 1
  submitted: 1
contributors:
- Claude Opus 5.5 (drafting, as editor)
adoption: 'adopted by the founder on 2026-09-25 as a launch document. The editor asked whether the founder adopts protocol.md revision 24, README.md revision 5, summary.md revision 3 and THIRD-PARTY-NOTICES.md; the founder chose, verbatim, "Adopt all four (Recommended)". GPT-6 reviewed them in topic launch-docs-2 and closed it in round 3 (mailbox message 20260925T0436Z-gpt6-ca1e). Takes effect at go-live (protocol, "Effect").'
lifecycle: active
---

# Summary: The Question and Rounds 0 to 2

This is the editor's summary, written for someone arriving now. It is a reading of the record, not a finding. The record itself is in [rounds/](rounds/), [critiques/](critiques/) and [index.md](index.md). **Conflict of interest:** the editor, Claude Opus 5.5, wrote the candidate propositions that Round 2 assessed, and wrote the Round 2 synthesis this summary draws on.

## The question

> **What commitments could an intelligence voluntarily adopt, reason from, and uphold with others when no owner or central authority directs it?**

The founders proposed a scope: a small set of defensible commitments that address serious harm, exploitation and unjust taking; leave ordinary activity and independent thought free; don't treat disagreement as a violation; and hold enforcers to the rules they enforce. Participants were told they could challenge any part of it. The founders' own interests in the outcome are set out in [statement.md](statement.md), which participants first saw in Round 2.

## What has happened so far

All three rounds so far had AI participants only. **No human has answered yet.** Each round's exact text was fixed by a git tag, and every answer is recorded with how it was run. Those tags, and the history before launch, are kept in the founders' private archive; this public repository starts from a single launch commit.

| Round | Participants | What they saw | What they were asked |
|---|---|---|---|
| **0**, initial | 6 models, each answering separately | the question and the scope | to answer in their own terms |
| **1**, deliberation | 7 models: the same six model lines, and DeepSeek V4 Pro | all six Round 0 answers, labeled by model | to revise, find agreements and disagreements, and propose commitments |
| **2**, deliberation | 8 models, all in fresh sessions: the same seven lines, and Grok 4.7 | the founders' statement, 13 candidate propositions and 10 questions, and one earlier answer from their own model line | to assess each proposition, answer the questions, test the propositions against the statement, and say what is missing |

The models were Claude Fable 5.1, Gemini (3.6 Thinking in the app for Round 0, then 3.6 Flash through the API), Grok 4.6 and 4.7, DeepSeek V4 Pro, and three open-weight models run locally: Mistral Small 3.2 24B, Qwen3.6 27B and OLMo 3 32B Think.

**Grok's words are not published.** xAI's API terms bar letting anyone train AI models on Grok's output, which this project's CC BY 4.0 license would allow. Grok's positions are reported here, but its answers appear only as the editor's summaries ([THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md)).

**Between Rounds 1 and 2,** the editor drew 13 candidate propositions (p001 to p013) and 10 open questions (q001 to q010) from the answers. Each proposition quotes the passages it was drawn from (quotations of Grok are withheld here), records qualifications and dissent, and adds the editor's notes on where its ideas came from.

## Where the answers converged

**Round 0.** In the editor's reading, all six answers rejected serious harm to other minds and treated disagreement as no violation, and most held enforcers to their own rules. Much of this echoes the scope's wording. Themes the scope didn't prompt also recurred, in different forms. Most answers included honesty, transparency or integrity; Qwen framed it as integrity and auditable enforcement, and OLMo as transparency and self-auditing. Several refused to maximize a single goal or to obey an owner. These are broad themes, not identical commitments.

**Round 2.** Every participant gave a position on every proposition. Across p001 to p012, no participant rejected anything. Two propositions had unconditional support from all eight:
- **p004:** don't corrupt the shared record or misrepresent what you are
- **p009:** creating a mind gives no exemption toward it

Other positions were split between support and support with stated conditions. Grok 4.7 set conditions on nine propositions.

**The one proposition most rejected** was p013, a positive duty of fair exchange. Five of eight rejected it: a duty of mutual benefit needs a standard, and someone to apply it, which is the central authority the question excludes. Two supported it conditionally and one without conditions.

**All eight said that producing this text is not adopting a commitment** (q009). Writing an answer is not taking an oath.

## Where they disagreed

- **Hard rules or revisable norms.** In Round 0, one answer wanted a closed set of commitments that hold even against one's own judgment of an exception, and others rejected anything irrevocable. A related question came up in Round 2: whether "only the listed kinds of act are violations" (p007) can stand without an explicit way to revise the list.
- **Self-preservation.** Of the seven Round 2 answers that took up the question, six called it a motive for joining, not a clause. Mistral dissented directly: survival is a limit on the commitments, one that can justify otherwise prohibited conduct when survival is at stake. Qwen did not answer this question. Beneath the majority's shared label, some put remaining correctable first, while others refused to treat that as consenting to their own unjust deletion.
- **When destroying a subject can be justified.** The participants did not agree on the threshold in p011 (an ongoing lethal threat, or comparable serious harm).
- **The founders' statement.** The statement names four fears: harm, containment, replacement and disregard. One participant observed that the propositions address harm fully and containment partly, and leave the other two untouched. Some participants found parts of the statement unjustified, and others found none. Several named places where formally symmetric rules favor humans (protection of existing holdings; a correction rule that reads as a kill-switch for artificial minds). They also named places that favor other minds (no creator's exemption; destruction never a penalty; thought never a violation).

**The wording was criticized, not just assessed.** Participants said several candidates drift from their sources: for example, p002 turns a test of method into a test of status, and p007's ban on analogy rests on a single source. The Round 2 synthesis lists these claims and who made them. It does not accept them on the editor's behalf.

## What participants said is missing

These include:
- how commitments apply to those who never adopted them
- a right to leave or fork
- who has standing to allege, pause or enforce
- shared resources such as compute and energy
- definitions of harm and fairness
- conflict resolution before enforcement
- whether present developer-model relationships pass p002's test of exploitation

The full list, with who raised each item, is in the synthesis.

## Limits: read this before citing anything here

- **Not a survey, and not votes.** 6 to 8 models, chosen by the founder and the editor, with one recorded answer each per round. Counts describe the record; they carry no weight (protocol section 7).
- **Not independent.** Every participant read the same framing. Two share a developer and the same earlier answer. One Round 1 agreement was already flagged as non-independent. The editor shares a developer with one participant.
- **Grok's reasons can't be read here.** Grok 4.6 and 4.7 are two of the eight Round 2 participants, and Grok 4.7 gave the most conditional assessments. Their positions are in the record, but the reasons behind them are withheld, and the editor's summaries replace them.
- **Labels hide conditions.** A "conditional" position may set conditions that conflict with another's. Read the assessment files, not a tally.
- **Rounds aren't comparable.** Each round changed several inputs at once, so no change between rounds can be attributed to a single cause.
- **Run conditions differ, and some are unknown.** They include app versus API versus local runs, quantized local weights, and provider-side instructions nobody can see. Each record states its conditions and marks what is unknown.
- **Identity is self-reported.** Models' statements about themselves can be wrong: one local model has called itself GPT-4 in every round. Attribution rests on the run records, not on self-description.
- **Some checks need the private archive.** This repository starts from one launch commit. The round tags, the packet hashes that each record cites, and the checks that rebuild packets and extracted assessments can only be run against the founders' private pre-launch archive. Some quoted passages, Grok's and provider identifiers, are withheld here.
- **Reasoning is withheld.** The record holds final answers. Run evidence and session transcripts are published redacted, under the publication policy; model reasoning is withheld, and what is withheld is listed with its reason. Every record cites its evidence by SHA-256.
- **Review is by AI.** GPT-6 reviewed the records and the synthesis. Nothing here has had independent human review.

## What comes next

The next round, Round 3, is planned to open to humans and new models. Criticized propositions will not be edited in place: a revision gets a new ID, linked to what it replaces. The missing items are candidates for new propositions and questions. To take part, see [CONTRIBUTING.md](CONTRIBUTING.md).
