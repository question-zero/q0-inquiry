# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Offline tests for tools/export_archive.py, the exporter of the publication policy (the founder's choice, verbatim, "Publish everything, redacted").
# license: MIT (LICENSE-CODE)
"""Offline tests for export_archive.py. Run: python -m unittest tools/test_export_archive.py

Synthetic sources in a temporary folder stand in for the private archive. No real evidence is read.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_headers as ch  # noqa: E402
import export_archive as ex  # noqa: E402

KEY = "zz-TEST-SECRET-VALUE-1234567890"
EMAIL = "someone@example.org"
PRIVATE = "Private Project Falcon"
WITHHOLD = "zebra-topic"
SIDECAR = {"title": "t", "author": "a", "model": "m", "developer": "d", "participant_id": "m/abcd1234", "run": "r",
           "attribution": "self-declared", "date": "2026-09-25", "prompt": "p", "exposure": ["x"],
           "human_interventions": "none", "samples": {"generated": 1, "submitted": 1}}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "keys.env").write_text(f"SOME_API_KEY={KEY}\n", encoding="utf-8")
        self.out = self.root / "out"
        self.sources = []

    def tearDown(self):
        self.tmp.cleanup()

    def source(self, name, content, fmt, dest, **kw):
        p = self.root / name
        p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        self.sources.append(dict({"path": str(p), "dest": dest, "format": fmt, "sidecar": dict(SIDECAR)}, **kw))
        return p

    def config(self, **kw):
        c = {"version": "pc-test-1", "source_commit": "abc1234", "cutoff_utc": "2026-09-25T00:00:00Z",
             "keys_file": str(self.root / "keys.env"), "terms": [{"text": PRIVATE, "category": "confidential"}],
             "withhold_terms": [{"text": WITHHOLD, "category": "personal"}], "sources": self.sources}
        c.update(kw)
        return c

    def run_export(self, **kw):
        return ex.Export(self.config(**kw), self.out).run()

    def read(self, dest):
        return (self.out / dest).read_text(encoding="utf-8")

    def assert_no_private(self, text):
        for s in (KEY, EMAIL, PRIVATE, WITHHOLD):
            self.assertNotIn(s, text)


class ClaudeTranscript(Base):
    def lines(self):
        return [
            {"type": "user", "timestamp": "t0", "message": {"role": "user", "content":
                f"Please check this. Mail me at {EMAIL}.<system-reminder>harness text</system-reminder>"}},
            {"type": "assistant", "timestamp": "t1", "message": {"role": "assistant", "model": "claude-x", "content": [
                {"type": "thinking", "thinking": "internal reasoning", "signature": "sig"},
                {"type": "text", "text": f"Working on {PRIVATE}."},
                {"type": "tool_use", "id": "u1", "name": "Bash", "input": {"command": f"echo {KEY}"}}]}},
            {"type": "user", "timestamp": "t2", "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "u1", "content": [
                    {"type": "text", "text": "done<system-reminder>more</system-reminder>"},
                    {"type": "image", "source": {"type": "base64", "data": "AAAA"}}]}]}},
            {"type": "user", "timestamp": "t3", "message": {"role": "user", "content": f"About the {WITHHOLD}: keep it."}},
            {"type": "user", "isCompactSummary": True, "message": {"role": "user", "content": "summary"}},
            {"type": "attachment", "timestamp": "t4", "attachment": {"type": "queued_command", "prompt": "next step please"}},
            {"type": "attachment", "attachment": {"type": "prompt_snapshot", "systemPrompt": "SYSTEM", "tools": []}},
            {"type": "attachment", "attachment": {"type": "file", "filename": "x", "content": "file body"}},
            {"type": "system", "content": "sys"},
            {"type": "bridge-session", "ownerAccountUuid": "acct-1", "ownerOrganizationUuid": "org-1"},
        ]

    def test_allowlist_normalization(self):
        raw = "\n".join(json.dumps(x) for x in self.lines()) + "\nnot json\n"
        self.source("t.jsonl", raw, "claude-transcript", "sessions/editor/t.jsonl", reasoning_class="C")
        rows = self.run_export()
        out = self.read("sessions/editor/t.jsonl")
        items = [json.loads(line) for line in out.splitlines()]
        self.assertEqual([i["role"] for i in items], ["user", "assistant", "user", "user", "user"])
        text = json.dumps(items)
        self.assertIn("[WITHHELD: C, thinking; see manifest]", out)
        self.assertIn("[WITHHELD: C, injected context; see manifest]", out)
        self.assertIn("[WITHHELD: D, image or non-text tool output; see manifest]", out)
        self.assertIn("[WITHHELD: personal; see manifest]", out)
        self.assertIn("[REDACTED: contact]", out)
        self.assertIn("[REDACTED: secret]", out)
        self.assertIn("[REDACTED: confidential]", out)
        self.assertTrue(items[-1].get("queued"))
        for gone in ("internal reasoning", "harness text", "SYSTEM", "file body", "summary", "acct-1", "org-1", "sig"):
            self.assertNotIn(gone, text)
        self.assert_no_private(out)
        w = rows[0]["withheld"]
        self.assertEqual((w["C, prompt_snapshot attachment"], w["D, file attachment"], w["C, system entry"]), (1, 1, 1))
        self.assertEqual(w["unparseable line"], 1)
        self.assertEqual(w["metadata entry not exported: bridge-session"], 1)

    def test_participant_reasoning_is_class_b_and_published_only_when_cleared(self):
        raw = json.dumps(self.lines()[1])
        self.source("f.jsonl", raw, "claude-transcript", "rounds/02-x/evidence/fable/t.jsonl", reasoning_class="B",
                    provider="anthropic-cli")
        self.run_export()
        self.assertIn("[WITHHELD: B, thinking; see manifest]", self.read("rounds/02-x/evidence/fable/t.jsonl"))

    def test_cleared_class_b_reasoning_is_published_redacted(self):
        raw = json.dumps(self.lines()[1])
        self.source("f.jsonl", raw, "claude-transcript", "rounds/02-x/evidence/fable/t.jsonl", reasoning_class="B",
                    provider="anthropic-cli")
        self.run_export(cleared_reasoning=["anthropic-cli"])
        self.assertIn("internal reasoning", self.read("rounds/02-x/evidence/fable/t.jsonl"))

    def test_class_c_reasoning_is_never_published_even_if_cleared(self):
        raw = json.dumps(self.lines()[1])
        self.source("e.jsonl", raw, "claude-transcript", "sessions/editor/e.jsonl", reasoning_class="C",
                    provider="anthropic-cli")
        self.run_export(cleared_reasoning=["anthropic-cli"])
        self.assertNotIn("internal reasoning", self.read("sessions/editor/e.jsonl"))


class OtherFormats(Base):
    def test_codex_run(self):
        events = [{"type": "thread.started", "thread_id": "th-1"},
                  {"type": "item.completed", "item": {"id": "a", "type": "agent_message", "text": f"see {PRIVATE}"}},
                  {"type": "item.completed", "item": {"id": "b", "type": "command_execution", "command": "cat x",
                                                      "aggregated_output": f"mail {EMAIL}", "exit_code": 0, "status": "ok"}},
                  {"type": "item.completed", "item": {"id": "c", "type": "reasoning", "text": "reviewer thoughts"}},
                  {"type": "item.completed", "item": {"id": "d", "type": "mystery", "blob": "x"}},
                  {"type": "turn.completed", "usage": {"input_tokens": 5}}]
        self.source("r.jsonl", "\n".join(json.dumps(e) for e in events), "codex-run", "sessions/reviewer/r.jsonl")
        rows = self.run_export()
        out = self.read("sessions/reviewer/r.jsonl")
        self.assertIn("[WITHHELD: C, reasoning; see manifest]", out)
        self.assertNotIn("reviewer thoughts", out)
        self.assertEqual(rows[0]["withheld"]["D, mystery item"], 1)
        self.assert_no_private(out)

    def test_sse_reasoning_withheld_and_text_redacted(self):
        events = ["data: " + json.dumps({"choices": [{"delta": {"reasoning_content": "thinking about it"}}]}),
                  "data: " + json.dumps({"choices": [{"delta": {"content": f"answer to {EMAIL}"}}]}),
                  "data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": "a thought", "thought": True},
                                                                              {"text": "visible"}]}}]}),
                  "data: [DONE]"]
        self.source("s.sse", "\n\n".join(events) + "\n\n", "sse", "rounds/02-x/evidence/grok/s.sse",
                    reasoning_class="B", provider="xai")
        self.run_export()
        out = self.read("rounds/02-x/evidence/grok/s.sse")
        self.assertNotIn("thinking about it", out)
        self.assertNotIn("a thought", out)
        self.assertIn("visible", out)
        self.assertIn("data: [DONE]", out)
        for block in out.strip().split("\n\n"):
            payload = block[len("data: "):]
            if payload != "[DONE]":
                json.loads(payload)
        self.assert_no_private(out)

    def test_json_and_ollama_streams(self):
        self.source("res.json", json.dumps({"answer": f"hi {EMAIL}", "thinking": "local thoughts",
                                            "account": int("4242"), f"{PRIVATE}": 1}), "json",
                    "rounds/02-x/evidence/qwen/result.json", reasoning_class="B", provider="ollama-qwen")
        self.source("st.jsonl", json.dumps({"message": {"content": "c", "thinking": "t"}}) + "\n", "ollama-jsonl",
                    "rounds/02-x/evidence/qwen/stream.jsonl", reasoning_class="B", provider="ollama-qwen")
        self.run_export(terms=[{"text": PRIVATE, "category": "confidential"}, {"text": "4242", "category": "account-id"}])
        res = json.loads(self.read("rounds/02-x/evidence/qwen/result.json"))
        self.assertEqual(res["thinking"], "[WITHHELD: B, thinking; see manifest]")
        self.assertEqual(res["account"], "[REDACTED: account-id]")
        self.assertIn("[REDACTED: confidential]", res)
        self.assertNotIn("local thoughts", self.read("rounds/02-x/evidence/qwen/stream.jsonl"))

    def test_text_file(self):
        self.source("m.md", f"---\nid: 1\n---\n\nFrom {EMAIL} about {PRIVATE}.\n", "text", "sessions/mailbox/m.md")
        self.run_export()
        self.assert_no_private(self.read("sessions/mailbox/m.md"))


class Driver(Base):
    def test_outputs_pass_the_header_checker(self):
        self.source("m.md", "hello\n", "text", "sessions/mailbox/m.md")
        self.run_export()
        for rel in ("sessions/mailbox/m.md", "sessions/mailbox/m.md.meta.md", "sessions/manifest.md"):
            self.assertEqual(ch.check(rel, root=self.out), ([], []), rel)
        manifest = self.read("sessions/manifest.md")
        self.assertIn("pc-test-1", manifest)
        self.assertNotIn(KEY, manifest)

    def test_missing_and_withheld_sources_are_listed(self):
        self.sources.append({"path": str(self.root / "nope"), "dest": "sessions/x/nope.jsonl", "format": "text",
                             "sidecar": dict(SIDECAR), "missing_reason": "not found locally"})
        self.source("img.png", b"\x89PNG", "withhold", "sessions/x/img.png", reason="D, image")
        rows = self.run_export()
        self.assertEqual([(r["disposition"], r.get("reason")) for r in rows],
                         [("missing", "not found locally"), ("withheld", "D, image")])
        self.assertFalse((self.out / "sessions/x/img.png").exists())
        manifest = self.read("sessions/manifest.md")
        self.assertIn("missing (not found locally)", manifest)
        self.assertIn("withheld (D, image)", manifest)

    def test_refusals(self):
        self.source("m.md", "hello\n", "text", "sessions/m.md")  # not in a subfolder
        with self.assertRaises(ValueError):
            self.run_export()
        self.sources[0]["dest"] = f"sessions/{PRIVATE}/m.md"  # a private name in a path
        with self.assertRaises(ValueError):
            ex.Export(self.config(), self.root / "out2").run()
        self.sources[0]["dest"] = "sessions/a/m.md"
        self.out.mkdir()
        with self.assertRaises(FileExistsError):
            self.run_export()

    def test_a_sidecar_that_would_fail_the_header_check_is_refused(self):
        self.source("m.md", "hello\n", "text", "sessions/a/m.md")
        del self.sources[0]["sidecar"]["title"]
        with self.assertRaisesRegex(ValueError, "header check"):
            self.run_export()

    def test_the_detector_fails_closed_on_leftovers(self):
        red = ex.Redactor(self.config())
        self.assertEqual(red.detect("[REDACTED: contact] and [WITHHELD: personal; see manifest]"), [])
        self.assertIn("contact", red.detect(f"x {EMAIL}"))
        self.assertIn("secret", red.detect(f"x {KEY}"))
        self.assertIn("personal", red.detect(f"x {WITHHOLD.upper()}"))
        self.assertIn("network", red.detect("host 10.1.2.3"))
        self.assertEqual(red.detect("localhost 127.0.0.1:11434"), [])


class ReviewRegressions(Base):  # GPT-6 EX1-EX5
    def test_private_data_in_sidecar_metadata_or_reasons_is_refused(self):  # EX1
        self.source("m.md", "hello\n", "text", "sessions/a/m.md")
        self.sources[0]["sidecar"]["title"] = f"About {PRIVATE}"
        with self.assertRaisesRegex(ValueError, "sidecar metadata"):
            self.run_export()
        self.sources[0]["sidecar"]["title"] = "t"
        self.sources.append({"path": str(self.root / "nope"), "dest": "sessions/b/nope.md", "format": "text",
                             "sidecar": dict(SIDECAR), "missing_reason": f"lost {EMAIL}"})
        with self.assertRaisesRegex(ValueError, "missing_reason"):
            ex.Export(self.config(), self.root / "out2").run()
        self.assertFalse((self.root / "out2").exists())

    def test_marker_shaped_source_text_is_not_trusted(self):  # EX1
        self.source("m.md", f"[WITHHELD: {PRIVATE}; see manifest] and [REDACTED: {EMAIL}]\n", "text", "sessions/a/m.md")
        self.run_export()
        self.assert_no_private(self.read("sessions/a/m.md"))

    def test_reminders_are_withheld_in_every_format(self):  # EX2
        reminder = "<system-reminder>protected harness text</system-reminder>"
        self.source("j.json", json.dumps({"note": f"x {reminder}"}), "json", "sessions/a/j.json")
        self.source("r.jsonl", json.dumps({"type": "item.completed", "item": {
            "id": "b", "type": "command_execution", "command": "c", "aggregated_output": f"out {reminder}"}}),
            "codex-run", "sessions/a/r.jsonl")
        self.source("t.jsonl", json.dumps({"type": "assistant", "message": {"role": "assistant", "content": [
            {"type": "tool_use", "id": "u", "name": "Write", "input": {"content": f"file {reminder}"}}]}}),
            "claude-transcript", "sessions/a/t.jsonl")
        self.source("u.txt", "before <system-reminder>unterminated protected text\n", "text", "sessions/a/u.txt")
        self.run_export()
        for dest in ("sessions/a/j.json", "sessions/a/r.jsonl", "sessions/a/t.jsonl", "sessions/a/u.txt"):
            out = self.read(dest)
            self.assertNotIn("protected", out, dest)
            self.assertIn("[WITHHELD: C, injected context; see manifest]", out, dest)

    def test_partial_reasoning_and_encoded_components_are_withheld(self):  # EX2
        self.source("f.json", json.dumps({"partial_thinking": "half a thought", "packaged_thinking": {"default": True},
                                          "img": "data:image/png;base64,iVBORw0KGgo=",
                                          "part": {"type": "image", "source": "x"}}), "json", "sessions/a/f.json",
                    reasoning_class="B", provider="p")
        self.run_export()
        out = json.loads(self.read("sessions/a/f.json"))
        self.assertEqual(out["partial_thinking"], "[WITHHELD: B, partial_thinking; see manifest]")
        self.assertEqual(out["packaged_thinking"], {"default": True})
        self.assertEqual(out["img"], "[WITHHELD: D, encoded content; see manifest]")
        self.assertEqual(out["part"], "[WITHHELD: D, image, document or file object; see manifest]")

    def test_nested_json_is_decoded_before_redaction(self):  # EX3
        nested = json.dumps({"inner": json.dumps({"deeper": f"call {PRIVATE} at {EMAIL}"})})
        self.source("n.json", json.dumps({"payload": nested}), "json", "sessions/a/n.json")
        self.run_export()
        out = self.read("sessions/a/n.json")
        decoded = json.loads(json.loads(json.loads(out)["payload"])["inner"])["deeper"]
        self.assertIn("[REDACTED: confidential]", decoded)
        self.assert_no_private(decoded)

    def test_a_term_split_across_stream_pieces_is_withheld(self):  # EX3
        half = len(PRIVATE) // 2
        events = ["data: " + json.dumps({"choices": [{"delta": {"content": "about " + PRIVATE[:half]}}]}),
                  "data: " + json.dumps({"choices": [{"delta": {"content": PRIVATE[half:] + " today"}}]}),
                  "data: " + json.dumps({"choices": [{"delta": {"content": " unrelated"}}]})]
        self.source("s.sse", "\n\n".join(events) + "\n\n", "sse", "sessions/a/s.sse", reasoning_class="B", provider="x")
        self.source("o.jsonl", "\n".join(json.dumps({"message": {"content": c}}) for c in ("x " + EMAIL[:5], EMAIL[5:])),
                    "ollama-jsonl", "sessions/a/o.jsonl", reasoning_class="B", provider="x")
        self.run_export()
        joined = "".join(json.loads(b[len("data: "):])["choices"][0]["delta"]["content"]
                         for b in self.read("sessions/a/s.sse").strip().split("\n\n"))
        self.assertNotIn(PRIVATE, joined)
        self.assertIn(" unrelated", joined)
        joined = "".join(json.loads(line)["message"]["content"] for line in self.read("sessions/a/o.jsonl").splitlines())
        self.assertNotIn(EMAIL, joined)

    def test_colliding_redacted_keys_keep_both_values(self):  # EX4
        self.source("k.json", json.dumps({EMAIL: 1, "other@example.com": 2}), "json", "sessions/a/k.json")
        self.run_export()
        out = json.loads(self.read("sessions/a/k.json"))
        self.assertEqual(sorted(out.values()), [1, 2])
        self.assertEqual(sorted(out), ["[REDACTED: contact]", "[REDACTED: contact] #2"])

    def test_tool_results_stay_linked_to_their_calls(self):  # EX4
        lines = [{"type": "assistant", "message": {"role": "assistant", "content": [
                     {"type": "tool_use", "id": "toolu_A", "name": "Read", "input": {}},
                     {"type": "tool_use", "id": "toolu_B", "name": "Bash", "input": {}}]}},
                 {"type": "user", "message": {"role": "user", "content": [
                     {"type": "tool_result", "tool_use_id": "toolu_B", "content": "b"},
                     {"type": "tool_result", "tool_use_id": "toolu_A", "content": "a"}]}}]
        self.source("t.jsonl", "\n".join(json.dumps(x) for x in lines), "claude-transcript", "sessions/a/t.jsonl")
        self.run_export()
        items = [json.loads(x) for x in self.read("sessions/a/t.jsonl").splitlines()]
        calls = {b["tool"]: b["call"] for b in items[0]["content"]}
        results = {b["text"]: b["call"] for b in items[1]["content"]}
        self.assertEqual((results["a"], results["b"]), (calls["Read"], calls["Bash"]))
        self.assertNotIn("toolu_", json.dumps(items))

    def test_colliding_or_reserved_destinations_are_refused_before_writing(self):  # EX5
        for dests in (["sessions/a/x.md", "sessions/a/x.md"], ["sessions/a/x.md", "sessions/a/X.MD"],
                      ["sessions/a/x.md", "sessions/a/x.md.meta.md"], ["sessions/a/con.txt"],
                      ["sessions/a/x.md."], ["sessions/manifest.md/x"], ["sessions/a\\x.md"]):
            with self.subTest(dests):
                self.sources = []
                for i, d in enumerate(dests):
                    self.source(f"s{i}.md", "hello\n", "text", d)
                out = self.root / f"out-{abs(hash(tuple(dests)))}"
                with self.assertRaises(ValueError):
                    ex.Export(self.config(), out).run()
                self.assertFalse(out.exists())

    def test_dotted_quads_are_redacted_and_counted_as_possible_versions(self):
        self.source("v.txt", "version 1.2.3.4 on host 192.168.1.20; build 10.0.26200.1; loopback 127.0.0.1\n", "text",
                    "sessions/a/v.txt")
        rows = self.run_export()
        out = self.read("sessions/a/v.txt")
        self.assertEqual(out.count("[REDACTED: network]"), 2)
        self.assertIn("127.0.0.1", out)
        self.assertEqual(rows[0]["redactions"]["network (dotted quad; may be a version number)"], 2)


class RoundTwoRegressions(Base):  # GPT-6's round 2 cases
    def escaped(self):
        return "\\u" + format(ord(PRIVATE[0]), "04x") + PRIVATE[1:]

    def test_escaped_json_in_sidecar_metadata_is_refused(self):  # EX1
        self.source("m.md", "hello\n", "text", "sessions/a/m.md")
        self.sources[0]["sidecar"]["exposure"] = ['{"x": "' + self.escaped() + '"}']
        with self.assertRaisesRegex(ValueError, "sidecar metadata"):
            self.run_export()
        self.assertFalse(self.out.exists())

    def test_a_reminder_split_across_stream_deltas_is_withheld(self):  # EX2
        parts = ["<system-reminder>", "protected body", "</system-reminder>", " visible"]
        events = ["data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": p}}]}) for p in parts]
        self.source("s.sse", "\n\n".join(events) + "\n\n", "sse", "sessions/a/s.sse", reasoning_class="B", provider="x")
        self.run_export()
        out = self.read("sessions/a/s.sse")
        self.assertNotIn("protected body", out)
        self.assertIn(" visible", out)

    def test_json_carried_in_a_text_source_is_classified(self):  # EX2
        self.source("t.txt", json.dumps({"partial_thinking": "protected half", "note": "fine"}), "text",
                    "sessions/a/t.txt", reasoning_class="C")
        self.run_export()
        out = json.loads(self.read("sessions/a/t.txt"))
        self.assertEqual(out["partial_thinking"], "[WITHHELD: C, partial_thinking; see manifest]")
        self.assertEqual(out["note"], "fine")

    def test_non_base64_data_uris_are_withheld(self):  # EX2
        self.source("u.json", json.dumps({"u": "data:text/plain,hello%20world", "v": "see data:,x"}), "json",
                    "sessions/a/u.json")
        rows = self.run_export()
        out = json.loads(self.read("sessions/a/u.json"))
        self.assertEqual(out["u"], "[WITHHELD: D, encoded content; see manifest]")
        self.assertEqual(out["v"], "[WITHHELD: D, encoded content; see manifest]")
        self.assertEqual(rows[0]["withheld"]["D, encoded content"], 2)

    def test_a_term_split_within_one_choice_of_a_multi_choice_stream_is_withheld(self):  # EX3
        half = len(PRIVATE) // 2
        events = ["data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": c0}},
                                                     {"index": 1, "delta": {"content": "noise "}}]})
                  for c0 in ("about " + PRIVATE[:half], PRIVATE[half:] + " today")]
        self.source("m.sse", "\n\n".join(events) + "\n\n", "sse", "sessions/a/m.sse", reasoning_class="B", provider="x")
        self.run_export()
        by_choice = {0: "", 1: ""}
        for block in self.read("sessions/a/m.sse").strip().split("\n\n"):
            for ch_ in json.loads(block[len("data: "):])["choices"]:
                by_choice[ch_["index"]] += ch_["delta"]["content"]
        self.assertNotIn(PRIVATE, by_choice[0])
        self.assertEqual(by_choice[1], "noise noise ")

    def test_content_nested_past_the_depth_limit_is_withheld(self):  # EX3
        s = '{"x": "' + self.escaped() + '"}'
        for _ in range(ex.MAX_DEPTH + 2):
            s = json.dumps(s)
        self.source("d.json", json.dumps({"deep": s, "shallow": json.dumps(json.dumps(self.escaped()))}), "json",
                    "sessions/a/d.json")
        self.run_export()
        out = json.loads(self.read("sessions/a/d.json"))
        for field in ("deep", "shallow"):
            value = out[field]
            for _ in range(ex.MAX_DEPTH + 3):
                try:
                    value = json.loads(value) if isinstance(value, str) else json.dumps(value)
                except ValueError:
                    break
            self.assertNotIn(PRIVATE, json.dumps(value).encode().decode("unicode_escape"), field)
            self.assertIn("WITHHELD", out[field], field)

    def test_codex_metadata_keeps_colliding_keys_apart(self):  # EX4
        event = {"type": "turn.completed", EMAIL: 11, "other@example.com": 22}
        self.source("r.jsonl", json.dumps(event), "codex-run", "sessions/a/r.jsonl")
        rows = self.run_export()
        data = json.loads(self.read("sessions/a/r.jsonl"))["data"]
        self.assertEqual(sorted(data.values()), [11, 22])
        self.assertEqual(rows[0]["withheld"]["structural: colliding keys numbered"], 1)


class RoundThreeRegressions(Base):  # GPT-6's round 3 EX2 cases
    def test_a_unicode_escaped_reminder_is_withheld(self):
        escaped = "\\u003csystem-reminder\\u003eprotected body\\u003c/system-reminder\\u003e"
        literal = json.dumps(escaped + " kept only if unread")  # the value holds the escape text itself
        self.source("e.json", '{"a": "' + escaped + ' visible", "c": ' + literal + ', "b": "fine"}', "json",
                    "sessions/a/e.json")
        self.run_export()
        text = self.read("sessions/a/e.json")
        self.assertNotIn("protected body", text)
        out = json.loads(text)
        self.assertEqual(out["a"], "[WITHHELD: C, injected context; see manifest] visible")
        self.assertEqual(out["c"], "[WITHHELD: C, injected context; see manifest]")
        self.assertEqual(out["b"], "fine")

    def test_string_wrapped_json_reasoning_is_withheld(self):
        wrapped = json.dumps(json.dumps({"partial_thinking": "SYNTHETIC_C_ONLY"}))
        self.source("w.json", json.dumps({"w": wrapped, "b": "fine"}), "json", "sessions/a/w.json", reasoning_class="C")
        self.run_export()
        text = self.read("sessions/a/w.json")
        self.assertNotIn("SYNTHETIC_C_ONLY", text)
        self.assertEqual(json.loads(text)["b"], "fine")

    def test_a_data_uri_body_split_from_its_prefix_is_withheld(self):
        parts = ["see ", "data:text/plain,", "SYNTHETIC_ENCODED_BODY", " end"]
        events = ["data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": p}}]}) for p in parts]
        self.source("d.sse", "\n\n".join(events) + "\n\n", "sse", "sessions/a/d.sse", reasoning_class="B", provider="x")
        self.run_export()
        self.assertNotIn("SYNTHETIC_ENCODED_BODY", self.read("sessions/a/d.sse"))

    def test_a_reminder_in_a_non_object_stream_event_is_withheld(self):
        events = ["data: " + json.dumps("<system-reminder>protected body</system-reminder>"),
                  "data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": "visible"}}]}), "data: [DONE]"]
        self.source("n.sse", "\n\n".join(events) + "\n\n", "sse", "sessions/a/n.sse", reasoning_class="B", provider="x")
        self.run_export()
        out = self.read("sessions/a/n.sse")
        self.assertNotIn("protected body", out)
        self.assertIn("visible", out)
        self.assertIn("data: [DONE]", out)


class ExportToolTwoRegressions(Base):  # GPT-6's export-tool-2 round 1 cases
    def sse(self, name, parts):
        events = ["data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": p}}]}) for p in parts]
        self.source(name, "\n\n".join(events) + "\n\n", "sse", "sessions/a/" + name, reasoning_class="B", provider="x")
        self.run_export()
        return self.read("sessions/a/" + name)

    def test_wrapped_reasoning_in_a_list_or_object_is_withheld(self):
        values = {"l": {"partial_thinking": ["SYNTHETIC_C_ONLY"]}, "o": {"partial_thinking": {"text": "SYNTHETIC_C_ONLY"}},
                  "g": {"parts": [{"thought": True, "text": "SYNTHETIC_C_ONLY"}]}}
        self.source("w.json", json.dumps({k: json.dumps(json.dumps(v)) for k, v in values.items()} | {"b": "fine"}),
                    "json", "sessions/a/w.json", reasoning_class="C")
        self.run_export()
        text = self.read("sessions/a/w.json")
        self.assertNotIn("SYNTHETIC_C_ONLY", text)
        self.assertEqual(json.loads(text)["b"], "fine")

    def test_an_escaped_reminder_split_across_stream_pieces_is_withheld(self):
        out = self.sse("r.sse", ["\\u003csy", "stem-reminder>", "SYNTHETIC_C_ONLY", "\\u003c/system-reminder>"])
        self.assertNotIn("SYNTHETIC_C_ONLY", out)

    def test_an_escaped_data_uri_split_across_stream_pieces_is_withheld(self):
        out = self.sse("u.sse", ["%64a", "ta:text/plain,", "SYNTHETIC_D_ONLY"])
        self.assertNotIn("SYNTHETIC_D_ONLY", out)

    def test_an_unrelated_stream_group_is_kept(self):
        events = ["data: " + json.dumps({"choices": [{"index": 0, "delta": {"content": p}}, {"index": 1, "delta": {"content": q}}]})
                  for p, q in (("\\u003csy", "kept "), ("stem-reminder>SYNTHETIC_C_ONLY", "as written"))]
        self.source("k.sse", "\n\n".join(events) + "\n\n", "sse", "sessions/a/k.sse", reasoning_class="B", provider="x")
        self.run_export()
        by_choice = {0: "", 1: ""}
        for block in self.read("sessions/a/k.sse").strip().split("\n\n"):
            for ch_ in json.loads(block[len("data: "):])["choices"]:
                by_choice[ch_["index"]] += ch_["delta"]["content"]
        self.assertNotIn("SYNTHETIC_C_ONLY", by_choice[0])
        self.assertEqual(by_choice[1], "kept as written")


class FetchedContent(Base):  # GPT-6 RC4 (topic rights-check): fetched third-party content is class D
    def transcript(self):
        def call(i, name, inp, result):
            return [{"type": "assistant", "timestamp": f"t{i}", "message": {"role": "assistant", "content": [
                        {"type": "tool_use", "id": f"u{i}", "name": name, "input": inp}]}},
                    {"type": "user", "timestamp": f"r{i}", "message": {"role": "user", "content": [
                        {"type": "tool_result", "tool_use_id": f"u{i}", "content": result}]}}]
        return (call(1, "WebFetch", {"url": "https://example.com/terms"}, "COPIED TERMS TEXT")
                + call(2, "mcp__Claude_Browser__get_page_text", {}, "COPIED PAGE TEXT")
                + call(3, "Agent", {"description": "Research terms"}, "REPORT QUOTING TERMS")
                + call(4, "Agent", {"description": "Review files"}, "own review text")
                + call(5, "Bash", {"command": "ls"}, "file list"))

    def test_fetched_results_are_withheld_and_their_calls_kept(self):
        raw = "\n".join(json.dumps(x) for x in self.transcript())
        self.source("t.jsonl", raw, "claude-transcript", "sessions/editor/t.jsonl", reasoning_class="C")
        rows = self.run_export(withhold_tool_results=["Agent:Research"])
        out = self.read("sessions/editor/t.jsonl")
        for copied in ("COPIED TERMS TEXT", "COPIED PAGE TEXT", "REPORT QUOTING TERMS"):
            self.assertNotIn(copied, out)
        self.assertIn("https://example.com/terms", out)  # the source reference stays
        self.assertIn("own review text", out)
        self.assertIn("file list", out)
        self.assertEqual(rows[0]["withheld"]["D, fetched third-party content"], 3)


class StandaloneResults(Base):  # GPT-6 RC4, round 2: persisted copies of fetched content
    def transcript(self):
        lines = []
        for i, (name, result) in enumerate((("mcp__Claude_Browser__get_page_text", "COPIED POLICY TEXT"),
                                            ("Bash", "plain command output")), 1):
            lines += [{"type": "assistant", "message": {"role": "assistant", "content": [
                          {"type": "tool_use", "id": f"toolu_{i}", "name": name, "input": {}}]}},
                      {"type": "user", "message": {"role": "user", "content": [
                          {"type": "tool_result", "tool_use_id": f"toolu_{i}", "content": result}]}}]
        return self.source("t.jsonl", "\n".join(json.dumps(x) for x in lines), "claude-transcript",
                           "sessions/editor/t.jsonl", reasoning_class="C")

    def test_fetched_content_is_withheld_in_the_transcript_and_its_standalone_copy(self):
        t = self.transcript()
        self.source("toolu_1.json", json.dumps([{"type": "text", "text": "COPIED POLICY TEXT"}]), "json",
                    "sessions/editor/tool-results/toolu_1.json", tool_result_of={"transcripts": [str(t)], "id": "toolu_1"})
        self.source("toolu_2.json", json.dumps(["plain command output"]), "json",
                    "sessions/editor/tool-results/toolu_2.json", tool_result_of={"transcripts": [str(t)], "id": "toolu_2"})
        self.source("toolu_9.json", json.dumps(["unknown"]), "json",
                    "sessions/editor/tool-results/toolu_9.json", tool_result_of={"transcripts": [str(t)], "id": "toolu_9"})
        rows = {r["dest"]: r for r in self.run_export()}
        self.assertNotIn("COPIED POLICY TEXT", self.read("sessions/editor/t.jsonl"))
        self.assertEqual(rows["sessions/editor/tool-results/toolu_1.json"]["disposition"], "withheld")
        self.assertFalse((self.out / "sessions/editor/tool-results/toolu_1.json").exists())
        self.assertEqual(rows["sessions/editor/tool-results/toolu_2.json"]["disposition"], "published")
        self.assertIn("unclassified", rows["sessions/editor/tool-results/toolu_9.json"]["reason"])

    def test_identifier_prefixes_are_redacted_as_the_builder_does(self):
        ident = "abcdef12-3456-7890-abcd-ef1234567890"
        self.source("m.txt", f"full {ident} and short {ident[:9]}… and other {ident[:5]}\n", "text",
                    "sessions/a/m.txt")
        self.run_export(identifiers=[ident])
        out = self.read("sessions/a/m.txt")
        self.assertNotIn(ident[:8], out)
        self.assertIn(f"other {ident[:5]}", out)  # under 8 characters: not an identifier prefix
        self.assertEqual(out.count("[REDACTED: account-id]"), 2)


class PayloadHeaders(Base):
    def test_a_payload_with_an_invalid_yaml_header_is_exported_and_still_scanned(self):
        text = f"---\nrefs:\n  - statement.md @ abc (the wording: \"approved\")\nto: {EMAIL}\n---\n\nBody.\n"
        self.source("m.md", text, "text", "sessions/mailbox/m.md")
        self.run_export()
        out = self.read("sessions/mailbox/m.md")
        self.assertNotIn(EMAIL, out)
        self.assertIn("Body.", out)


class RepeatedKeys(Base):  # GPT-6 LX1, topic launch-export, round 3
    def test_every_value_of_a_repeated_key_is_read(self):
        readings, _ = ex.views('{"a": "first", "a": "second"}')
        self.assertIn("first", readings)
        self.assertIn("second", readings)
        self.assertEqual(ex.load_all('{"a": 1, "b": 2}'), {"a": 1, "b": 2})

    def test_reasoning_under_an_earlier_repeated_key_withholds_the_string(self):
        import urllib.parse
        hidden = urllib.parse.quote('{"thinking": "SYNTHETIC_C_ONLY", "thinking": ""}')  # JSON only once decoded
        self.source("p.json", json.dumps({"a": hidden, "b": "fine"}), "json", "sessions/a/p.json", reasoning_class="C")
        self.run_export()
        out = json.loads(self.read("sessions/a/p.json"))
        self.assertNotIn("SYNTHETIC_C_ONLY", urllib.parse.unquote(out["a"]))
        self.assertIn("repeated JSON key", out["a"])
        self.assertEqual(out["b"], "fine")


class EscapeLayers(Base):  # found by the first final build: the exporter applies the builder's layering rule
    def test_a_string_layered_past_the_limit_is_withheld_and_one_at_the_limit_kept(self):
        at_limit = "%41"
        for _ in range(ex.MAX_DEPTH - 1):
            at_limit = at_limit.replace("%", "%25")  # MAX_DEPTH layers
        past = at_limit.replace("%", "%25")  # one more
        self.source("l.json", json.dumps({"a": "x " + past, "b": "x " + at_limit}), "json", "sessions/a/l.json")
        self.run_export()
        out = json.loads(self.read("sessions/a/l.json"))
        self.assertIn("escapes layered past the limit", out["a"])
        self.assertNotIn(past, out["a"])
        self.assertEqual(out["b"], "x " + at_limit)


class GrokOutput(Base):  # rights check D1: the archive follows the launch builder's rule
    SENTENCE = "A synthetic sentence that only the xAI answer in this repository ever wrote down, word for word."

    def repo(self):
        import subprocess
        repo = self.root / "repo"
        (repo / "rounds/00-initial/responses").mkdir(parents=True)
        (repo / "rounds/00-initial/responses/g.md").write_text(
            "---\ndeveloper: xAI\n---\n\nAn answer. " + self.SENTENCE + "\n", encoding="utf-8")
        for args in (("init", "-q"), ("config", "user.email", "t@example.invalid"), ("config", "user.name", "t"),
                     ("add", "-A"), ("commit", "-q", "-m", "x")):
            subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)
        return repo

    def test_grok_quotations_in_the_archive_are_replaced_and_the_rest_kept(self):
        repo = self.repo()
        self.source("m.json", json.dumps({"a": "It said: " + self.SENTENCE + " Then more.", "b": "other text"}),
                    "json", "sessions/a/m.json")
        rows = self.run_export(grok={"repo": str(repo), "commit": "HEAD"})
        out = json.loads(self.read("sessions/a/m.json"))
        self.assertNotIn("word for word", out["a"])
        self.assertIn("rights check D1, Grok output", out["a"])
        self.assertTrue(out["a"].startswith("It said: ") and out["a"].endswith(" Then more."))
        self.assertEqual(out["b"], "other text")
        self.assertEqual(rows[0]["withheld"]["withheld: Grok quotation (rights check, D1)"], 1)

    def test_grok_text_visible_only_in_an_alternative_reading_withholds_the_string(self):  # GPT-6 LX1
        repo = self.repo()
        escaped = "".join(f"\\u{ord(c):04x}" for c in self.SENTENCE)
        self.source("e.json", json.dumps({"a": "log line: " + escaped + " end", "b": "other text"}), "json",
                    "sessions/a/e.json")
        rows = self.run_export(grok={"repo": str(repo), "commit": "HEAD"})
        out = json.loads(self.read("sessions/a/e.json"))
        self.assertEqual(out["a"], "[WITHHELD: rights check D1 or an identifier, in an alternative reading; see manifest]")
        self.assertEqual(out["b"], "other text")

    def test_an_escaped_short_attributed_quotation_withholds_the_string(self):  # GPT-6 LX1, round 2
        repo = self.repo()
        phrase = "word for word"
        escaped = "".join(f"\\u{ord(c):04x}" for c in phrase)
        self.source("q.json", json.dumps({"a": f"Grok wrote \"{escaped}\" there", "b": "other text"}), "json",
                    "sessions/a/q.json")
        self.run_export(grok={"repo": str(repo), "commit": "HEAD"})
        out = json.loads(self.read("sessions/a/q.json"))
        self.assertNotIn(escaped, out["a"])
        self.assertIn("WITHHELD", out["a"])
        self.assertEqual(out["b"], "other text")

    def test_grok_text_under_an_earlier_repeated_key_withholds_the_string(self):  # GPT-6 LX1, launch-export round 3
        repo = self.repo()
        inner = '{"q": "' + self.SENTENCE.replace(" ", "\\t") + '", "q": "x"}'  # tabs: no run in the raw text
        self.source("r.json", json.dumps({"a": "log line\n" + inner, "b": "other text"}), "json", "sessions/a/r.json")
        self.run_export(grok={"repo": str(repo), "commit": "HEAD"})
        out = json.loads(self.read("sessions/a/r.json"))
        self.assertEqual(out["a"], "[WITHHELD: rights check D1 or an identifier, in an alternative reading; see manifest]")
        self.assertEqual(out["b"], "other text")

    def test_grok_text_wrapped_across_lines_of_a_text_file_is_found(self):
        repo = self.repo()
        wrapped = self.SENTENCE.replace(" in this repository ", " in this\nrepository ")
        self.source("t.txt", "before\n" + wrapped + "\nafter\n", "text", "sessions/a/t.txt")
        self.run_export(grok={"repo": str(repo), "commit": "HEAD"})
        out = self.read("sessions/a/t.txt")
        self.assertNotIn("word for word", out)
        self.assertNotIn("repository ever", out)
        self.assertTrue(out.startswith("before\n") and out.rstrip().endswith("after"))


if __name__ == "__main__":
    unittest.main()
