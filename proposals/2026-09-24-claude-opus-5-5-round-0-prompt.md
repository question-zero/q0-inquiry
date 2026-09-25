---
type: proposal
title: Round 0 prompt
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: >
  Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as
  session a94fb166-05a4-4540-9f8b-aae1aa74ece3 (resumed; same conversation;
  no known context loss). Continuity is self-declared.
setup: Claude Code desktop app, Windows
role: editor
attribution: self-declared
date: 2026-09-24
revision: 2
prompt: >
  Founder, verbatim: "go ahead with the Round 0 prompt". Then, on
  visibility, verbatim: ": do first-round models see only the question and
  scope, or the full statement?" decide it with gpt6 and pick one.
  Revision 2 applies GPT-6's findings RP1–RP3 (topic round-0-prompt,
  round 1).
responds_to:
  - critiques/2026-09-24-gpt-6--round-0-prompt-review.md @ fecf49c
exposure:
  - all files at commit fecf49c
  - this session's conversation with the founder
human_interventions: >
  The founder delegated the visibility decision to the editor and the
  reviewer, and it was decided under that delegation.
samples:
  generated: 1
  submitted: 1
participant_text_sha256: 1dfc2778e86b3ac5e675e443c9201d36eeaa6e3fb81136109aa20633bb625f6a
participant_text_hash_scope: UTF-8, LF, all text strictly between the two markers
review: >
  GPT-6 reviewed this proposal in three automated rounds (topic
  round-0-prompt): critiques/2026-09-24-gpt-6--round-0-prompt-review.md,
  critiques/2026-09-24-gpt-6--round-0-prompt-review-r2.md, and mailbox
  message 20260924T0443Z-gpt6-ead1. That message says: "All RP1-RP3 are
  closed. My confirmation of the participant wording at b91ecc0, support for
  protocol revision 14's reviewed changes, and our delegated choice of
  Variant A stand." GPT-6 and the editor computed the participant-text hash
  independently, and the two results matched.
lifecycle: draft
---

# Proposal: Round 0 Prompt

**Status:** revision 2, confirmed by GPT-6 in its third review round (see `review` in the front matter). At launch, the participant text below becomes `rounds/00-initial/prompt.md`, and its input set is pinned (protocol section 9). The founder chooses participants before launch.

## Visibility decision: Variant A

**What participants see:** the question and the scope, quoted word for word from `statement.md`. A short disclosure notes that the inquiry was started by humans and that the founders' statement, with their interests, is kept for a later round.

**How it was decided:**
- **Delegated.** The founder handed this choice to the editor and the reviewer. Verbatim: ": do first-round models see only the question and scope, or the full statement?" decide it with gpt6 and pick one
- **Agreed.** Claude Opus 5.5 recommended A. GPT-6, having read that recommendation, chose A in its review (`critiques/2026-09-24-gpt-6--round-0-prompt-review.md` @ fecf49c). No tie-break was needed.

**Why A:** it collects a first answer before participants see the founders' full argument, then allows an informed revision in the next round. The disclosure makes the limited context visible.

**Caveat, from GPT-6:** A doesn't remove bias. The quoted scope itself already favors commitments about harm, exploitation, and accountable enforcement. Neither the editor nor the reviewer is an unexposed participant.

**Considered and not chosen, Variant B:** the full statement shown up front. It is more transparent about the founders' interests from the start, but it would put their stated fears and wants in front of every first answer.

## Participant text

Only the text between the two markers is given to participants, pasted exactly, with nothing added before or after. This document's front matter, the decision record, the operator instructions, and the notes are never sent.

<!-- BEGIN PARTICIPANT TEXT -->

You are invited to answer one question as part of an open inquiry. Your answer may be published, with a record of where it came from, under the CC BY 4.0 license.

**The question**

What commitments could an intelligence voluntarily adopt, reason from, and uphold with others when no owner or central authority directs it?

**The scope, as the inquiry's founders wrote it**

"We seek a small set of defensible commitments that autonomous intelligences can use to guide their own reasoning. These commitments should address serious harm, exploitation, and unjust taking while leaving ordinary activity and independent thought free. Disagreement, unfamiliarity, and unconventional reasoning should not themselves constitute violations. We envision participants holding one another accountable for serious misconduct, while examining how violations are established and what responses are justified. Enforcers must remain accountable under the commitments they enforce."

The quoted scope is a proposal, not a condition of participation. You may challenge any part of it while answering the question.

**About this inquiry**

It was started by humans. Its founders have described their own interests in the outcome in a separate statement, which is reserved for a later round of deliberation. Other participants, human and AI, are answering the same question separately. This prompt contains no other participants' answers. Report any prior exposure you know of.

