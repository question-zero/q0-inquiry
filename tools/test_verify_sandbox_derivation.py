# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/verify_sandbox_derivation.py (GPT-6's round-2 and round-3 AC9 findings on the sandbox plan): the R, T, D chain, the tag's target, the manifest's candidates and hash, the form's exact default, and the refusal of every other change, including the negative fixtures GPT-6 named (activation only, an arbitrary default, an extra comment in the form). Synthetic repositories only.
# license: MIT (LICENSE-CODE)
"""Offline tests for the sandbox derivation check. Run: python -m unittest tools/test_verify_sandbox_derivation.py"""
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_sandbox_derivation as vd  # noqa: E402

FORM_SRC = HERE.parent / vd.FORM
TEXT = "\nSandbox round text.\n"


def manifest(n=3, text=TEXT, good_hash=True):
    front = {"closes_utc": "2026-12-01T00:00:00Z",
             "candidates": [{"id": f"p{900 + i}", "path": f"x{i}"} for i in range(n)],
             "participant_text_sha256": hashlib.sha256(text.encode()).hexdigest() if good_hash else "0" * 64,
             "participant_text_bytes": len(text.encode())}
    return ("---\n" + yaml.safe_dump(front) + "---\n\n<!-- BEGIN PARTICIPANT TEXT -->" + text
            + "<!-- END PARTICIPANT TEXT -->\n").encode("utf-8")


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
        self.r = self.commit("reviewed")

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
        self.git("commit", "-q", "--allow-empty", "-m", msg)
        return self.git("rev-parse", "HEAD").strip()

    def chain(self, t_change=None, d_change=None, form_default=None, tag_at=None, n=3, good_hash=True):
        self.git("reset", "-q", "--hard", self.r)
        self.git("tag", "-d", vd.TAG) if vd.TAG in self.git("tag") else None
        self.put(vd.MANIFEST, manifest(n=n, good_hash=good_hash))
        if t_change:
            t_change()
        t = self.commit("T")
        self.put(vd.WORKFLOW_DST, (self.repo / vd.WORKFLOW_SRC).read_bytes())
        form = (self.repo / vd.FORM).read_text(encoding="utf-8")
        self.put(vd.FORM, form.replace("1ea6bf4cdae494d4198e81d5cfb07f0cc0e46d0d", form_default or t).encode("utf-8"))
        if d_change:
            d_change()
        d = self.commit("D")
        self.git("tag", vd.TAG, tag_at or t)
        return t, d

    def test_the_exact_chain_passes(self):
        t, d = self.chain()
        self.assertEqual(vd.problems(self.repo, self.r, t, d), [])

    def test_every_other_derivation_is_refused(self):
        cases = {
            "a tool changed in D": dict(d_change=lambda: self.put("tools/validate.py", b"print(2)\n")),
            "a tool changed in T": dict(t_change=lambda: self.put("tools/validate.py", b"print(2)\n")),
            "a new file": dict(d_change=lambda: self.put("tools/extra.py", b"x\n")),
            "a workflow edit": dict(d_change=lambda: self.put(vd.WORKFLOW_DST, b"name: y\n")),
            "an arbitrary default": dict(form_default="f" * 40),
            "an extra comment in the form": dict(d_change=lambda: self.put(
                vd.FORM, (self.repo / vd.FORM).read_bytes() + b"# extra\n")),
            "the tag elsewhere": dict(tag_at=self.r),
            "two candidates": dict(n=2),
            "a wrong text hash": dict(good_hash=False),
        }
        for name, kw in cases.items():
            with self.subTest(name=name):
                t, d = self.chain(**kw)
                self.assertTrue(vd.problems(self.repo, self.r, t, d))

    def test_activation_only_is_refused(self):
        self.git("reset", "-q", "--hard", self.r)
        self.put(vd.WORKFLOW_DST, (self.repo / vd.WORKFLOW_SRC).read_bytes())
        d = self.commit("activation only")
        self.git("tag", "-f", vd.TAG, self.r)
        self.assertTrue(vd.problems(self.repo, self.r, self.r, d))


if __name__ == "__main__":
    unittest.main()
