# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/round_03_feedback_job.py (D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md), with GitHub's API replaced by a fake: both routes, a moved pull request, a stale result, several files, non-regular Git modes, and a copied marker in another user's comment. Revision 2 adds GPT-6's AC4-AC6 regressions (critiques/2026-09-26-gpt-6--automation-code-review.md): the pinned trusted revision, an edit during the comment lookup, removal of the last response, loss of the form's headings, incomplete pagination, and the complete body's digest. Revision 3 adds GPT-6's round-2 regressions (critiques/2026-09-26-gpt-6--automation-code-review-r2.md): an old rerun reconciles to the current version, an oversized page is incomplete, and a validator stopped by its limit gives a typed result. Revision 4 (topic automation-sandbox-report): same-repository fixtures; a fork or missing head repository is skipped before anything is read (SR3); the workflow's conditions; the comment's version-only wording (F2); POSIX-only checks of the real CPU and address-space limits and the typed result when either stops the child (SR2). Synthetic data only; no network.
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
        self.fake.routes[("GET", f"/repos/{BASE}/issues/{number}/comments?per_page={job.PER_PAGE}&page=1")] = items

    def writes(self):
        return [c for c in self.fake.calls if c[0] in ("POST", "PATCH")]

    # pull requests
    def pr_event(self, sha="a" * 40, head=BASE):
        return {"repository": {"full_name": BASE}, "pull_request": {"number": 5, "head": {"sha": sha, "repo": {"full_name": head}}}}

    def serve_pr(self, files, tree=(), blobs=None, sha="a" * 40, head=BASE):
        self.fake.routes[("GET", f"/repos/{BASE}/pulls/5")] = {
            "head": {"sha": sha, "repo": {"full_name": head} if head else None}}
        self.fake.routes[("GET", f"/repos/{BASE}/pulls/5/files?per_page={job.PER_PAGE}&page=1")] = files
        self.fake.routes[("GET", f"/repos/{head}/git/trees/{sha}?recursive=1")] = {"truncated": False, "tree": list(tree)}
        for blob_sha, data in (blobs or {}).items():
            self.fake.routes[("GET", f"/repos/{head}/git/blobs/{blob_sha}")] = {
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

    def test_an_old_event_reconciles_to_the_current_head(self):  # GPT-6 round 2, AC5
        data = self.response_file(tv.block("p014"))
        self.event(self.pr_event("a" * 40))
        self.serve_pr([{"filename": PATH, "status": "added"}], tree=[self.regular(PATH, data)],
                      blobs={"b" * 40: data}, sha="c" * 40)
        job.parse()
        self.assertEqual(self.result()["version"], "c" * 40)

    def test_an_old_issue_event_reconciles_to_the_current_body(self):  # GPT-6 round 2, AC5
        old = self.issue_body(tv.block("p014")).decode()
        new = self.issue_body(tv.block("p019")).decode()
        self.event({"repository": {"full_name": BASE}, "issue": {"number": 7, "body": old}})
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7")] = {"body": new}
        job.parse()
        self.assertEqual(self.result()["version"], hashlib.sha256(new.encode()).hexdigest())

    def test_an_oversized_page_is_incomplete_not_a_crash(self):  # GPT-6 round 2, AC6
        def too_big(method, url, token, data=None, accept=None):
            raise job.Incomplete()
        body = self.issue_body(tv.block("p014")).decode()
        self.issue_event(body)
        orig = job.api
        job.api = lambda m, u, t, d=None, a=None: too_big(m, u, t) if "comments" in u else orig(m, u, t, d, a)
        try:
            self.assertEqual(job.managed_comment(BASE, 7, "t"), (None, False))
        finally:
            job.api = orig

    def test_a_validator_stopped_by_its_limit_gives_a_typed_result(self):  # GPT-6 round 2, AC6
        import subprocess
        data = self.response_file(tv.block("p014"))
        real = subprocess.run

        def stopped(cmd, **kw):
            if str(job.VALIDATOR) in cmd:
                raise subprocess.TimeoutExpired(cmd, 60)
            return real(cmd, **kw)
        job.subprocess.run = stopped
        try:
            r = job.validate_isolated("file", data, 5, "a" * 40)
        finally:
            job.subprocess.run = real
        self.assertEqual((r["codes"], r["checked"]), (["not_checked_resources"], False))

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
        full = [{"filename": f"x{i}", "status": "added"} for i in range(job.PER_PAGE)]
        for page in range(1, job.MAX_PAGES + 1):
            self.fake.routes[("GET", f"/repos/{BASE}/pulls/5/files?per_page={job.PER_PAGE}&page={page}")] = full
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


class SameRepository(JobBase):
    """Forks are not cleared (GPT-6 SR3): nothing is read from them and nothing is published."""

    def test_a_fork_or_a_missing_head_repository_is_skipped_before_anything_is_read(self):
        data = self.response_file(tv.block("p014"))
        for head in (FORK, None):
            with self.subTest(head=head):
                self.fake.calls.clear()
                self.out.write_text("", encoding="utf-8")
                self.event(self.pr_event(head=head))
                self.serve_pr([{"filename": PATH, "status": "added"}], tree=[self.regular(PATH, data)],
                              blobs={"b" * 40: data}, head=head)
                job.parse()
                self.assertIsNone(self.result())
                self.assertEqual([c[1] for c in self.fake.calls], [f"/repos/{BASE}/pulls/5"])
                self.assertFalse(self.writes())

    def test_a_same_repository_pull_request_is_still_checked(self):
        data = self.response_file(tv.block("p014"))
        self.event(self.pr_event())
        self.serve_pr([{"filename": PATH, "status": "added"}], tree=[self.regular(PATH, data)], blobs={"b" * 40: data})
        job.parse()
        self.assertEqual(self.result()["counts"]["read"], 1)

    def test_the_workflow_excludes_forks_from_both_jobs_and_keeps_issues(self):
        import yaml
        wf = yaml.safe_load((HERE / "workflows" / "round-3-feedback.yml").read_text(encoding="utf-8"))
        for name in ("parse", "publish"):
            cond = " ".join(wf["jobs"][name]["if"].split())
            with self.subTest(job=name):
                self.assertIn("vars.Q0_ROUND3_FEEDBACK == 'on'", cond)
                self.assertIn("(github.event_name == 'issues' || "
                              "github.event.pull_request.head.repo.full_name == github.repository)", cond)

    def test_the_comment_promises_no_update(self):
        body = self.issue_body(tv.block("p014")).decode()
        self.issue_event(body)
        job.parse()
        text = rf.render(self.result(), "issue", 7, hashlib.sha256(body.encode()).hexdigest(), self.trusted, self.repo)
        self.assertIn("This comment describes only the version named above.", text)
        self.assertNotIn("is updated", text)


@unittest.skipUnless(os.name == "posix", "the resource limits exist only on POSIX")
class PosixLimits(JobBase):
    """The validator child's real limits, on a POSIX host such as the CI runner (GPT-6 SR2, AC6)."""

    def child(self, code, timeout=30):
        import subprocess
        return subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=timeout,
                              preexec_fn=job.limits)

    def test_the_child_runs_under_the_configured_limits(self):
        r = self.child("import resource; print(resource.getrlimit(resource.RLIMIT_AS)[0], "
                       "resource.getrlimit(resource.RLIMIT_CPU)[0])")
        self.assertEqual(r.stdout.split(), [str(job.LIMIT_MEMORY).encode(), str(job.LIMIT_SECONDS).encode()])
        print(f"POSIX limits in the child: address space {job.LIMIT_MEMORY} bytes, CPU {job.LIMIT_SECONDS} s")

    def test_the_cpu_limit_stops_a_busy_child(self):
        # With the soft and hard limits equal, as configured, Linux ends the child with SIGKILL at the hard limit;
        # other kernels may send SIGXCPU first. Either way it stops far sooner than the 30-second wall timeout here.
        import signal
        import time
        orig = job.LIMIT_SECONDS
        job.LIMIT_SECONDS = 1
        start = time.monotonic()
        try:
            r = self.child("while True: pass", timeout=30)
        finally:
            job.LIMIT_SECONDS = orig
        elapsed = time.monotonic() - start
        self.assertIn(r.returncode, (-signal.SIGXCPU, -signal.SIGKILL))
        self.assertLess(elapsed, 10)
        print(f"POSIX CPU limit: a busy child with a 1 s CPU limit stopped by signal {-r.returncode} "
              f"after {elapsed:.1f} s")

    def test_the_address_space_limit_stops_an_oversized_allocation(self):
        r = self.child("import sys\ntry:\n    b = bytearray(%d)\nexcept MemoryError:\n    sys.exit(3)\nsys.exit(0)"
                       % (job.LIMIT_MEMORY + 512 * 1024 * 1024))
        self.assertEqual(r.returncode, 3)
        print("POSIX address-space limit: an allocation over the limit raised MemoryError in the child")

    def test_a_child_stopped_by_either_limit_gives_the_typed_result(self):
        data = self.response_file(tv.block("p014"))
        hogs = {"cpu": "while True: pass\n",
                "memory": "b = bytearray(%d)\n" % (job.LIMIT_MEMORY + 512 * 1024 * 1024)}
        orig = (job.VALIDATOR, job.LIMIT_SECONDS)
        try:
            for name, code in hogs.items():
                with self.subTest(limit=name), tempfile.TemporaryDirectory() as td:
                    hog = Path(td) / "hog.py"
                    hog.write_text(code, encoding="utf-8")
                    job.VALIDATOR, job.LIMIT_SECONDS = hog, 2
                    r = job.validate_isolated("file", data, 5, "a" * 40)
                    self.assertEqual((r["codes"], r["checked"]), (["not_checked_resources"], False))
                    print(f"POSIX {name} limit: validate_isolated gave not_checked_resources")
        finally:
            job.VALIDATOR, job.LIMIT_SECONDS = orig


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
        self.fake.routes[("GET", f"/repos/{BASE}/issues/7/comments?per_page={job.PER_PAGE}&page=1")] = comment_lookup
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
        others = [{"id": i, "user": {"login": "someone"}, "body": "hi"} for i in range(job.PER_PAGE)]
        for page in range(1, job.MAX_PAGES + 1):
            self.fake.routes[("GET", f"/repos/{BASE}/issues/7/comments?per_page={job.PER_PAGE}&page={page}")] = others
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
