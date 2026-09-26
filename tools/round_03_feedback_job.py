# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): the two jobs of the advisory feedback workflow. Revision 2 applies GPT-6's AC4-AC6 (critiques/2026-09-26-gpt-6--automation-code-review.md): one pinned trusted revision checked by both jobs; an explicit "no current response" update when a managed item stops holding a response; the source re-read after the comment lookup, immediately before writing; exhaustive pagination or an explicit incomplete result; a Git blob-mode check at the head commit; the complete body's digest as an issue's version.
# license: MIT (LICENSE-CODE)
"""The two jobs of the Round 3 advisory feedback workflow. Trusted code from one pinned revision only.

  python tools/round_03_feedback_job.py parse     read-only token; writes `result` and `trusted_sha` to $GITHUB_OUTPUT
  python tools/round_03_feedback_job.py publish   comment-write token; reads RESULT and TRUSTED_SHA from the environment

Everything about the triggering item (route, number, repository) comes from the event payload file that GitHub writes
($GITHUB_EVENT_PATH), read as JSON, never through shell interpolation. Submitted content is fetched through the API
as data, bounded, and never written into the workspace's code paths or executed. Logs print fixed messages and
identifiers only.

A managed item is one that already carries this workflow's comment. When it stops holding a recognizable response
(a response file removed or renamed away, the form's headings removed), its comment is updated to say so. An item
that never had a comment and holds no response gets nothing.
"""
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_round_03_feedback as rf  # noqa: E402
import validate_round_03_response as v  # noqa: E402

API = "https://api.github.com"
RESPONSE_PATH = re.compile(r"^rounds/03-open/responses/[a-z0-9][a-z0-9-]*\.md$")
PER_PAGE = 100
MAX_PAGES = 30          # up to 3,000 files or comments; beyond that the result is explicitly incomplete
BOT = "github-actions[bot]"
REPO = v.ex.REPO        # the trusted checkout; tests point it at a synthetic repository
REGULAR_MODES = {"100644", "100755"}


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


def paged(path, token):
    """(items, complete). complete is False if the page budget ran out before the last page."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        sep = "&" if "?" in path else "?"
        got = api("GET", f"{path}{sep}per_page={PER_PAGE}&page={page}", token)
        items += got
        if len(got) < PER_PAGE:
            return items, True
    return items, False


def event():
    return json.loads(Path(os.environ["GITHUB_EVENT_PATH"]).read_text(encoding="utf-8"))


def item(ev):
    base = ev["repository"]["full_name"]
    if "pull_request" in ev:
        return "file", int(ev["pull_request"]["number"]), base
    return "issue", int(ev["issue"]["number"]), base


def head_sha(repo):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, check=True,
                          text=True).stdout.strip()


def managed_comment(base, number, token):
    """(comment id or None, complete). Only this workflow's bot identity with the marker counts."""
    comments, complete = paged(f"/repos/{base}/issues/{number}/comments", token)
    found = None
    for c in comments:
        if c.get("user", {}).get("login") == BOT and (c.get("body") or "").startswith(rf.MARKER):
            found = c["id"]
    return found, complete


def current_pr(base, number, token):
    pr = api("GET", f"/repos/{base}/pulls/{number}", token)
    return pr["head"]["sha"], pr["head"]["repo"]["full_name"] if pr["head"]["repo"] else None


def current_issue_digest(base, number, token):
    issue = api("GET", f"/repos/{base}/issues/{number}", token)
    body = (issue.get("body") or "").encode("utf-8")
    return hashlib.sha256(body).hexdigest(), body


def regular_blob(head_repo, sha, path, token):
    """The file's bytes if it is a regular blob (mode 100644/100755) within the limit at `sha`; else a reason."""
    tree = api("GET", f"/repos/{head_repo}/git/trees/{sha}?recursive=1", token)
    if not isinstance(tree, dict) or tree.get("truncated"):
        return None, "incomplete"
    entry = next((e for e in tree.get("tree", []) if e.get("path") == path), None)
    if entry is None:
        return None, "incomplete"
    if entry.get("type") != "blob" or entry.get("mode") not in REGULAR_MODES or \
            not isinstance(entry.get("size"), int) or entry["size"] > v.MAX_BYTES:
        return None, "not_regular"
    blob = api("GET", f"/repos/{head_repo}/git/blobs/{entry['sha']}", token)
    if blob.get("encoding") != "base64" or blob.get("size") != entry["size"]:
        return None, "incomplete"
    data = base64.b64decode(blob["content"])
    if len(data) != entry["size"]:
        return None, "incomplete"
    return data, None


