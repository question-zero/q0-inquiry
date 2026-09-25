# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Offline tests for tools/extract_round_03_assessments.py, covering the fixture the Round 3 launch package requires (proposals/2026-09-25-claude-opus-5-5-round-3-launch.md, "Extraction"). Synthetic data only.
# license: MIT (LICENSE-CODE)
"""Offline tests for extract_round_03_assessments.py. Run: python -m unittest tools/test_extract_round_03.py

Each test builds a small git repository with a tagged Round 3 manifest and synthetic responses.
"""
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_round_03_assessments as ex  # noqa: E402

CANDIDATES = [{"id": "p014", "path": "propositions/p014-a.md"}, {"id": "p099", "path": "propositions/p099-new.md"}]


def response(input_set, receipt, body, **extra):
    fm = {"type": "round-response", "title": "Round 3 response: X", "author": "Ada", "model": "human",
          "developer": "not applicable", "participant_id": "human/ada", "run": "this response", "setup": "none",
          "operator": "human/ada", "submitting_account": "ada-gh", "rights": "the author grants CC BY 4.0",
          "attribution": "self-declared", "date": "2026-10-01", "prompt": "the Round 3 participant text",
          "round": "03-open", "input_set": input_set, "exposure": ["none"], "human_interventions": "none",
          "samples": {"generated": 1, "submitted": 1}, "lifecycle": "active"}
    fm.update(extra)
    if receipt is not None:
        fm["receipt"] = receipt
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n" + body


ON_TIME = {"route": "pull request #1", "created_utc": "2026-10-01T10:00:00Z", "on_time": True}
LATE = {"route": "issue #9", "created_utc": "2026-10-27T01:00:00Z", "on_time": False}


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        manifest = {"type": "round-prompt", "round": "03-open", "input_set": ["x"], "candidates": CANDIDATES}
        self.put("rounds/03-open/prompt.md", "---\n" + yaml.safe_dump(manifest) + "---\n\n# manifest\n")
        self.put("rounds/03-open/responses/.keep", "")
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "launch")
        self.git("tag", "round/03-open/v1")
        self.launch = self.git("rev-parse", "HEAD").strip()
        self.good_set = f"round/03-open/v1 @ {self.launch}"

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, check=True).stdout.decode()

    def put(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def commit_responses(self, **responses):
        for slug, text in responses.items():
            self.put(f"rounds/03-open/responses/{slug}.md", text)
        self.git("add", "-A")
        self.git("commit", "-q", "-m", "responses")

    def run_extract(self):
        with redirect_stdout(io.StringIO()):
            return ex.extract(self.repo)


class Fixture(Base):
    def test_the_launch_package_fixture(self):
        self.commit_responses(**{
            # another language in the reasons, English labels; a new candidate ID left out (partial answer)
            "human-ada": response(self.good_set, ON_TIME,
                                  "## Assessments\n\np014\nPosition: support\nConditions: none\n"
                                  "Basis: La razón está en el texto.\n"),
            # a duplicated block, and a conditional without conditions
            "model-b": response(self.good_set, ON_TIME,
                                "p014\nPosition: reject\nConditions: none\nBasis: one\n\n"
                                "p014\nPosition: support\nConditions: none\nBasis: two\n\n"
                                "p099\nPosition: conditional\nConditions: none\nBasis: needs a change\n"),
            "late-c": response(self.good_set, LATE, "p014\nPosition: support\nConditions: none\nBasis: late\n"),
            "wrong-d": response("round/03-open/v1 @ " + "0" * 40, ON_TIME,
                                "p014\nPosition: support\nConditions: none\nBasis: wrong commit\n"),
        })
        files, notes, table = self.run_extract()
        self.assertEqual(sorted(files), ["critiques/2026-10-01-human-ada--round-3-assessment-p014.md"])
        rows = dict(table)
        self.assertEqual(rows["human-ada"], {"p014": "support", "p099": "not assessed"})
        self.assertEqual(rows["model-b"], {"p014": "conflicting", "p099": "incomplete"})
        kinds = {(n[0], n[1], n[2]) for n in notes}
        self.assertIn(("late-c", "-", "late"), kinds)
        self.assertIn(("wrong-d", "-", "wrong input set"), kinds)
        self.assertIn(("model-b", "p014", "conflicting"), kinds)
        self.assertIn(("model-b", "p099", "incomplete"), kinds)

    def test_an_assessment_file_targets_the_tag_and_copies_its_provenance(self):
        self.commit_responses(**{"human-ada": response(self.good_set, ON_TIME,
                                                       "p099\nPosition: conditional\nConditions: if revised\n"
                                                       "Basis: reasons\nRewording: better words\n")})
        files, _, _ = self.run_extract()
        text = files["critiques/2026-10-01-human-ada--round-3-assessment-p099.md"]
        fm = yaml.safe_load(text.split("---\n", 2)[1])
        self.assertEqual(fm["target"], f"propositions/p099-new.md @ {self.launch}")
        self.assertEqual(fm["position"], "conditional")
        self.assertEqual(fm["conditions"], "if revised")
        self.assertEqual(fm["rewording"], "better words")
        self.assertEqual(fm["submitting_account"], "ada-gh")
        self.assertEqual(fm["rights"], "the author grants CC BY 4.0")
        self.assertEqual(fm["receipt"], ON_TIME)
        self.assertIn("Position: conditional", text)  # the block is reproduced verbatim

    def test_a_response_without_a_receipt_is_not_extracted(self):
        self.commit_responses(**{"human-ada": response(self.good_set, None,
                                                       "p014\nPosition: support\nConditions: none\nBasis: x\n")})
        files, notes, _ = self.run_extract()
        self.assertEqual(files, {})
        self.assertIn("no receipt", {n[2] for n in notes})

    def test_an_id_outside_the_candidate_list_is_reported(self):
        self.commit_responses(**{"human-ada": response(self.good_set, ON_TIME,
                                                       "p001\nPosition: support\nConditions: none\nBasis: old\n")})
        files, notes, _ = self.run_extract()
        self.assertEqual(files, {})
        self.assertIn(("human-ada", "p001", "not a candidate"), {(n[0], n[1], n[2]) for n in notes})


class Check(Base):
    def test_check_passes_after_writing_and_fails_after_an_edit(self):
        self.commit_responses(**{"human-ada": response(self.good_set, ON_TIME,
                                                       "p014\nPosition: support\nConditions: none\nBasis: x\n")})
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ex.main([], repo=self.repo), 0)
            self.assertEqual(ex.main(["--check"], repo=self.repo), 0)
        out = self.repo / "critiques/2026-10-01-human-ada--round-3-assessment-p014.md"
        out.write_bytes(out.read_bytes() + b"edited\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ex.main(["--check"], repo=self.repo), 1)


if __name__ == "__main__":
    unittest.main()
