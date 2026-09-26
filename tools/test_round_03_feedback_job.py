# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/round_03_feedback_job.py (D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md), with GitHub's API replaced by a fake: both routes, a moved pull request, a stale result, several files, non-regular Git modes, and a copied marker in another user's comment. Revision 2 adds GPT-6's AC4-AC6 regressions (critiques/2026-09-26-gpt-6--automation-code-review.md): the pinned trusted revision, an edit during the comment lookup, removal of the last response, loss of the form's headings, incomplete pagination, and the complete body's digest. Synthetic data only; no network.
# license: MIT (LICENSE-CODE)
"""Offline tests for the feedback workflow's jobs. Run: python -m unittest tools/test_round_03_feedback_job.py"""
import base64
import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import round_03_feedback_job as job  # noqa: E402
import render_round_03_feedback as rf  # noqa: E402
import test_validate_round_03 as tv  # noqa: E402

BASE = "question-zero/q0-inquiry"
FORK = "someone/fork"
PATH = "rounds/03-open/responses/ada.md"


class FakeApi:
    """Routes by (method, path). A route's value may be a callable taking (data) for dynamic behaviour."""

    def __init__(self):
        self.routes, self.calls = {}, []

    def __call__(self, method, url, token, data=None, accept=None):
        self.calls.append((method, url, data))
        value = self.routes.get((method, url))
        if value is None and method == "GET" and "per_page=" in url and "page=1" not in url.split("per_page=")[1]:
            return []
        return value(data) if callable(value) else value


class JobBase(tv.Base):
    def setUp(self):
        super().setUp()
        self.fake = FakeApi()
        self.orig = (job.api, job.REPO)
        job.api, job.REPO = self.fake, self.repo
        self.out = Path(tempfile.mkstemp()[1])
        self.evf = Path(tempfile.mkstemp()[1])
        self.trusted = self.git("rev-parse", "HEAD").strip()
        os.environ.update({"GH_TOKEN": "t", "GITHUB_OUTPUT": str(self.out), "GITHUB_EVENT_PATH": str(self.evf),
                           "TRUSTED_SHA": self.trusted})

    def tearDown(self):
        job.api, job.REPO = self.orig
        os.environ.pop("RESULT", None)
        super().tearDown()

    def event(self, ev):
        self.evf.write_text(json.dumps(ev), encoding="utf-8")

    def outputs(self):
        out = {}
        for line in self.out.read_text(encoding="utf-8").splitlines():
            k, _, val = line.partition("=")
            out[k] = val
        return out

    def result(self):
        r = self.outputs().get("result")
        return json.loads(r) if r else None

    def comments(self, number, items):
        self.fake.routes[("GET", f"/repos/{BASE}/issues/{number}/comments?per_page=100&page=1")] = items

    def writes(self):
        return [c for c in self.fake.calls if c[0] in ("POST", "PATCH")]

    # pull requests
    def pr_event(self, sha="a" * 40):
        return {"repository": {"full_name": BASE}, "pull_request": {"number": 5, "head": {"sha": sha, "repo": {"full_name": FORK}}}}

    def serve_pr(self, files, tree=(), blobs=None, sha="a" * 40):
        self.fake.routes[("GET", f"/repos/{BASE}/pulls/5")] = {"head": {"sha": sha, "repo": {"full_name": FORK}}}
        self.fake.routes[("GET", f"/repos/{BASE}/pulls/5/files?per_page=100&page=1")] = files
        self.fake.routes[("GET", f"/repos/{FORK}/git/trees/{sha}?recursive=1")] = {"truncated": False, "tree": list(tree)}
        for blob_sha, data in (blobs or {}).items():
            self.fake.routes[("GET", f"/repos/{FORK}/git/blobs/{blob_sha}")] = {
                "encoding": "base64", "size": len(data), "content": base64.b64encode(data).decode()}
        self.comments(5, [])

    def regular(self, path, data, mode="100644"):
        return {"path": path, "type": "blob", "mode": mode, "sha": "b" * 40, "size": len(data)}

    # issues
    def issue_event(self, body):
        self.event({"repository": {"full_name": BASE}, "issue": {"number": 7, "body": body}})
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = {"body": body}