def write_output(name, value):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def parse_pr(ev, base, number, token):
    sha = ev["pull_request"]["head"]["sha"]
    head_repo = ev["pull_request"]["head"]["repo"]["full_name"] if ev["pull_request"]["head"]["repo"] else None
    if not re.fullmatch(r"[0-9a-f]{40}", sha) or head_repo is None:
        print("skipped: the pull request's head is not usable")
        return None
    if current_pr(base, number, token) != (sha, head_repo):
        print("skipped: the pull request moved on; a newer run handles it")
        return None
    files, complete = paged(f"/repos/{base}/pulls/{number}/files", token)
    paths = [f["filename"] for f in files if f.get("status") != "removed" and RESPONSE_PATH.match(f["filename"])]
    if not complete:
        return v.incomplete("file", number, sha, REPO)
    if not paths:
        mine, _ = managed_comment(base, number, token)
        return v.no_current_response("file", number, sha, REPO) if mine else None
    extra = {"pr_several_response_files"} if len(paths) > 1 else set()
    data, why = regular_blob(head_repo, sha, paths[0], token)
    if why == "incomplete":
        return v.incomplete("file", number, sha, REPO, extra=extra)
    if why == "not_regular":
        return v.build("file", number, sha, REPO, {"pr_file_not_regular_or_too_large", *extra}, {}, False)
    result = v.validate("file", data, number, sha, REPO)
    if extra:
        result = v.build("file", number, sha, REPO, set(result["codes"]) | extra, result["assessments"],
                         result["checked"])
    return result


def parse_issue(ev, base, number, token):
    body = (ev["issue"].get("body") or "").encode("utf-8")
    if v.is_form_issue(body.decode("utf-8", "replace")):
        return v.validate("issue", body, number, None, REPO)
    mine, _ = managed_comment(base, number, token)
    return v.no_current_response("issue", number, hashlib.sha256(body).hexdigest(), REPO) if mine else None


def parse():
    token, ev = os.environ["GH_TOKEN"], event()
    route, number, base = item(ev)
    trusted = head_sha(REPO)
    write_output("trusted_sha", trusted)
    result = parse_pr(ev, base, number, token) if route == "file" else parse_issue(ev, base, number, token)
    if result is None:
        return
    if result["validator_revision"] != trusted:
        raise SystemExit("refused: the validator's revision is not the pinned trusted revision")
    write_output("result", json.dumps(result, sort_keys=True, separators=(",", ":")))
    print(f"parsed {route} {number}: checked={result['checked']}, {len(result['codes'])} codes")


def current_version(route, base, number, token):
    if route == "file":
        return current_pr(base, number, token)[0]
    return current_issue_digest(base, number, token)[0]


def publish():
    token, ev = os.environ["GH_TOKEN"], event()
    raw, trusted = os.environ.get("RESULT", ""), os.environ.get("TRUSTED_SHA", "")
    if not raw:
        print("nothing to publish")
        return
    if len(raw) > 64 * 1024:
        raise SystemExit("refused: the result is larger than any valid result")
    if not re.fullmatch(r"[0-9a-f]{40}", trusted) or head_sha(REPO) != trusted:
        raise SystemExit("refused: this job is not running the pinned trusted revision")
    route, number, base = item(ev)
    result = json.loads(raw)
    mine, complete = managed_comment(base, number, token)
    # Re-read the source after the comment lookup, immediately before writing: publish only the checked version.
    version = current_version(route, base, number, token)
    try:
        body = rf.render(result, route, number, version, trusted, REPO)   # refuses any other version or revision
    except ValueError:
        print("skipped: the result is not for the current version, or not from the pinned revision")
        return
    if mine:
        api("PATCH", f"/repos/{base}/issues/comments/{mine}", token, {"body": body})
        print(f"updated the feedback comment on {route} {number}")
    elif complete:
        api("POST", f"/repos/{base}/issues/{number}/comments", token, {"body": body})
        print(f"posted feedback on {route} {number}")
    else:
        print("skipped: could not establish whether a feedback comment already exists")


if __name__ == "__main__":
    try:
        {"parse": parse, "publish": publish}[sys.argv[1]]()
    except urllib.error.HTTPError as e:
        raise SystemExit(f"GitHub API error {e.code}") from None
