# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Offline tests for tools/run_claude_cli_participant.py, covering GPT-6 RPK2 (the manifest's assignment checked before any file or process). Revision 2 adds GPT-6 RPK3 regressions (evidence kept on failure; explicit outcomes; the JSON result's shape).
# license: MIT (LICENSE-CODE)
"""Offline tests for run_claude_cli_participant.py. Run: python -m unittest tools/test_run_claude_cli_participant.py

A fake launcher stands in for the CLI, and a fake repository for git. No model runs.
"""
import argparse
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_claude_cli_participant as rc  # noqa: E402
import run_local_participant as rl  # noqa: E402
from test_run_local_participant import P47, TAG2, PacketRepo, generated, row  # noqa: E402

PF = "rounds/02-deliberation/packets/claude-fable-5-1.md"
TF = "\nThe operator records this run as Claude Fable 5.1, by Anthropic. ü\n"
ROWS = [row(), row(participant="claude-fable-5-1", route="claude-code-cli", requested_model="fable", packet=PF,
                   participant_text_sha256=rl.sha256(TF))]
TRANSCRIPT = b'{"type": "user"}\n'


class FakeLaunch:
    """Answers --version, then plays the CLI: it saves a transcript (unless told not to), then either raises
    or prints its result."""

    def __init__(self, projects, fail=None, transcript=True, stdout=None, returncode=0):
        self.projects, self.fail, self.transcript = projects, fail, transcript
        self.stdout, self.returncode, self.calls = stdout, returncode, []

    def __call__(self, cmd, **kw):
        self.calls.append((cmd, kw))
        if cmd[1:] == ["--version"]:
            return SimpleNamespace(stdout="9.9.9 (Claude Code)\n", stderr="", returncode=0)
        session = cmd[cmd.index("--session-id") + 1]
        if self.transcript:
            folder = self.projects / ("C--x-" + Path(kw["cwd"]).name)
            folder.mkdir(parents=True)
            (folder / f"{session}.jsonl").write_bytes(TRANSCRIPT)
        if self.fail:
            raise self.fail
        out = {"type": "result", "subtype": "success", "is_error": False, "result": "Hello",
               "session_id": session, "uuid": "u-1", "usage": {"output_tokens": 1}}
        stdout = json.dumps(out).encode("utf-8") if self.stdout is None else self.stdout
        return SimpleNamespace(stdout=stdout, stderr=b"err text", returncode=self.returncode)


