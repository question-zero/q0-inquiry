# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/round_03_feedback_job.py (D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md), with GitHub's API replaced by a fake: both routes, a moved pull request, a stale result, several files, a non-regular file, and a copied marker in another user's comment. Synthetic data only; no network.
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
import validate_round_03_response as v  # noqa: E402

BASE = "question-zero/q0-inquiry"


class FakeApi:
    def __init__(self):
        self.routes, self.calls = {}, []

    def __call__(self, method, url, token, data=None, accept=None):
        self.calls.append((method, url, data))
        key = (method, url.split("?")[0]) if method != "GET" else (method, url)
        for (m, prefix), value in self.routes.items():
            if m == method and (url == prefix or url.split("?")[0] == prefix):
                return value(data) if callable(value) else value
        return None


class JobBase(tv.Base):
    def setUp(self):
        super().setUp()
        self.fake = FakeApi()
        self.orig_api, job.api = job.api, self.fake
        self.orig_validate = v.validate
        repo = self.repo
        job.v.validate = lambda route, data, number, version, r=None: self.orig_validate(route, data, number, version, repo)
        self.orig_render = rf.render
        job.rf.render = lambda result, route, number, version, r=None: self.orig_render(result, route, number, version, repo)
        self.out = Path(tempfile.mkstemp()[1])
        self.evf = Path(tempfile.mkstemp()[1])
        os.environ.update({"GH_TOKEN": "t", "GITHUB_OUTPUT": str(self.out), "GITHUB_EVENT_PATH": str(self.evf)})

    def tearDown(self):
        job.api, job.v.validate, job.rf.render = self.orig_api, self.orig_validate, self.orig_render
        os.environ.pop("RESULT", None)
        super().tearDown()

    def event(self, ev):
        self.evf.write_text(json.dumps(ev), encoding="utf-8")

    def output(self):
        text = self.out.read_text(encoding="utf-8")
        return json.loads(text.split("result=", 1)[1]) if "result=" in text else None

    def pr_event(self, sha="a" * 40):
        return {"repository": {"full_name": BASE},
                "pull_request": {"number": 5, "head": {"sha": sha, "repo": {"full_name": "someone/fork"}}}}

    def serve_pr(self, files, contents, sha="a" * 40):
        self.fake.routes[("GET", f"/repos/{BASE}/pulls/5")] = {"head": {"sha": sha, "repo": {"full_name": "someone/fork"}}}
        self.fake.routes[("GET", f"/repos/{BASE}/pulls/5/files?per_page=100&page=1")] = files
        for path, meta in contents.items():
            self.fake.routes[("GET", f"/repos/someone/fork/contents/{path}?ref={sha}")] = meta


def file_meta(data):
    return {"type": "file", "size": len(data), "encoding": "base64", "content": base64.b64encode(data).decode()}


class Parse(JobBase):
    def test_issue_route(self):
        body = self.issue_body(tv.block("p014")).decode()
        self.event({"repository": {"full_name": BASE}, "issue": {"number": 7, "body": body}})
        job.parse()
        r = self.output()
        self.assertEqual((r["route"], r["number"]), ("issue", 7))
        self.assertEqual(r["version"], hashlib.sha256(body.encode()).hexdigest())

    def test_pr_route_reads_the_file_as_data_at_the_head(self):
        data = self.response_file(tv.block("p014"))
        self.event(self.pr_event())
        self.serve_pr([{"filename": "rounds/03-open/responses/ada.md", "status": "added"},
                       {"filename": "tools/evil.py", "status": "added"}],
                      {"rounds/03-open/responses/ada.md": file_meta(data)})
        job.parse()
        r = self.output()
        self.assertEqual((r["route"], r["version"], r["counts"]["read"]), ("file", "a" * 40, 1))
        self.assertFalse(any("evil" in c[1] for c in self.fake.calls))

    def test_a_moved_pull_request_is_skipped(self):
        self.event(self.pr_event("a" * 40))
        self.serve_pr([], {}, sha="b" * 40)
        job.parse()
        self.assertIsNone(self.output())

    def test_several_files_and_a_symlink(self):
        self.event(self.pr_event())
        self.serve_pr([{"filename": "rounds/03-open/responses/a.md", "status": "added"},
                       {"filename": "rounds/03-open/responses/b.md", "status": "added"}],
                      {"rounds/03-open/responses/a.md": {"type": "symlink", "size": 10}})
        job.parse()
        r = self.output()
        self.assertFalse(r["checked"])
        self.assertTrue({"pr_several_response_files", "pr_file_not_regular_or_too_large"} <= set(r["codes"]))
        self.assertEqual(v.schema_problems(r, ["p014", "p019", "p025"]), [])


class Publish(JobBase):
    def result_for_issue(self, body):
        return self.orig_validate("issue", body, 7, None, self.repo)

    def test_stale_result_is_not_published(self):
        body = self.issue_body(tv.block("p014"))
        os.environ["RESULT"] = json.dumps(self.result_for_issue(body))
        self.event({"repository": {"full_name": BASE}, "issue": {"number": 7, "body": body.decode()}})
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = {"body": body.decode() + "edited"}
        job.publish()
        self.assertFalse([c for c in self.fake.calls if c[0] in ("POST", "PATCH")])

    def test_updates_only_its_own_comment(self):
        body = self.issue_body(tv.block("p014"))
        os.environ["RESULT"] = json.dumps(self.result_for_issue(body))
        self.event({"repository": {"full_name": BASE}, "issue": {"number": 7, "body": body.decode()}})
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = {"body": body.decode()}
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7/comments?per_page=100&page=1")] = [
            {"id": 1, "user": {"login": "mallory"}, "body": rf.MARKER + " fake"},
            {"id": 2, "user": {"login": job.BOT}, "body": rf.MARKER + "\nold"}]
        job.publish()
        writes = [c for c in self.fake.calls if c[0] in ("POST", "PATCH")]
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][:2], ("PATCH", f"/repos/{BASE}/issues/comments/2"))

    def test_posts_when_it_has_no_comment_yet(self):
        body = self.issue_body(tv.block("p014"))
        os.environ["RESULT"] = json.dumps(self.result_for_issue(body))
        self.event({"repository": {"full_name": BASE}, "issue": {"number": 7, "body": body.decode()}})
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = {"body": body.decode()}
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7/comments?per_page=100&page=1")] = [
            {"id": 1, "user": {"login": "mallory"}, "body": rf.MARKER}]
        job.publish()
        writes = [c for c in self.fake.calls if c[0] in ("POST", "PATCH")]
        self.assertEqual(writes[0][:2], ("POST", f"/repos/{BASE}/issues/7/comments"))
        self.assertTrue(writes[0][2]["body"].startswith(rf.MARKER))


if __name__ == "__main__":
    unittest.main()
