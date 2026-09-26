# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/validate_round_03_response.py and tools/render_round_03_feedback.py (D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md), covering the fixtures GPT-6 listed for D1 and D2 that apply to code without GitHub: parity with extraction, optional fields and unknowns, partial assessments, unresolved declarations, processing limits, ambiguous form headings, injected markup, Unicode and newlines, and the renderer's schema and source binding. Synthetic data only.
# license: MIT (LICENSE-CODE)
"""Offline tests for the Round 3 advisory feedback. Run: python -m unittest tools/test_validate_round_03.py

Each test builds a small git repository with a tagged manifest (the real candidate IDs are not needed; three
synthetic ones suffice) and the real issue form copied in, then validates synthetic responses.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import extract_round_03_assessments as ex  # noqa: E402
import render_round_03_feedback as rf  # noqa: E402
import validate_round_03_response as v  # noqa: E402

CANDS = [{"id": "p014", "path": "propositions/p014.md"}, {"id": "p019", "path": "propositions/p019.md"},
         {"id": "p025", "path": "propositions/p025.md"}]
SHA = "a" * 40


def block(pid, pos="support", cond="none", basis="reasons"):
    return f"{pid}\nPosition: {pos}\nConditions: {cond}\nBasis: {basis}\n"


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        g = self.git
        g("init", "-q")
        g("config", "user.email", "t@example.invalid")
        g("config", "user.name", "t")
        manifest = {"closes_utc": "2026-10-26T23:59:59Z", "candidates": CANDS}
        self.put("rounds/03-open/prompt.md", "---\n" + yaml.safe_dump(manifest) + "---\n\nx\n")
        form = HERE.parent / v.FORM
        (self.repo / v.FORM).parent.mkdir(parents=True)
        shutil.copy(form, self.repo / v.FORM)
        g("add", "-A")
        g("commit", "-q", "-m", "launch")
        g("tag", "round/03-open/v1")
        self.launch = g("rev-parse", "HEAD").strip()
        self.good_set = f"round/03-open/v1 @ {self.launch}"

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, check=True).stdout.decode()

    def put(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(text.encode("utf-8"))

    def response_file(self, body, **fields):
        fm = {k: "unknown" for k in v.TEMPLATE_FIELDS}
        fm.update({"type": "round-response", "input_set": self.good_set, "rights": "the author grants CC BY 4.0",
                   "samples": {"generated": 1, "submitted": 1}, "exposure": ["none"]})
        fm.update(fields)
        fm = {k: val for k, val in fm.items() if val is not None}
        return ("---\n" + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True) + "---\n\n" + body).encode("utf-8")

    def issue_body(self, answer, input_set=None, rights="the operator grants CC BY 4.0 under the provider's terms",
                   ticks=(True, True, True), relay=None, fence=True):
        input_set = self.good_set if input_set is None else input_set
        form = yaml.safe_load((self.repo / v.FORM).read_text(encoding="utf-8"))
        consent = [i for i in form["body"] if i.get("id") == "consent"][0]["attributes"]["options"]
        values = {"who": "A person, for themselves", "name": "Ada", "input_set": input_set, "model": None,
                  "added_instructions": None, "interventions": "none", "relay": relay, "operator": "human/ada",
                  "rights": rights, "exposure": "none",
                  "answer": ("```markdown\n" + answer + "\n```") if fence else answer}
        out = []
        for item in form["body"]:
            if item["type"] == "markdown":
                continue
            label = item["attributes"]["label"]
            out.append(f"### {label}\n")
            if item["id"] == "consent":
                out.append("\n".join(f"- [{'X' if t else ' '}] {o['label']}" for t, o in zip(ticks, consent)) + "\n")
            else:
                val = values.get(item["id"])
                out.append((val if val is not None else v.NO_RESPONSE) + "\n")
        return "\n".join(out).encode("utf-8")

    def run_file(self, data):
        return v.validate("file", data, 5, SHA, self.repo)

    def run_issue(self, data):
        return v.validate("issue", data, 7, None, self.repo)


class Parity(Base):
    """Feedback statuses must follow extraction's classification exactly, without positions (GA4)."""

    def test_statuses_follow_classify_for_every_case(self):
        bodies = [block("p014") + "\n" + block("p019", "conditional", "if x") + "\n## Questions\n\nq001\nanswer\n",
                  block("p014") + "\n" + block("p014", "reject"),
                  "p014\nPosition: support, mostly\nBasis: x\n",
                  "p019\nPosition: conditional\nConditions: none\nBasis: x\n",
                  "p025\nPosition: support\nConditions: none\n",
                  block("p001") + "\n" + block("p025"),
                  ""]
        ids = [c["id"] for c in CANDS]
        for body in bodies:
            with self.subTest(body=body[:30]):
                r = self.run_file(self.response_file(body))
                _, results, _ = ex.classify(body, ids)
                self.assertEqual(r["assessments"], {pid: v.status_of(res["status"]) for pid, res in results.items()})

    def test_positions_never_appear(self):
        r = self.run_file(self.response_file(block("p014", "reject") + "\n" + block("p019", "uncertain")))
        text = json.dumps(r)
        for word in ("support", "reject", "conditional", "uncertain"):
            self.assertNotIn(word, text)
        self.assertEqual(r["assessments"]["p014"], "read")