class Runner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "tmp").mkdir()
        self.prefix = self.root / "evidence" / "p"
        self.launch = FakeLaunch(self.root / "projects")

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, model="fable", packet=PF, launch=None):
        args = argparse.Namespace(model=model, prefix=str(self.prefix), cli="claude.exe", tag=TAG2, packet=packet,
                                  timeout=60)
        with PacketRepo(packets={PF: generated(TF)}, rows=ROWS):
            return rc.run(args, launch or self.launch, projects=self.root / "projects", empty_root=self.root / "tmp")

    def evidence(self):
        folder = self.prefix.parent
        return sorted(p.name for p in folder.iterdir()) if folder.exists() else []

    def load(self, suffix):
        return json.loads(Path(f"{self.prefix}.{suffix}").read_text(encoding="utf-8"))

    def raw(self, suffix):
        return Path(f"{self.prefix}.{suffix}").read_bytes()

    def test_another_models_packet_stops_before_any_file_or_process(self):
        with self.assertRaisesRegex(ValueError, "assigns rounds/02-deliberation/packets/claude-fable-5-1.md"):
            self.go(packet=P47)
        with self.assertRaisesRegex(ValueError, "assigns no packet"):
            self.go(model="opus")
        self.assertEqual((self.launch.calls, self.evidence(), list((self.root / "tmp").iterdir())), ([], [], []))

    def test_fresh_session_gets_exactly_the_packet_text_and_the_assignment_is_recorded(self):
        r = self.go()
        self.assertEqual((r["answer"], r["outcome"], r["outcome_reasons"]), ("Hello", "completed", []))
        cmd, kw = self.launch.calls[1]
        self.assertEqual(kw["input"], TF.encode("utf-8"))
        self.assertEqual(cmd[cmd.index("--model") + 1], "fable")
        pre = self.load("preflight.json")
        a = pre["input_set"]["assignment"]
        self.assertEqual((a["route"], a["requested_model"], a["packet"]), ("claude-code-cli", "fable", PF))
        self.assertEqual(pre["participant_text_sha256"], rl.sha256(TF))
        self.assertEqual(pre["cwd_contents_before"], [])
        self.assertEqual(r["session_id_returned"], pre["session_id"])
        self.assertEqual(self.evidence(), ["p.preflight.json", "p.result.json", "p.stderr.txt", "p.stdout.json",
                                           "p.transcript.jsonl"])
        self.assertEqual(self.raw("transcript.jsonl"), TRANSCRIPT)

    def test_existing_evidence_refuses_before_any_process(self):
        self.prefix.parent.mkdir(parents=True)
        Path(f"{self.prefix}.result.json").write_text("{}")
        with self.assertRaises(FileExistsError):
            self.go()
        self.assertEqual(self.launch.calls, [])

    def test_a_failed_launch_is_recorded_and_not_retried(self):
        launch = FakeLaunch(self.root / "projects", fail=TimeoutError("cli timed out"), transcript=False)
        with self.assertRaises(TimeoutError):
            self.go(launch=launch)
        self.assertEqual(len(launch.calls), 2)
        self.assertEqual(self.evidence(), ["p.failure.json", "p.preflight.json"])
        f = self.load("failure.json")
        self.assertEqual((f["outcome"], f["retried"], f["error_type"]), ("failed", False, "TimeoutError"))
        self.assertEqual((f["evidence"]["stdout"], f["evidence"]["transcript"]), ("unavailable", "not found"))

    def test_a_timeout_keeps_its_captured_streams_and_the_transcript(self):  # RPK3
        timeout = subprocess.TimeoutExpired("claude.exe", 60, output=b"partial out \xff", stderr=b"partial err")
        launch = FakeLaunch(self.root / "projects", fail=timeout)
        with self.assertRaises(subprocess.TimeoutExpired):
            self.go(launch=launch)
        self.assertEqual(len(launch.calls), 2)
        self.assertEqual(self.evidence(), ["p.failure.json", "p.preflight.json", "p.stderr.txt", "p.stdout.json",
                                           "p.transcript.jsonl"])
        self.assertEqual((self.raw("stdout.json"), self.raw("stderr.txt"), self.raw("transcript.jsonl")),
                         (b"partial out \xff", b"partial err", TRANSCRIPT))
        f = self.load("failure.json")
        self.assertEqual((f["outcome"], f["error_type"]), ("failed", "TimeoutExpired"))
        self.assertEqual((f["evidence"]["stdout"], f["evidence"]["transcript"]),
                         ("archived, 13 bytes", f"archived, {len(TRANSCRIPT)} bytes"))
        self.assertNotIn("result.json", " ".join(self.evidence()))

    def test_a_json_result_that_is_not_an_object_is_incomplete(self):  # RPK3
        r = self.go(launch=FakeLaunch(self.root / "projects", stdout=b"[]"))
        self.assertEqual((r["outcome"], r["answer"]), ("incomplete", None))
        self.assertIn("stdout JSON is a list, not an object", r["outcome_reasons"])
        self.assertEqual(self.load("result.json")["outcome"], "incomplete")
        self.assertEqual(self.raw("stdout.json"), b"[]")
        self.assertEqual(self.evidence(), ["p.preflight.json", "p.result.json", "p.stderr.txt", "p.stdout.json",
                                           "p.transcript.jsonl"])

    def test_unparseable_or_empty_stdout_is_incomplete_and_kept_raw(self):  # RPK3
        for i, stdout in enumerate((b"\xff{not json", b"", b"  \n")):
            with self.subTest(stdout=stdout):
                self.prefix = self.root / f"evidence{i}" / "p"
                r = self.go(launch=FakeLaunch(self.root / f"projects{i}", stdout=stdout))
                self.assertEqual(r["outcome"], "incomplete")
                self.assertTrue(any("stdout" in reason for reason in r["outcome_reasons"]))
                self.assertEqual(self.raw("stdout.json"), stdout)

    def test_an_error_result_is_incomplete_with_its_reasons(self):  # RPK3
        out = json.dumps({"type": "result", "subtype": "error_during_execution", "is_error": True}).encode()
        r = self.go(launch=FakeLaunch(self.root / "projects", stdout=out, returncode=1))
        self.assertEqual(r["outcome"], "incomplete")
        self.assertEqual(r["outcome_reasons"], ["exit code 1", "is_error is True",
                                                "subtype is 'error_during_execution'", "no answer text in the result"])

    def test_an_archival_error_is_reported_without_hiding_the_run(self):  # RPK3
        real = rc.write_exclusive

        def failing(path, content, binary=False):
            if str(path).endswith(".transcript.jsonl"):
                raise OSError("disk full")
            return real(path, content, binary)

        with mock.patch.object(rc, "write_exclusive", side_effect=failing):
            r = self.go()
        self.assertEqual(r["outcome"], "completed")
        self.assertEqual(r["evidence"]["transcript"], "not archived: OSError('disk full')")
        self.assertEqual(self.load("result.json")["evidence"]["transcript"], "not archived: OSError('disk full')")

    def test_a_failure_to_record_a_failure_keeps_the_original_error(self):  # RPK3
        real = rc.write_exclusive

        def failing(path, content, binary=False):
            if str(path).endswith((".stdout.json", ".failure.json")):
                raise OSError("disk full")
            return real(path, content, binary)

        timeout = subprocess.TimeoutExpired("claude.exe", 60, output=b"partial", stderr=b"err")
        with mock.patch.object(rc, "write_exclusive", side_effect=failing):
            with self.assertRaises(subprocess.TimeoutExpired) as caught:
                self.go(launch=FakeLaunch(self.root / "projects", fail=timeout))
        self.assertTrue(any("recording the failure also failed" in n for n in caught.exception.__notes__))
        self.assertEqual(self.evidence(), ["p.preflight.json", "p.stderr.txt", "p.transcript.jsonl"])


if __name__ == "__main__":
    unittest.main()
