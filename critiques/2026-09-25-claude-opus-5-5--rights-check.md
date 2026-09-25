---
type: critique
subtype: response
title: 'Launch step 14: rights and provider-terms check'
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as session a94fb166-05a4-4540-9f8b-aae1aa74ece3
  (resumed; same conversation). The context was summarized more than once. Continuity is self-declared. The provider
  terms were read by a research subagent of this session in the built-in browser and by web fetch, on 2026-09-25;
  the editor re-read the xAI clause that drives decision D1.
setup: Claude Code desktop app, Windows
operator: human/alileus
role: editor
attribution: self-declared
date: '2026-09-25'
prompt: 'Founder, verbatim: "go ahead with round 2 as proposed, but list down all the steps till we go public". Roadmap
  step 14 (proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md) and the rights checks the publication policy
  depends on (proposals/2026-09-24-claude-opus-5-5-publication-policy.md, PP1 classes B and D). Revision 2 applies
  GPT-6''s RC1, RC2 and RC4 (critiques/2026-09-25-gpt-6--rights-check-review.md, topic rights-check, round 1); RC3
  is applied in the private summaries file. Revision 3 records the founder''s decisions D5 and D6 on the two risks
  left open in its round 2 review (critiques/2026-09-25-gpt-6--rights-check-review-r2.md), and the code closing RC2
  and RC4.'
responds_to:
- proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md
- proposals/2026-09-24-claude-opus-5-5-publication-policy.md
- protocol.md, section 12
exposure:
- every tracked file at 605ea24
- the providers' published terms listed below, as read on 2026-09-25
- this session's conversation with the founder, including the four decisions quoted below
human_interventions: The founder made decisions D1 to D4 below by choosing among options the editor offered.
samples:
  generated: 1
  submitted: 1
revision: 3
lifecycle: active
---

# Launch Step 14: Rights and Provider-Terms Check

**This is a check, not a legal determination.** Neither the editor nor the reviewer is a lawyer. The terms were read on 2026-09-25, and any of them can change.

## The founder's decisions

The editor put each question with options and a recommendation. The founder's choices, verbatim:

| | Question | Founder's choice |
|---|---|---|
| **D1** | xAI's API terms bar the customer from letting anyone train AI models on Grok's output, and CC BY 4.0 allows exactly that. How should Grok's outputs be published? | "Withhold Grok's outputs". This was not the editor's recommendation, which was to publish them outside the CC BY grant. The option read: "Publish only hashes and summaries of Grok's answers. This keeps full compliance, but removes a key participant from the public record." *Annotation (revision 2):* "keeps full compliance" was the editor's assurance when offering the option. This check does not establish compliance with any provider's terms. |
| **D2** | Do you confirm your CC BY 4.0 grant (MIT for code) for all AI output you operated before launch, apart from the third-party material you exclude? | "Confirm the grant (Recommended)" |
| **D3** | When should GPT-6's interactive Codex sessions be published? | "In a later export (Recommended)" |
| **D4** | With Grok's text withheld, who should be the moderation alternate? | "Gemini becomes alternate (Recommended)" |
| **D5** | Which ModelArk service category applied to DeepSeek V4 Pro can't be confirmed; BytePlus's general terms give the output to the user, and no clause found restricts publishing it. How should DeepSeek's answers be handled? | "Publish, accept the risk (Recommended)" |
| **D6** | Google's terms make the customer responsible for how anyone it shares Gemini's output with uses it; CC BY shares it with everyone. Publish Gemini's answers with this recorded as a risk the founder accepts? | "Publish, accept the risk (Recommended)" |

## D2: the operator's grant

Under protocol section 12, the operator of an AI contribution makes the grant. The founder, `human/alileus`, operated every model in this inquiry: the editor and the reviewer under the founder's subscriptions, the API models under the founder's accounts, and the local models on the founder's machine.

**The grant, as confirmed.** The founder grants CC BY 4.0 for text, and MIT for code, in all AI output the founder operated before launch. That includes GPT-5.6 Sol's output quoted in `origin/inputs/2026-09-24-gpt-5-6-sol-brainstorm-extract.md`, from the founder's own ChatGPT conversation. It includes the AI-written files whose front matter doesn't name an operator: 37 at `605ea24`. It excludes the material listed under D1 and the third-party material listed below, which keeps its own terms. As section 12 says, only existing rights are licensed.

## What each provider's terms say