class Parse(JobBase):
    def test_issue_route_records_the_trusted_revision(self):
        body = self.issue_body(tv.block("p014")).decode()
        self.issue_event(body)
        job.parse()
        r = self.result()
        self.assertEqual((r["route"], r["number"], r["validator_revision"]), ("issue", 7, self.trusted))
        self.assertEqual(r["version"], hashlib.sha256(body.encode()).hexdigest())
        self.assertEqual(self.outputs()["trusted_sha"], self.trusted)

    def test_pr_route_reads_a_regular_blob_at_the_head(self):
        data = self.response_file(tv.block("p014"))
        self.event(self.pr_event())
        self.serve_pr([{"filename": PATH, "status": "added"}, {"filename": "tools/evil.py", "status": "added"}],
                      tree=[self.regular(PATH, data)], blobs={"b" * 40: data})
        job.parse()
        r = self.result()
        self.assertEqual((r["route"], r["version"], r["counts"]["read"]), ("file", "a" * 40, 1))
        self.assertFalse(any("evil" in c[1] for c in self.fake.calls))

    def test_a_moved_pull_request_is_skipped(self):
        self.event(self.pr_event("a" * 40))
        self.serve_pr([], sha="b" * 40)
        job.parse()
        self.assertIsNone(self.result())

    def test_symlinks_submodules_and_oversized_files_are_not_checked(self):  # GPT-6 AC6
        data = self.response_file(tv.block("p014"))
        for entry in (self.regular(PATH, data, mode="120000"), dict(self.regular(PATH, data), type="commit", mode="160000"),
                      dict(self.regular(PATH, data), size=10**7)):
            with self.subTest(entry=entry["mode"]):
                self.fake.calls.clear()
                self.out.write_text("", encoding="utf-8")
                self.event(self.pr_event())
                self.serve_pr([{"filename": PATH, "status": "added"},
                               {"filename": "rounds/03-open/responses/b.md", "status": "added"}], tree=[entry])
                job.parse()
                r = self.result()
                self.assertFalse(r["checked"])
                self.assertEqual(r["codes"], ["pr_file_not_regular_or_too_large", "pr_several_response_files"])

    def test_incomplete_file_listing_is_explicit(self):  # GPT-6 AC6
        self.event(self.pr_event())
        self.serve_pr([])
        full = [{"filename": f"x{i}", "status": "added"} for i in range(100)]
        for page in range(1, job.MAX_PAGES + 1):
            self.fake.routes[("GET", f"/repos/{BASE}/pulls/5/files?per_page=100&page={page}")] = full
        job.parse()
        self.assertEqual(self.result()["codes"], ["incomplete_retrieval"])

    def test_removing_the_last_response_updates_a_managed_comment_only(self):  # GPT-6 AC5
        self.event(self.pr_event())
        self.serve_pr([{"filename": "README.md", "status": "modified"}])
        job.parse()
        self.assertIsNone(self.result())
        self.comments(5, [{"id": 2, "user": {"login": job.BOT}, "body": rf.MARKER}])
        job.parse()
        self.assertEqual(self.result()["codes"], ["no_current_response"])

    def test_losing_the_form_headings_updates_a_managed_comment_only(self):  # GPT-6 AC5
        self.issue_event("just a question, not a response")
        self.comments(7, [])
        job.parse()
        self.assertIsNone(self.result())
        self.comments(7, [{"id": 2, "user": {"login": job.BOT}, "body": rf.MARKER}])
        job.parse()
        self.assertEqual(self.result()["codes"], ["no_current_response"])


class Publish(JobBase):
    def prepare_issue(self, body):
        self.issue_event(body)
        job.parse()
        os.environ["RESULT"] = self.outputs()["result"]

    def test_stale_result_is_not_published(self):
        body = self.issue_body(tv.block("p014")).decode()
        self.prepare_issue(body)
        self.comments(7, [])
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = {"body": body + "edited"}
        job.publish()
        self.assertFalse(self.writes())

    def test_an_edit_during_the_comment_lookup_is_caught(self):  # GPT-6 AC5
        body = self.issue_body(tv.block("p014")).decode()
        self.prepare_issue(body)
        state = {"body": body}

        def comment_lookup(_):
            state["body"] = body + "\nedited later"
            return [{"id": 9, "user": {"login": job.BOT}, "body": rf.MARKER + "\nnewer result"}]
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7/comments?per_page=100&page=1")] = comment_lookup
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = lambda _: {"body": state["body"]}
        job.publish()
        self.assertFalse(self.writes())

    def test_updates_only_its_own_comment(self):
        body = self.issue_body(tv.block("p014")).decode()
        self.prepare_issue(body)
        self.comments(7, [{"id": 1, "user": {"login": "mallory"}, "body": rf.MARKER + " fake"},
                          {"id": 2, "user": {"login": job.BOT}, "body": rf.MARKER + "\nold"}])
        job.publish()
        writes = self.writes()
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][:2], ("PATCH", f"/repos/{BASE}/issues/comments/2"))

    def test_posts_only_when_the_comment_list_is_complete(self):  # GPT-6 AC6
        body = self.issue_body(tv.block("p014")).decode()
        self.prepare_issue(body)
        self.comments(7, [{"id": 1, "user": {"login": "mallory"}, "body": rf.MARKER}])
        job.publish()
        self.assertEqual(self.writes()[0][:2], ("POST", f"/repos/{BASE}/issues/7/comments"))
        self.assertTrue(self.writes()[0][2]["body"].startswith(rf.MARKER))
        self.fake.calls.clear()
        others = [{"id": i, "user": {"login": "someone"}, "body": "hi"} for i in range(100)]
        for page in range(1, job.MAX_PAGES + 1):
            self.fake.routes[("GET", f"/repos/{BASE}/issues/7/comments?per_page=100&page={page}")] = others
        job.publish()
        self.assertFalse(self.writes())

    def test_refuses_to_run_off_the_pinned_revision(self):  # GPT-6 AC4
        body = self.issue_body(tv.block("p014")).decode()
        self.prepare_issue(body)
        self.comments(7, [])
        for bad in ("c" * 40, ""):
            os.environ["TRUSTED_SHA"] = bad
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                job.publish()
        self.assertFalse(self.writes())

    def test_a_result_from_another_revision_is_not_published(self):  # GPT-6 AC4
        body = self.issue_body(tv.block("p014")).decode()
        self.prepare_issue(body)
        self.comments(7, [])
        tampered = json.loads(os.environ["RESULT"])
        tampered["validator_revision"] = "d" * 40
        os.environ["RESULT"] = json.dumps(tampered)
        job.publish()
        self.assertFalse(self.writes())


if __name__ == "__main__":
    unittest.main()
