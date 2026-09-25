# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Offline tests for tools/run_moderation_alternate.py (the moderation alternate the founder chose, verbatim: "Grok 4.7, Gemini as backup (Recommended)"; revision 2 follows the change, verbatim: "Gemini becomes alternate (Recommended)").
# license: MIT (LICENSE-CODE)
"""Offline tests for run_moderation_alternate.py. Run: python -m unittest tools/test_run_moderation_alternate.py

A fake repository stands in for git and a fake transport for the provider. No request leaves the machine.
"""
import argparse
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_local_participant as rl  # noqa: E402
import run_moderation_alternate as ma  # noqa: E402
from test_run_api_participant import GEMINI_STREAM, KEY, FakeHttp  # noqa: E402

CASE = "moderation/2026-09-25-case.md"
TEXT = "\nThe case: a challenge to a removal. ü\n"
COMMIT = "e" * 40


def case_blob(text=TEXT, digest=None):
    return ("---\ntype: moderation\nparticipant_text_sha256: " + (digest or rl.sha256(text)) + "\n---\n\n# Case\n\n"
            + rl.BEGIN + text + rl.END + "\n")


class Alternate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.prefix = Path(self.tmp.name) / "m" / "case"
        self.blob = case_blob()

    def tearDown(self):
        self.tmp.cleanup()

    def go(self, provider="gemini", model="gemini-3.6-flash", case=CASE, http=None):
        args = argparse.Namespace(provider=provider, model=model, case=case, prefix=str(self.prefix), commit="HEAD",
                                  max_output_tokens=None, max_input_tokens=None, keys_file="unused")
        with mock.patch.object(rl, "git_commit", return_value=COMMIT), \
                mock.patch.object(rl, "git_blob", side_effect=lambda c, p: self.blob):
            return ma.run(args, http or FakeHttp(GEMINI_STREAM), key=KEY)

    def files(self):
        folder = self.prefix.parent
        return sorted(p.name for p in folder.iterdir()) if folder.exists() else []

    def test_the_alternate_gets_exactly_the_case_text_and_the_case_is_recorded(self):
        http = FakeHttp(GEMINI_STREAM)
        r = self.go(http=http)
        self.assertEqual(r["answer"], "Hello")
        self.assertEqual(http.body["contents"], [{"role": "user", "parts": [{"text": TEXT}]}])
        case = json.loads(Path(f"{self.prefix}.case.json").read_text(encoding="utf-8"))
        self.assertEqual((case["case"], case["commit"], case["case_text_sha256"], case["role"]),
                         (CASE, COMMIT, rl.sha256(TEXT), "the alternate"))
        self.assertIn("case.case.json", self.files())
        self.assertIn("case.preflight.json", self.files())

    def test_only_the_recorded_alternates_are_accepted(self):
        for provider, model in (("xai", "grok-4.7"), ("xai", "grok-4.6"), ("gemini", "gemini-3.5"),
                                ("modelark", "deepseek-v4-pro-ga-260813")):
            with self.subTest(model=model), self.assertRaises(ValueError):
                self.go(provider, model)
        self.assertEqual(self.files(), [])

    def test_case_paths_outside_moderation_are_refused(self):
        for bad in ("critiques/x.md", "moderation/sub/x.md", "moderation/../protocol.md", "moderation/x.txt", ""):
            with self.subTest(bad), self.assertRaises(ValueError):
                self.go(case=bad)
        self.assertEqual(self.files(), [])

    def test_a_case_whose_text_does_not_match_its_hash_is_refused(self):
        self.blob = case_blob(digest="0" * 64)
        http = FakeHttp(GEMINI_STREAM)
        with self.assertRaisesRegex(ValueError, "hash"):
            self.go(http=http)
        self.assertEqual((http.calls, self.files()), (0, []))

    def test_existing_evidence_refuses_before_any_request(self):
        self.prefix.parent.mkdir(parents=True)
        Path(f"{self.prefix}.case.json").write_text("{}")
        http = FakeHttp(GEMINI_STREAM)
        with self.assertRaises(FileExistsError):
            self.go(http=http)
        self.assertEqual(http.calls, 0)


if __name__ == "__main__":
    unittest.main()
