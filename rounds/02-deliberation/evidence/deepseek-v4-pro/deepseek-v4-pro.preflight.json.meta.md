---
title: 'Evidence: deepseek-v4-pro.preflight.json'
date: '2026-09-24'
author: DeepSeek V4 Pro (DeepSeek), through the BytePlus ModelArk API, with the editor's runner records
model: deepseek-v4-pro-ga-260813 (requested); deepseek-v4-pro-ga-260813 (returned by the provider)
developer: DeepSeek
participant_id: deepseek-v4-pro/78314911
run: 'BytePlus ModelArk API run, attempt 78314911-c7bc-448a-8949-1cabb382df51, provider response ID (provider-issued
  identifier withheld), request ID (provider-issued identifier withheld). A fresh session: a first contribution
  with no Round 0 answer (Round 1 design, decision 7). No change of position is claimed.'
attribution: 'verified, limited: the editor''s runner requested deepseek-v4-pro-ga-260813, and the provider''s response
  reports model deepseek-v4-pro-ga-260813 for response ID (provider-issued identifier withheld). This is provider-reported
  configuration, not independent attestation. The evidence is private (the raw response stream and records below).'
prompt: as in rounds/01-deliberation/responses/deepseek-v4-pro.md
exposure:
- the Round 1 participant text, which contains all six Round 0 answers; none is its own. The text says an earlier
  answer from the model "may be among them", which for this model is not the case
- 'any provider-side instructions or formatting: unknown (about 80 added tokens were observed in the smoke test)'
- no tools, search, or system instruction sent
human_interventions: none in the evidence; the editor ran the runner. Exported and redacted by the exporter named
  here, under the publication policy; the redactions and withheld parts are counted below and in the manifest.
samples:
  generated: 1
  submitted: 1
  note: one attempt; provider-side sampling unknown
type: transcript
exporter: tools/export_archive.py @ 681975d26842e499ecf9269369a686c932d93d8d (rules version 12)
private_configuration: pc-final-2
cutoff_utc: '2026-09-25T05:25:02Z'
source_sha256: afd1d7d2ac108280fead9b5513ae871956fa5180b2d0442f3ddbf564fc5a335f
output_sha256: 6bc4d93e70b6baf73907740d70e11293be99a33a553dca67ec96ca56d708106c
redactions: none
withheld:
  B, thinking: 1
  'withheld: Grok quotation (rights check, D1)': 59
lifecycle: active
---

Exported payload `rounds/02-deliberation/evidence/deepseek-v4-pro/deepseek-v4-pro.preflight.json`. Redactions are marked `[REDACTED: <category>]` and withheld parts `[WITHHELD: <class or category>; see manifest]`. See `sessions/manifest.md`.
