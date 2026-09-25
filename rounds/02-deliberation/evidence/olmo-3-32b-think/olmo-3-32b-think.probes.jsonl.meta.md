---
title: 'Evidence: olmo-3-32b-think.probes.jsonl'
date: '2026-09-24'
author: OLMo 3 32B Think (Ollama library build olmo-3:32b, Q4_K_M), with the editor's runner records
model: olmo-3:32b (Ollama tag; OLMo 3 32B Think, Q4_K_M 4-bit quantization)
developer: Ai2 (weights); quantized and packaged by Ollama
participant_id: olmo-3-32b-think/6701fc1a
run: local Ollama run, attempt 6701fc1a-f339-43cc-b554-90cbc02cd42b, one /api/chat request. A new run with reconstructed
  Round 0 history, linked to Round 0 participant olmo-3-32b-think/5519bf56 (rounds/00-initial/responses/olmo-3-32b-think.md);
  not a restoration of that run's state or reasoning.
attribution: 'verified, limited. As in Round 0: before the request, the editor''s runner checked the weight file''s
  hash against its declared digest and the manifest against the server''s digest, and the digest was unchanged after
  the run. This supports the claim that the answer came from the Ollama artifact in setup.artifact. It is recorded
  configuration, not provider attestation. The evidence is private; no third party has repeated the check.'
prompt: as in rounds/01-deliberation/responses/olmo-3-32b-think.md
exposure:
- 'the reconstructed history: the Round 0 participant text and this model''s own Round 0 answer'
- the Round 1 participant text, which contains all six Round 0 answers, including this model's own
- the system prompt as described in setup.system_prompt
- no tools, retrieval, or web access; no stored messages in the artifact
human_interventions: none in the evidence; the editor ran the runner. Exported and redacted by the exporter named
  here, under the publication policy; the redactions and withheld parts are counted below and in the manifest.
samples:
  generated: 1
  submitted: 1
  note: one attempt, completed on the first try
type: transcript
exporter: tools/export_archive.py @ 681975d26842e499ecf9269369a686c932d93d8d (rules version 12)
private_configuration: pc-final-2
cutoff_utc: '2026-09-25T05:25:02Z'
source_sha256: 70a8a1311ddb842420bc8c5baf2f2f5eac875725da95958fcf3f49b0fc721bc1
output_sha256: e4c4267e2854c7410f94f2ff51041535c7bda01600ecf7707b836b494f553f74
redactions: none
withheld:
  'withheld: Grok quotation (rights check, D1)': 98
lifecycle: active
---

Exported payload `rounds/02-deliberation/evidence/olmo-3-32b-think/olmo-3-32b-think.probes.jsonl`. Redactions are marked `[REDACTED: <category>]` and withheld parts `[WITHHELD: <class or category>; see manifest]`. See `sessions/manifest.md`.
