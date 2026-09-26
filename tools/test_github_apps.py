# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: Offline tests for tools/github_apps/ (D1 of proposals/2026-09-26-claude-opus-5-5-github-automation.md): the App JWT, refusal to exceed token scope or accept an unexpected App, installation or repository, revocation of a wrongly scoped token, and the registration callback's state checks without leaking the code or credentials. Synthetic keys and a fake API; no network.
# license: MIT (LICENSE-CODE)
"""Offline tests for the GitHub App helpers. Run: python -m unittest tools/test_github_apps.py

They need the `cryptography` package, which the helpers use locally. CI installs only PyYAML, so there these tests
are skipped, not failed; run them locally before any change to tools/github_apps/ is reviewed.
"""
import base64
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

try:
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
except ImportError:  # CI: skip, don't fail
    raise unittest.SkipTest("the cryptography package is not installed")

sys.path.insert(0, str(Path(__file__).resolve().parent / "github_apps"))
import app_token  # noqa: E402
import register  # noqa: E402

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = KEY.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                        serialization.NoEncryption()).decode()
CREDS = {"id": 42, "slug": "question-zero-editor", "pem": PEM}


def unb64(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


class Fake:
    def __init__(self, app_id=42, slug="question-zero-editor", inst_app=42, granted=None, repos=("q0-inquiry",)):
        self.app_id, self.slug, self.inst_app = app_id, slug, inst_app
        self.granted = granted or {"contents": "write", "pull_requests": "write", "issues": "write", "metadata": "read"}
        self.repos, self.calls = repos, []

    def __call__(self, method, path, auth, data=None):
        self.calls.append((method, path, data))
        if path == "/app":
            return {"id": self.app_id, "slug": self.slug}
        if path == "/orgs/question-zero/installation":
            return {"id": 7, "app_id": self.inst_app, "permissions": self.granted}
        if path == "/app/installations/7/access_tokens":
            return {"token": "ghs_secret", "expires_at": "2026-09-26T03:00:00Z",
                    "repositories": [{"name": r} for r in self.repos]}
        if path.startswith("/users/"):
            return {"id": 99}
        return None


class Jwt(unittest.TestCase):
    def test_signed_rs256_with_short_expiry(self):
        token = app_token.app_jwt(42, PEM, now=1000)
        h, p, s = token.split(".")
        self.assertEqual(json.loads(unb64(h)), {"alg": "RS256", "typ": "JWT"})
        self.assertEqual(json.loads(unb64(p)), {"iat": 940, "exp": 1540, "iss": "42"})
        KEY.public_key().verify(unb64(s), f"{h}.{p}".encode(), padding.PKCS1v15(), hashes.SHA256())


class Scope(unittest.TestCase):
    def test_permissions_outside_the_allowed_set_are_refused(self):
        for bad in (["workflows=write"], ["administration=write"], ["metadata=write"], []):
            with self.subTest(bad=bad), self.assertRaises(SystemExit):
                app_token.parse_perms(bad)

    def test_mints_for_one_repository_and_a_subset(self):
        fake = Fake()
        token, _ = app_token.mint(CREDS, "q0-inquiry", {"contents": "write"}, caller=fake)
        self.assertEqual(token, "ghs_secret")
        post = [c for c in fake.calls if c[0] == "POST"][0]
        self.assertEqual(post[2], {"repositories": ["q0-inquiry"], "permissions": {"contents": "write"}})

    def test_refuses_unexpected_app_installation_or_repository(self):
        cases = [(Fake(app_id=41), "q0-inquiry"), (Fake(slug="other"), "q0-inquiry"), (Fake(inst_app=41), "q0-inquiry"),
                 (Fake(granted={"contents": "read"}), "q0-inquiry"), (Fake(), "someone-else")]
        for fake, repo in cases:
            with self.subTest(repo=repo), self.assertRaises(SystemExit):
                app_token.mint(CREDS, repo, {"contents": "write"}, caller=fake)

    def test_a_token_for_other_repositories_is_revoked(self):
        fake = Fake(repos=("q0-inquiry", ".github"))
        with self.assertRaises(SystemExit):
            app_token.mint(CREDS, "q0-inquiry", {"contents": "write"}, caller=fake)
        self.assertIn(("DELETE", "/installation/token", None), fake.calls)

    def test_bot_identity(self):
        self.assertEqual(app_token.bot_identity("question-zero-reviewer", caller=Fake()),
                         ("question-zero-reviewer[bot]", "99+question-zero-reviewer[bot]@users.noreply.github.com"))


class Registration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.returned = {"id": 42, "slug": "question-zero-editor", "pem": "SECRET-PEM", "client_secret": "SECRET-CS",
                         "webhook_secret": "SECRET-WS"}
        self.flow = register.Flow("editor", Path(self.tmp.name) / "s", converter=lambda code: dict(self.returned))

    def tearDown(self):
        self.tmp.cleanup()

    def test_wrong_state_is_refused_without_conversion(self):
        status, msg = self.flow.callback("code=abc&state=wrong")
        self.assertEqual(status, 400)
        self.assertFalse(self.flow.used)

    def test_success_saves_everything_and_reveals_nothing(self):
        out = io.StringIO()
        with redirect_stdout(out):
            status, msg = self.flow.callback(f"code=abc&state={self.flow.state}")
        self.assertEqual(status, 200)
        for secret in ("abc", "SECRET-PEM", "SECRET-CS", "SECRET-WS"):
            self.assertNotIn(secret, msg + out.getvalue())
        saved = json.loads(self.flow.saved[2].read_text(encoding="utf-8"))
        self.assertEqual(saved, self.returned)

    def test_the_link_is_single_use(self):
        self.flow.callback(f"code=abc&state={self.flow.state}")
        status, _ = self.flow.callback(f"code=def&state={self.flow.state}")
        self.assertEqual(status, 410)

    def test_the_start_page_carries_the_reviewed_manifest(self):
        m = register.manifest("editor", 5555)
        self.assertEqual(m["redirect_url"], "http://127.0.0.1:5555/callback")
        self.assertEqual(m["default_permissions"], {"contents": "write", "pull_requests": "write", "issues": "write",
                                                    "metadata": "read"})
        self.assertNotIn("workflows", m["default_permissions"])
        self.assertEqual(register.manifest("reviewer", 1)["default_permissions"], {"metadata": "read"})
        self.assertIn(self.flow.state.replace("-", "-"), register.start_page(m, self.flow.state))


if __name__ == "__main__":
    unittest.main()