class Declarations(Base):
    def test_partial_answer_is_valid_and_optional_fields_may_be_empty(self):
        r = self.run_issue(self.issue_body(block("p014")))
        self.assertTrue(r["checked"])
        self.assertEqual(r["counts"]["read"], 1)
        self.assertEqual(r["counts"]["not_assessed"], 2)
        self.assertFalse([c for c in r["codes"] if c.startswith("form_field_missing")])

    def test_unresolved_rights_and_unticked_boxes_are_intake_matters_not_format_errors(self):
        r = self.run_issue(self.issue_body(block("p014"), rights="unknown as to basis", ticks=(False, False, True)))
        self.assertTrue(r["checked"])
        self.assertTrue({"rights_unresolved", "grant_box_unticked", "consent_box_unticked"} <= set(r["codes"]))
        self.assertNotIn("never_post_box_unticked", r["codes"])

    def test_unknown_values_are_permitted_in_a_file(self):
        r = self.run_file(self.response_file(block("p014")))
        self.assertFalse([c for c in r["codes"] if c.startswith("field_missing")])

    def test_a_missing_field_and_a_wrong_input_set_are_reported(self):
        r = self.run_file(self.response_file(block("p014"), operator=None, input_set="round/03-open/v1 @ " + "b" * 40))
        self.assertIn("field_missing:operator", r["codes"])
        self.assertIn("input_set_mismatch", r["codes"])

    def test_a_receipt_in_a_participant_file_is_flagged(self):
        r = self.run_file(self.response_file(block("p014"), receipt={"route": "x"}))
        self.assertIn("receipt_present", r["codes"])


class Limits(Base):
    def test_too_large_is_not_checked_never_rejected(self):
        r = self.run_file(b"x" * (v.MAX_BYTES + 1))
        self.assertFalse(r["checked"])
        self.assertEqual(r["codes"], ["not_checked_too_large"])
        self.assertEqual(r["assessments"], {})

    def test_yaml_anchors_aliases_and_tags_are_not_checked(self):
        for header in ("a: &x [1]\nb: *x\n", "a: !!python/object:os.system x\n"):
            with self.subTest(header=header):
                r = self.run_file(("---\n" + header + "---\n\n" + block("p014")).encode())
                self.assertFalse(r["checked"])
                self.assertIn("not_checked_yaml_limits", r["codes"])

    def test_deep_yaml_is_not_checked(self):
        deep = "a:\n" + "".join("  " * i + f"k{i}:\n" for i in range(1, 30)) + "  " * 30 + "x: 1\n"
        r = self.run_file(("---\n" + deep + "---\n\n").encode())
        self.assertIn("not_checked_yaml_limits", r["codes"])

    def test_not_utf8_is_not_checked(self):
        r = self.run_file(b"---\ntype: x\n---\n\n\xff\xfe")
        self.assertEqual(r["codes"], ["not_checked_not_utf8"])


class Forms(Base):
    def test_duplicated_heading_is_flagged_not_guessed(self):
        body = self.issue_body(block("p014")) + b"\n### Rights\n\nsomething else\n"
        self.assertIn("form_heading_duplicated", self.run_issue(body)["codes"])

    def test_text_before_the_first_heading_is_flagged(self):
        body = b"hello\n### Something\n\n" + self.issue_body(block("p014"))
        self.assertIn("form_heading_unknown", self.run_issue(body)["codes"])

    def test_headings_inside_the_answer_stay_in_the_answer(self):
        answer = "## My answer\n\n### p014\nPosition: support\nConditions: none\nBasis: x\n\n### q001\ntext"
        r = self.run_issue(self.issue_body(answer))
        self.assertEqual(r["assessments"]["p014"], "read")
        self.assertNotIn("form_heading_unknown", r["codes"])

    def test_unfenced_answer_and_crlf_and_unicode(self):
        answer = "p014\r\nPosition: support\r\nConditions: none\r\nBasis: é 漢字 — ok\r\n"
        r = self.run_issue(self.issue_body(answer, fence=False).replace(b"\n", b"\r\n"))
        self.assertEqual(r["assessments"]["p014"], "read")

    def test_issue_version_is_the_body_digest(self):
        body = self.issue_body(block("p014"))
        self.assertEqual(self.run_issue(body)["version"], hashlib.sha256(body).hexdigest())


class Renderer(Base):
    def result(self, **over):
        r = self.run_file(self.response_file(block("p014") + "\n" + block("p014", "reject")))
        r.update(over)
        return r

    def test_renders_fixed_text_only(self):
        answer = "p014\nPosition: support\nConditions: none\nBasis: @someone <script>x</script> [link](http://e)\n"
        r = self.run_file(self.response_file(answer, author="@everyone <b>"))
        text = rf.render(r, "file", 5, SHA, self.repo)
        for bad in ("@someone", "<script>", "http://e", "@everyone", "<b>"):
            self.assertNotIn(bad, text)
        self.assertTrue(text.startswith(rf.MARKER))

    def test_refuses_a_result_for_another_item_or_version(self):
        r = self.result()
        for args in (("issue", 5, SHA), ("file", 6, SHA), ("file", 5, "b" * 40)):
            with self.subTest(args=args), self.assertRaises(ValueError):
                rf.render(r, *args, repo=self.repo)

    def test_refuses_a_result_that_fails_the_schema(self):
        for over in ({"codes": ["<img src=x>"]}, {"assessments": {"p999": "read"}}, {"extra": 1},
                     {"version": "not-hex"}, {"counts": {"read": 1}}, {"number": True}):
            r = self.result()
            r.update(over)
            with self.subTest(over=over), self.assertRaises(ValueError):
                rf.render(r, "file", 5, SHA, self.repo)

    def test_problem_blocks_are_listed_by_id_only(self):
        text = rf.render(self.result(), "file", 5, SHA, self.repo)
        self.assertIn("`p014`: more than one block", text)


if __name__ == "__main__":
    unittest.main()
