# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/verify_sandbox_derivation.py (GPT-6's round-2 AC9 finding on the sandbox plan). Synthetic repositories only.
# license: MIT (LICENSE-CODE)
"""Offline tests for the sandbox derivation check. Run: python -m unittest tools/test_verify_sandbox_derivation.py"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_sandbox_derivation as vd  # noqa: E402

FORM_SRC = HERE.parent / vd.FORM


class Derivation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("config", "user.email", "t@example.invalid")
        self.git("config", "user.name", "t")
        self.put(vd.WORKFLOW_SRC, b"name: x\n")
        self.put(vd.MANIFEST, b"---\ncloses_utc: '2026-10-26T23:59:59Z'\ncandidates: [{id: p014, path: a}]\n---\n\nx\n")
        (self.repo / vd.FORM).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(FORM_SRC, self.repo / vd.FORM)
        self.put("tools/validate.py", b"print(1)\n")
        self.reviewed = self.commit("reviewed")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, check=True).stdout.decode()

    def put(self, rel, data):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg)
        return self.git("rev-parse", "HEAD").strip()

    def derive(self, extra=None):
        self.put(vd.WORKFLOW_DST, (self.repo / vd.WORKFLOW_SRC).read_bytes())
        self.put(vd.MANIFEST, b"---\ncloses_utc: '2026-12-01T00:00:00Z'\ncandidates: [{id: p001, path: b}]\n---\n\ny\n")
        form = (self.repo / vd.FORM).read_text(encoding="utf-8")
        self.put(vd.FORM, form.replace("1ea6bf4cdae494d4198e81d5cfb07f0cc0e46d0d", "f" * 40).encode("utf-8"))
        if extra:
            extra()
        return self.commit("sandbox")

    def test_the_allowlisted_derivation_passes(self):
        self.assertEqual(vd.problems(self.repo, self.reviewed, self.derive()), [])

    def test_any_other_change_is_refused(self):
        cases = {"a tool": lambda: self.put("tools/validate.py", b"print(2)\n"),
                 "a new file": lambda: self.put("tools/extra.py", b"x\n"),
                 "a workflow edit": lambda: self.put(vd.WORKFLOW_DST, b"name: y\n"),
                 "another form change": lambda: self.put(vd.FORM, (self.repo / vd.FORM).read_bytes().replace(
                     b"Round 3 response", b"Round 3 answer", 1))}
        for name, change in cases.items():
            with self.subTest(name=name):
                self.git("reset", "-q", "--hard", self.reviewed)
                self.assertTrue(vd.problems(self.repo, self.reviewed, self.derive(change)))


if __name__ == "__main__":
    unittest.main()
