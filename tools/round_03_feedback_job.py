# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6): the two jobs of the advisory feedback workflow. Revision 2 applies GPT-6's AC4-AC6 (critiques/2026-09-26-gpt-6--automation-code-review.md): one pinned trusted revision checked by both jobs; an explicit "no current response" update when a managed item stops holding a response; the source re-read after the comment lookup, immediately before writing; exhaustive pagination or an explicit incomplete result; a Git blob-mode check at the head commit; the complete body's digest as an issue's version. Revision 3 applies GPT-6's round-2 findings (critiques/2026-09-26-gpt-6--automation-code-review-r2.md): every run checks the item's current version, read from the API, so an old rerun that cancels newer work still produces the current result; an oversized API response is an explicit incomplete state; the validator runs in a supervised subprocess whose time or memory limit gives a typed not-checked result. Revision 4 (topic automation-sandbox-report, GPT-6 SR3): a pull request whose head is not in this repository is skipped before anything is read from it.
# license: MIT (LICENSE-CODE)
"""The two jobs of the Round 3 advisory feedback workflow. Trusted code from one pinned revision only.

  python tools/round_03_feedback_job.py parse     read-only token; writes `result` and `trusted_sha` to $GITHUB_OUTPUT
  python tools/round_03_feedback_job.py publish   comment-write token; reads RESULT and TRUSTED_SHA from the environment

Everything about the triggering item (route, number, repository) comes from the event payload file that GitHub writes
($GITHUB_EVENT_PATH), read as JSON, never through shell interpolation. Submitted content is fetched through the API
as data, bounded, and never written into the workspace's code paths or executed. Logs print fixed messages and
identifiers only.

Every run checks the item's *current* version, read from the API, not the version in its own event. So an old
rerun that cancels a newer parse still produces the result for the current version, and any queued publisher only
publishes a result that still matches the item when it runs.

The validator runs in a separate process with time and memory limits. If a limit stops it, the result is a typed
"not checked" outcome for the known source, not a job failure.

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
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_round_03_feedback as rf  # noqa: E402
import validate_round_03_response as v  # noqa: E402

API = "https://api.github.com"
RESPONSE_PATH = re.compile(r"^rounds/03-open/responses/[a-z0-9][a-z0-9-]*\.md$")
PER_PAGE = 30          # small pages: 30 comments of GitHub's maximum size stay within MAX_RESPONSE
MAX_PAGES = 100         # up to 3,000 files or comments; beyond that the result is explicitly incomplete
MAX_RESPONSE = 8 * 1024 * 1024
VALIDATOR = Path(__file__).resolve().parent / "validate_round_03_response.py"
LIMIT_SECONDS = 60
LIMIT_MEMORY = 1536 * 1024 * 1024


class Incomplete(Exception):
    """GitHub's response was larger than this tool reads; the retrieval is incomplete, never silently truncated."""
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
        body = r.read(MAX_RESPONSE + 1)
    if len(body) > MAX_RESPONSE:
        raise Incomplete()
    return json.loads(body) if body else None


def paged(path, token):
    """(items, complete). complete is False if the page budget ran out or a page was too large to read."""
    items = []
    for page in range(1, MAX_PAGES + 1):
        sep = "&" if "?" in path else "?"
        try:
            got = api("GET", f"{path}{sep}per_page={PER_PAGE}&page={page}", token)
        except Incomplete:
            return items, False
        if not isinstance(got, list):
            return items, False
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
    try:
        return _regular_blob(head_repo, sha, path, token)
    except Incomplete:
        return None, "incomplete"


def _regular_blob(head_repo, sha, path, token):
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


def limits():  # pragma: no cover - POSIX only; runs in the child before the validator starts
    import resource
    resource.setrlimit(resource.RLIMIT_AS, (LIMIT_MEMORY, LIMIT_MEMORY))
    resource.setrlimit(resource.RLIMIT_CPU, (LIMIT_SECONDS, LIMIT_SECONDS))


def validate_isolated(route, data, number, version):
    """Run the validator in a child process with time and memory limits. A killed, failed or malformed run gives
    the typed resource outcome for the known source. The child reads only the temporary file."""
    if route == "issue":
        version = hashlib.sha256(data).hexdigest()
    with tempfile.TemporaryDirectory(dir=os.environ.get("RUNNER_TEMP")) as td:
        src = Path(td) / "source"
        src.write_bytes(data)
        cmd = [sys.executable, str(VALIDATOR), route, str(src), "--number", str(number), "--repo", str(REPO)]
        if route == "file":
            cmd += ["--version", version]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=LIMIT_SECONDS,
                               preexec_fn=limits if os.name == "posix" else None)
            result = json.loads(r.stdout[:64 * 1024]) if r.returncode == 0 else None
        except (subprocess.TimeoutExpired, ValueError, OSError):
            result = None
    cand_ids, _, _ = v.trusted_inputs(REPO)
    if result is None or v.schema_problems(result, cand_ids) or \
            (result["route"], result["number"], result["version"]) != (route, number, version):
        return v.resources(route, number, version, REPO)
    return result


def write_output(name, value):
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
        f.write(f"{name}={value}\n")


def parse_pr(ev, base, number, token):
    sha, head_repo = current_pr(base, number, token)     # the current head, whatever this run's event said
    if not re.fullmatch(r"[0-9a-f]{40}", sha or "") or head_repo is None:
        print("skipped: the pull request's current head is not usable")
        return None
    if head_repo != base:   # forks are not cleared (GPT-6 SR3); nothing is read from a foreign repository
        print("skipped: the pull request's head is not in this repository")
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
    result = validate_isolated("file", data, number, sha)
    if extra:
        result = v.build("file", number, sha, REPO, set(result["codes"]) | extra, result["assessments"],
                         result["checked"])
    return result


def parse_issue(ev, base, number, token):
    _, body = current_issue_digest(base, number, token)   # the current body, whatever this run's event said
    if v.is_form_issue(body.decode("utf-8", "replace")):
        return validate_isolated("issue", body, number, None)
    mine, _ = managed_comment(base, number, token)
    return v.no_current_response("issue", number, hashlib.sha256(body).hexdigest(), REPO) if mine else None


def parse():
    token, ev = os.environ["GH_TOKEN"], event()
    route, number, base = item(ev)
    trusted = head_sha(REPO)
    write_output("trusted_sha", trusted)
    try:
        result = parse_pr(ev, base, number, token) if route == "file" else parse_issue(ev, base, number, token)
    except Incomplete:
        print("skipped: a GitHub response was larger than this tool reads")
        return
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
    try:
        version = current_version(route, base, number, token)
    except Incomplete:
        print("skipped: could not re-read the item")
        return
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
