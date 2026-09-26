# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D1 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): registration of the organization's GitHub Apps through the manifest flow, run by the founder on their own machine. Revision 2 applies GPT-6's AC2 (critiques/2026-09-26-gpt-6--automation-code-review.md): the destination is refused if it or any ancestor is in a repository, failing closed; the returned slug is checked; access is restricted and verified before any secret is written; failures leave no file and show only fixed messages; the server and its timer always stop.
# license: MIT (LICENSE-CODE)
"""Register one of Question Zero's GitHub Apps from its reviewed manifest. Run by the founder, locally, once per App.

Usage: python tools/github_apps/register.py editor|reviewer --secrets DIR [--sandbox]

With --sandbox, the App is registered as question-zero-<which>-sandbox, for the separately authorized controlled test
only; it is installed on the private sandbox repository alone and deleted after the test.

1. DIR is checked first: neither it nor any ancestor may be (or be inside) a git repository. If that can't be
   determined, the script refuses.
2. The script serves a page on a random loopback port only (127.0.0.1), with a fresh single-use state value.
3. The founder opens that page in a browser signed in to GitHub. It sends the manifest to the organization's
   "new GitHub App" page, where the founder reviews it and clicks Create.
4. GitHub redirects back with a one-time code. The script checks the state, converts the code once, and checks that
   the returned App is the expected one. It creates DIR, restricts it and an empty credential file to the current
   user, verifies both restrictions, and only then writes the credentials. On any failure the file is removed. It
   never prints, logs or echoes the code, a credential or an exception. The server stops after one callback, a
   failure, or 10 minutes.
5. Registration is not installation. The script prints the App's installation page, where the founder chooses the
   repositories and approves the permissions.

The reviewer App's key is saved but never used: that App is an attribution label only.
"""
import argparse
import html
import http.server
import json
import os
import secrets
import stat
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

ORG = "question-zero"
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
TIMEOUT_S = 600


def expected_slug(which, sandbox):
    return f"question-zero-{which}" + ("-sandbox" if sandbox else "")


def manifest(which, port, sandbox=False):
    m = json.loads((HERE / f"{which}.manifest.json").read_text(encoding="utf-8"))
    m["redirect_url"] = f"http://127.0.0.1:{port}/callback"
    if sandbox:
        m["name"] += "-sandbox"
        m["url"] = f"https://github.com/{ORG}/q0-sandbox"
        m["description"] = "Controlled test only; deleted after the test. " + m["description"]
    return m


def start_page(m, state):
    target = f"https://github.com/organizations/{ORG}/settings/apps/new?state={urllib.parse.quote(state)}"
    return ("<!doctype html><meta charset=utf-8><title>Register a Question Zero App</title>"
            f"<p>This sends the reviewed manifest for <b>{html.escape(m['name'])}</b> to GitHub. "
            "Review it there, then click <i>Create GitHub App</i>.</p>"
            f"<form method=post action=\"{html.escape(target)}\">"
            f"<input type=hidden name=manifest value=\"{html.escape(json.dumps(m))}\">"
            "<button type=submit>Continue to GitHub</button></form>")


def in_repository(path):
    """True if `path` or any ancestor is a git repository or inside one. Raises if that can't be determined."""
    p = Path(os.path.abspath(path))
    if p == REPO or REPO in p.parents:
        return True
    for d in [p, *p.parents]:
        if (d / ".git").exists():
            return True
    nearest = next((d for d in [p, *p.parents] if d.exists()), None)
    if nearest is None:
        raise OSError("no existing ancestor")
    r = subprocess.run(["git", "-C", str(nearest), "rev-parse", "--is-inside-work-tree"], capture_output=True,
                       text=True)
    if r.returncode == 0:
        return True
    if "not a git repository" in (r.stderr or "").lower():
        return False
    raise OSError("could not determine")


def principal():
    """The effective Windows account, as `whoami` reports it (not USERNAME)."""
    return subprocess.run(["whoami"], capture_output=True, check=True, text=True).stdout.strip()


