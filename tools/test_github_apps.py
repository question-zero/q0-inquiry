# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/github_apps/ (D1 of proposals/2026-09-26-claude-opus-5-5-github-automation.md). Revision 2 adds GPT-6's AC1-AC3 regressions (critiques/2026-09-26-gpt-6--automation-code-review.md): the credential helper's destination checks, registration's destination, slug, access-control and failure paths, and minting against an approved identity mapping with returned-scope, expiry and revocation checks. Revision 3 adds GPT-6's round-2 cases: URL-specific repository settings, approval of a private repository through an authentication-enforcing fake, enumerated permission levels, and the final exit status after launch failures. Revision 4 adds its round-3 AC1 cases (worktree configuration, inspection failure, fixed categories with no setting names in any message) and the approval lookup's exact scope. Revision 5 adds zero and negative repository IDs (topic automation-code-ac1). Synthetic keys and a fake API; no network.
# license: MIT (LICENSE-CODE)
"""Offline tests for the GitHub App helpers. Run: python -m unittest tools/test_github_apps.py

They need the `cryptography` package; the required CI job installs a pinned version, so a missing package fails
rather than skips.
"""
import base64
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

sys.path.insert(0, str(Path(__file__).resolve().parent / "github_apps"))
import app_token  # noqa: E402
import git_credential_helper as helper  # noqa: E402
import register  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption()).decode()
CREDS = {"id": 42, "slug": "question-zero-editor", "pem": PEM}
APPROVED = {"slug": "question-zero-editor", "app_id": 42, "installation_id": 7,
            "repositories": {"q0-inquiry": {"owner": "question-zero", "id": 1001}}}
