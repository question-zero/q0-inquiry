# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Offline tests for tools/run_local_participant.py covering GPT-6 findings LR1-LR3 and its round 2 findings; revision 4 adds tests for round prompts, history, render-only capture, and the input budget; revision 5 adds GPT-6 RV1-RV3 regressions; revision 6 adds the remaining RV1 cases; revision 7 tests --packet; revision 8 adds GPT-6 RPK1 and RPK2 regressions (generated packets, the manifest's assignment).
# license: MIT (LICENSE-CODE)
"""Offline tests for run_local_participant.py. Run: python -m unittest tools/test_run_local_participant.py

A fake Ollama stands in for the server. No model runs.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_local_participant as rl  # noqa: E402

PROMPT = ("participant text\n", "hash-not-checked-here", "0" * 40)
GOOD_CHUNKS = [
    {"message": {"content": "Hel", "thinking": "t1"}, "done": False},
    {"message": {"content": "lo", "thinking": ""}, "done": True, "done_reason": "stop", "eval_count": 2},
]


class FakeHttp:
    def __init__(self, chunks=None, fail_after=None, show_extra=None, stream_error=None,
                 raw_lines=None, tags_fail_on_call=None, render_response=None, render_error=None,
                 load_response=None, context_length=32768, port=41000, token_count=None, version="0.34.4"):
        self.chunks = GOOD_CHUNKS if chunks is None else chunks
        self.fail_after, self.show_extra = fail_after, show_extra or {}
        self.stream_error, self.raw_lines = stream_error, raw_lines
        self.tags_fail_on_call, self.tags_calls = tags_fail_on_call, 0
        self.render_response, self.render_error = render_response, render_error
        self.streamed, self.render_payload = False, None
        self.load_response, self.context_length = load_response, context_length
        self.port, self.token_count, self.load_payload = port, token_count, None
        self.version, self.calls, self.on_render = version, 0, None

    def json(self, path, payload=None, timeout=120):
        self.calls += 1
        if path == "/api/tags":
            self.tags_calls += 1
            if self.tags_fail_on_call == self.tags_calls:
                raise ConnectionError("server stopped")
            return {"models": [{"name": "fake:1b", "digest": "abc123", "size": 1}]}
        if path == "/api/show":
            return {"system": "packaged system", "thinking": {"values": [False, True], "default": True}, **self.show_extra}
        if path == "/api/version":
            return {"version": self.version}
        if path == "/api/generate" and "prompt" not in payload:
            self.load_payload = payload
            return self.load_response or {"model": payload["model"], "done": True, "done_reason": "load", "response": ""}
        if path == "/api/ps":
            return {"models": [{"name": "fake:1b", "context_length": self.context_length}]}
        if path == "/api/chat" and payload.get("_debug_render_only"):
            self.render_payload = payload
            if self.on_render:
                self.on_render()
            if self.render_error:
                raise self.render_error
            if self.render_response is not None:
                return self.render_response
            rendered = "".join(f"<{m['role']}>{m['content']}" for m in payload["messages"])
            return {"model": payload["model"], "done": True, "message": {"role": "assistant", "content": ""},
                    "_debug_info": {"rendered_template": rendered}}
        raise AssertionError(path)

    def runner_port(self, weights_hex):
        return self.port

    def tokenize(self, port, text):
        return list(range(len(text) if self.token_count is None else self.token_count))

    def stream(self, path, payload, timeout=7200):
        self.streamed = True
        self.payload = payload
        if self.stream_error:
            raise self.stream_error
        if self.raw_lines is not None:
            yield from self.raw_lines
            return
        for i, c in enumerate(self.chunks):
            if self.fail_after is not None and i == self.fail_after:
                raise ConnectionError("simulated drop")
            yield (json.dumps(c) + "\n").encode("utf-8")


def args(prefix, **kw):
    base = dict(model="fake:1b", prefix=str(prefix), system="packaged", think="default", seed=0,
                tag="round/00-initial/v1", verify_weights=False, history=None, history_record=None,
                history_tag="round/00-initial/v1", max_rendered_bytes=rl.DEFAULT_MAX_RENDERED_BYTES)
    base.update(kw)
    return argparse.Namespace(**base)


# ---- packet mode (GPT-6 RPK1, RPK2): a fake repository reached only through rl.git_commit and rl.git_blob ----

TAG2 = "round/02-deliberation/v1"
MANIFEST = "rounds/02-deliberation/prompt.md"
P46 = "rounds/02-deliberation/packets/grok-4-6.md"
P47 = "rounds/02-deliberation/packets/grok-4-7.md"
PLOCAL = "rounds/02-deliberation/packets/fake-1b.md"
FIRST = "Generated by tools/build_round_02_packets.py from commit abc1234: a packet."


def generated(text, first=FIRST):
    return first + "\n\n" + rl.BEGIN + text + rl.END + "\n"


def row(**kw):
    base = {"participant": "grok-4-7", "route": "xai", "requested_model": "grok-4.7", "packet": P47,
            "participant_text_sha256": rl.sha256(PacketRepo.TEXTS[P47])}
    base.update(kw)
    return base


class PacketRepo:
    """Committed blobs at one commit: a manifest with front matter and generated packets without it."""
    COMMIT = "c" * 40
    TEXTS = {P46: "\nThe operator records this run as Grok 4.6.\n  tab\there, non-ASCII: ü — 概念  \n\n",
             P47: "\nThe operator records this run as Grok 4.7.\n",
             PLOCAL: "\nThe operator records this run as a local model.\n"}
    RECIPIENTS = {P46: ("grok-4-6", "xai", "grok-4.6"), P47: ("grok-4-7", "xai", "grok-4.7"),
                  PLOCAL: ("fake-1b", "ollama", "fake:1b")}

    def __init__(self, packets=None, rows=None, shared="\n{{IDENTITY_LINE}}\n{{PART_C}}\n", shared_hash=None):
        self.blobs = {p: generated(t) for p, t in self.TEXTS.items()}
        self.blobs.update(packets or {})
        if rows is None:
            rows = [{"participant": slug, "route": route, "requested_model": model, "packet": p,
                     "participant_text_sha256": rl.sha256(self.TEXTS[p]), "identity_line": "informational"}
                    for p, (slug, route, model) in self.RECIPIENTS.items()]
        front = {"type": "round-prompt", "round": "02-deliberation",
                 "participant_text_sha256": shared_hash or rl.sha256(shared), "packets": rows}
        self.blobs[MANIFEST] = ("---\n" + yaml.safe_dump(front, sort_keys=False, allow_unicode=True) + "---\n\n"
                                + "# Manifest\n\n" + rl.BEGIN + shared + rl.END + "\n")
        self.reads = []

    def __enter__(self):
        self.patches = [mock.patch.object(rl, "git_commit", side_effect=self.commit),
                        mock.patch.object(rl, "git_blob", side_effect=self.blob)]
        for p in self.patches:
            p.start()
        return self

    def __exit__(self, *exc):
        for p in self.patches:
            p.stop()

    def commit(self, tag):
        if tag != TAG2:
            raise subprocess.CalledProcessError(128, ["git", "rev-parse", tag])
        return self.COMMIT

    def blob(self, commit, path):
        assert commit == self.COMMIT, commit
        self.reads.append(path)
        if path not in self.blobs:
            raise subprocess.CalledProcessError(128, ["git", "show", f"{commit}:{path}"])
        return self.blobs[path]


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prefix = Path(self.tmp.name) / "p"

    def tearDown(self):
        self.tmp.cleanup()

    def files(self):
        return sorted(p.name for p in Path(self.tmp.name).iterdir())

    def load(self, suffix):
        return json.loads(Path(f"{self.prefix}.{suffix}").read_text(encoding="utf-8"))


class Runner(Base):
    def test_success_writes_preflight_attempt_stream_result(self):
        r = rl.run(args(self.prefix), FakeHttp(), PROMPT)
        self.assertEqual((r["answer"], r["thinking"], r["complete"]), ("Hello", "t1", True))
        self.assertEqual(r["post_run_check"], "completed")
        self.assertTrue(r["digest_unchanged"])
        self.assertEqual(self.files(), ["p.attempt.json", "p.preflight.json", "p.probes.jsonl", "p.result.json",
                                        "p.stream.jsonl"])

    def test_existing_evidence_refuses_before_request(self):  # LR1
        Path(f"{self.prefix}.attempt.json").write_text("{}")
        http = FakeHttp()
        with self.assertRaises(FileExistsError):
            rl.run(args(self.prefix), http, PROMPT)
        self.assertFalse(http.streamed)

    def test_failure_keeps_partial_output(self):  # LR1
        with self.assertRaises(ConnectionError):
            rl.run(args(self.prefix), FakeHttp(fail_after=1), PROMPT)
        self.assertEqual(self.files(), ["p.attempt.json", "p.failure.json", "p.preflight.json", "p.probes.jsonl",
                                        "p.stream.jsonl"])
        f = self.load("failure.json")
        self.assertEqual((f["partial_answer"], f["chunks_archived"], f["generation_status"]), ("Hel", 1, "failed"))

    def test_http_error_body_kept(self):  # LR1, round 2
        with self.assertRaises(rl.HttpFailure):
            rl.run(args(self.prefix), FakeHttp(stream_error=rl.HttpFailure(500, "model runner crashed")), PROMPT)
        f = self.load("failure.json")
        self.assertEqual((f["http_status"], f["http_body"]), (500, "model runner crashed"))

    def test_malformed_bytes_archived_before_decoding(self):  # LR1, round 2
        bad = b'{"message": {"content": "ok"}, "done": false}\n\xff\xfe broken\n'
        with self.assertRaises(Exception):
            rl.run(args(self.prefix), FakeHttp(raw_lines=bad.splitlines(keepends=True)), PROMPT)
        self.assertEqual(Path(f"{self.prefix}.stream.jsonl").read_bytes(), bad)
        self.assertEqual(self.load("failure.json")["partial_answer"], "ok")

    def test_post_run_check_failure_keeps_completed_answer(self):  # LR1, round 2
        r = rl.run(args(self.prefix), FakeHttp(tags_fail_on_call=2), PROMPT)
        self.assertEqual(r["generation_status"], "completed")
        self.assertTrue(r["post_run_check"].startswith("unavailable"))
        self.assertIsNone(r["digest_unchanged"])
        self.assertTrue(r["artifact_attribution"].startswith("unresolved"))
        self.assertIn("p.result.json", self.files())
        self.assertNotIn("p.failure.json", self.files())

    def test_truncated_answer_recorded_as_incomplete(self):
        r = rl.run(args(self.prefix), FakeHttp(chunks=[{"message": {"content": "cut"}, "done": True, "done_reason": "length"}]), PROMPT)
        self.assertEqual((r["complete"], r["done_reason"]), (False, "length"))

    def test_stream_without_done_is_failure(self):
        with self.assertRaises(RuntimeError):
            rl.run(args(self.prefix), FakeHttp(chunks=[{"message": {"content": "x"}, "done": False}]), PROMPT)
        self.assertIn("p.failure.json", self.files())

    def test_empty_answer_is_kept(self):
        r = rl.run(args(self.prefix), FakeHttp(chunks=[{"message": {"content": ""}, "done": True, "done_reason": "stop"}]), PROMPT)
        self.assertEqual((r["answer"], r["complete"]), ("", True))

    def test_stored_messages_refused_before_any_evidence(self):  # LR2
        http = FakeHttp(show_extra={"messages": [{"role": "user", "content": "earlier"}]})
        with self.assertRaises(ValueError):
            rl.run(args(self.prefix), http, PROMPT)
        self.assertEqual(self.files(), [])
        self.assertFalse(http.streamed)

    def test_system_and_think_choices(self):
        http = FakeHttp()
        rl.run(args(self.prefix, system="packaged", think="true"), http, PROMPT)
        self.assertEqual([m["role"] for m in http.payload["messages"]], ["user"])
        self.assertIs(http.payload["think"], True)
        http2 = FakeHttp()
        rl.run(args(Path(self.tmp.name) / "q", system="empty"), http2, PROMPT)
        self.assertEqual(http2.payload["messages"][0], {"role": "system", "content": ""})
        self.assertNotIn("think", http2.payload)

    def test_preflight_records_packaged_defaults(self):  # LR2
        rl.run(args(self.prefix), FakeHttp(), PROMPT)
        p = self.load("preflight.json")
        self.assertEqual(p["packaged_system_prompt"], "packaged system")
        self.assertIs(p["packaged_thinking"]["default"], True)
        self.assertIn("runner", p)
        self.assertEqual(p["model_before"]["tags_entry"]["digest"], "abc123")


class Verification(Base):  # LR2, round 2
    GOOD_MANIFEST = {"present": True, "manifest_sha256": "abc123", "layers": []}

    def run_verified(self, manifest, weights):
        http = FakeHttp()
        with mock.patch.object(rl, "manifest_info", return_value=manifest), \
                mock.patch.object(rl, "verify_weight_layer", return_value=weights):
            try:
                result = rl.run(args(self.prefix, verify_weights=True), http, PROMPT)
            except rl.PreflightError:
                result = None
        return http, result

    def assert_blocked(self, http):
        self.assertFalse(http.streamed)
        self.assertEqual(self.files(), ["p.preflight.json"])
        self.assertIs(self.load("preflight.json")["passed"], False)

    def test_missing_manifest_blocks_inference(self):
        http, _ = self.run_verified({"present": False}, {"matches": True})
        self.assert_blocked(http)

    def test_missing_weight_layer_blocks_inference(self):
        http, _ = self.run_verified(self.GOOD_MANIFEST, {"matches": False, "error": "no model layer in manifest"})
        self.assert_blocked(http)

    def test_weight_mismatch_blocks_inference(self):
        http, _ = self.run_verified(self.GOOD_MANIFEST, {"matches": False, "computed": "sha256:x", "layer_digest": "sha256:y"})
        self.assert_blocked(http)

    def test_manifest_server_mismatch_blocks_inference(self):
        http, _ = self.run_verified({"present": True, "manifest_sha256": "different", "layers": []}, {"matches": True})
        self.assert_blocked(http)

    def test_all_checks_pass_allows_inference_and_marks_verified(self):
        http, result = self.run_verified(self.GOOD_MANIFEST, {"matches": True})
        self.assertTrue(http.streamed)
        self.assertEqual(result["artifact_attribution"], "verified")


class Rendering(Base):  # revision 4: render-only capture before inference
    def blocked(self, http):
        self.assertFalse(http.streamed)
        self.assertEqual(self.files(), ["p.preflight.json", "p.probes.jsonl"])
        self.assertIs(self.load("preflight.json")["passed"], False)

    def probes(self):
        return Path(f"{self.prefix}.probes.jsonl").read_text(encoding="utf-8")

    def test_rendered_prompt_recorded_before_inference(self):
        http = FakeHttp()
        rl.run(args(self.prefix), http, PROMPT)
        r = self.load("preflight.json")["rendered_prompt"]
        self.assertEqual(r["rendered_template"], "<user>participant text\n")
        self.assertEqual(r["rendered_sha256"], rl.sha256("<user>participant text\n"))
        self.assertEqual(r["generation_signs"], [])
        self.assertIs(http.render_payload["stream"], False)
        self.assertNotIn("_debug_render_only", http.payload)  # the real request carries no debug flag
        self.assertEqual(http.render_payload["messages"], http.payload["messages"])

    def test_too_large_blocks_inference(self):
        http = FakeHttp()
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, max_rendered_bytes=5), http, PROMPT)
        self.blocked(http)

    def test_generation_signs_block_inference(self):
        http = FakeHttp(render_response={"done": True, "done_reason": "stop", "eval_count": 3,
                                         "message": {"content": "hi"}, "_debug_info": {"rendered_template": "x"}})
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)
        self.assertIn("eval_count", self.load("preflight.json")["rendered_prompt"]["generation_signs"])

    def test_render_failure_blocks_inference(self):
        http = FakeHttp(render_error=rl.HttpFailure(400, "unknown field"))
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)

    def test_probe_generation_is_kept_and_blocks(self):  # RV1
        http = FakeHttp(render_response={"done": True, "done_reason": "stop", "eval_count": 1,
                                         "message": {"content": "UNEXPECTED_PROBE_ANSWER"},
                                         "_debug_info": {"rendered_template": "x"}})
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)
        self.assertIn("UNEXPECTED_PROBE_ANSWER", self.probes())

    def test_probe_thinking_only_is_detected_and_kept(self):  # RV1
        http = FakeHttp(render_response={"done": True, "message": {"content": "", "thinking": "UNEXPECTED_PROBE_THINKING"},
                                         "_debug_info": {"rendered_template": "x"}})
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)
        self.assertIn("UNEXPECTED_PROBE_THINKING", self.probes())
        self.assertIn("message.thinking", self.load("preflight.json")["rendered_prompt"]["generation_signs"])

    def test_probe_http_error_body_is_kept(self):  # RV1
        http = FakeHttp(render_error=rl.HttpFailure(400, "unknown field _debug_render_only"))
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)
        entry = [json.loads(x) for x in self.probes().splitlines()][-1]
        self.assertEqual((entry["event"], entry["http_status"], entry["http_body"]),
                         ("end", 400, "unknown field _debug_render_only"))

    def test_probe_request_is_saved_before_sending(self):  # RV1, round 2
        http = FakeHttp()
        seen = {}

        def inspect():
            lines = self.probes().splitlines()
            seen["entries"] = [json.loads(x) for x in lines]

        http.on_render = inspect
        rl.run(args(self.prefix), http, PROMPT)
        first = seen["entries"][0]
        self.assertEqual((len(seen["entries"]), first["event"], first["kind"]), (1, "start", "render"))
        self.assertIs(first["request"]["payload"]["_debug_render_only"], True)
        events = [json.loads(x)["event"] for x in self.probes().splitlines()]
        self.assertEqual(events, ["start", "end"])

    def test_probe_log_write_failure_prevents_the_probe(self):  # RV1, round 2
        http = FakeHttp()
        with mock.patch.object(rl.ProbeLog, "start", side_effect=OSError("disk full")):
            with self.assertRaises(rl.PreflightError):
                rl.run(args(self.prefix), http, PROMPT)
        self.assertIsNone(http.render_payload)
        self.assertFalse(http.streamed)

    def test_unparseable_probe_body_is_kept(self):  # RV1, round 2
        body = '{"message": {"content": "UNEXPECTED_PROBE_ANSWER"'
        http = FakeHttp(render_error=rl.BadResponse(200, body, "truncated JSON"))
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)
        end = [json.loads(x) for x in self.probes().splitlines()][-1]
        self.assertEqual((end["event"], end["http_status"], end["http_body"]), ("end", 200, body))

    def test_parse_body_keeps_text_on_failure(self):  # RV1, round 2
        with self.assertRaises(rl.BadResponse) as cm:
            rl.parse_body(200, b'{"message": {"content": "UNEXPECTED')
        self.assertEqual((cm.exception.status, cm.exception.body), (200, '{"message": {"content": "UNEXPECTED'))

    def test_unsupported_version_blocks_before_probing(self):  # RV1
        http = FakeHttp(version="0.35.0")
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.assertFalse(http.streamed)
        self.assertIsNone(http.render_payload)
        self.assertEqual(self.files(), ["p.preflight.json"])

    def test_missing_rendered_template_blocks_inference(self):
        http = FakeHttp(render_response={"done": True, "message": {"content": ""}})
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix), http, PROMPT)
        self.blocked(http)


class Budget(Base):  # revision 4, GPT-6 R1D3
    ROUND1 = dict(num_ctx=32768, num_predict=12000, strict_context=True, max_input_tokens=20000)

    def blocked(self, http):
        self.assertFalse(http.streamed)
        self.assertEqual(self.files(), ["p.preflight.json", "p.probes.jsonl"])
        self.assertIs(self.load("preflight.json")["passed"], False)

    def probes(self):
        return Path(f"{self.prefix}.probes.jsonl").read_text(encoding="utf-8")

    def test_budget_controls_in_request_and_recorded(self):
        http = FakeHttp(token_count=15000)
        rl.run(args(self.prefix, **self.ROUND1), http, PROMPT)
        self.assertEqual(http.payload["options"], {"seed": 0, "num_ctx": 32768, "num_predict": 12000})
        self.assertIs(http.payload["truncate"], False)
        self.assertIs(http.payload["shift"], False)
        self.assertEqual(http.load_payload["options"], {"num_ctx": 32768})
        b = self.load("preflight.json")["input_budget"]
        self.assertEqual((b["input_tokens"], b["loaded_context_length"], b["runner_port"]), (15000, 32768, 41000))
        self.assertTrue(all(b["checks"].values()))

    def test_over_input_limit_blocks(self):
        http = FakeHttp(token_count=20001)
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, **self.ROUND1), http, PROMPT)
        self.blocked(http)

    def test_input_plus_output_over_context_blocks(self):
        http = FakeHttp(token_count=19000, context_length=30000)
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, **dict(self.ROUND1, num_ctx=30000)), http, PROMPT)
        self.blocked(http)

    def test_load_probe_output_is_kept(self):  # RV1
        http = FakeHttp(load_response={"done": True, "done_reason": "load", "response": "UNEXPECTED_LOAD_TEXT"})
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, **self.ROUND1), http, PROMPT)
        self.blocked(http)
        self.assertIn("UNEXPECTED_LOAD_TEXT", self.probes())

    def test_invalid_budget_settings_rejected_before_any_request(self):  # RV2
        bad = [dict(self.ROUND1, num_predict=0), dict(self.ROUND1, num_predict=-5), dict(self.ROUND1, num_ctx=0),
               dict(self.ROUND1, max_input_tokens=0), dict(self.ROUND1, num_predict=None),
               dict(self.ROUND1, num_ctx=None), dict(self.ROUND1, strict_context=False),
               dict(self.ROUND1, max_rendered_bytes=0)]
        for kw in bad:
            http = FakeHttp(token_count=40000)
            with self.assertRaises(ValueError, msg=kw):
                rl.run(args(self.prefix, **kw), http, PROMPT)
            self.assertEqual((http.calls, http.streamed, self.files()), (0, False, []), kw)

    def test_context_mismatch_blocks(self):
        http = FakeHttp(token_count=100, context_length=4096)
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, **self.ROUND1), http, PROMPT)
        self.blocked(http)

    def test_counting_unavailable_blocks(self):
        http = FakeHttp(port=None)
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, **self.ROUND1), http, PROMPT)
        self.blocked(http)

    def test_load_that_generates_blocks(self):
        http = FakeHttp(load_response={"done": True, "done_reason": "stop", "response": "text"})
        with self.assertRaises(rl.PreflightError):
            rl.run(args(self.prefix, **self.ROUND1), http, PROMPT)
        self.blocked(http)

    def test_round0_defaults_skip_the_budget(self):
        http = FakeHttp()
        rl.run(args(self.prefix), http, PROMPT)
        self.assertEqual(http.payload["options"], {"seed": 0})
        self.assertNotIn("truncate", http.payload)
        self.assertIsNone(http.load_payload)


class History(Base):  # revision 4
    EARLIER = ("earlier text\n", "d" * 64, "1" * 40)

    def write_result(self, **kw):
        result = {"attempt_id": "a1", "generation_status": "completed", "complete": True,
                  "answer": "earlier answer", "thinking": "private"}
        result.update(kw)
        path = Path(self.tmp.name) / "earlier.result.json"
        path.write_text(json.dumps(result), encoding="utf-8")
        return path

    NOTE_FM = "---\nhuman_interventions: 'Edited nothing. " + rl.FINAL_NEWLINE_NOTE + "'\n---\n\n"
    PLAIN_FM = "---\nhuman_interventions: none\n---\n\n"

    def test_history_goes_before_the_new_text_without_thinking(self):
        path = self.write_result()
        history = rl.load_history(path, "rounds/00-initial/responses/x.md", "round/00-initial/v1",
                                  prompt=self.EARLIER, blob=self.NOTE_FM + "earlier answer\n")
        http = FakeHttp()
        rl.run(args(self.prefix), http, PROMPT, history=history)
        self.assertEqual(http.payload["messages"], [
            {"role": "user", "content": "earlier text\n"},
            {"role": "assistant", "content": "earlier answer"},
            {"role": "user", "content": "participant text\n"}])
        h = self.load("preflight.json")["history"]
        self.assertEqual(h["answer_sha256"], rl.sha256("earlier answer"))
        self.assertEqual(h["earlier_participant_text_sha256"], "d" * 64)
        self.assertNotIn("private", json.dumps(http.payload))

    def test_history_must_match_the_record(self):
        path = self.write_result()
        with self.assertRaises(ValueError):
            rl.load_history(path, "r.md", "round/00-initial/v1", prompt=self.EARLIER,
                            blob=self.NOTE_FM + "edited answer\n")

    def test_history_must_be_a_completed_answer(self):
        path = self.write_result(complete=False, done_reason="length")
        with self.assertRaises(ValueError):
            rl.load_history(path, "r.md", "round/00-initial/v1", prompt=self.EARLIER,
                            blob=self.NOTE_FM + "earlier answer\n")

    def test_answer_with_its_own_final_newline_matches_exactly(self):  # RV3
        path = self.write_result(answer="earlier answer\n")
        messages, info = rl.load_history(path, "r.md", "round/00-initial/v1", prompt=self.EARLIER,
                                         blob=self.PLAIN_FM + "earlier answer\n")
        self.assertEqual(messages[1]["content"], "earlier answer\n")
        self.assertIs(info["record_final_newline_added"], False)

    def test_extra_newline_in_the_answer_is_rejected(self):  # RV3
        path = self.write_result(answer="earlier answer\n")
        with self.assertRaises(ValueError):
            rl.load_history(path, "r.md", "round/00-initial/v1", prompt=self.EARLIER,
                            blob=self.NOTE_FM + "earlier answer\n")

    def test_missing_newline_in_the_answer_is_rejected(self):  # RV3
        path = self.write_result(answer="earlier answer")
        with self.assertRaises(ValueError):
            rl.load_history(path, "r.md", "round/00-initial/v1", prompt=self.EARLIER,
                            blob=self.PLAIN_FM + "earlier answer\n")

    def test_record_body(self):
        self.assertEqual(rl.record_body("---\na: 1\n---\n\nline one\nline two\n"), "line one\nline two")
        with self.assertRaises(ValueError):
            rl.record_body("no front matter\n")


class Extraction(unittest.TestCase):  # LR3
    def test_prompt_path_from_tag(self):
        self.assertEqual(rl.prompt_path("round/01-deliberation/v1"), "rounds/01-deliberation/prompt.md")
        with self.assertRaises(ValueError):
            rl.prompt_path("v1")

    def test_markers_quoted_in_front_matter_are_ignored(self):
        blob = ("---\nnote: 'text between " + rl.BEGIN + " and " + rl.END + "'\n---\n\nintro\n"
                + rl.BEGIN + "\nREAL TEXT\n" + rl.END + "\n")
        text, front = rl.extract_participant_text(blob)
        self.assertEqual(text, "\nREAL TEXT\n")
        self.assertIn(rl.BEGIN, front["note"])

    def test_two_blocks_rejected(self):
        blob = "---\na: 1\n---\n" + rl.BEGIN + "\nx\n" + rl.END + "\n" + rl.BEGIN + "\ny\n" + rl.END + "\n"
        with self.assertRaises(ValueError):
            rl.extract_participant_text(blob)

    @unittest.skipUnless(
        subprocess.run(["git", "rev-parse", "-q", "--verify", "refs/tags/round/00-initial/v1"],
                       capture_output=True).returncode == 0,
        "round tag not present in this checkout (e.g. a shallow CI clone)")
    def test_matches_pinned_prompt_bytes(self):
        text, digest, commit = rl.pinned_prompt("round/00-initial/v1")
        self.assertEqual(digest, "1dfc2778e86b3ac5e675e443c9201d36eeaa6e3fb81136109aa20633bb625f6a")
        self.assertEqual(len(text.encode("utf-8")), 2313)


class PacketMode(Base):  # GPT-6 RPK1 and RPK2
    def test_generated_packet_accepted_with_exact_text_and_digest(self):
        with PacketRepo() as repo:
            text, digest, commit, a = rl.pinned_packet(TAG2, P46, "xai", "grok-4.6")
        self.assertEqual(text.encode("utf-8"), PacketRepo.TEXTS[P46].encode("utf-8"))
        self.assertEqual((digest, commit), (rl.sha256(PacketRepo.TEXTS[P46]), PacketRepo.COMMIT))
        self.assertEqual((a["participant"], a["route"], a["requested_model"], a["packet"], a["manifest"]),
                         ("grok-4-6", "xai", "grok-4.6", P46, MANIFEST))
        self.assertEqual(a["packet_first_line"], FIRST)
        self.assertEqual(repo.reads, [MANIFEST, P46])
        self.assertNotIn("(Grok quotation withheld under the rights check, D1)", text)

    def test_another_models_packet_is_refused(self):
        with PacketRepo():
            with self.assertRaisesRegex(ValueError, "assigns rounds/02-deliberation/packets/grok-4-7.md"):
                rl.pinned_packet(TAG2, P46, "xai", "grok-4.7")
            with self.assertRaisesRegex(ValueError, "assigns rounds/02-deliberation/packets/grok-4-6.md"):
                rl.pinned_packet(TAG2, P47, "xai", "grok-4.6")

    def test_unassigned_recipient_is_refused(self):
        with PacketRepo():
            for route, model in (("xai", "grok-9"), ("gemini", "grok-4.7"), ("xai", "Grok-4.7"),
                                 ("ollama", "grok-4.7"), ("xai", "grok-4.7 "), ("xai", None)):
                with self.subTest(route=route, model=model), self.assertRaises(ValueError):
                    rl.pinned_packet(TAG2, P47, route, model)

    def test_packet_text_must_have_the_manifests_hash(self):
        with PacketRepo(packets={P47: generated("\nThe operator records this run as Grok 4.6.\n")}):
            with self.assertRaisesRegex(ValueError, "differs from the manifest"):
                rl.pinned_packet(TAG2, P47, "xai", "grok-4.7")

    def test_manifest_shared_text_hash_is_checked(self):
        with PacketRepo(shared_hash="0" * 64):
            with self.assertRaisesRegex(ValueError, "shared-text hash"):
                rl.pinned_packet(TAG2, P47, "xai", "grok-4.7")

    def test_malformed_packets_are_refused(self):
        B, E, t = rl.BEGIN, rl.END, "\nx\n"
        cases = {
            "no generator line": "A packet.\n\n" + B + t + E + "\n",
            "front matter": "---\ntype: round-prompt\nparticipant_text_sha256: x\n---\n\n" + B + t + E + "\n",
            "front matter then a generator line": "---\n" + FIRST + "\n---\n\n" + B + t + E + "\n",
            "no markers": FIRST + "\n\n" + t,
            "no end marker": FIRST + "\n\n" + B + t,
            "reversed": FIRST + "\n\n" + E + t + B + "\n",
            "two begin markers": FIRST + "\n\n" + B + "\n" + B + t + E + "\n",
            "two pairs": FIRST + "\n\n" + B + t + E + "\n" + B + t + E + "\n",
            "begin inside a line": FIRST + "\n\nlead " + B + t + E + "\n",
            "indented begin": FIRST + "\n\n  " + B + t + E + "\n",
            "end inside a line": FIRST + "\n\n" + B + t + E + " tail\n",
            "text after end": FIRST + "\n\n" + B + t + E + "\nmore\n",
            "CRLF": FIRST + "\r\n\r\n" + B + "\r\nx\r\n" + E + "\r\n",
        }
        for name, blob in cases.items():
            with self.subTest(name), self.assertRaises(ValueError):
                rl.extract_generated_packet(blob)
        with PacketRepo(packets={P47: cases["front matter"]}):
            with self.assertRaisesRegex(ValueError, "generated file"):
                rl.pinned_packet(TAG2, P47, "xai", "grok-4.7")

    def test_malformed_manifests_are_refused(self):
        cases = {
            "no assignments": [],
            "same recipient twice": [row(), row(participant="grok-4-6", packet=P46)],
            "same participant twice": [row(), row(route="gemini")],
            "path spelled differently": [row(packet="rounds/02-deliberation/packets/./grok-4-7.md")],
            "another participant's path": [row(packet=P46)],
            "field missing": [{k: v for k, v in row().items() if k != "route"}],
            "hash malformed": [row(participant_text_sha256="abc")],
            "not a list": {"grok-4-7": row()},
        }
        for name, rows in cases.items():
            with self.subTest(name), PacketRepo(rows=rows), self.assertRaises(ValueError):
                rl.pinned_packet(TAG2, P47, "xai", "grok-4.7")

    def test_packet_paths_spelled_differently_are_refused_before_git(self):
        for bad in ("rounds/02-deliberation/prompt.md", "rounds/01-deliberation/packets/grok-4-7.md",
                    "rounds/02-deliberation/packets/../prompt.md", "elsewhere/packets/grok-4-7.md",
                    "rounds/02-deliberation/packets/./grok-4-7.md", "rounds/02-deliberation/packets//grok-4-7.md",
                    "rounds\\02-deliberation\\packets\\grok-4-7.md", "rounds/02-deliberation/packets/Grok-4-7.md",
                    "/rounds/02-deliberation/packets/grok-4-7.md", "rounds/02-deliberation/packets/grok-4-7.md ",
                    "rounds/02-deliberation/packets/grok..4-7.md", "rounds/02-deliberation/packets/sub/grok-4-7.md",
                    "", None):
            with self.subTest(bad), PacketRepo() as repo:
                with self.assertRaises(ValueError):
                    rl.pinned_packet(TAG2, bad, "xai", "grok-4.7")
                self.assertEqual(repo.reads, [])

    def test_a_packet_mode_round_refuses_the_round_prompt_path(self):
        with PacketRepo():
            with self.assertRaisesRegex(ValueError, "packet-mode round"):
                rl.pinned_prompt(TAG2)

    def test_earlier_round_prompts_are_read_as_before(self):
        text = "\nRound one text, ü\n"
        blob = ("---\ntype: round-prompt\nparticipant_text_sha256: " + rl.sha256(text) + "\n---\n\nintro\n"
                + rl.BEGIN + text + rl.END + "\n")
        with mock.patch.object(rl, "git_commit", return_value="d" * 40), \
                mock.patch.object(rl, "git_blob", return_value=blob) as git_blob:
            self.assertEqual(rl.pinned_prompt("round/01-deliberation/v1"), (text, rl.sha256(text), "d" * 40))
        git_blob.assert_called_once_with("d" * 40, "rounds/01-deliberation/prompt.md")

    def test_a_supplied_prompt_is_refused_in_packet_mode(self):
        with PacketRepo() as repo, self.assertRaises(ValueError):
            rl.participant_input(args(self.prefix, tag=TAG2, packet=PLOCAL), rl.ROUTE, PROMPT)
        self.assertEqual(repo.reads, [])

    def test_local_run_with_another_models_packet_stops_before_any_request_or_file(self):
        http = FakeHttp()
        with PacketRepo():
            with self.assertRaisesRegex(ValueError, "assigns rounds/02-deliberation/packets/fake-1b.md"):
                rl.run(args(self.prefix, model="fake:1b", tag=TAG2, packet=P47), http)
            with self.assertRaisesRegex(ValueError, "assigns no packet"):
                rl.run(args(self.prefix, model="other:2b", tag=TAG2, packet=PLOCAL), http)
        self.assertEqual((http.calls, http.streamed, self.files()), (0, False, []))

    def test_local_run_sends_the_packet_and_records_the_verified_assignment(self):
        http = FakeHttp()
        with PacketRepo():
            r = rl.run(args(self.prefix, model="fake:1b", tag=TAG2, packet=PLOCAL), http)
        self.assertTrue(r["complete"])
        self.assertEqual(http.payload["messages"][-1], {"role": "user", "content": PacketRepo.TEXTS[PLOCAL]})
        pre = self.load("preflight.json")
        a = pre["input_set"]["assignment"]
        self.assertEqual((pre["input_set"]["packet"], a["route"], a["requested_model"], a["packet"]),
                         (PLOCAL, "ollama", "fake:1b", PLOCAL))
        self.assertEqual(pre["participant_text_sha256"], rl.sha256(PacketRepo.TEXTS[PLOCAL]))
        self.assertEqual(a["participant_text_sha256"], pre["participant_text_sha256"])


TAG3 = "round/03-open/v1"
MANIFEST3 = "rounds/03-open/prompt.md"


class PanelRepo(PacketRepo):
    """A Round 3 manifest at one commit: one shared text between the markers and a named panel."""
    TEXT = "\nThe shared Round 3 text.\n"

    def __init__(self, panel=None, include_panel=True):
        front = {"type": "round-prompt", "round": "03-open", "participant_text_sha256": rl.sha256(self.TEXT)}
        if include_panel:
            front["panel"] = panel if panel is not None else [
                {"participant": "fake-1b", "recorded_as": "Fake 1B", "route": "ollama", "requested_model": "fake:1b"},
                {"participant": "gpt-x", "recorded_as": "GPT X", "route": "openai", "requested_model": "gpt-x"}]
        self.blobs = {MANIFEST3: ("---\n" + yaml.safe_dump(front, sort_keys=False) + "---\n\n# Manifest\n\n"
                                  + rl.BEGIN + self.TEXT + rl.END + "\n")}
        self.reads = []

    def commit(self, tag):
        if tag != TAG3:
            raise subprocess.CalledProcessError(128, ["git", "rev-parse", tag])
        return self.COMMIT


class Panel(Base):  # Round 3: the manifest names the panel (launch package, "The panel")
    def test_a_named_member_gets_the_shared_text_and_its_panel_entry(self):
        with PanelRepo():
            text, digest, commit, a = rl.participant_input(args(self.prefix, tag=TAG3), "ollama")
        self.assertEqual((text, digest, commit), (PanelRepo.TEXT, rl.sha256(PanelRepo.TEXT), PanelRepo.COMMIT))
        self.assertEqual((a["participant"], a["route"], a["requested_model"], a["manifest"]),
                         ("fake-1b", "ollama", "fake:1b", MANIFEST3))

    def test_a_run_the_panel_does_not_name_is_refused(self):
        with PanelRepo():
            for route in ("gemini", "openai"):
                with self.subTest(route=route), self.assertRaisesRegex(ValueError, "exactly once"):
                    rl.participant_input(args(self.prefix, tag=TAG3), route)

    def test_a_duplicated_or_malformed_panel_is_refused(self):
        entry = {"participant": "fake-1b", "route": "ollama", "requested_model": "fake:1b"}
        for panel in ([entry, dict(entry, participant="fake-1b-again")], [], ["not a mapping"]):
            with self.subTest(panel=panel), PanelRepo(panel=panel), self.assertRaises(ValueError):
                rl.participant_input(args(self.prefix, tag=TAG3), "ollama")

    def test_a_round_without_a_panel_has_no_assignment(self):
        with PanelRepo(include_panel=False):
            *_, a = rl.participant_input(args(self.prefix, tag=TAG3), "ollama")
        self.assertIsNone(a)


class PanelMalformed(Base):  # GPT-6 R3P3
    def test_a_null_panel_or_an_unnamed_entry_is_refused(self):
        for panel in ("null", [{"route": "ollama", "requested_model": "fake:1b"}],
                      [{"participant": " ", "route": "ollama", "requested_model": "fake:1b"}]):
            with self.subTest(panel=panel), PanelRepo(panel=[] if panel == "null" else panel) as repo:
                if panel == "null":
                    repo.blobs[MANIFEST3] = repo.blobs[MANIFEST3].replace("panel: []", "panel: null")
                with self.assertRaisesRegex(ValueError, "nonempty list of named entries"):
                    rl.participant_input(args(self.prefix, tag=TAG3), "ollama")


if __name__ == "__main__":
    unittest.main()