def restrict(path, is_dir=False):
    """Limit `path` to the current user and verify it. Raises on failure."""
    if os.name == "nt":
        who = principal()
        grant = f"{who}:(OI)(CI)F" if is_dir else f"{who}:F"
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", grant], capture_output=True, check=True)
        out = subprocess.run(["icacls", str(path)], capture_output=True, check=True, text=True).stdout
        names = set()
        for line in out.splitlines():
            line = line.replace(str(path), "", 1).strip()
            if ":(" in line:
                names.add(line.split(":(", 1)[0].strip().lower())
        if names != {who.lower()}:
            raise PermissionError("access is not limited to the current user")
    else:
        os.chmod(path, 0o700 if is_dir else 0o600)
        mode = stat.S_IMODE(os.stat(path).st_mode)
        if mode & 0o077:
            raise PermissionError("access is not limited to the current user")


def convert(code):
    req = urllib.request.Request(f"https://api.github.com/app-manifests/{urllib.parse.quote(code)}/conversions",
                                 method="POST", headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read(1024 * 1024))


class Flow:
    def __init__(self, which, secrets_dir, converter=convert, sandbox=False):
        self.which, self.dir, self.converter, self.sandbox = which, Path(secrets_dir), converter, sandbox
        self.state = secrets.token_urlsafe(32)
        self.used = False
        self.saved = None
        self.done = threading.Event()

    def store(self, data):
        """Write the credentials only after the folder and an empty file are restricted and verified."""
        self.dir.mkdir(parents=True, exist_ok=True)
        restrict(self.dir, is_dir=True)
        path = self.dir / f"{data['slug']}.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            os.close(fd)
            restrict(path)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except BaseException:
            path.unlink(missing_ok=True)
            raise
        return path

    def callback(self, query):
        """Handle the redirect. Returns (status, fixed message); never includes the code or credentials."""
        q = urllib.parse.parse_qs(query)
        if self.used:
            return 410, "This registration link has already been used."
        if q.get("state", [""])[0] != self.state or not q.get("code", [""])[0]:
            return 400, "The state did not match. Nothing was registered by this script."
        self.used = True
        try:
            data = self.converter(q["code"][0])
            if not isinstance(data, dict) or data.get("slug") != expected_slug(self.which, self.sandbox):
                self.done.set()
                return 502, ("GitHub returned a different App than expected. Nothing was saved; delete that App in "
                             "the organization's settings.")
            path = self.store(data)
        except Exception:  # noqa: BLE001 - never echo an exception: it could contain a credential
            self.done.set()
            return 500, "Registration could not be completed. Nothing was saved by this script."
        self.saved = (data["slug"], data.get("id"), path)
        self.done.set()
        return 200, "Registered. You can close this page; the terminal shows the next step."


def serve(flow):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # never log request lines: they contain the one-time code
            pass

        def do_GET(self):
            try:
                u = urllib.parse.urlsplit(self.path)
                if u.path == "/start" and not flow.used:
                    status, body = 200, start_page(manifest(flow.which, self.server.server_port, flow.sandbox),
                                                   flow.state)
                elif u.path == "/callback":
                    status, body = flow.callback(u.query)
                    body = f"<!doctype html><meta charset=utf-8><p>{html.escape(body)}</p>"
                else:
                    status, body = 404, "Not found."
            except Exception:  # noqa: BLE001
                status, body = 500, "Error."
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def handle_error(self, *a):  # pragma: no cover - never print tracebacks
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    server.handle_error = lambda *a: None
    return server


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("which", choices=("editor", "reviewer"))
    ap.add_argument("--secrets", required=True, help="a private folder outside every repository")
    ap.add_argument("--sandbox", action="store_true", help="register the controlled-test variant")
    a = ap.parse_args(argv)
    try:
        inside = in_repository(a.secrets)
    except OSError:
        raise SystemExit("refused: could not determine whether the secrets folder is inside a git repository")
    if inside:
        raise SystemExit("refused: the secrets folder is inside a git repository")
    flow = Flow(a.which, Path(os.path.abspath(a.secrets)), sandbox=a.sandbox)
    server = serve(flow)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print(f"Open http://127.0.0.1:{server.server_port}/start in a browser signed in to GitHub (expires in 10 minutes).")
    try:
        flow.done.wait(TIMEOUT_S)
    finally:
        server.shutdown()
        server.server_close()
    if not flow.saved:
        raise SystemExit("No App was registered by this script.")
    slug, app_id, path = flow.saved
    print(f"Registered {slug} (App ID {app_id}). Its credentials are in {path}, readable by you only.")
    print(f"Next, install it on the selected repositories: https://github.com/apps/{slug}/installations/new")


if __name__ == "__main__":
    main()
