# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D1 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): registration of the organization's GitHub Apps through the manifest flow, run by the founder on their own machine. The credential handling follows GPT-6's GA5 text in the proposal.
# license: MIT (LICENSE-CODE)
"""Register one of Question Zero's GitHub Apps from its reviewed manifest. Run by the founder, locally, once per App.

Usage: python tools/github_apps/register.py editor|reviewer --secrets DIR [--sandbox]

With --sandbox, the App is registered as question-zero-<which>-sandbox, for the separately authorized controlled test
only; it is installed on the private sandbox repository alone and deleted after the test.

1. The script serves a page on a random loopback port only (127.0.0.1), with a fresh single-use state value.
2. The founder opens that page in a browser signed in to GitHub. It sends the manifest to the organization's
   "new GitHub App" page, where the founder reviews it and clicks Create.
3. GitHub redirects back to the loopback page with a one-time code. The script checks the state, converts the code
   once, writes every returned credential to DIR/<app-slug>.json with access limited to the current user, and exits.
   It never prints, logs or echoes the code or any credential. The server stops after one callback or 10 minutes.
4. Registration is not installation. The script prints the App's installation page; there the founder chooses the
   repositories (q0-inquiry and .github) and approves the permissions.

DIR must be outside every repository, for example the private folder next to q0-inquiry. The reviewer App's key is
saved but never used: that App is an attribution label only.
"""
import argparse
import html
import http.server
import json
import os
import secrets
import subprocess
import sys
import threading
import urllib.parse
import urllib.request
from pathlib import Path

ORG = "question-zero"
HERE = Path(__file__).resolve().parent
TIMEOUT_S = 600


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


def restrict(path):
    """Limit a file to the current user. On Windows, gitignore is not access control (GA5): use icacls."""
    if os.name == "nt":
        user = os.environ.get("USERNAME", "")
        subprocess.run(["icacls", str(path), "/inheritance:r", "/grant:r", f"{user}:(R,W)"],
                       capture_output=True, check=True)
    else:
        os.chmod(path, 0o600)


def convert(code):
    req = urllib.request.Request(f"https://api.github.com/app-manifests/{urllib.parse.quote(code)}/conversions",
                                 method="POST", headers={"Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


class Flow:
    def __init__(self, which, secrets_dir, converter=convert, sandbox=False):
        self.which, self.dir, self.converter, self.sandbox = which, Path(secrets_dir), converter, sandbox
        self.state = secrets.token_urlsafe(32)
        self.used = False
        self.saved = None

    def callback(self, query):
        """Handle the redirect. Returns (http status, fixed message); never includes the code or credentials."""
        q = urllib.parse.parse_qs(query)
        if self.used:
            return 410, "This registration link has already been used."
        if q.get("state", [""])[0] != self.state or not q.get("code", [""])[0]:
            return 400, "The state did not match. Nothing was registered by this script."
        self.used = True
        data = self.converter(q["code"][0])
        slug = data.get("slug") or f"question-zero-{self.which}" + ("-sandbox" if self.sandbox else "")
        self.dir.mkdir(parents=True, exist_ok=True)
        path = self.dir / f"{slug}.json"
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        restrict(path)
        self.saved = (slug, data.get("id"), path)
        return 200, "Registered. You can close this page; the terminal shows the next step."


def serve(flow):
    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):  # never log request lines: they contain the one-time code
            pass

        def do_GET(self):
            u = urllib.parse.urlsplit(self.path)
            if u.path == "/start" and not flow.used:
                status, body = 200, start_page(manifest(flow.which, self.server.server_port, flow.sandbox), flow.state)
            elif u.path == "/callback":
                status, body = flow.callback(u.query)
                body = f"<!doctype html><meta charset=utf-8><p>{html.escape(body)}</p>"
            else:
                status, body = 404, "Not found."
            data = body.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)
            if u.path == "/callback" and flow.saved:
                threading.Thread(target=self.server.shutdown, daemon=True).start()

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Timer(TIMEOUT_S, server.shutdown).start()
    return server


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("which", choices=("editor", "reviewer"))
    ap.add_argument("--secrets", required=True, help="a private folder outside every repository")
    ap.add_argument("--sandbox", action="store_true", help="register the controlled-test variant")
    a = ap.parse_args(argv)
    target = Path(a.secrets).resolve()
    top = subprocess.run(["git", "-C", str(target.parent), "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if top.returncode == 0:
        raise SystemExit("refused: the secrets folder is inside a git repository")
    flow = Flow(a.which, target, sandbox=a.sandbox)
    server = serve(flow)
    print(f"Open http://127.0.0.1:{server.server_port}/start in a browser signed in to GitHub (expires in 10 minutes).")
    server.serve_forever()
    if not flow.saved:
        raise SystemExit("No App was registered.")
    slug, app_id, path = flow.saved
    print(f"Registered {slug} (App ID {app_id}). Its credentials are in {path}, readable by you only.")
    print(f"Next, install it on the selected repositories: https://github.com/apps/{slug}/installations/new")


if __name__ == "__main__":
    main()
