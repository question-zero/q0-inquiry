# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D1 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): short-lived, narrowly scoped installation tokens for the editor App, used locally by the editor. The credential handling follows GPT-6's GA5 text in the proposal.
# license: MIT (LICENSE-CODE)
"""Run one command with a short-lived editor-App token in its environment only, then revoke the token.

Usage:
  python tools/github_apps/app_token.py --secrets DIR --repo q0-inquiry --perm contents=write --perm pull_requests=write \
      -- git push origin my-branch

The token is minted for exactly one repository and the listed permissions, which must be a subset of the App's
installation. It reaches the command only through its environment: GH_TOKEN for the gh CLI, and a one-shot git
credential helper that reads it from the environment. It is never printed, never written to a file, never placed in a
command argument, a remote URL or persistent git configuration. The script checks the App, installation and repository
IDs it expects, and revokes the token when the command ends, whatever its result.

Commits made this way should name the App's bot account as author: see bot_identity().
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

API = "https://api.github.com"
ORG = "question-zero"
SLUG = "question-zero-editor"
ALLOWED_REPOS = {"q0-inquiry", ".github"}
ALLOWED_PERMS = {"contents": {"read", "write"}, "pull_requests": {"read", "write"}, "issues": {"read", "write"},
                 "metadata": {"read"}}
# A git credential helper that answers from the environment; the token never appears in its arguments.
HELPER = '!f() { echo username=x-access-token; echo "password=$Q0_APP_TOKEN"; }; f'


def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def app_jwt(app_id, pem, now=None):
    """An RS256 JWT for the App, valid for 9 minutes (GitHub allows at most 10)."""
    now = int(now if now is not None else time.time())
    header = b64url(json.dumps({"alg": "RS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps({"iat": now - 60, "exp": now + 540, "iss": str(app_id)},
                                separators=(",", ":")).encode())
    key = serialization.load_pem_private_key(pem.encode() if isinstance(pem, str) else pem, password=None)
    sig = key.sign(f"{header}.{payload}".encode(), padding.PKCS1v15(), hashes.SHA256())
    return f"{header}.{payload}.{b64url(sig)}"


def parse_perms(items):
    perms = {}
    for item in items:
        name, _, level = item.partition("=")
        if level not in ALLOWED_PERMS.get(name, set()):
            raise SystemExit(f"refused: permission {name}={level} is not one this tool may request")
        perms[name] = level
    if not perms:
        raise SystemExit("refused: name the permissions this operation needs")
    return perms


def call(method, path, auth, data=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=None if data is None else json.dumps(data).encode())
    req.add_header("Authorization", auth)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
        return json.loads(body) if body else None


def mint(creds, repo, perms, caller=call):
    """(token, expires_at) for one repository and a subset of permissions, after checking the expected IDs."""
    if repo not in ALLOWED_REPOS:
        raise SystemExit(f"refused: {repo} is not a repository this App is meant for")
    if creds.get("slug") != SLUG:
        raise SystemExit("refused: these are not the editor App's credentials")
    jwt = "Bearer " + app_jwt(creds["id"], creds["pem"])
    app = caller("GET", "/app", jwt)
    if app.get("id") != creds["id"] or app.get("slug") != SLUG:
        raise SystemExit("refused: the key does not belong to the expected App")
    inst = caller("GET", f"/orgs/{ORG}/installation", jwt)
    if inst.get("app_id") != creds["id"]:
        raise SystemExit("refused: the installation is not the expected App's")
    granted = inst.get("permissions", {})
    for name, level in perms.items():
        if granted.get(name) not in ({"write"} if level == "write" else {"read", "write"}):
            raise SystemExit(f"refused: the installation does not grant {name}={level}")
    got = caller("POST", f"/app/installations/{inst['id']}/access_tokens", jwt,
                 {"repositories": [repo], "permissions": perms})
    if [r.get("name") for r in got.get("repositories", [])] != [repo]:
        caller("DELETE", "/installation/token", "Bearer " + got["token"])
        raise SystemExit("refused: GitHub returned a token for other repositories than requested")
    return got["token"], got["expires_at"]


def bot_identity(slug, caller=call):
    """(name, email) for commits authored by an App's bot account."""
    user = caller("GET", f"/users/{slug}%5Bbot%5D", "")
    return f"{slug}[bot]", f"{user['id']}+{slug}[bot]@users.noreply.github.com"


def run(command, token):
    env = dict(os.environ, GH_TOKEN=token, Q0_APP_TOKEN=token, GIT_TERMINAL_PROMPT="0")
    env.pop("GITHUB_TOKEN", None)
    # One-shot configuration through the environment, not arguments: GIT_CONFIG_COUNT/KEY/VALUE (git 2.31+).
    env.update({"GIT_CONFIG_COUNT": "2", "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "",
                "GIT_CONFIG_KEY_1": "credential.helper", "GIT_CONFIG_VALUE_1": HELPER})
    return subprocess.run(command, env=env).returncode


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("--secrets", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--perm", action="append", default=[])
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    command = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not command:
        raise SystemExit("refused: give the command to run after --")
    creds = json.loads((Path(a.secrets) / f"{SLUG}.json").read_text(encoding="utf-8"))
    token, expires = mint(creds, a.repo, parse_perms(a.perm))
    print(f"token for {a.repo} ({', '.join(f'{k}={v}' for k, v in sorted(parse_perms(a.perm).items()))}), "
          f"expires {expires}")
    try:
        code = run(command, token)
    finally:
        try:
            call("DELETE", "/installation/token", "Bearer " + token)
            print("token revoked")
        except Exception:  # noqa: BLE001 - the token still expires within the hour
            print("could not revoke the token; it expires within the hour")
    sys.exit(code)


if __name__ == "__main__":
    main()
