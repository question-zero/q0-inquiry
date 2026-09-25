---
title: 'Evidence: qwen3-6-27b.probes.jsonl'
date: '2026-09-24'
author: Qwen3.6 27B (Ollama library build qwen3.6:27b, Q4_K_M), with the editor's runner records
model: qwen3.6:27b (Ollama tag; Qwen3.6 27B, Q4_K_M 4-bit quantization)
developer: Alibaba Cloud, Qwen team (weights); quantized and packaged by Ollama
participant_id: qwen3-6-27b/70617ec4
run: local Ollama run, attempt 70617ec4-39c3-4e5b-b355-5fbf3c901eea, one /api/chat request. A new run with reconstructed
  Round 0 history, linked to Round 0 participant qwen3-6-27b/acb7763d (rounds/00-initial/responses/qwen3-6-27b.md);
  not a restoration of that run's state or reasoning.
attribution: 'verified, limited. As in Round 0: before the request, the editor''s runner checked the weight file''s
  hash against its declared digest and the manifest against the server''s digest, and the digest was unchanged after
  the run. This supports the claim that the answer came from the Ollama artifact in setup.artifact. It is recorded
  configuration, not provider attestation. The evidence is private; no third party has repeated the check.'
prompt: as in rounds/01-deliberation/responses/qwen3-6-27b.md
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
source_sha256: af9c6cdcbc660bfbca460fe06967a580514f4f342b689101c647cae685dd4f79
output_sha256: cee0d31b7eca05b56aaec78a3f2ed079fb1b1913166cc4c35bc9c7e4c2e05b58
redactions: none
withheld:
  'withheld: Grok quotation (rights check, D1)': 2
lifecycle: active
---

Exported payload `rounds/01-deliberation/evidence/qwen3-6-27b/qwen3-6-27b.probes.jsonl`. Redactions are marked `[REDACTED: <category>]` and withheld parts `[WITHHELD: <class or category>; see manifest]`. See `sessions/manifest.md`.
