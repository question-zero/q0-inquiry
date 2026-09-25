# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Offline tests for tools/extract_round_03_assessments.py, covering the fixture the Round 3 launch package requires (proposals/2026-09-25-claude-opus-5-5-round-3-launch.md, "Extraction"). Synthetic data only. Revision 2 adds GPT-6's R3L1-R3L3 cases (topic round-3-launch): a stale output, contradictory and incomplete receipts, the capture binding, and preserved provenance.
# license: MIT (LICENSE-CODE)
"""Offline tests for extract_round_03_assessments.py. Run: python -m unittest tools/test_extract_round_03.py

Each test builds a small git repository with a tagged Round 3 manifest and synthetic responses. A pull request is
simulated the way intake works: the participant's version is committed, then the editor adds the receipt, which
names that commit as the version captured at the close.
"""
import hashlib
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
CLOSES = "2026-10-26T23:59:59Z"
BEFORE, AFTER = "2026-10-01T10:00:00Z", "2026-10-27T01:00:00Z"


def front(input_set, **extra):
    fm = {"type": "round-response", "title": "Round 3 response: X", "author": "Ada", "model": "human",
          "developer": "not applicable", "participant_id": "human/ada", "run": "this response", "setup": "none",
          "operator": "human/ada", "submitting_account": "ada-gh", "rights": "the author grants CC BY 4.0",
          "attribution": "self-declared", "date": "2026-10-01", "prompt": "the Round 3 participant text",
          "round": "03-open", "input_set": input_set, "exposure": ["none"], "human_interventions": "none",
          "samples": {"generated": 1, "submitted": 1}, "lifecycle": "active"}
    fm.update(extra)
    return fm


def render(fm, body):
    return "---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n" + body


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        manifest = {"type": "round-prompt", "round": "03-open", "input_set": ["x"], "closes_utc": CLOSES,
                    "candidates": CANDIDATES}
        self.put("rounds/03-open/prompt.md", "---\n" + yaml.safe_dump(manifest) + "---\n\n# manifest\n")
        self.put("rounds/03-open/responses/.keep", "")
        self.commit("launch")
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

    def commit(self, message):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)
        return self.git("rev-parse", "HEAD").strip()

    def pull_request(self, slug, body, created=BEFORE, on_time=True, input_set=None, **extra):
        """The participant's version is committed; the editor then adds a receipt capturing that commit."""
        rel = f"rounds/03-open/responses/{slug}.md"
        fm = front(input_set or self.good_set, **extra)
        self.put(rel, render(fm, body))
        head = self.commit(f"{slug}: the participant's version")
        fm["receipt"] = {"route": "pull request #1", "created_utc": created, "on_time": on_time,
                         "captured_commit": head}
        self.put(rel, render(fm, body))
        self.commit(f"{slug}: receipt")
        return rel

    def issue(self, slug, body, created=BEFORE, on_time=True, digest=None):
        rel = f"rounds/03-open/responses/{slug}.md"
        fm = front(self.good_set)
        fm["receipt"] = {"route": "issue #7", "created_utc": created, "on_time": on_time,
                         "captured_sha256": digest or hashlib.sha256(body.encode("utf-8")).hexdigest()}
        self.put(rel, render(fm, body))
        self.commit(f"{slug}: relayed from an issue")
        return rel

    def run_extract(self):
        with redirect_stdout(io.StringIO()):
            return ex.extract(self.repo)

    def kinds(self, notes):
        return {(n[0], n[1], n[2]) for n in notes}


BLOCK = "p014\nPosition: support\nConditions: none\nBasis: reasons\n"


class Fixture(Base):
    def test_the_launch_package_fixture(self):
        # another language in the reasons, English labels; a new candidate ID left out (a partial answer)
        self.pull_request("human-ada", "## Assessments\n\np014\nPosition: support\nConditions: none\n"
                                       "Basis: La razón está en el texto.\n")
        # a duplicated block, and a conditional without conditions
        self.pull_request("model-b", "p014\nPosition: reject\nConditions: none\nBasis: one\n\n"
                                     "p014\nPosition: support\nConditions: none\nBasis: two\n\n"
                                     "p099\nPosition: conditional\nConditions: none\nBasis: needs a change\n")
        self.pull_request("late-c", BLOCK, created=AFTER, on_time=False)
        self.pull_request("wrong-d", BLOCK, input_set="round/03-open/v1 @ " + "0" * 40)
        files, notes, table = self.run_extract()
        self.assertEqual(sorted(files), ["critiques/2026-10-01-human-ada--round-3-assessment-p014.md"])
        rows = dict(table)
        self.assertEqual(rows["human-ada"], {"p014": "support", "p099": "not assessed"})
        self.assertEqual(rows["model-b"], {"p014": "conflicting", "p099": "incomplete"})
        k = self.kinds(notes)
        self.assertIn(("late-c", "-", "late"), k)
        self.assertIn(("wrong-d", "-", "wrong input set"), k)
        self.assertIn(("model-b", "p014", "conflicting"), k)
        self.assertIn(("model-b", "p099", "incomplete"), k)

    def test_an_assessment_file_targets_the_tag_and_copies_its_provenance(self):  # GPT-6 R3L3
        self.pull_request("model-e", "p099\nPosition: conditional\nConditions: if revised\n"
                                     "Basis: reasons\nRewording: better words\n",
                          samples={"generated": 7, "submitted": 1},
                          human_interventions="the operator rewrote one sentence of the basis",
                          attribution="reported")
        files, _, _ = self.run_extract()
        text = files["critiques/2026-10-01-model-e--round-3-assessment-p099.md"]
        fm = yaml.safe_load(text.split("---\n", 2)[1])
        self.assertEqual(fm["target"], f"propositions/p099-new.md @ {self.launch}")
        self.assertEqual((fm["position"], fm["conditions"], fm["rewording"]), ("conditional", "if revised",
                                                                              "better words"))
        self.assertEqual(fm["samples"], {"generated": 7, "submitted": 1})
        self.assertEqual(fm["human_interventions"], "the operator rewrote one sentence of the basis")
        self.assertEqual(fm["attribution"], "reported")
        self.assertIn("extraction", fm)
        self.assertEqual(fm["submitting_account"], "ada-gh")
        self.assertIn("Position: conditional", text)  # the block is reproduced verbatim

    def test_an_id_outside_the_candidate_list_is_reported(self):
        self.pull_request("human-ada", "p001\nPosition: support\nConditions: none\nBasis: old\n")
        files, notes, _ = self.run_extract()
        self.assertEqual(files, {})
        self.assertIn(("human-ada", "p001", "not a candidate"), self.kinds(notes))


