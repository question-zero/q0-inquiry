# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): the two jobs of the advisory feedback workflow. The parse job holds only read permissions and emits a typed result; the publish job holds only comment permissions, re-reads the item, and renders from fixed templates.
# license: MIT (LICENSE-CODE)
"""The two jobs of .github/workflows/round-3-feedback.yml. Trusted code from the default branch only.

  python tools/round_03_feedback_job.py parse     read-only token; writes `result` to $GITHUB_OUTPUT
  python tools/round_03_feedback_job.py publish   comment-write token; reads RESULT from the environment

Everything about the triggering item (route, number, version, repository) comes from the event payload file that
GitHub writes ($GITHUB_EVENT_PATH), read as JSON, never through shell interpolation. Submitted content is fetched
through the API as data, bounded, and never written into the workspace's code paths or executed. Logs print fixed
messages and identifiers only. The publish job re-reads the item and does nothing if it changed since the parse job
ran, so a stale result can't replace newer feedback.
"""
import base64
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_round_03_feedback as rf  # noqa: E402
import validate_round_03_response as v  # noqa: E402

API = "https://api.github.com"
RESPONSE_PATH = re.compile(r"^rounds/03-open/responses/[a-z0-9][a-z0-9-]*\.md$")
MAX_PAGES = 5
BOT = "github-actions[bot]"


def api(method, url, token, data=None, accept="application/vnd.github+json"):
    req = urllib.request.Request(url if url.startswith("http") else API + url, method=method,
                                 data=None if data is None else json.dumps(data).encode("utf-8"))
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", accept)
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read(v.MAX_BYTES * 2 + 1)
        return json.loads(body) if body else None


def event():
    return json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))


def item(ev):
    """(route, number, base repository) from the event; the version is established separately."""
    base = ev["repository"]["full_name"]
    if "pull_request" in ev:
        return "file", int(ev["pull_request"]["number"]), base
    return "issue", int(ev["issue"]["number"]), base


def current_pr(base, number, token):
    pr = api("GET", f"/repos/{base}/pulls/{number}", token)
    return pr["head"]["sha"], pr["head"]["repo"]["full_name"] if pr["head"]["repo"] else None


def response_files(base, number, token):
    files = []
    for page in range(1, MAX_PAGES + 1):
        got = api("GET", f"/repos/{base}/pulls/{number}/files?per_page=100&page={page}", token)
        files += got
        if len(got) < 100:
            break
    return [f["filename"] for f in files if f.get("status") != "removed" and RESPONSE_PATH.match(f["filename"])]


def fetch_file(head_repo, path, sha, token):
    """The file's bytes at the head commit, or None if it isn't a regular file within the size limit."""
    meta = api("GET", f"/repos/{head_repo}/contents/{path}?ref={sha}", token)
    if not isinstance(meta, dict) or meta.get("type") != "file" or meta.get("size", v.MAX_BYTES + 1) > v.MAX_BYTES:
        return None
    if meta.get("encoding") != "base64":
        return None
    return base64.b64decode(meta["content"])


def write_output(name, value):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def parse():
    token, ev = os.environ["GH_TOKEN"], event()
    route, number, base = item(ev)
    if route == "issue":
        body = (ev["issue"].get("body") or "").encode("utf-8")[:v.MAX_BYTES + 1]
        result = v.validate("issue", body, number, None)
    else:
        sha = ev["pull_request"]["head"]["sha"]
        head_repo = ev["pull_request"]["head"]["repo"]["full_name"] if ev["pull_request"]["head"]["repo"] else None
        if not re.fullmatch(r"[0-9a-f]{40}", sha) or head_repo is None:
            print("skipped: the pull request's head is not usable")
            return
        now_sha, now_repo = current_pr(base, number, token)
        if (now_sha, now_repo) != (sha, head_repo):
            print("skipped: the pull request moved on; a newer run handles it")
            return
        paths = response_files(base, number, token)
        extra = set()
        if not paths:
            print("skipped: no Round 3 response file in this pull request")
            return
        if len(paths) > 1:
            extra.add("pr_several_response_files")
        data = fetch_file(head_repo, paths[0], sha, token)
        if data is None:
            data = b""
            extra.add("pr_file_not_regular_or_too_large")
        result = v.validate("file", data, number, sha)
        if extra:
            result["codes"] = sorted(set(result["codes"]) | extra)
            if "pr_file_not_regular_or_too_large" in extra:
                result["checked"], result["assessments"] = False, {}
                result["counts"] = {s: 0 for s in sorted(v.STATUSES)}
                result["codes"] = [c for c in result["codes"] if not c.startswith(("header_", "field_missing"))]
    write_output("result", json.dumps(result, sort_keys=True, separators=(",", ":")))
    print(f"parsed {route} {number}: checked={result['checked']}, {len(result['codes'])} codes")


def publish():
    token, ev = os.environ["GH_TOKEN"], event()
    raw = os.environ.get("RESULT", "")
    if not raw:
        print("nothing to publish")
        return
    if len(raw) > 64 * 1024:
        raise SystemExit("refused: the result is larger than any valid result")
    route, number, base = item(ev)
    result = json.loads(raw)
    # Re-read the item now; publish only if it is still the version that was checked.
    if route == "file":
        version, _ = current_pr(base, number, token)
    else:
        issue = api("GET", f"/repos/{base}/issues/{number}", token)
        version = hashlib.sha256((issue.get("body") or "").encode("utf-8")[:v.MAX_BYTES + 1]).hexdigest()
    if result.get("version") != version:
        print("skipped: the item changed after it was checked; the newer run publishes")
        return
    body = rf.render(result, route, number, version)
    mine = None
    for page in range(1, MAX_PAGES + 1):
        got = api("GET", f"/repos/{base}/issues/{number}/comments?per_page=100&page={page}", token)
        for c in got:
            if c.get("user", {}).get("login") == BOT and (c.get("body") or "").startswith(rf.MARKER):
                mine = c["id"]
        if len(got) < 100:
            break
    if mine:
        api("PATCH", f"/repos/{base}/issues/comments/{mine}", token, {"body": body})
        print(f"updated the feedback comment on {route} {number}")
    else:
        api("POST", f"/repos/{base}/issues/{number}/comments", token, {"body": body})
        print(f"posted feedback on {route} {number}")


if __name__ == "__main__":
    try:
        {"parse": parse, "publish": publish}[sys.argv[1]]()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GitHub API error {e.code}") from None