NOW = datetime(2026, 9, 26, 3, 0, 0, tzinfo=timezone.utc)


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Fake:
    def __init__(self, app_id=42, slug="question-zero-editor", inst_id=7, inst_app=42, granted=None,
                 repos=None, returned_perms=None, expires=None, revoke_fails=False):
        self.app_id, self.slug, self.inst_id, self.inst_app = app_id, slug, inst_id, inst_app
        self.granted = granted or {"contents": "write", "pull_requests": "write", "issues": "write", "metadata": "read"}
        self.repos = repos if repos is not None else [{"id": 1001, "full_name": "question-zero/q0-inquiry"}]
        self.returned_perms = returned_perms
        self.expires = expires if expires is not None else (NOW + timedelta(minutes=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.revoke_fails, self.calls = revoke_fails, []

    def __call__(self, method, path, auth, data=None):
        self.calls.append((method, path, data))
        if path == "/app":
            return {"id": self.app_id, "slug": self.slug}
        if path.endswith("/installation"):
            return {"id": self.inst_id, "app_id": self.inst_app, "permissions": self.granted}
        if path.startswith("/app/installations/") and method == "POST":
            got = {"token": "ghs_secret", "repositories": self.repos,
                   "permissions": self.returned_perms or dict(data["permissions"], metadata="read")}
            if self.expires != "omit":
                got["expires_at"] = self.expires
            return got
        if method == "DELETE":
            if self.revoke_fails:
                raise OSError("synthetic")
            return None
        if path.startswith("/users/"):
            return {"id": 99}
        return None


def mint(fake, perms=None, approved=APPROVED, creds=CREDS, repo="q0-inquiry", slug="question-zero-editor"):
    return app_token.mint(creds, approved, repo, perms or {"contents": "write"}, caller=fake, slug=slug, now=NOW)


class Jwt(unittest.TestCase):
    def test_signed_rs256_with_short_expiry(self):
        token = app_token.app_jwt(42, PEM, now=1000)
        h, p, s = token.split(".")
        self.assertEqual(json.loads(unb64(h)), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(json.loads(unb64(p)), {"iat": 940, "exp": 1540, "iss": "42"})
        KEY.public_key().verify(unb64(s), f"{h}.{p}".encode(), padding.PKCS1v15(), hashes.SHA256())


class Helper(unittest.TestCase):  # GPT-6 AC1
    ENV = {"Q0_APP_TOKEN": "tok", "Q0_APP_DEST": "github.com/question-zero/q0-inquiry"}

    def ask(self, op, **fields):
        return helper.answer(op, "".join(f"{k}={v}\n" for k, v in fields.items()) + "\n", self.ENV)

    def test_answers_only_get_for_the_exact_destination(self):
        good = dict(protocol="https", host="github.com", path="question-zero/q0-inquiry.git")
        self.assertIn("password=tok", self.ask("get", **good))
        self.assertIn("password=tok", self.ask("get", **dict(good, path="question-zero/q0-inquiry")))
        for op in ("store", "erase", ""):
            self.assertEqual(self.ask(op, **good), "")
        for bad in (dict(good, host="example.invalid"), dict(good, host="github.com:443"), dict(good, protocol="http"),
                    dict(good, path="question-zero/other.git"), dict(good, path="attacker/q0-inquiry.git"),
                    {"protocol": "https", "host": "github.com"}):
            with self.subTest(bad=bad):
                self.assertEqual(self.ask("get", **bad), "")

    def test_git_itself_gives_no_token_to_a_foreign_host(self):
        env = app_token.command_env("tok", "question-zero", "q0-inquiry", base=dict(os.environ))
        for target, expect in (("protocol=https\nhost=example.invalid\npath=unrelated/project.git\n\n", False),
                               ("protocol=https\nhost=github.com\npath=question-zero/q0-inquiry.git\n\n", True)):
            out = subprocess.run(["git", "credential", "fill"], input=target, capture_output=True, text=True,
                                 env=env).stdout
            self.assertEqual("password=tok" in out, expect, target)

    def test_repository_and_worktree_settings_are_refused_by_category(self):  # GPT-6 rounds 2 and 3, AC1
        marker = "SECRETMARKER"
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)
            self.assertEqual(app_token.config_problems(td), [])
            cases = [("--local", f"http.https://{marker}@github.com/.extraheader", "AUTHORIZATION: basic fake",
                      "extra HTTP headers"),
                     ("--local", f"credential.https://{marker}.github.com.helper", "store", "credential settings"),
                     ("--local", f"url.https://{marker}.invalid/.insteadof", "https://github.com/", "URL rewrites"),
                     ("--local", "include.path", "other.cfg", "configuration includes"),
                     ("--worktree", f"http.https://{marker}@github.com/.extraheader", "AUTHORIZATION: basic fake",
                      "extra HTTP headers")]
            subprocess.run(["git", "-C", td, "config", "--local", "extensions.worktreeConfig", "true"], check=True)
            for scope, key, value, category in cases:
                with self.subTest(scope=scope, key=key):
                    subprocess.run(["git", "-C", td, "config", scope, key, value], check=True)
                    found = app_token.config_problems(td)
                    self.assertIn(category, found)
                    self.assertNotIn(marker, " ".join(found))
                    subprocess.run(["git", "-C", td, "config", scope, "--unset", key], check=True)

    def test_refusal_happens_before_minting_and_names_no_setting(self):  # GPT-6 round 3, AC1
        marker = "SECRETMARKER"
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["git", "init", "-q", td], check=True)
            subprocess.run(["git", "-C", td, "config", "--local", f"http.https://{marker}@github.com/.extraheader",
                            "AUTHORIZATION: basic fake"], check=True)
            (Path(td) / "question-zero-editor.json").write_text(json.dumps(CREDS), encoding="utf-8")
            cwd = os.getcwd()
            os.chdir(td)
            try:
                with patch.object(app_token, "mint", side_effect=AssertionError("reached minting")), \
                        redirect_stdout(io.StringIO()) as out, self.assertRaises(SystemExit) as cm:
                    app_token.main(["run", "--secrets", td, "--repo", "q0-inquiry", "--perm", "contents=read",
                                    "--", "git", "status"])
            finally:
                os.chdir(cwd)
            self.assertIn("extra HTTP headers", str(cm.exception.code))
            self.assertNotIn(marker, str(cm.exception.code) + out.getvalue())

    def test_an_inspection_failure_refuses(self):  # GPT-6 round 3, AC1: fail closed
        failed = subprocess.CompletedProcess([], 128, stdout="", stderr="fatal: something")
        with patch.object(app_token.subprocess, "run", return_value=failed), self.assertRaises(SystemExit) as cm:
            app_token.config_problems()
        self.assertIn("could not inspect", str(cm.exception.code))
        with patch.object(app_token.subprocess, "run", side_effect=OSError("no git")), self.assertRaises(SystemExit):
            app_token.config_problems()

    def test_command_env_scrubs_inherited_credentials_and_tracing(self):
        env = app_token.command_env("tok", "question-zero", "q0-inquiry",
                                    base={"GITHUB_TOKEN": "x", "GIT_TRACE": "1", "GIT_ASKPASS": "a", "GH_HOST": "h"})
        for name in ("GITHUB_TOKEN", "GIT_TRACE", "GIT_ASKPASS", "GH_HOST"):
            self.assertNotIn(name, env)
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        self.assertEqual(env["Q0_APP_DEST"], "github.com/question-zero/q0-inquiry")


class Scope(unittest.TestCase):  # GPT-6 AC3
    def test_permissions_outside_the_allowed_set_are_refused(self):
        for bad in (["workflows=write"], ["administration=write"], ["metadata=write"], []):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                app_token.parse_perms(bad)

    def test_mints_for_the_approved_repository_id_and_a_subset(self):
        fake = Fake()
        token, _ = mint(fake)
        self.assertEqual(token, "ghs_secret")
        post = [c for c in fake.calls if c[0] == "POST"][0]
        self.assertEqual(post[2], {"repository_ids": [1001], "permissions": {"contents": "write"}})

    def test_refuses_before_minting(self):
        cases = [Fake(app_id=41), Fake(slug="other"), Fake(inst_id=8), Fake(inst_app=41),
                 Fake(granted={"contents": "read", "metadata": "read"})]
        for fake in cases:
            with self.subTest(fake=vars(fake)), self.assertRaises(SystemExit):
                mint(fake)
            self.assertFalse([c for c in fake.calls if c[0] == "POST"])
        with self.assertRaises(SystemExit):
            mint(Fake(), repo="someone-else")
        with self.assertRaises(SystemExit):
            mint(Fake(), approved=dict(APPROVED, app_id=41))

    def test_a_wrong_returned_scope_is_revoked(self):
        cases = {"other owner, same name": Fake(repos=[{"id": 1001, "full_name": "other-owner/q0-inquiry"}]),
                 "other repository id": Fake(repos=[{"id": 999, "full_name": "question-zero/q0-inquiry"}]),
                 "two repositories": Fake(repos=[{"id": 1001, "full_name": "question-zero/q0-inquiry"},
                                                 {"id": 1002, "full_name": "question-zero/.github"}]),
                 "extra permission": Fake(returned_perms={"contents": "write", "workflows": "write",
                                                          "metadata": "read"}),
                 "write for a read request": Fake(returned_perms={"contents": "write", "metadata": "read"}),
                 "no expiry": Fake(expires="omit"),
                 "malformed expiry": Fake(expires="tomorrow"),
                 "expired": Fake(expires=(NOW - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")),
                 "too long": Fake(expires=(NOW + timedelta(hours=5)).strftime("%Y-%m-%dT%H:%M:%SZ"))}
        for name, fake in cases.items():
            perms = {"contents": "read"} if name == "write for a read request" else None
            with self.subTest(name=name):
                with self.assertRaises(SystemExit) as cm:
                    mint(fake, perms=perms)
                self.assertNotEqual(cm.exception.code, app_token.REVOKE_UNCONFIRMED)
                self.assertIn(("DELETE", "/installation/token", None), fake.calls)

    def test_levels_are_an_explicit_enumeration(self):  # GPT-6 round 2, AC3
        for bad in ("admin", None, 3, "WRITE", ["write"]):
            with self.subTest(bad=bad):
                fake = Fake(returned_perms={"contents": bad, "metadata": "read"})
                with self.assertRaises(SystemExit):
                    mint(fake)
                self.assertIn(("DELETE", "/installation/token", None), fake.calls)
        self.assertFalse(app_token.covers("write", "admin"))
        self.assertFalse(app_token.covers(None, "read"))
        self.assertTrue(app_token.covers("write", "read"))

    def test_finish_settles_the_status_after_cleanup(self):  # GPT-6 round 2, AC3
        exp = (datetime.now(timezone.utc) + timedelta(minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ")

        def boom(*a):
            raise OSError("synthetic launch failure with GH_TOKEN=ghs_secret")

        def interrupt(*a):
            raise KeyboardInterrupt()
        cases = [(boom, False, app_token.REVOKE_UNCONFIRMED), (boom, True, 125), (interrupt, True, 130),
                 (lambda *a: 124, True, 124), (lambda *a: 0, False, app_token.REVOKE_UNCONFIRMED)]
        for runner, revoked, expected in cases:
            calls = []
            with self.subTest(expected=expected), redirect_stdout(io.StringIO()) as out:
                code = app_token.finish("ghs_secret", exp, {"contents": "read"}, ["x"], "question-zero", "q0-inquiry",
                                        runner=runner, revoker=lambda t: calls.append(t) or revoked)
                self.assertEqual(code, expected)
                self.assertEqual(calls, ["ghs_secret"])
                self.assertNotIn("ghs_secret", out.getvalue())

    def test_approve_reads_a_private_repository_through_a_revoked_temporary_token(self):  # GPT-6 round 2, AC3
        class AuthFake(Fake):
            def __call__(self, method, path, auth, data=None):
                if not auth:
                    raise PermissionError("authentication required")
                if method == "POST":
                    self.calls.append((method, path, data))
                    return {"token": "ghs_lookup", "repositories": [{"id": 2002, "full_name": "question-zero/q0-sandbox"}],
                            "permissions": {"metadata": "read"}}
                return super().__call__(method, path, auth, data)
        creds = dict(CREDS, slug="question-zero-editor-sandbox")
        fake = AuthFake(slug="question-zero-editor-sandbox")
        with tempfile.TemporaryDirectory() as td, redirect_stdout(io.StringIO()):
            self.assertIsNone(app_token.approve(creds, "question-zero-editor-sandbox", "q0-sandbox", None, td, caller=fake))
            posts = [c for c in fake.calls if c[0] == "POST"]
            self.assertEqual(posts[0][2], {"repositories": ["q0-sandbox"], "permissions": {"metadata": "read"}})
            self.assertIn(("DELETE", "/installation/token", None), fake.calls)
            mapping = app_token.approve(creds, "question-zero-editor-sandbox", "q0-sandbox", 7, td, caller=fake)
            self.assertEqual(mapping["repositories"]["q0-sandbox"], {"owner": "question-zero", "id": 2002})
        class ExtraScope(AuthFake):
            def __call__(self, method, path, auth, data=None):
                got = super().__call__(method, path, auth, data)
                if method == "POST":
                    got["permissions"] = {"metadata": "read", "contents": "write"}
                return got
        extra = ExtraScope(slug="question-zero-editor-sandbox")
        with tempfile.TemporaryDirectory() as td, redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
            app_token.approve(creds, "question-zero-editor-sandbox", "q0-sandbox", None, td, caller=extra)
        self.assertIn(("DELETE", "/installation/token", None), extra.calls)   # GPT-6 round 3: revoked, then refused
        for bad_id in (0, -5):
            class BadId(AuthFake):
                def __call__(self, method, path, auth, data=None, _id=bad_id):
                    got = super().__call__(method, path, auth, data)
                    if method == "POST":
                        got["repositories"] = [{"id": _id, "full_name": "question-zero/q0-sandbox"}]
                    return got
            fake_bad = BadId(slug="question-zero-editor-sandbox")
            with self.subTest(bad_id=bad_id), tempfile.TemporaryDirectory() as td, \
                    redirect_stdout(io.StringIO()), self.assertRaises(SystemExit):
                app_token.approve(creds, "question-zero-editor-sandbox", "q0-sandbox", 7, td, caller=fake_bad)
            self.assertIn(("DELETE", "/installation/token", None), fake_bad.calls)
        with self.assertRaises(SystemExit):
            mint(Fake(), approved=dict(APPROVED, repositories={"q0-inquiry": {"owner": "question-zero", "id": 0}}))
        bad = AuthFake(slug="question-zero-editor-sandbox", revoke_fails=True)
        with tempfile.TemporaryDirectory() as td, redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as cm:
            app_token.approve(creds, "question-zero-editor-sandbox", "q0-sandbox", None, td, caller=bad)
        self.assertEqual(cm.exception.code, app_token.REVOKE_UNCONFIRMED)

    def test_an_unconfirmed_revocation_is_a_distinct_failure(self):
        with self.assertRaises(SystemExit) as cm:
            mint(Fake(repos=[], revoke_fails=True))
        self.assertEqual(cm.exception.code, app_token.REVOKE_UNCONFIRMED)

    def test_run_revokes_and_propagates_child_failure_and_revoke_failure(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "question-zero-editor.json").write_text(json.dumps(CREDS), encoding="utf-8")
            (Path(td) / "question-zero-editor.approved.json").write_text(json.dumps(APPROVED), encoding="utf-8")
            for child, revoke_ok, expected in ((5, True, 5), (0, False, app_token.REVOKE_UNCONFIRMED)):
                with self.subTest(child=child, revoke_ok=revoke_ok), \
                        patch.object(app_token, "mint", return_value=("ghs_secret", (datetime.now(timezone.utc) + timedelta(minutes=50)).strftime("%Y-%m-%dT%H:%M:%SZ"))), \
                        patch.object(app_token, "run", return_value=child), \
                        patch.object(app_token, "revoke", return_value=revoke_ok), redirect_stdout(io.StringIO()) as out:
                    with self.assertRaises(SystemExit) as cm:
                        app_token.main(["run", "--secrets", td, "--repo", "q0-inquiry", "--perm", "contents=read",
                                        "--", "git", "status"])
                    self.assertEqual(cm.exception.code, expected)
                    self.assertNotIn("ghs_secret", out.getvalue())

    def test_the_sandbox_app_is_confined_to_the_sandbox(self):
        creds = dict(CREDS, slug="question-zero-editor-sandbox")
        approved = {"slug": "question-zero-editor-sandbox", "app_id": 42, "installation_id": 7,
                    "repositories": {"q0-sandbox": {"owner": "question-zero", "id": 2002}}}
        fake = Fake(slug="question-zero-editor-sandbox", repos=[{"id": 2002, "full_name": "question-zero/q0-sandbox"}])
        token, _ = mint(fake, approved=approved, creds=creds, repo="q0-sandbox", slug="question-zero-editor-sandbox")
        self.assertEqual(token, "ghs_secret")
        with self.assertRaises(SystemExit):
            mint(Fake(), approved=approved, creds=creds, repo="q0-inquiry", slug="question-zero-editor-sandbox")
        self.assertEqual(register.manifest("editor", 1, sandbox=True)["name"], "question-zero-editor-sandbox")

    def test_bot_identity(self):
        self.assertEqual(app_token.bot_identity("question-zero-reviewer", caller=Fake()),
                         ("question-zero-reviewer[bot]", "99+question-zero-reviewer[bot]@users.noreply.github.com"))


class Registration(unittest.TestCase):  # GPT-6 AC2
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.returned = {"id": 42, "slug": "question-zero-editor", "pem": "SECRET-PEM", "client_secret": "SECRET-CS",
                         "webhook_secret": "SECRET-WS"}
        self.dir = Path(self.tmp.name) / "s"
        self.flow = register.Flow("editor", self.dir, converter=lambda code: dict(self.returned))
        self.restrict = patch.object(register, "restrict", lambda path, is_dir=False: None)
        self.restrict.start()

    def tearDown(self):
        self.restrict.stop()
        self.tmp.cleanup()

    def test_destinations_inside_a_repository_are_refused(self):
        repo = register.REPO
        for path in (repo, repo / ".relay" / "not-created" / "secrets", Path(self.tmp.name)):
            with self.subTest(path=path):
                if path == Path(self.tmp.name):
                    subprocess.run(["git", "init", "-q", str(path)], check=True)
                with patch.object(register, "serve", side_effect=AssertionError("reached the server")), \
                        self.assertRaises(SystemExit):
                    register.main(["editor", "--secrets", str(path / "sub")])

    def test_wrong_state_is_refused_without_conversion(self):
        status, _ = self.flow.callback("code=abc&state=wrong")
        self.assertEqual(status, 400)
        self.assertFalse(self.flow.used)

    def test_success_saves_everything_and_reveals_nothing(self):
        with redirect_stdout(io.StringIO()) as out:
            status, msg = self.flow.callback(f"code=abc&state={self.flow.state}")
        self.assertEqual(status, 200)
        for secret in ("abc", "SECRET-PEM", "SECRET-CS", "SECRET-WS"):
            self.assertNotIn(secret, msg + out.getvalue())
        self.assertEqual(json.loads(self.flow.saved[2].read_text(encoding="utf-8")), self.returned)

    def test_the_link_is_single_use(self):
        self.flow.callback(f"code=abc&state={self.flow.state}")
        status, _ = self.flow.callback(f"code=def&state={self.flow.state}")
        self.assertEqual(status, 410)

    def test_an_unexpected_app_is_not_saved(self):
        self.returned["slug"] = "someone-else"
        status, _ = self.flow.callback(f"code=abc&state={self.flow.state}")
        self.assertEqual(status, 502)
        self.assertFalse(self.dir.exists() and any(self.dir.iterdir()))

    def test_access_control_failure_leaves_no_file_and_no_secret(self):
        def failing(path, is_dir=False):
            if not is_dir:
                raise PermissionError("synthetic")
        with patch.object(register, "restrict", failing):
            status, msg = self.flow.callback(f"code=abc&state={self.flow.state}")
        self.assertEqual(status, 500)
        self.assertFalse((self.dir / "question-zero-editor.json").exists())
        self.assertNotIn("synthetic", msg)
        self.assertTrue(self.flow.done.is_set())

    def test_conversion_failure_is_a_fixed_message(self):
        flow = register.Flow("editor", self.dir, converter=lambda code: (_ for _ in ()).throw(RuntimeError("SECRET")))
        status, msg = flow.callback(f"code=abc&state={flow.state}")
        self.assertEqual(status, 500)
        self.assertNotIn("SECRET", msg)
        self.assertTrue(flow.done.is_set())

    def test_the_start_page_carries_the_reviewed_manifest(self):
        m = register.manifest("editor", 5555)
        self.assertEqual(m["redirect_url"], "http://127.0.0.1:5555/callback")
        self.assertEqual(m["default_permissions"], {"contents": "write", "pull_requests": "write", "issues": "write",
                                                    "metadata": "read"})
        self.assertEqual(register.manifest("reviewer", 1)["default_permissions"], {"metadata": "read"})
        self.assertIn(self.flow.state, register.start_page(m, self.flow.state))


class RealAccessControl(unittest.TestCase):
    """The real restrict() on this machine: the file ends up limited to the current account."""

    def test_restrict_limits_a_file_to_the_current_user(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td) / "s"
            d.mkdir()
            register.restrict(d, is_dir=True)
            f = d / "x.json"
            f.write_text("{}", encoding="utf-8")
            register.restrict(f)
            self.assertEqual(f.read_text(encoding="utf-8"), "{}")


if __name__ == "__main__":
    unittest.main()