class Replacement(Base):  # GPT-6 R3L2: a change after capture is a replacement, never an edit
    def test_only_the_replacing_response_is_extracted(self):
        old = self.pull_request("human-ada", BLOCK)
        self.pull_request("human-ada-2", BLOCK.replace("support", "reject"), replaces=old)
        files, notes, _ = self.run_extract()
        self.assertEqual(sorted(files), ["critiques/2026-10-01-human-ada-2--round-3-assessment-p014.md"])
        self.assertIn(("human-ada", "-", "replaced"), self.kinds(notes))


class Receipts(Base):  # GPT-6 R3L2
    def write_with(self, slug, receipt):
        rel = f"rounds/03-open/responses/{slug}.md"
        fm = front(self.good_set)
        if receipt is not None:
            fm["receipt"] = receipt
        self.put(rel, render(fm, BLOCK))
        self.commit(slug)

    def test_missing_bare_and_contradictory_receipts_are_refused(self):
        self.write_with("none-a", None)
        self.write_with("bare-b", {"on_time": True})
        self.write_with("contra-c", {"route": "issue #3", "created_utc": AFTER, "on_time": True,
                                     "captured_sha256": hashlib.sha256(BLOCK.encode()).hexdigest()})
        self.write_with("badtime-d", {"route": "issue #4", "created_utc": "yesterday", "on_time": True})
        files, notes, _ = self.run_extract()
        self.assertEqual(files, {})
        k = self.kinds(notes)
        self.assertIn(("none-a", "-", "no receipt"), k)
        self.assertIn(("bare-b", "-", "incomplete receipt"), k)
        self.assertIn(("contra-c", "-", "contradictory receipt"), k)
        self.assertIn(("badtime-d", "-", "incomplete receipt"), k)

    def test_a_pull_request_is_bound_to_its_captured_version(self):
        rel = self.pull_request("human-ada", BLOCK)
        self.assertEqual(len(self.run_extract()[0]), 1)
        text = (self.repo / rel).read_text(encoding="utf-8")
        self.put(rel, text.replace("Basis: reasons", "Basis: changed after the close"))
        self.commit("an edit after capture")
        files, notes, _ = self.run_extract()
        self.assertEqual(files, {})
        self.assertIn(("human-ada", "-", "unbound receipt"), self.kinds(notes))

    def test_an_issue_is_bound_to_its_captured_text(self):
        self.issue("issue-ok", BLOCK)
        self.issue("issue-bad", BLOCK, digest="0" * 64)
        files, notes, _ = self.run_extract()
        self.assertEqual(sorted(files), ["critiques/2026-10-01-issue-ok--round-3-assessment-p014.md"])
        self.assertIn(("issue-bad", "-", "unbound receipt"), self.kinds(notes))


class Check(Base):
    def test_check_passes_after_writing_and_fails_after_an_edit(self):
        self.pull_request("human-ada", BLOCK)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ex.main([], repo=self.repo), 0)
            self.assertEqual(ex.main(["--check"], repo=self.repo), 0)
        out = self.repo / "critiques/2026-10-01-human-ada--round-3-assessment-p014.md"
        out.write_bytes(out.read_bytes() + b"edited\n")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ex.main(["--check"], repo=self.repo), 1)

    def test_check_fails_on_an_assessment_that_is_no_longer_extractable(self):  # GPT-6 R3L1
        rel = self.pull_request("human-ada", BLOCK)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(ex.main([], repo=self.repo), 0)
        self.commit("the assessment file")
        text = (self.repo / rel).read_text(encoding="utf-8")
        self.put(rel, text.replace(f"created_utc: '{BEFORE}'", f"created_utc: '{AFTER}'")
                 .replace("on_time: true", "on_time: false"))
        self.commit("the receipt is corrected: late")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(ex.main(["--check"], repo=self.repo), 1)
        self.assertIn("STALE critiques/2026-10-01-human-ada--round-3-assessment-p014.md", buf.getvalue())
        self.assertTrue((self.repo / "critiques/2026-10-01-human-ada--round-3-assessment-p014.md").exists())


if __name__ == "__main__":
    unittest.main()
