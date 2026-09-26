# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: GPT-6's round-2 AC9 finding on the sandbox plan (critiques/2026-09-26-gpt-6--automation-code-review-r2.md): the sandbox necessarily runs a derived commit, so the derivation from the reviewed commit must be recorded and verified against an allowlist of fixture and activation changes.
# license: MIT (LICENSE-CODE)
"""Verify that a sandbox commit differs from the reviewed commit only by the allowlisted test substitutions.

Usage: python tools/verify_sandbox_derivation.py REVIEWED_COMMIT SANDBOX_COMMIT [--repo DIR]

Allowed differences, and nothing else:
  - .github/workflows/round-3-feedback.yml added, byte-identical to tools/workflows/round-3-feedback.yml at the
    reviewed commit (the activation step);
  - rounds/03-open/prompt.md replaced by the synthetic sandbox manifest (it must still parse, with its own candidates
    and closing time);
  - .github/ISSUE_TEMPLATE/round-3-response.yml changed only in the input_set field's default value.
Every other path, including every file under tools/ and the required CI workflow, must be byte-identical. Prints the
result and exits 0 only if the derivation is exactly this.
"""
import argparse
import subprocess
import sys
from pathlib import Path

import yaml

WORKFLOW_SRC = "tools/workflows/round-3-feedback.yml"
WORKFLOW_DST = ".github/workflows/round-3-feedback.yml"
MANIFEST = "rounds/03-open/prompt.md"
FORM = ".github/ISSUE_TEMPLATE/round-3-response.yml"


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True).stdout


def problems(repo, reviewed, sandbox):
    out = []
    changed = {}
    for line in git(repo, "diff", "--name-status", "--no-renames", reviewed, sandbox).decode().splitlines():
        status, _, path = line.partition("\t")
        changed[path] = status
    allowed = {WORKFLOW_DST: "A", MANIFEST: "M", FORM: "M"}
    for path, status in changed.items():
        if allowed.get(path) != status:
            out.append(f"unexpected change: {status} {path}")
    if changed.get(WORKFLOW_DST) == "A" and \
            git(repo, "show", f"{sandbox}:{WORKFLOW_DST}") != git(repo, "show", f"{reviewed}:{WORKFLOW_SRC}"):
        out.append("the installed workflow is not byte-identical to the reviewed one")
    if WORKFLOW_DST not in changed:
        out.append("the workflow is not installed in the sandbox commit")
    if changed.get(MANIFEST) == "M":
        text = git(repo, "show", f"{sandbox}:{MANIFEST}").decode("utf-8")
        try:
            fm = yaml.safe_load(text.split("---\n", 2)[1])
            if not (isinstance(fm.get("candidates"), list) and fm["candidates"] and fm.get("closes_utc")):
                out.append("the sandbox manifest lacks candidates or a closing time")
        except (IndexError, AttributeError, yaml.YAMLError):
            out.append("the sandbox manifest does not parse")
    if changed.get(FORM) == "M":
        a = yaml.safe_load(git(repo, "show", f"{reviewed}:{FORM}"))
        b = yaml.safe_load(git(repo, "show", f"{sandbox}:{FORM}"))
        for item in a.get("body", []):
            if item.get("id") == "input_set":
                item.get("attributes", {}).pop("value", None)
        for item in b.get("body", []):
            if item.get("id") == "input_set":
                item.get("attributes", {}).pop("value", None)
        if a != b:
            out.append("the form differs in more than the input_set default")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("reviewed")
    ap.add_argument("sandbox")
    ap.add_argument("--repo", default=str(Path.cwd()))
    a = ap.parse_args(argv)
    found = problems(a.repo, a.reviewed, a.sandbox)
    for p in found:
        print(p)
    print("derivation verified" if not found else "derivation refused")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
