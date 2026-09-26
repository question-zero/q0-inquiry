# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: GPT-6's AC9 (critiques/2026-09-26-gpt-6--automation-code-review.md): a committed, synthetic-only parity check that the classify() refactor of tools/extract_round_03_assessments.py preserves the old extractor's output. The expected output in tools/fixtures/extract_round_03_parity.json was produced by the extractor as it stood before the refactor (main at ace25c0), with full and short commit hashes normalized, by `python tools/test_extract_round_03_parity.py --regenerate <path to the old extractor>`.
# license: MIT (LICENSE-CODE)
"""Parity of the refactored extractor with the old one. Run: python -m unittest tools/test_extract_round_03_parity.py

The answers below are synthetic edge cases. Each is committed as a response with a bound receipt in a small tagged
repository; extraction's files, notes and table are compared with the fixture, after replacing every 40-character
commit hash with a placeholder (the hashes differ from run to run).
"""
import hashlib
import importlib.util
import io
import json
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "extract_round_03_parity.json"
CANDS = [{"id": f"p{n:03d}", "path": f"propositions/p{n:03d}.md"} for n in (4, 14, 15, 16, 17, 18, 19, 20, 21,
                                                                            22, 23, 24, 25)]
B = "p{}\nPosition: {}\nConditions: {}\nBasis: {}\n"
BODIES = {
    "all-support": "\n".join(B.format(c["id"][1:], "support", "none", "r") for c in CANDS),
    "mixed": B.format("014", "conditional", "if x", "b") + "\n" + B.format("019", "reject", "none", "b")
             + "\n## Questions\n\nq001\nanswer\n",
    "conflict": B.format("014", "support", "none", "a") + "\n" + B.format("014", "reject", "none", "b"),
    "bad-position": "p015\nPosition: support, mostly\nBasis: x\n",
    "no-basis": "p016\nPosition: support\nConditions: none\n",
    "cond-none": "p017\nPosition: conditional\nConditions: none\nBasis: x\n",
    "dup-label": "p018\nPosition: support\nBasis: a\nBasis: b\n",
    "text-before": "p021\n\nPosition: support\nBasis: x\n",
    "non-candidate": B.format("001", "support", "none", "x") + "\n" + B.format("099", "support", "none", "x"),
    "decorated": "### **p022**\n**Position:** uncertain\n**Conditions:** none\n**Basis:** multi\nline\n\npara\n---\nafter\n",
    "trailing-absorb": B.format("023", "support", "none", "x") + "q002\nthis is absorbed\n",
    "fenced": "```\np024\nPosition: support\nBasis: in fence\n```\n",
    "empty": "",
    "unicode": "p025\nPosition: support\nConditions: none\nBasis: é 漢字 — ok\n",
    "rewording": "p004\nPosition: conditional\nConditions: if y\nBasis: z\nRewording: say it better\n",
    "quoted": "> p019\n> Position: reject\n> Conditions: none\n> Basis: quoted\n",
}


def build_repo(root):
    def git(*a):
        return subprocess.run(["git", "-C", str(root), *a], capture_output=True, check=True).stdout.decode()
    git("init", "-q")
    git("config", "user.email", "t@example.invalid")
    git("config", "user.name", "t")
    (root / "rounds/03-open/responses").mkdir(parents=True)
    (root / "rounds/03-open/prompt.md").write_bytes(   # explicit LF bytes: no dependence on git's newline settings
        ("---\n" + yaml.safe_dump({"closes_utc": "2026-10-26T23:59:59Z", "candidates": CANDS}) + "---\n\nx\n")
        .encode("utf-8"))
    (root / "rounds/03-open/responses/.keep").write_bytes(b"")
    git("add", "-A")
    git("commit", "-qm", "launch")
    git("tag", "round/03-open/v1")
    launch = git("rev-parse", "HEAD").strip()
    for slug, body in BODIES.items():
        fm = {"author": "T", "input_set": f"round/03-open/v1 @ {launch}", "date": "2026-10-01"}
        rel = f"rounds/03-open/responses/{slug}.md"
        (root / rel).write_bytes(("---\n" + yaml.safe_dump(fm) + "---\n\n" + body).encode("utf-8"))
        git("add", "-A")
        git("commit", "-qm", slug)
        head = git("rev-parse", "HEAD").strip()
        fm["receipt"] = {"route": "pull request #1", "created_utc": "2026-10-01T00:00:00Z", "on_time": True,
                         "captured_commit": head, "captured_evidence": "synthetic"}
        (root / rel).write_bytes(("---\n" + yaml.safe_dump(fm) + "---\n\n" + body).encode("utf-8"))
        git("add", "-A")
        git("commit", "-qm", slug + " receipt")


def normalized(extractor, root):
    with redirect_stdout(io.StringIO()):
        files, notes, table = extractor.extract(root)
    def hide(s):  # full and short (backticked, 7-character) commit hashes differ from run to run
        return re.sub(r"`[0-9a-f]{7}`", "`<short>`", re.sub(r"\b[0-9a-f]{40}\b", "<commit>", s))
    return {"files": {k: hashlib.sha256(hide(t).encode("utf-8")).hexdigest() for k, t in sorted(files.items())},
            "notes": [[hide(str(x)) for x in n] for n in notes],
            "table": [[slug, row] for slug, row in table]}


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Parity(unittest.TestCase):
    def test_the_refactored_extractor_reproduces_the_old_output(self):
        expected = json.loads(FIXTURE.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as td:
            build_repo(Path(td))
            got = normalized(load("new_extract", HERE / "extract_round_03_assessments.py"), Path(td))
        self.assertEqual(got, expected)
        self.assertGreater(len(expected["files"]), 10)
        self.assertGreater(len(expected["notes"]), 5)


if __name__ == "__main__":
    if sys.argv[1:2] == ["--regenerate"]:
        with tempfile.TemporaryDirectory() as td:
            build_repo(Path(td))
            out = normalized(load("old_extract", sys.argv[2]), Path(td))
        FIXTURE.parent.mkdir(exist_ok=True)
        FIXTURE.write_bytes((json.dumps(out, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print(f"wrote {FIXTURE}: {len(out['files'])} files, {len(out['notes'])} notes")
    else:
        unittest.main()
