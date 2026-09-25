# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Offline tests for tools/run_api_participant.py (Round 1 design decision 8). Revision 2 adds regressions for GPT-6 findings API1-API4; revision 3 adds the remaining API4 cases; revision 4 adds ModelArk; revision 5 adds the R1API1 cases; revision 6 adds GPT-6 RPK2 regressions (the manifest's assignment is checked for the provider and model); revision 7 adds the OpenAI route; revision 8 adds GPT-6 R3P1 and R3P2 regressions.
# license: MIT (LICENSE-CODE)
"""Offline tests for run_api_participant.py. Run: python -m unittest tools/test_run_api_participant.py

A fake transport stands in for the providers. No request leaves the machine.
"""
import argparse
import json
import sys
import tempfile
import traceback
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_api_participant as ra  # noqa: E402
from test_run_local_participant import P46, P47, TAG2, PacketRepo  # noqa: E402

KEY = "SECRET-KEY-must-never-appear"
PROMPT = ("round one text\n", "p" * 64, "2" * 40)
HISTORY = [{"role": "user", "content": "round zero text\n"}, {"role": "assistant", "content": "earlier answer"}]


def sse(obj):
    """One complete server-sent event."""
    return ("data: " + json.dumps(obj) + "\n\n").encode("utf-8")


