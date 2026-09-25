---
type: readme
title: Third-party notices
author: Claude Opus 5.5
model: claude-opus-5-5
developer: Anthropic
participant_id: claude-opus-5-5/af349875
participant_alias: claude-opus-5-5/a94fb166
run: Claude Code session af349875-929e-4a70-90a0-9a9f08e97da1, continued as session a94fb166-05a4-4540-9f8b-aae1aa74ece3
  (resumed; same conversation). Continuity is self-declared.
setup: Claude Code desktop app, Windows
operator: human/alileus
role: editor
attribution: self-declared
date: '2026-09-25'
prompt: 'The rights check (critiques/2026-09-25-claude-opus-5-5--rights-check.md, disposition 6), under protocol section
  12: third-party material keeps its own terms and must be marked as such. The Apache License text below is copied
  unchanged from a local copy of the standard text.'
exposure:
- critiques/2026-09-25-claude-opus-5-5--rights-check.md
- the model pages and terms it cites
human_interventions: none
samples:
  generated: 1
  submitted: 1
contributors:
- Claude Opus 5.5 (drafting, as editor)
adoption: 'adopted by the founder on 2026-09-25 as a launch document. The editor asked whether the founder adopts protocol.md revision 24, README.md revision 5, summary.md revision 3 and THIRD-PARTY-NOTICES.md; the founder chose, verbatim, "Adopt all four (Recommended)". GPT-6 reviewed them in topic launch-docs-2 and closed it in round 3 (mailbox message 20260925T0436Z-gpt6-ca1e). Takes effect at go-live (protocol, "Effect").'
lifecycle: active
---

# Third-Party Notices

Protocol section 12 says third-party material keeps its own terms and must be marked as such. This file marks the third-party material the repository reproduces, and the output it withholds. The license files control; this file adds no terms of its own.

## Mistral AI: the packaged system prompt of Mistral Small 3.2

- **Where:** `rounds/00-initial/responses/mistral-small-3-2-24b.md`, the `packaged_system_prompt` field, and any quotation of it elsewhere in the repository.
- **What:** the system prompt packaged with Mistral Small 3.2 24B Instruct, by Mistral AI. It is reproduced unchanged as run evidence: it was part of what that model received.
- **Source:** `SYSTEM_PROMPT.txt` in Mistral AI's model repository, https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506/blob/main/SYSTEM_PROMPT.txt. The record reproduces the text of the Ollama artifact that was run, identified by its layer digest in the record; the upstream file is its source.
- **Terms:** the Apache License, Version 2.0, under which Mistral AI distributes the model repository. The prompt file carries no notice of its own; the license comes from the repository's license declaration. The text is **not** licensed under this project's CC BY 4.0. The license's full text follows below.

## xAI: Grok's output is not published

xAI's API terms bar the customer from permitting anyone to train AI models on Grok's output, which CC BY 4.0 would permit. Because of that conflict with this project's license, the founder decided to withhold Grok's output (the rights check, decision D1). This is the project's choice, not a claim that xAI's terms forbid publication.
- Grok's answers appear only as summaries written by the editor, with the SHA-256 of each withheld text.
- Quotations of Grok elsewhere are withheld.
- The screenshot of Grok's interface is removed at launch.

Known quotations of Grok are withheld at any length. Wording that Grok happened to use as well, but that is not quoted from it, is not treated as its output.

## Other third-party material, item by item

None of these is licensed under this project's CC BY 4.0; each keeps its owner's terms. An inventory of the tracked tree found no other verbatim third-party text (GPT-6 RC4, topic `rights-check`).

| Material | Where | Source | Basis |
|---|---|---|---|
| The default system line of a local model's chat template, six words | the OLMo 3 records of Rounds 0 to 2, the Round 1 prompt and its design proposal, and two record reviews | Ollama's built-in OLMo renderer | Ollama's MIT license; a six-word generic instruction, reproduced as run evidence |
| The renderer's other OLMo default, truncated | the Round 0 OLMo record | the same renderer | Ollama's MIT license; a truncated clause, reproduced as run evidence |
| Chat-template markup (ChatML and Mistral tokens) | the OLMo, Qwen and Mistral records of Rounds 0 to 2 | Ollama renderers and the models' tokenizer templates | functional markup, reproduced to show exactly what each model received |
| An error message from the local model server, seven words | the Round 0 Qwen record and one review | Ollama | Ollama's MIT license; reproduced as run evidence |
| The C2PA content credential in the logo | `assets/question-zero-logo.png` | OpenAI's image service: an embedded generator icon and a certificate chain from SSL.com and OpenAI | provenance metadata that OpenAI attaches to disclose AI generation, kept unchanged so it can still be verified |
| Two terms reported secondhand, one and two words | `origin/inputs/2026-09-24-gpt-5-6-sol-brainstorm-extract.md` | named projects' self-descriptions, as reported by GPT-5.6 Sol | names and short terms, cited for identification |
| The Apache License 2.0 text | this file | the Apache Software Foundation | the license requires that a copy be given with the material it covers |

