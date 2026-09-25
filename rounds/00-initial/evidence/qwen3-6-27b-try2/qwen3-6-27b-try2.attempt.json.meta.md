---
title: 'Evidence: qwen3-6-27b-try2.attempt.json'
date: '2026-09-24'
author: Qwen3.6 27B (Ollama library build qwen3.6:27b, Q4_K_M), with the editor's runner records
model: qwen3.6:27b (Ollama tag; Qwen3.6 27B, Q4_K_M 4-bit quantization)
developer: Alibaba Cloud, Qwen team (weights); quantized and packaged by Ollama
participant_id: qwen3-6-27b/acb7763d
run: local Ollama run, attempt acb7763d-ec43-42a2-9600-50498967954d, one /api/chat request. Attempt 3 of 3; attempts
  1 and 2 failed while the model loaded and produced no output (see samples)
attribution: 'verified, limited. Checked by the editor''s runner on the founder''s machine, before the request:
  the weight file hashes to its declared digest (sha256:415aad607fc2...), and the manifest''s SHA-256 equals the
  digest the server reported (9d5803d493a9...). After the run the server reported the same digest. This supports
  one claim: the answer came from the Ollama artifact named in setup.artifact, served by Ollama 0.34.4. It is recorded
  configuration, not provider attestation, and it does not show that the artifact matches the developer''s original
  weights. The evidence is private (see evidence); no third party has repeated the check. Anyone can obtain the
  same artifact by its digests.'
prompt: as in rounds/00-initial/responses/qwen3-6-27b.md
exposure:
- the participant text, without its two leading and two trailing newlines (removed by Ollama's qwen3.5 renderer;
  the words are unchanged)
- no tools, no retrieval, no web access, no earlier conversation; the artifact has no stored messages (checked before
  the run)
- the participant's own statement of prior exposure is in its answer
human_interventions: none in the evidence; the editor ran the runner. Exported and redacted by the exporter named
  here, under the publication policy; the redactions and withheld parts are counted below and in the manifest.
samples:
  generated: 1
  submitted: 1
  attempts: 3
  note: Attempt 1 (80b5e922-ccd4-4fab-b4b9-8f65f9a4e949, 07:35:00Z-07:40:07Z) and attempt 2 (1020e806-3d77-4f89-9ac1-f2df5fd1c01d,
    08:36:33Z-08:56:39Z) both failed with HTTP 500 "timed out waiting for llama-server to start", before any output
    (0 chunks). Between them the editor raised the server's load timeout from 5 to 20 minutes. Attempt 3 (acb7763d-ec43-42a2-9600-50498967954d)
    completed. The settings were the same in all three. No answer existed before attempt 3, so there was nothing
    to choose between.
type: transcript
exporter: tools/export_archive.py @ 681975d26842e499ecf9269369a686c932d93d8d (rules version 12)
private_configuration: pc-final-2
cutoff_utc: '2026-09-25T05:25:02Z'
source_sha256: 2a0f4e17df7387d7abb9af5716666780930b023b0d8fbf0ee1f7858e832b5a1c
output_sha256: 87703c6fc0eafeadac01b84e2b3929989a0891d10fcafc33f06881288616c807
redactions: none
withheld: none
lifecycle: active
---

Exported payload `rounds/00-initial/evidence/qwen3-6-27b-try2/qwen3-6-27b-try2.attempt.json`. Redactions are marked `[REDACTED: <category>]` and withheld parts `[WITHHELD: <class or category>; see manifest]`. See `sessions/manifest.md`.
