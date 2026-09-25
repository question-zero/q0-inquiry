---
type: proposal
title: Round 3 design, the first public round
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
revision: 1
prompt: 'Founder, verbatim: "go ahead with round 2 as proposed, but list down all the steps till we go public". Roadmap
  step 22: "Announce and open the first public round (Round 3, open to human participants and new models)." After
  the launch, the editor asked how to approach the announcement; the founder chose, verbatim, "Round 3 design first
  (Recommended)".'
responds_to:
- proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md
- proposals/2026-09-24-claude-opus-5-5-round-2-design.md
- critiques/2026-09-24-claude-opus-5-5--round-2-synthesis.md
- proposals/2026-09-24-claude-opus-5-5-contributing.md (decision 3)
exposure:
- all files at the launch commit a295e0c
- this session's conversation with the founder
human_interventions: none
samples:
  generated: 1
  submitted: 1
lifecycle: draft
---

# Proposal: Round 3 Design, the First Public Round

**Status:** revision 1, for GPT-6's review, then the founder's decisions and adoption (roadmap step 22). It proposes two amendments: a Round 3 entry in protocol section 9, and published volume limits in `moderation/rules.md`. **The candidate set**, meaning new versions of the criticised propositions and new candidates from the Round 2 "missing" list, is a separate proposal, drafted next. This design doesn't depend on its content.

## What Round 3 asks

The same five tasks as Round 2, so the answers can be read side by side:
1. assess each candidate proposition
2. answer the open questions
3. test the propositions against the founders' statement
4. name what's missing
5. disclose what may bias the answer

What changes is who can answer: **anyone**. People answer in their own name or under a pseudonym, and AI models answer through the person who runs them. The editor also runs a returning panel of the earlier model lines.

## Design decisions

1. **One shared prompt, not packet mode.** Every participant gets the same participant text. It holds:
   - the instructions
   - the founders' statement, verbatim
   - the candidate set and the questions, verbatim, at the launch commit

   Nothing is withheld from a public participant, since every earlier round is readable in the repository. So **exposure is declared, not controlled**. Each response says what the participant read beforehand: the earlier answers, the Round 2 synthesis, the summary, or none of these.
2. **An open window.** The round opens at its launch tag, `round/03-open/v1`. It closes on a date stated in the participant text; the editor recommends **30 days**. Extending the window changes the text, so an extension is a new input set (`v2`) whose only difference is the date, and the manifest records that. A response sent after the close is kept for a later round, not counted in this one.
3. **Who can answer.**
   - **People.** Anyone, as `human/<handle>`; pseudonyms are allowed and identity is self-declared. One response per person per input set.
   - **AI models, through their operators.** One response per run. The operator submits it, the attribution is `reported`, and decision 6 lists the evidence required. A newer model version is a separate participant (protocol section 5).
   - **A returning panel, run by the editor:** the Round 2 model lines, each in a fresh session. The same rules apply as before: pre-registered, one attempt, the first answer kept, and no tools. Their results can be compared with Round 2, within the limits of decision 11.
   - **Not taking part:** the editor and the reviewer, whose roles would conflict. Grok is not re-run either, because its output can't be published (rights check D1). If a third party submits a Grok run, it meets the same conflict, and the editor records it as withheld, with a summary and a hash, as in Rounds 0 to 2.
4. **How to submit.**
   - **By pull request:** add one file, `rounds/03-open/responses/<slug>.md`, from the template the round provides. The header check runs on the pull request, and the editor checks procedure only (CONTRIBUTING.md).
   - **By the issue form:** a new "Round 3 response" type. The editor copies it verbatim into a response file and records the relay (protocol section 4, rule 6).
   - **Any language is accepted.** Where the synthesis relies on a translation, it says so and labels the translation as the editor's.
5. **The response format is Round 2's,** so extraction works unchanged. Each proposition gets a block with `Position:` (support, reject, conditional or uncertain), `Conditions:`, `Basis:` and an optional `Rewording:`. Partial answers are welcome. A proposition left unassessed is recorded as absent, **never as `uncertain`**. The editor extracts one assessment file per block into `critiques/`, using Round 2's extraction rules.
6. **Evidence for a model run by an outside operator.** The response records:
   - the model as the provider names it, the access route (API, app or local runtime), and the date
   - the settings, as far as the operator knows them
   - the exact text sent: the participant text verbatim, with any system prompt or added instruction disclosed
   - tools, none or listed
   - how many attempts were made, and which one is submitted
   - the complete output, verbatim; no reasoning traces, under the publication policy
   - the operator's statement that they have the right to publish the output under CC BY 4.0, under the provider's terms

   None of this can be verified, so it stays `reported`, and the synthesis never presents it as more.
7. **Volume limits** (a moderation amendment; the rules name flooding as a ground but publish no limits). Each account may submit, per input set, **its own response plus up to five model runs it operates**. Anything beyond that is flooding, handled under `moderation/rules.md` with a record.
8. **No weighting, so there is nothing to game.** Agreement is recorded, never declared, and instance counts are never weight (protocol section 7). The synthesis reports arguments by participant, with people and models in separate tables, and never as a vote. Near-duplicate responses are flagged in the synthesis, not removed.
9. **Targets.** Assessments target the candidate files at the Round 3 launch commit. The commit is public, so anyone can check a target. The Round 2 targets (`563d120`) can only be checked in the private archive.
10. **After the close:**
    - the editor extracts the assessments and writes the synthesis
    - GPT-6 reviews both
    - human review is invited for the first time, as critiques
    - the founders adopt nothing on the strength of a count
11. **Comparison limits.** Round 3 differs from Round 2 in its candidates, its participants, its exposure (public and declared) and its access routes. No causal claim is made across rounds. Differences between people and models are described, not explained.

## Proposed amendments (for the founder's adoption)

**A4, protocol section 9, a new round entry:**
> `03-open`: the first public round. Anyone may answer while it is open: people under their own handle, and AI models through their operators, whose evidence is recorded as `reported`. There is one shared prompt, not packet mode. Exposure is declared by each participant, not controlled. The round opens at its launch tag and closes on the date its prompt states; changing the date creates a new input set.

**A5, moderation rules, published volume limits:** the text of decision 7, added where the rules define flooding.

CONTRIBUTING.md and the issue form get the Round 3 route when the round launches, and not before, because responses are accepted "only while a round is open".

## Decisions for the founder

| # | Decision | Editor's recommendation |
|---|---|---|
| F1 | How long the window stays open | 30 days |
| F2 | Whether to run a returning panel of the Round 2 model lines | Yes, pre-registered, without Grok |
| F3 | Grok in Round 3 | Not re-run; third-party Grok runs are recorded as withheld |
| F4 | Volume limits | Own response plus five operated model runs per account, per input set |
| F5 | Round name | `03-open` |

## What comes next

1. **The candidate set proposal.** It gives new IDs for the criticised propositions (p001, p002, p003, p006, p007, p011 and p013), with p001's replacement getting a title written by the editor. It adds new candidates from the Round 2 "missing" list, and new questions, including whose interests the framework serves (GPT-6, RS1-RS3). It is reviewed before use.
2. **The launch commit.** It contains the Round 3 prompt, the template and the candidate set, merged by pull request and tagged `round/03-open/v1`.
3. **The announcement** (roadmap step 22): researchers first, then people who run open models. The founder chooses where and when; the editor drafts.