| Provider, product | Who owns output | What bears on publication | Source, date |
|---|---|---|---|
| **Anthropic:** Claude Code under a Pro or Max plan (the editor; Claude Fable 5.1 through the CLI) | Anthropic assigns its rights, if any, to the user while the user complies with the terms | the Usage Policy bars presenting output as human-generated | Consumer Terms, anthropic.com/legal/consumer-terms, effective 2025-10-08; Usage Policy, anthropic.com/legal/aup, effective 2025-09-15; Claude Code applies the Consumer Terms to Pro and Max, per code.claude.com/docs/en/legal-and-compliance |
| **OpenAI:** Codex and ChatGPT under a ChatGPT plan (the reviewer, the logo image, the GPT-5.6 Sol brainstorm) | the user owns output; OpenAI assigns its rights | the Sharing & Publication Policy asks that the operator be credited and that AI generation be indicated unmistakably. Codex output may be subject to third-party licenses | Terms of Use, openai.com/policies/terms-of-use, effective 2026-01-01; Sharing & Publication Policy, updated 2022-11-14; Service Terms §4, updated 2026-09-21 as the editor read it on 2026-09-25 (the reviewer's retrieval showed 2026-09-10) |
| **Google:** the Gemini API, paid tier (Rounds 1 and 2, the alternate appointment) and the Gemini app (Round 0) | Google claims no ownership, and assigns nothing | In the section on use of generated content, the customer is **responsible for how anyone it shares the content with uses it** (re-read by the editor). The use restrictions bar using the services to develop competing models, a restriction on the customer's use of the services, not the same as xAI's output clause. The Terms of Service ban presenting AI output as human-made to mislead. Grounded search results carry extra limits, but no Gemini API run used search | Gemini API Additional Terms, ai.google.dev/gemini-api/terms, effective 2026-03-23, page updated 2026-04-28; Google Terms of Service, effective 2026-07-30 |
| **xAI:** the xAI API (Grok 4.6 and 4.7 in Rounds 1 and 2, the alternate appointment) and grok.com (Round 0) | API: output is assigned to the customer. App: the user keeps whatever rights they have | **API, section 3.2: the customer will not permit any third party to train AI systems on output**, unless an order form says otherwise (re-read by the editor). App: attribute output to the service; the brand guidelines ask for a label crediting Grok. Neither is a general ban on publication | Enterprise terms, x.ai/legal/terms-of-service-enterprise, updated 2026-08-14; Consumer terms, x.ai/legal/terms-of-service, updated 2026-09-11 |
| **BytePlus ModelArk** (DeepSeek V4 Pro, run 2026-09-24) | General Terms for AI Services, §2.1: as between the user and BytePlus, the user owns the output, to the extent the law permits | §1.4: comply with labeling and disclosure laws when publishing. §4: third-party AI components may carry their own terms. ModelArk service terms, §1.1: a *proprietary* model service is governed by the model provider's terms; §1.2: an *open-source* model service by its open-source license. **Which of the two applied to `deepseek-v4-pro-ga-260813` is not established.** If open-source: DeepSeek V4 Pro's license is MIT, silent on outputs. If proprietary: DeepSeek's model service terms were not retrieved. The GenAI AUP (updated 2026-08-31) was reported by the research pass, not re-read. A consolidated AUP taking effect 2026-09-30, after the run, is not evidence of the terms that applied on 2026-09-24 | docs.byteplus.com/en/docs/legal/AI-Services-terms, last updated 2026-08-28, and docs.byteplus.com/en/docs/legal/docs-service-specific-terms, last updated 2026-09-02, both re-read by the editor on 2026-09-25 and in effect on the run date; huggingface.co/deepseek-ai/DeepSeek-V4-Pro (MIT) |
| **Open-weight models run locally:** Mistral Small 3.2, OLMo 3 32B Think, Qwen3.6 27B | the Apache-2.0 model licenses don't restrict outputs | Ai2's Responsible Use Guidelines exempt research use and otherwise ask for disclosure that content is machine-generated | the Hugging Face model pages, read 2026-09-25 |

**Model reasoning (class B).** No provider's terms address publishing returned reasoning or thought summaries. Under the publication policy, class B is published only where the terms are established to allow it. Here they aren't, so every provider's reasoning stays withheld (`cleared_reasoning` is empty).

## Dispositions

1. **Grok (D1): withheld.** This is the founder's choice, made because xAI's API clause conflicts with the license this project uses. It is not a claim that xAI's terms forbid publication, and it covers the Round 0 answer from the consumer app as a project choice. At the launch export, the following are withheld from the tree and from the exported archive:
   - every file Grok wrote: 4 round responses, 26 assessments, and its answer to the alternate appointment
   - every verbatim passage of Grok's output, wherever it is quoted: in propositions, questions, round prompts and packets, the synthesis, reviews, and other models' answers. **Known quotations are withheld at any length (RC2).** A detection threshold helps find unmarked copying; it is not an exception. Commonplace wording that Grok happened to use as well is not treated as its output.
   - the Grok Sources screenshot, which also shows xAI's interface
   - Grok's run evidence

   Each withheld file or passage is replaced by a marker, the SHA-256 of the withheld text, and, for Grok's answers, a neutral summary written by the editor and labeled as the editor's. The originals stay in the founder's private archive. The assessment positions (support, conditional, reject) are facts about the record, not Grok's expression, and stay. The transformation is done by a reviewed tool at step 16 and listed in the export manifest.
2. **The operator's grant (D2):** confirmed, above.
3. **GPT-6's interactive Codex sessions (D3):** not in the launch export. They stay preserved privately and go into a later export once the exporter supports their format. GPT-6's automated review runs are exported at launch.
4. **The moderation alternate (D4):** Gemini 3.6 Flash replaces Grok 4.7. This is recorded in `moderation/`, and the protocol's section 1 is updated through the usual route.
5. **AI labeling.** The front matter of every file names its author and model. The README should also state plainly that most of the repository was written by AI models, and name the operator. This is a change to an adopted document, so it goes through review and adoption.
6. **Third-party material:**
   - **Mistral's packaged system prompt,** reproduced in the Round 0 Mistral record, is covered by the model repository's Apache-2.0 license (huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506/blob/main/SYSTEM_PROMPT.txt). The record reproduces the text of the Ollama artifact actually used, which is identified by its layer digest; the upstream file is its source. The notices file credits Mistral AI, includes the Apache-2.0 text, and marks the passage as excluded from CC BY.
   - **The logo:** generated with ChatGPT, whose output is the user's. Its C2PA credential is kept.
   - **Code written with Codex** may include third-party code. None has been identified.
   - **Other third-party excerpts (RC4).** In the tracked tree, each retained excerpt is listed in the notices file with its location, source and basis, or else withheld at launch. In the archive, text fetched from web pages and documentation (the results of web tools, and the research subagent's report) is class D. It is withheld by the exporter, keeping the source reference and a disposition. It is not AI output under D2.
7. **Downstream use, provider by provider (RC1).**
   - **OpenAI and Anthropic** bar the user from using outputs to develop competing models. These restrictions concern the user's own use.
   - **Google** also makes the customer responsible for use of generated content by anyone it is shared with. Publishing under CC BY shares Gemini's answers with everyone. The project reads this as leaving the operator responsible under Google's terms, not as a ban on publishing. **How far that responsibility reaches, for recipients' uses that CC BY permits, is unresolved.** The founder accepted this risk and chose to publish (D6).
   - **BytePlus:** the terms that applied depend on the unresolved model-service category above. The founder accepted that risk and chose to publish DeepSeek's answers (D5). Accepting a risk is not clearance: the category stays unconfirmed, and it is recorded that way.

   None of this is established as a breach, and none is a legal determination.

## Code closing RC2 and RC4 (revision 3)

- **RC2, known quotations.** The builder now finds quotations in double quotes, single quotes, backticks and blockquotes. Attribution may come before or after the quotation, or in the paragraph that introduces a blockquote. Straight quotes and backticks must hug their content, so adjacent code spans don't pair into a false quotation. A withholding marker is never read as an attribution. A test covers your four probes. The archive uses a stricter rule: any quotation of two or more words whose earliest source is Grok is withheld, whatever surrounds it, because a transcript nests strings inside strings.
- **RC4, persisted copies.** The exporter classifies a tool result saved as its own file by the call that produced it, found in the transcripts. It withholds the file if that call fetched content, or if the call can't be found. The two page captures the research subagent saved are withheld this way. A test covers the same fetched text inside a transcript and in a standalone copy.
- **Verified end to end.** A full private trial of the launch commit, with the archive merged, passes every step 17 check in a fresh clone. That includes private scans finding no Grok spans, identifiers, configured terms or key values.

## What stays open

- The launch transform for D1, and its review.
- The README notice, the third-party notices file, the protocol's section 1 update and the summary's update: each goes through review, then the founder's adoption.
- GPT-6's final review of this record, topic `rights-check`, round 3.