GEMINI_STREAM = [
    sse({"candidates": [{"content": {"role": "model", "parts": [{"text": "thought summary", "thought": True}]}}],
         "modelVersion": "gemini-x-001", "responseId": "resp-1"}),
    sse({"candidates": [{"content": {"role": "model", "parts": [{"text": "Hel"}]}}]}),
    sse({"candidates": [{"content": {"role": "model", "parts": [{"text": "lo"}]}, "finishReason": "STOP"}],
         "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 2, "thoughtsTokenCount": 5}}),
]
XAI_STREAM = [
    sse({"id": "chat-1", "model": "grok-x", "system_fingerprint": "fp1",
         "choices": [{"delta": {"reasoning_content": "reasoning"}}]}),
    sse({"id": "chat-1", "model": "grok-x", "choices": [{"delta": {"content": "Hel"}}]}),
    sse({"id": "chat-1", "model": "grok-x", "choices": [{"delta": {"content": "lo"}, "finish_reason": "stop"}]}),
    sse({"id": "chat-1", "model": "grok-x", "choices": [], "usage": {"prompt_tokens": 10, "completion_tokens": 2}}),
    b"data: [DONE]\n\n",
]


class FakeHttp:
    def __init__(self, lines, stream_error=None, fail_after=None, model_error=None, model_response=None,
                 count_response=None, headers=None):
        self.lines, self.stream_error, self.fail_after = lines, stream_error, fail_after
        self.model_error, self.model_response, self.count_response = model_error, model_response, count_response
        self.headers = headers if headers is not None else {"x-request-id": "req-1"}
        self.last_headers, self.streamed, self.seen_headers, self.bodies, self.calls = {}, False, [], [], 0
        self.url = None

    def json(self, method, url, headers, body=None, timeout=120):
        self.calls += 1
        self.seen_headers.append(headers)
        self.bodies.append(body)
        if url.endswith(":countTokens"):
            return self.count_response if self.count_response is not None else {"totalTokens": 100}
        if url.endswith("/tokenize-text"):
            return self.count_response if self.count_response is not None else {"token_ids": list(range(100))}
        if url.endswith("/tokenization"):
            return self.count_response if self.count_response is not None else {
                "data": [{"index": 0, "total_tokens": 100, "token_ids": list(range(100))}]}
        if url.endswith("/responses/input_tokens"):
            return self.count_response if self.count_response is not None else {"object": "response.input_tokens",
                                                                               "input_tokens": 100}
        if url.endswith("/api/v3/models"):
            return self.model_response or {"data": [{"id": "m-1", "owned_by": "x"}, {"id": "other"}]}
        if self.model_error:
            raise self.model_error
        return self.model_response or {"name": "models/x", "id": "x"}

    def stream(self, url, headers, body, timeout=3600):
        self.calls += 1
        self.streamed, self.body, self.url = True, body, url
        self.seen_headers.append(headers)
        self.last_headers = self.headers
        if self.stream_error:
            raise self.stream_error
        for i, line in enumerate(self.lines):
            if self.fail_after is not None and i == self.fail_after:
                raise ConnectionError("simulated drop")
            yield line


def args(prefix, provider, **kw):
    base = dict(provider=provider, model="m-1", prefix=str(prefix), tag="round/01-deliberation/v1",
                history_record=None, history_tag="round/00-initial/v1", max_output_tokens=None,
                max_input_tokens=None, keys_file="unused")
    base.update(kw)
    return argparse.Namespace(**base)


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

    def all_evidence(self):
        return "".join(p.read_text(encoding="utf-8", errors="replace") for p in Path(self.tmp.name).iterdir())

    def go(self, provider, http, **kw):
        return ra.run(args(self.prefix, provider, **kw), http, PROMPT, HISTORY, key=KEY)


class Gemini(Base):
    def test_success_separates_thoughts_and_records_ids(self):
        r = self.go("gemini", FakeHttp(GEMINI_STREAM))
        self.assertEqual((r["answer"], r["thinking"], r["finish_reason"], r["complete"]), ("Hello", "thought summary", "STOP", True))
        self.assertEqual((r["returned_model"], r["response_id"]), ("gemini-x-001", "resp-1"))
        self.assertEqual((r["generation_status"], r["transport_complete"]), ("completed", True))
        self.assertEqual(r["response_headers"], {"x-request-id": "req-1"})
        self.assertEqual(self.files(), ["p.attempt.json", "p.preflight.json", "p.result.json", "p.stream.sse"])

    def test_history_roles_and_no_tools_or_system(self):
        http = FakeHttp(GEMINI_STREAM)
        self.go("gemini", http)
        self.assertEqual([c["role"] for c in http.body["contents"]], ["user", "model", "user"])
        self.assertEqual(http.body["contents"][1]["parts"][0]["text"], "earlier answer")
        for k in ("tools", "systemInstruction", "system_instruction"):
            self.assertNotIn(k, http.body)
        self.assertTrue(http.url.endswith(":streamGenerateContent?alt=sse"))

    def test_max_tokens_recorded_as_incomplete(self):
        lines = [sse({"candidates": [{"content": {"parts": [{"text": "cut"}]}, "finishReason": "MAX_TOKENS"}]})]
        r = self.go("gemini", FakeHttp(lines))
        self.assertEqual((r["complete"], r["finish_reason"], r["generation_status"]), (False, "MAX_TOKENS", "completed"))

    def test_prompt_block_is_a_provider_outcome(self):  # API3
        lines = [sse({"promptFeedback": {"blockReason": "SAFETY"}, "responseId": "resp-9", "modelVersion": "g-1"})]
        r = self.go("gemini", FakeHttp(lines))
        self.assertEqual(r["generation_status"], "provider_blocked")
        self.assertEqual((r["block"]["blockReason"], r["response_id"]), ("SAFETY", "resp-9"))
        self.assertNotIn("p.failure.json", self.files())


class Xai(Base):
    def test_success_with_reasoning_usage_and_done(self):
        r = self.go("xai", FakeHttp(XAI_STREAM))
        self.assertEqual((r["answer"], r["thinking"], r["finish_reason"], r["complete"]), ("Hello", "reasoning", "stop", True))
        self.assertEqual((r["returned_model"], r["response_id"], r["system_fingerprint"]), ("grok-x", "chat-1", "fp1"))
        self.assertEqual(r["usage"], {"prompt_tokens": 10, "completion_tokens": 2})
        self.assertEqual((r["done_marker"], r["transport_complete"]), (True, True))

    def test_history_roles_and_model_in_body(self):
        http = FakeHttp(XAI_STREAM)
        self.go("xai", http)
        self.assertEqual([m["role"] for m in http.body["messages"]], ["user", "assistant", "user"])
        self.assertEqual(http.body["model"], "m-1")
        self.assertNotIn("tools", http.body)

    def test_length_recorded_as_incomplete(self):
        lines = [sse({"choices": [{"delta": {"content": "cut"}, "finish_reason": "length"}]}), b"data: [DONE]\n\n"]
        r = self.go("xai", FakeHttp(lines))
        self.assertEqual((r["complete"], r["finish_reason"]), (False, "length"))

    def test_missing_done_marker_is_an_incomplete_transport(self):  # API2
        r = self.go("xai", FakeHttp(XAI_STREAM[:-1]))
        self.assertEqual((r["complete"], r["transport_complete"], r["done_marker"]), (True, False, False))
        self.assertEqual(r["answer"], "Hello")


class ModelArk(Base):  # revision 4
    def test_success_uses_chat_completions_and_list_metadata(self):
        http = FakeHttp(XAI_STREAM)
        r = self.go("modelark", http)
        self.assertEqual((r["answer"], r["thinking"], r["complete"], r["transport_complete"]), ("Hello", "reasoning", True, True))
        self.assertTrue(http.url.endswith("/api/v3/chat/completions"))
        self.assertEqual(http.body["model"], "m-1")
        p = self.load("preflight.json")
        self.assertEqual(p["stages"]["model_metadata"]["response"], {"id": "m-1", "owned_by": "x"})
        self.assertEqual(p["stages"]["input_count"]["input_tokens"], 100)
        self.assertIn("modelark reasoning_content", r["thinking_note"])

    def test_unlisted_model_blocks(self):
        http = FakeHttp(XAI_STREAM, model_response={"data": [{"id": "other"}]})
        with self.assertRaises(ra.PreflightError):
            self.go("modelark", http)
        self.assertFalse(http.streamed)

    def test_malformed_tokenization_blocks(self):
        for i, resp in enumerate(({}, {"data": []}, {"data": [{"total_tokens": 0}]},
                                  {"data": [{"total_tokens": 5, "token_ids": [1, 2]}]},
                                  {"data": [{"total_tokens": 1}]},  # R1API1: token IDs missing
                                  {"data": [{"total_tokens": 1, "token_ids": None}]},  # null
                                  {"data": [{"total_tokens": 1, "token_ids": "not a list"}]},  # wrong type
                                  {"data": [{"total_tokens": True, "token_ids": [1]}]})):
            prefix = Path(self.tmp.name) / f"t{i}"
            http = FakeHttp(XAI_STREAM, count_response=resp)
            with self.assertRaises(ra.PreflightError, msg=resp):
                ra.run(args(prefix, "modelark", max_input_tokens=10), http, PROMPT, [], key=KEY)
            self.assertFalse(http.streamed, resp)
            self.assertFalse(Path(f"{prefix}.attempt.json").exists(), resp)

    def test_fresh_session_sends_only_the_new_text(self):
        http = FakeHttp(XAI_STREAM)
        ra.run(args(self.prefix, "modelark"), http, PROMPT, [], key=KEY)
        self.assertEqual(http.body["messages"], [{"role": "user", "content": "round one text\n"}])
        self.assertIsNone(self.load("preflight.json")["history"])


class Limits(Base):  # API1
    def test_zero_or_negative_limits_rejected_before_any_request(self):
        for kw in (dict(max_input_tokens=0), dict(max_output_tokens=0), dict(max_input_tokens=-3),
                   dict(max_output_tokens=-1), dict(max_output_tokens=True)):
            http = FakeHttp(GEMINI_STREAM)
            with self.assertRaises(ValueError, msg=kw):
                self.go("gemini", http, **kw)
            self.assertEqual((http.calls, self.files()), (0, []), kw)

    def test_malformed_counts_block_generation(self):
        cases = [("gemini", {}), ("gemini", {"totalTokens": 0}), ("gemini", {"totalTokens": "12"}),
                 ("xai", {}), ("xai", {"token_ids": []})]
        for i, (provider, resp) in enumerate(cases):
            prefix = Path(self.tmp.name) / f"c{i}"
            http = FakeHttp(GEMINI_STREAM if provider == "gemini" else XAI_STREAM, count_response=resp)
            with self.assertRaises(ra.PreflightError, msg=(provider, resp)):
                ra.run(args(prefix, provider, max_input_tokens=1000), http, PROMPT, HISTORY, key=KEY)
            self.assertFalse(http.streamed, (provider, resp))

    def test_input_limit_blocks_generation(self):
        http = FakeHttp(GEMINI_STREAM, count_response={"totalTokens": 50000})
        with self.assertRaises(ra.PreflightError):
            self.go("gemini", http, max_input_tokens=20000)
        self.assertFalse(http.streamed)

    def test_xai_count_scope_is_labeled_text_only(self):
        self.go("xai", FakeHttp(XAI_STREAM), max_input_tokens=1000)
        p = self.load("preflight.json")
        self.assertIn("not a complete request budget", p["stages"]["input_count"]["scope"])
        self.assertEqual(p["stages"]["input_count"]["input_tokens"], 100)

    def test_output_limit_is_sent(self):
        http = FakeHttp(GEMINI_STREAM)
        self.go("gemini", http, max_output_tokens=65536)
        self.assertEqual(http.body["generationConfig"]["maxOutputTokens"], 65536)


class Stream(Base):  # API2
    def test_multiline_data_event_is_joined(self):
        event = {"candidates": [{"content": {"parts": [{"text": "Hi"}]}, "finishReason": "STOP"}]}
        text = json.dumps(event, indent=1)  # a JSON object spread over several lines
        raw = ("".join("data: " + line + "\n" for line in text.splitlines()) + "\n").encode("utf-8")
        r = self.go("gemini", FakeHttp([raw]))
        self.assertEqual((r["answer"], r["complete"]), ("Hi", True))

    def test_bytes_split_across_reads_and_comments(self):
        whole = b": keep-alive\n\n" + b"".join(GEMINI_STREAM)
        chunks = [whole[i:i + 7] for i in range(0, len(whole), 7)]
        r = self.go("gemini", FakeHttp(chunks))
        self.assertEqual(r["answer"], "Hello")

    def test_archive_is_byte_exact_without_added_newlines(self):
        lines = GEMINI_STREAM + [b"data: {\"partial"]  # an unterminated final line
        r = self.go("gemini", FakeHttp(lines))
        self.assertEqual(Path(f"{self.prefix}.stream.sse").read_bytes(), b"".join(lines))
        self.assertEqual((r["partial_final_event"], r["transport_complete"], r["stream_byte_exact"]), (True, False, True))

    def test_stream_without_finish_is_failure(self):
        lines = [sse({"choices": [{"delta": {"content": "x"}}]})]
        with self.assertRaises(ra.GenerationFailure):
            self.go("xai", FakeHttp(lines))
        self.assertEqual(self.load("failure.json")["partial_answer"], "x")


class Failures(Base):  # API3
    def test_existing_evidence_refuses_before_any_request(self):
        Path(f"{self.prefix}.attempt.json").write_text("{}")
        http = FakeHttp(XAI_STREAM)
        with self.assertRaises(FileExistsError):
            self.go("xai", http)
        self.assertEqual(http.calls, 0)

    def test_mid_stream_drop_keeps_partial_output_and_metadata(self):
        with self.assertRaises(ra.GenerationFailure) as cm:
            self.go("xai", FakeHttp(XAI_STREAM, fail_after=2))
        self.assertEqual(cm.exception.original_type, "ConnectionError")
        f = self.load("failure.json")
        self.assertEqual((f["partial_answer"], f["partial_thinking"], f["generation_status"]), ("Hel", "reasoning", "failed"))
        self.assertEqual((f["returned_model"], f["response_id"]), ("grok-x", "chat-1"))
        self.assertIn("p.stream.sse", self.files())

    def test_generation_http_error_keeps_status_body_and_headers(self):
        err = ra.HttpFailure(429, "rate limited", {"retry-after": "30", "x-request-id": "req-429"})
        with self.assertRaises(ra.GenerationFailure) as cm:
            self.go("gemini", FakeHttp([], stream_error=err, headers={"retry-after": "30", "x-request-id": "req-429"}))
        self.assertEqual((cm.exception.status, cm.exception.body), (429, "rate limited"))
        f = self.load("failure.json")
        self.assertEqual((f["http_status"], f["http_body"]), (429, "rate limited"))
        self.assertEqual(f["http_headers"]["x-request-id"], "req-429")

    def test_preflight_http_error_is_structured_and_blocks(self):
        err = ra.HttpFailure(403, '{"error": "no credits"}', {"x-request-id": "req-403"})
        http = FakeHttp(XAI_STREAM, model_error=err)
        with self.assertRaises(ra.PreflightError):
            self.go("xai", http)
        stage = self.load("preflight.json")["stages"]["model_metadata"]
        self.assertEqual((stage["http_status"], stage["http_body"], stage["http_headers"]["x-request-id"]),
                         (403, '{"error": "no credits"}', "req-403"))
        self.assertFalse(http.streamed)
        self.assertEqual(self.files(), ["p.preflight.json"])


class Secrecy(Base):  # API4
    def test_key_only_in_headers_on_the_success_path(self):
        for provider, lines in (("gemini", GEMINI_STREAM), ("xai", XAI_STREAM)):
            prefix = Path(self.tmp.name) / provider
            http = FakeHttp(lines)
            ra.run(args(prefix, provider), http, PROMPT, HISTORY, key=KEY)
            self.assertNotIn(KEY, http.url)
            self.assertTrue(any(KEY in json.dumps(h) for h in http.seen_headers))
            self.assertNotIn(KEY, json.dumps(http.bodies) + json.dumps(http.body))
        self.assertNotIn(KEY, self.all_evidence())

    def test_echoed_key_in_error_body_is_redacted(self):
        err = ra.HttpFailure(401, f"invalid key {KEY}", {"x-echo": KEY})
        with self.assertRaises(ra.GenerationFailure) as cm:
            self.go("xai", FakeHttp([], stream_error=err, headers={"x-echo": KEY}))
        self.assertNotIn(KEY, self.all_evidence())
        self.assertIn(ra.REDACTED, self.load("failure.json")["http_body"])
        e = cm.exception
        shown = "".join(traceback.format_exception(e)) + str(e) + repr((e.status, e.body, e.headers))
        self.assertNotIn(KEY, shown)  # no echoed key in the raised error or its printed chain
        self.assertIsNone(e.__cause__)
        self.assertTrue(e.__suppress_context__)

    def test_echoed_key_in_stream_is_redacted_and_marked(self):
        lines = [sse({"choices": [{"delta": {"content": f"echo {KEY}"}, "finish_reason": "stop"}]}), b"data: [DONE]\n\n"]
        r = self.go("xai", FakeHttp(lines))
        self.assertNotIn(KEY, self.all_evidence())
        self.assertEqual((r["stream_redactions"], r["stream_byte_exact"]), (1, False))
        self.assertIn(ra.REDACTED, r["answer"])

    def test_key_split_across_reads_is_redacted(self):
        whole = sse({"choices": [{"delta": {"content": f"echo {KEY} end"}, "finish_reason": "stop"}]}) + b"data: [DONE]\n\n"
        cut = whole.index(KEY.encode()) + len(KEY) // 2
        for chunks in ([whole[:cut], whole[cut:]], [whole[i:i + 3] for i in range(0, len(whole), 3)]):
            prefix = Path(self.tmp.name) / f"split{len(chunks)}"
            r = ra.run(args(prefix, "xai"), FakeHttp(chunks), PROMPT, HISTORY, key=KEY)
            archived = Path(f"{prefix}.stream.sse").read_bytes()
            self.assertNotIn(KEY.encode(), archived)
            self.assertEqual((r["stream_redactions"], r["stream_byte_exact"]), (1, False))
            self.assertEqual(r["answer"], f"echo {ra.REDACTED} end")

    def test_split_key_then_failure_is_redacted(self):
        whole = sse({"choices": [{"delta": {"content": f"echo {KEY}"}}]})
        cut = whole.index(KEY.encode()) + 5
        with self.assertRaises(ra.GenerationFailure) as cm:
            self.go("xai", FakeHttp([whole[:cut], whole[cut:]], fail_after=2))
        self.assertNotIn(KEY, self.all_evidence())
        self.assertNotIn(KEY, "".join(traceback.format_exception(cm.exception)))
        f = self.load("failure.json")
        self.assertEqual((f["stream_redactions"], f["stream_byte_exact"]), (1, False))

    def test_key_prefix_held_back_is_released_at_the_end(self):
        tail = KEY[:6].encode()  # looks like the start of a key, but the stream ends
        lines = [sse({"choices": [{"delta": {"content": "ok"}, "finish_reason": "stop"}]}), b"data: [DONE]\n\n" + tail]
        r = self.go("xai", FakeHttp(lines))
        self.assertEqual(Path(f"{self.prefix}.stream.sse").read_bytes(), b"".join(lines))
        self.assertEqual((r["stream_redactions"], r["partial_final_event"]), (0, True))

    def test_echoed_key_in_preflight_is_redacted(self):
        self.go("gemini", FakeHttp(GEMINI_STREAM, model_response={"name": "models/x", "note": KEY}))
        p = self.load("preflight.json")
        self.assertNotIn(KEY, self.all_evidence())
        self.assertEqual(p["redactions"], 1)

    def test_load_key_reads_named_line_only(self):
        f = Path(self.tmp.name) / "keys.env"
        f.write_text("﻿GEMINI_API_KEY=abc\nXAI_API_KEY=\n", encoding="utf-8")
        self.assertEqual(ra.load_key(f, "GEMINI_API_KEY"), "abc")
        with self.assertRaises(ValueError):
            ra.load_key(f, "XAI_API_KEY")


class PacketMode(Base):  # GPT-6 RPK2
    def packet_run(self, provider, model, packet, http):
        return ra.run(args(self.prefix, provider, model=model, tag=TAG2, packet=packet), http, None, None, key=KEY)

    def test_grok_4_7_given_the_grok_4_6_packet_stops_before_any_request_or_file(self):
        http = FakeHttp(XAI_STREAM)
        with PacketRepo():
            with self.assertRaisesRegex(ValueError, "assigns rounds/02-deliberation/packets/grok-4-7.md"):
                self.packet_run("xai", "grok-4.7", P46, http)
        self.assertEqual((http.calls, http.streamed, self.files()), (0, False, []))

    def test_the_provider_is_part_of_the_recipient(self):
        http = FakeHttp(GEMINI_STREAM)
        with PacketRepo():
            with self.assertRaisesRegex(ValueError, "assigns no packet"):
                self.packet_run("gemini", "grok-4.7", P47, http)
        self.assertEqual((http.calls, self.files()), (0, []))

    def test_a_supplied_prompt_is_refused_in_packet_mode(self):
        http = FakeHttp(XAI_STREAM)
        with PacketRepo(), self.assertRaises(ValueError):
            ra.run(args(self.prefix, "xai", model="grok-4.7", tag=TAG2, packet=P47), http, PROMPT, None, key=KEY)
        self.assertEqual((http.calls, self.files()), (0, []))

    def test_grok_4_7_with_its_own_packet_sends_exactly_that_text_and_records_the_assignment(self):
        http = FakeHttp(XAI_STREAM)
        with PacketRepo():
            r = self.packet_run("xai", "grok-4.7", P47, http)
        self.assertEqual(r["answer"], "Hello")
        self.assertEqual(http.body["messages"], [{"role": "user", "content": PacketRepo.TEXTS[P47]}])
        pre = self.load("preflight.json")
        a = pre["input_set"]["assignment"]
        self.assertEqual((a["route"], a["requested_model"], a["packet"], a["participant"]),
                         ("xai", "grok-4.7", P47, "grok-4-7"))
        self.assertEqual(pre["participant_text_sha256"], a["participant_text_sha256"])
        self.assertEqual(pre["requested_model"], "grok-4.7")


class OpenAIRoute(Base):  # revision 7: GPT-5.6 Sol in the Round 3 panel
    STREAM = [
        sse({"id": "chatcmpl-1", "model": "gpt-x-2026", "system_fingerprint": "fp1",
             "choices": [{"delta": {"role": "assistant", "content": "Hel"}}]}),
        sse({"id": "chatcmpl-1", "model": "gpt-x-2026", "choices": [{"delta": {"content": "lo"}, "finish_reason": "stop"}]}),
        sse({"id": "chatcmpl-1", "model": "gpt-x-2026", "choices": [],
             "usage": {"prompt_tokens": 10, "completion_tokens": 7,
                       "completion_tokens_details": {"reasoning_tokens": 5}}}),
        b"data: [DONE]\n\n",
    ]

    def test_success_counts_with_the_responses_endpoint_and_streams_chat(self):
        http = FakeHttp(self.STREAM)
        r = ra.run(args(self.prefix, "openai", max_output_tokens=4000), http, PROMPT, [], key=KEY)
        self.assertEqual((r["answer"], r["thinking"], r["complete"], r["transport_complete"]), ("Hello", "", True, True))
        self.assertTrue(http.url.endswith("/v1/chat/completions"))
        self.assertEqual(http.body["max_completion_tokens"], 4000)
        self.assertNotIn("max_tokens", http.body)
        self.assertNotIn("reasoning_effort", http.body)  # the provider's default applies
        self.assertEqual(http.body["messages"], [{"role": "user", "content": "round one text\n"}])
        count_body = [b for b in http.bodies if b and "input" in b][0]
        self.assertEqual(count_body, {"model": "m-1", "input": [{"role": "user", "content": "round one text\n"}]})
        self.assertEqual(self.load("preflight.json")["stages"]["input_count"]["input_tokens"], 100)
        self.assertEqual(r["usage"]["completion_tokens_details"]["reasoning_tokens"], 5)
        self.assertIn("no reasoning text", r["thinking_note"])
        self.assertTrue(all(h.get("Authorization") == "Bearer " + KEY for h in http.seen_headers))

    def test_malformed_input_counts_block_before_generation(self):
        for i, resp in enumerate(({}, {"input_tokens": 0}, {"input_tokens": True}, {"input_tokens": "100"}, [])):
            prefix = Path(self.tmp.name) / f"o{i}"
            http = FakeHttp(self.STREAM, count_response=resp)
            with self.assertRaises(ra.PreflightError, msg=resp):
                ra.run(args(prefix, "openai", max_input_tokens=10), http, PROMPT, [], key=KEY)
            self.assertFalse(http.streamed, resp)
            self.assertFalse(Path(f"{prefix}.attempt.json").exists(), resp)


class OpenAIRefusal(Base):  # GPT-6 R3P2
    def stream(self, finish="stop"):
        return [sse({"id": "c", "model": "gpt-x", "choices": [{"delta": {"role": "assistant", "refusal": "I can't "}}]}),
                sse({"id": "c", "model": "gpt-x", "choices": [{"delta": {"refusal": "help with that."},
                                                               "finish_reason": finish}]}),
                b"data: [DONE]\n\n"]

    def test_a_refusal_is_kept_and_recorded_as_refused(self):
        r = ra.run(args(self.prefix, "openai"), FakeHttp(self.stream()), PROMPT, [], key=KEY)
        self.assertEqual((r["generation_status"], r["refusal"], r["answer"]), ("refused", "I can't help with that.", ""))
        self.assertFalse(r["complete"])

    def test_an_interrupted_refusal_is_kept_in_the_failure_record(self):
        with self.assertRaises(ra.GenerationFailure):
            ra.run(args(self.prefix, "openai"), FakeHttp(self.stream(), fail_after=1), PROMPT, [], key=KEY)
        self.assertEqual(self.load("failure.json")["partial_refusal"], "I can't ")

    def test_a_content_filter_is_its_own_outcome(self):
        stream = [sse({"id": "c", "model": "gpt-x", "choices": [{"delta": {"content": "Par"}, "finish_reason": "content_filter"}]}),
                  b"data: [DONE]\n\n"]
        r = ra.run(args(self.prefix, "openai"), FakeHttp(stream), PROMPT, [], key=KEY)
        self.assertEqual((r["generation_status"], r["answer"], r["complete"]), ("content_filtered", "Par", False))


class EvidenceLocation(Base):  # GPT-6 R3P1
    def test_a_prefix_inside_the_repository_is_refused_before_any_request(self):
        http = FakeHttp(OpenAIRoute.STREAM)
        inside = Path(ra.__file__).resolve().parents[1] / ".private" / "round-03" / "x"
        with self.assertRaisesRegex(ValueError, "inside the repository"):
            ra.run(args(inside, "openai"), http, PROMPT, [], key=KEY)
        self.assertEqual(http.calls, 0)
        self.assertFalse(inside.parent.exists())


if __name__ == "__main__":
    unittest.main()
