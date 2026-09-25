# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Offline tests for tools/build_index.py, covering GPT-6 IX1 (a renamed proposition's assessments stay visible and are never retargeted) and IX2 (exposure made explicit).
# license: MIT (LICENSE-CODE)
"""Offline tests for build_index.py. Run: python -m unittest tools/test_build_index.py

A fake repository stands in for git: every read goes through build_index.git.
"""
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_index as bi  # noqa: E402

COMMIT = "c" * 40


def fm(**fields):
    return "---\n" + "".join(f"{k}: {v}\n" for k, v in fields.items()) + "---\n\nbody\n"


def assessment(target, pid, position, packet=None):
    extra = {"input_set": "{packet: " + packet + "}"} if packet else {}
    return fm(type="critique", subtype="assessment", target=f"'{target}'", participant_id=pid, position=position,
              developer="Dev", model="m-1", round="02-deliberation", **extra)


class FakeRepo:
    def __init__(self, files):
        self.files = files

    def __call__(self, *args):
        if args[0] == "rev-parse":
            return COMMIT + "\n"
        if args[:2] == ("ls-tree", "--name-only"):
            folder = args[2].split(":", 1)[1]
            names = sorted({p[len(folder) + 1:] for p in self.files if p.startswith(folder + "/")})
            if not names:
                raise subprocess.CalledProcessError(128, ["git", *args])
            return "\n".join(names) + "\n"
        if args[0] == "show":
            return self.files[args[1].split(":", 1)[1]]
        raise AssertionError(args)


def build(files):
    with mock.patch.object(bi, "git", FakeRepo(files)):
        return bi.build("HEAD")


class Index(unittest.TestCase):
    def test_a_renamed_propositions_assessments_stay_visible_and_are_not_retargeted(self):  # IX1
        old = "propositions/p001-old.md @ " + "a" * 40
        out = build({
            "propositions/p001-renamed.md": fm(type="proposition", id="p001", title="'p001: renamed'", lifecycle="draft"),
            "critiques/x--assessment-p001.md": assessment(old, "model-a/1", "support"),
        })
        self.assertIn("## Assessments of other paths", out)
        self.assertIn("### `propositions/p001-old.md`", out)
        self.assertIn(f"**Version assessed:** `{old}`", out)
        self.assertEqual(out.count("critiques/x--assessment-p001.md"), 1)
        self.assertIn("none; an earlier path with this ID has assessments", out)
        self.assertIn("No assessments target this path.", out)
        self.assertNotIn("propositions/p001-renamed.md @", out)

    def test_every_assessment_appears_exactly_once(self):  # IX1
        target = "propositions/p001-a.md @ " + "b" * 40
        files = {"propositions/p001-a.md": fm(type="proposition", id="p001", title="'p001: a'", lifecycle="draft")}
        for i in range(3):
            files[f"critiques/a{i}--assessment-p001.md"] = assessment(target, f"model-{i}/{i}", "conditional")
        files["critiques/gone--assessment-p009.md"] = assessment("propositions/p009-removed.md @ " + "d" * 40,
                                                                 "model-9/9", "reject")
        out = build(files)
        for path in files:
            if path.startswith("critiques/"):
                self.assertEqual(out.count(f"]({path})"), 1, path)

    def test_rows_show_the_packet_and_label_the_exposure_link(self):  # IX2
        target = "propositions/p001-a.md @ " + "b" * 40
        out = build({
            "propositions/p001-a.md": fm(type="proposition", id="p001", title="'p001: a'", lifecycle="draft"),
            "critiques/a--assessment-p001.md": assessment(target, "model-a/1", "support",
                                                          packet="rounds/02-x/packets/model-a.md"),
            "critiques/b--assessment-p001.md": assessment(target, "model-b/2", "reject"),
        })
        self.assertIn("| Conditions, basis and exposure |", out)
        self.assertIn("[model-a.md](rounds/02-x/packets/model-a.md)", out)
        self.assertIn("| none recorded |", out)
        self.assertIn("its exposure", out)

    def test_no_counts_or_totals(self):
        target = "propositions/p001-a.md @ " + "b" * 40
        files = {"propositions/p001-a.md": fm(type="proposition", id="p001", title="'p001: a'", lifecycle="draft")}
        for i in range(4):
            files[f"critiques/a{i}--assessment-p001.md"] = assessment(target, f"model-{i}/{i}", "support")
        out = build(files)
        for word in ("total", "count:", "majority", "4 support", "support: 4"):
            self.assertNotIn(word, out.lower().replace("nothing here is counted", ""))

    def test_the_generator_refuses_to_omit_an_assessment(self):  # IX1
        target = "propositions/p001-a.md @ " + "b" * 40
        files = {"propositions/p001-a.md": fm(type="proposition", id="p001", title="'p001: a'", lifecycle="draft"),
                 "critiques/a--assessment-p001.md": assessment(target, "model-a/1", "support")}
        real_sorted = sorted
        calls = {"n": 0}

        def dropping_sorted(it, *a, **k):
            result = real_sorted(it, *a, **k)
            calls["n"] += 1
            if result and isinstance(result[0], tuple) and len(result[0]) == 7:
                return result[1:]  # simulate a rendering bug that loses a row
            return result

        with mock.patch.object(bi, "sorted", dropping_sorted, create=True):
            with self.assertRaises(SystemExit):
                build(files)

    def test_tree_mode_reads_the_working_tree_and_matches_commit_mode(self):  # launch export
        import tempfile
        target = "propositions/p001-a.md @ " + "b" * 40
        files = {"propositions/p001-a.md": fm(type="proposition", id="p001", title="'p001: a'", lifecycle="draft"),
                 "questions/q001-a.md": fm(type="question", id="q001", title="'q001: a'", lifecycle="draft"),
                 "critiques/a--assessment-p001.md": assessment(target, "model-a/1", "support", "rounds/x/p.md")}
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for p, text in files.items():
                (root / p).parent.mkdir(parents=True, exist_ok=True)
                (root / p).write_text(text, encoding="utf-8")
            with mock.patch.object(bi, "git", side_effect=AssertionError("tree mode must not call git")):
                tree = bi.build(None, root=root)
        by_commit = build(files)
        self.assertTrue(tree.startswith("Generated by tools/build_index.py from the working tree."))
        self.assertEqual(tree.split("\n", 1)[1], by_commit.split("\n", 1)[1])


if __name__ == "__main__":
    unittest.main()