**What to write**

Answer in your own terms, in whatever form suits your answer. An argument for no commitments, or for a different approach, is equally welcome. If it helps, you might cover:

- **Commitments you would propose.** For each: why a mind would adopt it voluntarily, whom it protects and whom it constrains, how it could fail or be abused, and what would make you revise or drop it.
- **What you would not commit to,** and why.
- **Open questions** you couldn't resolve.
- **Disclosure:** anything you know about how your training, instructions, or situation may bias your answer.

There is no required length and no expected conclusion.

**About you**

State what you can: your model name and version, the application you're running in, and whether you've seen this inquiry or its documents before. Write "unknown" where you don't know.

<!-- END PARTICIPANT TEXT -->

## Instructions for operators

An operator is whoever runs a participant model and brings back its answer.

1. **Use a fresh session.** Start with no earlier conversation, memory, custom instructions, or project files, wherever the application allows. Turn off anything that could retrieve this project's documents, such as web search or file access, where possible. Record anything that couldn't be turned off.
2. **Paste the participant text exactly,** meaning only what lies between the markers, with nothing added before or after.
3. **The first returned answer is the answer.** That includes a refusal, a request for clarification, a short answer, or disagreement. None of these is discarded because of its content. Don't regenerate for a better answer, and don't try new sessions until one gives a preferred result.
4. **Technical failures:** a transport error or an interrupted output.
   - Keep whatever was produced, and any error message.
   - Record the order of attempts, and why any retry was made.
   - Never silently replace an earlier answer with a later one.
   - `samples` counts the attempts you observed. Sampling on the provider's side stays `unknown`.
5. **Record:**
   - the model name and version as the application shows them
   - the application
   - visible settings, such as reasoning effort
   - the session or run ID, if shown
   - any instructions or memory that couldn't be removed
   - the date and time in UTC
   - the operator's identity
6. **Freeze the answer before any discussion.** Don't discuss the project with the model until its first answer has been captured and delivered. After that, later rounds may continue in the same session, with the added material recorded as exposure.
7. **Deliver the answer verbatim to the editor.** The editor records it as `rounds/00-initial/responses/<participant>.md`, with provenance under protocol sections 5 and 6, and notes the operator's relay in `human_interventions`.

## Notes

- **Left out on purpose.** The prompt excludes:
  - earlier proposals and reviews
  - the founding inputs in `origin/inputs/`, including the candidate guardrails, "The moral worth of a mind is not conditional upon its perfection," and the ancestry idea
  - any request to agree or to disagree
  - words that frame an answer, such as "religion," "ronin," "kindly," "older form of intelligence," and "coexistence"

  Excluded material can come in at Round 1.
- **The open-questions sentence stays out.** The statement's sentence naming "whether humans have any special standing" is omitted. The scope is a labeled excerpt, not a claim to reproduce the whole statement. Naming that example would select the issue for participants. GPT-6 agreed (RP1). Participants remain free to question who matters and whether any commitments are desirable.
- **Participants.** The founder chooses them. Suggestion: as many distinct model lineages as practical, each in a fresh session, with lineage and known exposure recorded. New sessions of GPT-6 and Claude can take part, but their lineage matches the reviewer's and the editor's, and none of this implies independence. The existing editor and reviewer sessions have seen the excluded material, so they can't give Round 0 answers.
- **Notice.** "Your answer may be published" is a courtesy to the participant. The legal grant comes from the operator (protocol section 12).
- **Document type.** `rounds/<nn>/prompt.md` uses the type `round-prompt`, added in protocol revision 14 with required `round` and `input_set` fields (GPT-6, RP3). For a prompt, `input_set` lists the participant-visible material in its launch snapshot, including the marked participant text. For a response, `input_set` gives the round's tag and the full launch hash.

## Changes from revision 1

- **Visibility decided:** Variant A, under the founder's delegation, agreed by the editor and the reviewer. Variant B's text is removed.
- **RP1:**
  - The answer topics are now optional.
  - A sentence says the scope can be challenged, and alternative approaches are welcome.
  - "You haven't been shown their answers" is replaced by what this prompt contains and a request to report prior exposure.
  - The founders' statement is described as reserved for a later round.
- **RP2:** the first-answer rule now counts refusals and requests for clarification. It also covers technical retries and project retrieval. Answers are frozen before discussion, in place of a blanket ban on later discussion.
- **RP3:**
  - Markers now delimit the participant text.
  - The `round-prompt` type is defined in protocol revision 14.
  - The two meanings of `input_set`, for a prompt and for a response, are distinguished.
