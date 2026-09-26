# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: GPT-6's round-2 AC9 finding on the sandbox plan (critiques/2026-09-26-gpt-6--automation-code-review-r2.md): the sandbox necessarily runs a derived commit, so the derivation from the reviewed commit must be recorded and verified against an allowlist of fixture and activation changes. Revision 2 applies its round-3 AC9 finding (critiques/2026-09-26-gpt-6--automation-code-review-r3.md): the whole chain R, T, D is verified, including the tag's target, the three-candidate manifest and its hash, the form's exact default, and byte-level changes to the form.
# license: MIT (LICENSE-CODE)
"""Verify the sandbox's commits against the reviewed commit, R. Nothing else may differ.

Usage: python tools/verify_sandbox_derivation.py R T D [--repo DIR] [--candidates 3]

  T  R with only rounds/03-open/prompt.md replaced by the synthetic manifest: it must parse, name exactly the stated
     number of candidates, give a closing time, and carry participant_text_sha256 and participant_text_bytes that
     match its own participant text. The tag round/03-open/v1 in DIR must point to T.
  D  T with exactly two changes: .github/workflows/round-3-feedback.yml added, byte-identical to
     tools/workflows/round-3-feedback.yml at R; and in .github/ISSUE_TEMPLATE/round-3-response.yml, the input_set
     default line changed to exactly `round/03-open/v1 @ T`, with every other byte of the form unchanged.
Every other path, including all of tools/ and the required CI workflow, must be byte-identical to R. Prints each
problem and exits 0 only if the chain is exactly this.
"""
import argparse
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_local_participant import extract_participant_text  # noqa: E402

WORKFLOW_SRC = "tools/workflows/round-3-feedback.yml"
WORKFLOW_DST = ".github/workflows/round-3-feedback.yml"
MANIFEST = "rounds/03-open/prompt.md"
FORM = ".github/ISSUE_TEMPLATE/round-3-response.yml"
TAG = "round/03-open/v1"
DEFAULT_LINE = re.compile(rb'^( +value: )"round/03-open/v1 @ [0-9a-f]{40}"(\r?)$', re.M)


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True).stdout


def changes(repo, a, b):
    out = {}
    for line in git(repo, "diff", "--name-status", "--no-renames", a, b).decode().splitlines():
        status, _, path = line.partition("\t")
        out[path] = status
    return out


def problems(repo, r, t, d, candidates=3):
    out = []
    full = {name: git(repo, "rev-parse", f"{c}^{{commit}}").decode().strip() for name, c in (("R", r), ("T", t), ("D", d))}
    r, t, d = full["R"], full["T"], full["D"]
    if git(repo, "rev-parse", f"{TAG}^{{commit}}").decode().strip() != t:
        out.append("the sandbox tag does not point to T")
    rt = changes(repo, r, t)
    if rt != {MANIFEST: "M"}:
        out.append("T differs from R in more than the manifest")
    try:
        text, front = extract_participant_text(git(repo, "show", f"{t}:{MANIFEST}").decode("utf-8"))
        ids = [c.get("id") for c in front.get("candidates", [])]
        if len(ids) != candidates or len(set(ids)) != candidates:
            out.append(f"the sandbox manifest does not name exactly {candidates} distinct candidates")
        if not front.get("closes_utc"):
            out.append("the sandbox manifest has no closing time")
        body = text.encode("utf-8")
        if front.get("participant_text_sha256") != hashlib.sha256(body).hexdigest() or \
                front.get("participant_text_bytes") != len(body):
            out.append("the sandbox manifest's participant-text hash or size does not match its text")
    except (ValueError, AttributeError, TypeError, yaml.YAMLError, UnicodeDecodeError):
        out.append("the sandbox manifest does not parse")
    td = changes(repo, t, d)
    if td != {WORKFLOW_DST: "A", FORM: "M"}:
        out.append("D differs from T in more than installing the workflow and the form's default")
    if WORKFLOW_DST in td and git(repo, "show", f"{d}:{WORKFLOW_DST}") != git(repo, "show", f"{r}:{WORKFLOW_SRC}"):
        out.append("the installed workflow is not byte-identical to the reviewed one")
    if FORM in td:
        before, after = git(repo, "show", f"{t}:{FORM}"), git(repo, "show", f"{d}:{FORM}")
        want = f'"{TAG} @ {t}"'.encode()
        if len(DEFAULT_LINE.findall(before)) != 1 or len(DEFAULT_LINE.findall(after)) != 1:
            out.append("the form does not have exactly one input_set default line")
        elif DEFAULT_LINE.sub(rb"\1X\2", before) != DEFAULT_LINE.sub(rb"\1X\2", after):
            out.append("the form differs in more than the input_set default line")
        elif want not in after:
            out.append("the form's input_set default is not the sandbox tag and T")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("reviewed")
    ap.add_argument("tagged")
    ap.add_argument("sandbox")
    ap.add_argument("--repo", default=str(Path.cwd()))
    ap.add_argument("--candidates", type=int, default=3)
    a = ap.parse_args(argv)
    found = problems(a.repo, a.reviewed, a.tagged, a.sandbox, a.candidates)
    for p in found:
        print(p)
    print("derivation verified" if not found else "derivation refused")
    sys.exit(1 if found else 0)


if __name__ == "__main__":
    main()
