# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D1 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): short-lived, narrowly scoped installation tokens for the editor App, used locally by the editor. Revision 2 applies GPT-6's AC1 and AC3 (critiques/2026-09-26-gpt-6--automation-code-review.md): the credential helper answers only the approved destination; the App, installation and repository identities are checked against a founder-approved mapping; the returned scope and expiry are validated; a token is revoked as soon as anything fails; an unconfirmed revocation is a distinct failure.
# license: MIT (LICENSE-CODE)
"""Run one command with a short-lived editor-App token in its environment only, then revoke the token.

Usage:
  python tools/github_apps/app_token.py approve --secrets DIR [--sandbox] --repo NAME [--confirm INSTALLATION_ID]
  python tools/github_apps/app_token.py run --secrets DIR [--sandbox] --repo NAME --perm contents=write ... -- CMD...

`approve` looks up the App, the installation on the repository, and the repository's owner and numeric ID, and
prints them. Nothing is written until the founder has confirmed them and the command is repeated with --confirm and
the installation ID; the mapping is then saved as DIR/<slug>.approved.json. `run` refuses unless every identity
matches that mapping.

The token is minted for exactly the approved repository ID and the listed permissions, which must be a subset of the
installation's grant. It reaches the command only through its environment: GH_TOKEN for the gh CLI, and a git
credential helper (git_credential_helper.py) that answers only for the approved https://github.com/<owner>/<repo>
path. Global and system git configuration, other credential helpers, extra HTTP headers, git tracing and askpass
programs are switched off for the command. The token is never printed, never written to a file, and never placed in a
command argument, a remote URL or persistent git configuration. It is revoked as soon as the command ends or any check
fails; if revocation can't be confirmed, the exit status is 3 whatever the command's own status was.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

API = "https://api.github.com"
HOST = "github.com"
ORG = "question-zero"
SLUG = "question-zero-editor"
HERE = Path(__file__).resolve().parent
# Each App may be used only on its own repositories; the sandbox variant exists only for the controlled test.
ALLOWED_REPOS = {"question-zero-editor": {"q0-inquiry", ".github"}, "question-zero-editor-sandbox": {"q0-sandbox"}}
ALLOWED_PERMS = {"contents": {"read", "write"}, "pull_requests": {"read", "write"}, "issues": {"read", "write"}}
IMPLICIT = {"metadata": "read"}   # GitHub always includes metadata read in an installation token
REVOKE_UNCONFIRMED = 3
SCRUB = ("GITHUB_TOKEN", "GH_ENTERPRISE_TOKEN", "GITHUB_ENTERPRISE_TOKEN", "GH_HOST", "GIT_ASKPASS", "SSH_ASKPASS",
         "GIT_TRACE", "GIT_TRACE_CURL", "GIT_TRACE_PACKET", "GIT_TRACE_PERFORMANCE", "GIT_TRACE_SETUP",
         "GIT_TRACE2", "GIT_TRACE2_EVENT", "GIT_TRACE2_PERF", "GIT_CURL_VERBOSE", "GIT_CONFIG_PARAMETERS")


class Refused(SystemExit):
    pass


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
            raise Refused(f"refused: permission {name}={level} is not one this tool may request")
        perms[name] = level
    if not perms:
        raise Refused("refused: name the permissions this operation needs")
    return perms


def call(method, path, auth, data=None):
    req = urllib.request.Request(API + path, method=method,
                                 data=None if data is None else json.dumps(data).encode())
    if auth:
        req.add_header("Authorization", auth)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read(1024 * 1024)
        return json.loads(body) if body else None


def covers(granted, level):
    return granted == "write" or granted == level


def check_returned(got, approved, repo, perms, now):
    """Problems with a minted token's response, or an empty list. Called only after revocation is guaranteed."""
    problems = []
    repos = got.get("repositories")
    want = approved["repositories"][repo]
    if not isinstance(repos, list) or len(repos) != 1 or repos[0].get("id") != want["id"] or \
            repos[0].get("full_name") != f"{want['owner']}/{repo}":
        problems.append("repository")
    returned = got.get("permissions")
    if not isinstance(returned, dict):
        problems.append("permissions")
    else:
        for name, level in returned.items():
            if IMPLICIT.get(name) == level:
                continue
            if name not in perms or not covers(perms[name], level):
                problems.append("permissions")
                break
        if any(name not in returned for name in perms):
            problems.append("permissions")
    try:
        expires = datetime.strptime(got.get("expires_at", ""), "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        left = (expires - now).total_seconds()
        if not 60 < left <= 3700:
            problems.append("expiry")
    except (TypeError, ValueError):
        problems.append("expiry")
    return problems


def revoke(token, caller=call):
    try:
        caller("DELETE", "/installation/token", "Bearer " + token)
        return True
    except Exception:  # noqa: BLE001 - reported as a fixed, distinct failure
        return False


def mint(creds, approved, repo, perms, caller=call, slug=SLUG, now=None):
    """(token, expires_at) for the approved repository and a subset of permissions. Revokes on any failed check."""
    if slug not in ALLOWED_REPOS or repo not in ALLOWED_REPOS[slug]:
        raise Refused(f"refused: {repo} is not a repository this App is meant for")
    if creds.get("slug") != slug or approved.get("slug") != slug or approved.get("app_id") != creds.get("id"):
        raise Refused("refused: the credentials and the approved mapping are not for the expected App")
    if repo not in approved.get("repositories", {}):
        raise Refused("refused: this repository is not in the approved mapping")
    want = approved["repositories"][repo]
    jwt = "Bearer " + app_jwt(creds["id"], creds["pem"])
    app = caller("GET", "/app", jwt)
    if app.get("id") != creds["id"] or app.get("slug") != slug:
        raise Refused("refused: the key does not belong to the expected App")
    inst = caller("GET", f"/repos/{want['owner']}/{repo}/installation", jwt)
    if inst.get("id") != approved["installation_id"] or inst.get("app_id") != creds["id"]:
        raise Refused("refused: the installation is not the approved one")
    granted = inst.get("permissions", {})
    for name, level in perms.items():
        if not covers(granted.get(name), level):
            raise Refused(f"refused: the installation does not grant {name}={level}")
    got = caller("POST", f"/app/installations/{approved['installation_id']}/access_tokens", jwt,
                 {"repository_ids": [want["id"]], "permissions": perms})
    token = got.get("token") if isinstance(got, dict) else None
    if not token:
        raise Refused("refused: GitHub returned no token")
    try:
        problems = check_returned(got, approved, repo, perms, now or datetime.now(timezone.utc))
    except Exception:  # noqa: BLE001 - any surprise in the response counts as a failed check
        problems = ["response"]
    if problems:
        if not revoke(token, caller):
            raise Refused(REVOKE_UNCONFIRMED)
        raise Refused(f"refused: the returned token failed its checks ({', '.join(sorted(set(problems)))}); revoked")
    return token, got["expires_at"]


def bot_identity(slug, caller=call):
    """(name, email) for commits authored by an App's bot account."""
    user = caller("GET", f"/users/{slug}%5Bbot%5D", "")
    return f"{slug}[bot]", f"{user['id']}+{slug}[bot]@users.noreply.github.com"


def command_env(token, owner, repo, base=None):
    """The command's environment: the token, the approved destination, and git locked to the helper."""
    env = dict(base if base is not None else os.environ)
    for name in SCRUB:
        env.pop(name, None)
    helper = f'!"{Path(sys.executable).as_posix()}" "{(HERE / "git_credential_helper.py").as_posix()}"'
    env.update({"GH_TOKEN": token, "Q0_APP_TOKEN": token, "Q0_APP_DEST": f"{HOST}/{owner}/{repo}",
                "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never",
                "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_COUNT": "4",
                "GIT_CONFIG_KEY_0": "credential.helper", "GIT_CONFIG_VALUE_0": "",
                "GIT_CONFIG_KEY_1": "credential.helper", "GIT_CONFIG_VALUE_1": helper,
                "GIT_CONFIG_KEY_2": "credential.useHttpPath", "GIT_CONFIG_VALUE_2": "true",
                "GIT_CONFIG_KEY_3": "http.extraHeader", "GIT_CONFIG_VALUE_3": ""})
    return env


def run(command, token, owner, repo, seconds):
    try:
        return subprocess.run(command, env=command_env(token, owner, repo), timeout=max(1, seconds)).returncode
    except subprocess.TimeoutExpired:
        print("the command outlived the token's authorized lifetime and was stopped")
        return 124


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def approve(creds, slug, repo, confirm, secrets, caller=call):
    if slug not in ALLOWED_REPOS or repo not in ALLOWED_REPOS[slug]:
        raise Refused(f"refused: {repo} is not a repository this App is meant for")
    jwt = "Bearer " + app_jwt(creds["id"], creds["pem"])
    app = caller("GET", "/app", jwt)
    if app.get("id") != creds["id"] or app.get("slug") != slug:
        raise Refused("refused: the key does not belong to the expected App")
    inst = caller("GET", f"/repos/{ORG}/{repo}/installation", jwt)
    info = caller("GET", f"/repos/{ORG}/{repo}", "")
    mapping = {"slug": slug, "app_id": creds["id"], "installation_id": inst["id"],
               "repositories": {repo: {"owner": info["owner"]["login"], "id": info["id"]}}}
    print(f"App {slug} (ID {creds['id']}); installation {inst['id']}; repository "
          f"{info['owner']['login']}/{repo} (ID {info['id']}); granted {json.dumps(inst.get('permissions', {}))}")
    if confirm is None:
        print("Nothing saved. After the founder confirms these IDs, repeat with --confirm INSTALLATION_ID.")
        return None
    if confirm != inst["id"] or info["owner"]["login"] != ORG:
        raise Refused("refused: the confirmation does not match what GitHub reports")
    path = Path(secrets) / f"{slug}.approved.json"
    old = load(path) if path.exists() else None
    if old:
        if old.get("installation_id") != inst["id"] or old.get("app_id") != creds["id"]:
            raise Refused("refused: this differs from the approved mapping; the founder must replace it explicitly")
        old["repositories"].update(mapping["repositories"])
        mapping = old
    path.write_text(json.dumps(mapping, indent=2), encoding="utf-8")
    print(f"Saved {path}")
    return mapping


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("action", choices=("approve", "run"))
    ap.add_argument("--secrets", required=True)
    ap.add_argument("--repo", required=True)
    ap.add_argument("--sandbox", action="store_true", help="use the controlled-test App, on q0-sandbox only")
    ap.add_argument("--confirm", type=int)
    ap.add_argument("--perm", action="append", default=[])
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[argv.index("--") + 1:] if "--" in argv else []
    a = ap.parse_args(argv[:argv.index("--")] if "--" in argv else argv)
    slug = SLUG + ("-sandbox" if a.sandbox else "")
    creds = load(Path(a.secrets) / f"{slug}.json")
    if a.action == "approve":
        approve(creds, slug, a.repo, a.confirm, a.secrets)
        return
    if not command:
        raise Refused("refused: give the command to run after --")
    perms = parse_perms(a.perm)
    approved = load(Path(a.secrets) / f"{slug}.approved.json")
    token, expires = mint(creds, approved, a.repo, perms, slug=slug)
    code, revoked = 1, False
    try:
        left = (datetime.strptime(expires, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                - datetime.now(timezone.utc)).total_seconds() - 60
        print(f"token for {a.repo} ({', '.join(f'{k}={v}' for k, v in sorted(perms.items()))}), expires {expires}")
        code = run(command, token, approved["repositories"][a.repo]["owner"], a.repo, int(left))
    finally:
        revoked = revoke(token)
        print("token revoked" if revoked else "could not confirm that the token was revoked; it expires within the hour")
    sys.exit(code if revoked else REVOKE_UNCONFIRMED)


if __name__ == "__main__":
    try:
        main()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GitHub API error {e.code}") from None