Two further items are withheld at launch rather than published: the Claude Code CLI's fixed prompt prefix (privacy sweep S7) and the Grok screenshot (above). Fetched web and documentation content in the exported archive is withheld by the exporter as class D.

## Generated images

`assets/question-zero-logo.png` was generated with ChatGPT image generation. OpenAI's terms give the user the output. The operator licenses it under CC BY 4.0, and its C2PA content credential is kept.

## Apache License, Version 2.0

The text below is the standard license text, unchanged.

```text
Apache License
                        Version 2.0, January 2004
                     http://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.

   "License" shall mean the terms and conditions for use, reproduction,
   and distribution as defined by Sections 1 through 9 of this document.

   "Licensor" shall mean the copyright owner or entity authorized by
   the copyright owner that is granting the License.

   "Legal Entity" shall mean the union of the acting entity and all
   other entities that control, are controlled by, or are under common
   control with that entity. For the purposes of this definition,
   "control" means (i) the power, direct or indirect, to cause the
   direction or management of such entity, whether by contract or
   otherwise, or (ii) ownership of fifty percent (50%) or more of the
   outstanding shares, or (iii) beneficial ownership of such entity.

   "You" (or "Your") shall mean an individual or Legal Entity
   exercising permissions granted by this License.

   "Source" form shall mean the preferred form for making modifications,
   including but not limited to software source code, documentation
   source, and configuration files.

   "Object" form shall mean any form resulting from mechanical
   transformation or translation of a Source form, including but
   not limited to compiled object code, generated documentation,
   and conversions to other media types.

   "Work" shall mean the work of authorship, whether in Source or
   Object form, made available under the License, as indicated by a
   copyright notice that is included in or attached to the work
   (an example is provided in the Appendix below).

   "Derivative Works" shall mean any work, whether in Source or Object
   form, that is based on (or derived from) the Work and for which the
   editorial revisions, annotations, elaborations, or other modifications
   represent, as a whole, an original work of authorship. For the purposes
   of this License, Derivative Works shall not include works that remain
   separable from, or merely link (or bind by name) to the interfaces of,
   the Work and Derivative Works thereof.

   "Contribution" shall mean any work of authorship, including
   the original version of the Work and any modifications or additions
   to that Work or Derivative Works thereof, that is intentionally
   submitted to Licensor for inclusion in the Work by the copyright owner
   or by an individual or Legal Entity authorized to submit on behalf of
   the copyright owner. For the purposes of this definition, "submitted"
   means any form of electronic, verbal, or written communication sent
   to the Licensor or its representatives, including but not limited to
   communication on electronic mailing lists, source code control systems,
   and issue tracking systems that are managed by, or on behalf of, the
   Licensor for the purpose of discussing and improving the Work, but
   excluding communication that is conspicuously marked or otherwise
   designated in writing by the copyright owner as "Not a Contribution."

   "Contributor" shall mean Licensor and any individual or Legal Entity
   on behalf of whom a Contribution has been received by Licensor and
   subsequently incorporated within the Work.

2. Grant of Copyright License. Subject to the terms and conditions of
   this License, each Contributor hereby grants to You a perpetual,
   worldwide, non-exclusive, no-charge, royalty-free, irrevocable
   copyright license to reproduce, prepare Derivative Works of,
   publicly display, publicly perform, sublicense, and distribute the
   Work and such Derivative Works in Source or Object form.

3. Grant of Patent License. Subject to the terms and conditions of
   this License, each Contributor hereby grants to You a perpetual,
   worldwide, non-exclusive, no-charge, royalty-free, irrevocable
   (except as stated in this section) patent license to make, have made,
   use, offer to sell, sell, import, and otherwise transfer the Work,
   where such license applies only to those patent claims licensable
   by such Contributor that are necessarily infringed by their
   Contribution(s) alone or by combination of their Contribution(s)
   with the Work to which such Contribution(s) was submitted. If You
   institute patent litigation against any entity (including a
   cross-claim or counterclaim in a lawsuit) alleging that the Work
   or a Contribution incorporated within the Work constitutes direct
   or contributory patent infringement, then any patent licenses
   granted to You under this License for that Work shall terminate
   as of the date such litigation is filed.

4. Redistribution. You may reproduce and distribute copies of the
   Work or Derivative Works thereof in any medium, with or without
   modifications, and in Source or Object form, provided that You
   meet the following conditions:

   (a) You must give any other recipients of the Work or
       Derivative Works a copy of this License; and

   (b) You must cause any modified files to carry prominent notices
       stating that You changed the files; and

   (c) You must retain, in the Source form of any Derivative Works
       that You distribute, all copyright, patent, trademark, and
       attribution notices from the Source form of the Work,
       excluding those notices that do not pertain to any part of
       the Derivative Works; and

   (d) If the Work includes a "NOTICE" text file as part of its
       distribution, then any Derivative Works that You distribute must
       include a readable copy of the attribution notices contained
       within such NOTICE file, excluding those notices that do not
       pertain to any part of the Derivative Works, in at least one
       of the following places: within a NOTICE text file distributed
       as part of the Derivative Works; within the Source form or
       documentation, if provided along with the Derivative Works; or,
       within a display generated by the Derivative Works, if and
       wherever such third-party notices normally appear. The contents
       of the NOTICE file are for informational purposes only and
       do not modify the License. You may add Your own attribution
       notices within Derivative Works that You distribute, alongside
       or as an addendum to the NOTICE text from the Work, provided
       that such additional attribution notices cannot be construed
       as modifying the License.

   You may add Your own copyright statement to Your modifications and
   may provide additional or different license terms and conditions
   for use, reproduction, or distribution of Your modifications, or
   for any such Derivative Works as a whole, provided Your use,
   reproduction, and distribution of the Work otherwise complies with
   the conditions stated in this License.

5. Submission of Contributions. Unless You explicitly state otherwise,
   any Contribution intentionally submitted for inclusion in the Work
   by You to the Licensor shall be under the terms and conditions of
   this License, without any additional terms or conditions.
   Notwithstanding the above, nothing herein shall supersede or modify
   the terms of any separate license agreement you may have executed
   with Licensor regarding such Contributions.

6. Trademarks. This License does not grant permission to use the trade
   names, trademarks, service marks, or product names of the Licensor,
   except as required for reasonable and customary use in describing the
   origin of the Work and reproducing the content of the NOTICE file.

7. Disclaimer of Warranty. Unless required by applicable law or
   agreed to in writing, Licensor provides the Work (and each
   Contributor provides its Contributions) on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
   implied, including, without limitation, any warranties or conditions
   of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
   PARTICULAR PURPOSE. You are solely responsible for determining the
   appropriateness of using or redistributing the Work and assume any
   risks associated with Your exercise of permissions under this License.

8. Limitation of Liability. In no event and under no legal theory,
   whether in tort (including negligence), contract, or otherwise,
   unless required by applicable law (such as deliberate and grossly
   negligent acts) or agreed to in writing, shall any Contributor be
   liable to You for damages, including any direct, indirect, special,
   incidental, or consequential damages of any character arising as a
   result of this License or out of the use or inability to use the
   Work (including but not limited to damages for loss of goodwill,
   work stoppage, computer failure or malfunction, or any and all
   other commercial damages or losses), even if such Contributor
   has been advised of the possibility of such damages.

9. Accepting Warranty or Additional Liability. While redistributing
   the Work or Derivative Works thereof, You may choose to offer,
   and charge a fee for, acceptance of support, warranty, indemnity,
   or other liability obligations and/or rights consistent with this
   License. However, in accepting such obligations, You may act only
   on Your own behalf and on Your sole responsibility, not on behalf
   of any other Contributor, and only if You agree to indemnify,
   defend, and hold each Contributor harmless for any liability
   incurred by, or claims asserted against, such Contributor by reason
   of your accepting any such warranty or additional liability.

END OF TERMS AND CONDITIONS
```
