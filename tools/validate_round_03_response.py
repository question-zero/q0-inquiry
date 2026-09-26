# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6 in topic github-automation, round 3). The founder chose, verbatim: "All three below (Recommended)", which included building the D1 and D2 code for GPT-6's code review. Advisory feedback only: procedure, never positions or quoted text, never a gate.
# license: MIT (LICENSE-CODE)
"""Advisory feedback for one Round 3 response: can the editor read it? Procedure only.

Usage:
  python tools/validate_round_03_response.py file <path> --number N --version SHA [--repo DIR]
  python tools/validate_round_03_response.py issue <path> --number N [--repo DIR]

`file` is a response file from a pull request, fetched as data at the pull request's head; `issue` is the body of an
issue from the Round 3 form. The input is untrusted data: it is read as bytes, bounded, parsed with safe YAML and the
extractor's own rules, and never executed. The output is one JSON object (see RESULT_KEYS) holding only fixed codes,
statuses, counts and identifiers. No text from the input is ever copied into it, so nothing from a submission can
reach a public comment. The same classification as extraction is used: tools/extract_round_03_assessments.classify.

The result is advice. It is not intake, not a receipt, and not a decision about eligibility. A limit that stops a check
is reported as `not_checked`, never as a rejection. Partial assessment is valid; an undeclared grant is an unresolved
intake requirement, not a format error; a filled field or a ticked box verifies nothing.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_round_03_assessments as ex  # noqa: E402

SCHEMA = "q0-round3-feedback/1"
MAX_BYTES = 512 * 1024          # a response is typically under 40 KB
MAX_YAML_NODES = 2000
MAX_YAML_DEPTH = 20
FORM = ".github/ISSUE_TEMPLATE/round-3-response.yml"
NO_RESPONSE = "_No response_"   # what GitHub renders for an empty optional form field

# Every code the validator may emit. The renderer refuses anything else.
CODES = {
    "not_checked_too_large", "not_checked_not_utf8", "not_checked_yaml_limits",
    "header_missing", "header_unparseable", "header_not_a_mapping", "type_not_round_response",
    "receipt_present",
    "input_set_ok", "input_set_mismatch", "input_set_missing",
    "rights_declared", "rights_unresolved",
    "grant_box_unticked", "consent_box_unticked", "never_post_box_unticked",
    "form_heading_duplicated", "form_heading_unknown", "answer_empty",
    "no_assessment_found", "assessment_ids_not_candidates",
    "pr_several_response_files", "pr_file_not_regular_or_too_large",
}
FIELD_CODE = re.compile(r"^(field_missing|form_field_missing):[a-z_]+$")
STATUSES = {"read", "not_assessed", "unparseable", "incomplete", "conflicting"}
RESULT_KEYS = {"schema", "route", "number", "version", "validator_revision", "checked", "codes", "assessments",
               "counts"}

# The template's fields (PARTICIPATE.md): every one must be present; "unknown" is a permitted value.
TEMPLATE_FIELDS = ("type", "title", "author", "model", "developer", "participant_id", "run", "setup", "operator",
                   "submitting_account", "rights", "attribution", "date", "prompt", "round", "input_set",
                   "exposure", "human_interventions", "samples", "lifecycle")


def status_of(result_status):
    """The feedback status for one classification status. A position becomes "read": positions are never reported."""
    return {"not assessed": "not_assessed", "unparseable": "unparseable", "incomplete": "incomplete",
            "conflicting": "conflicting"}.get(result_status, "read")


def safe_yaml(text):
    """Parse YAML front matter with limits: no anchors or aliases, a bounded node count and depth."""
    for token in yaml.scan(text, Loader=yaml.SafeLoader):
        if isinstance(token, (yaml.AnchorToken, yaml.AliasToken, yaml.TagToken)):
            raise ValueError("limits")
    root = yaml.compose(text, Loader=yaml.SafeLoader)
    count = 0
    stack = [(root, 1)] if root is not None else []
    while stack:
        node, depth = stack.pop()
        count += 1
        if count > MAX_YAML_NODES or depth > MAX_YAML_DEPTH:
            raise ValueError("limits")
        if isinstance(node, yaml.MappingNode):
            for k, v in node.value:
                stack += [(k, depth + 1), (v, depth + 1)]
        elif isinstance(node, yaml.SequenceNode):
            stack += [(v, depth + 1) for v in node.value]
    return yaml.safe_load(text)


def blank(value):
    return value is None or (isinstance(value, str) and not value.strip())


def unresolved_rights(value):
    if blank(value):
        return True
    s = str(value).strip().lower()
    return s == "unknown" or s.startswith("unknown") or "unresolved" in s


def classify_answer(body, cand_ids, codes):
    _, results, notes = ex.classify(body, cand_ids)
    assessments = {pid: status_of(res["status"]) for pid, res in results.items()}
    if any(kind == "not a candidate" for _, kind, _ in notes):
        codes.add("assessment_ids_not_candidates")
    if all(s == "not_assessed" for s in assessments.values()):
        codes.add("no_assessment_found")
    return assessments


def check_input_set(value, launch, codes):
    if blank(value):
        codes.add("input_set_missing")
    elif str(value).split() == [ex.TAG, "@", launch]:
        codes.add("input_set_ok")
    else:
        codes.add("input_set_mismatch")


def check_file(text, cand_ids, launch, codes):
    if not text.startswith("---" + ex.NL):
        codes.add("header_missing")
        return None
    parts = text.split("---" + ex.NL, 2)
    if len(parts) < 3:
        codes.add("header_missing")
        return None
    try:
        fm = safe_yaml(parts[1])
    except ValueError:
        codes.add("not_checked_yaml_limits")
        return None
    except yaml.YAMLError:
        codes.add("header_unparseable")
        return None
    if not isinstance(fm, dict):
        codes.add("header_not_a_mapping")
        return None
    for field in TEMPLATE_FIELDS:
        if field not in fm:
            codes.add(f"field_missing:{field}")
    if fm.get("type") != "round-response":
        codes.add("type_not_round_response")
    if "receipt" in fm:
        codes.add("receipt_present")
    check_input_set(fm.get("input_set"), launch, codes)
    codes.add("rights_unresolved" if unresolved_rights(fm.get("rights")) else "rights_declared")
    body = parts[2][1:] if parts[2].startswith(ex.NL) else parts[2]
    return classify_answer(body, cand_ids, codes)


def form_fields(repo):
    """{label: (id, type, required)} from the trusted form definition in this checkout."""
    form = yaml.safe_load((repo / FORM).read_text(encoding="utf-8"))
    out = {}
    for item in form["body"]:
        if item.get("type") == "markdown":
            continue
        attrs = item.get("attributes", {})
        out[attrs["label"]] = (item.get("id"), item["type"], bool(item.get("validations", {}).get("required")),
                               attrs.get("options", []))
    return out


def split_issue(body, labels):
    """{label: value} for '### Label' sections; duplicated or unknown headings are reported, never guessed."""
    sections, current, dup, unknown = {}, None, False, False
    for line in body.split(ex.NL):
        if line.startswith("### "):
            label = line[4:].strip()
            if label in labels:
                if label in sections:
                    dup = True
                current = label
                sections[label] = []
                continue
            if current is None:
                unknown = True
        if current is not None:
            sections[current].append(line)
    return {k: ex.NL.join(v).strip() for k, v in sections.items()}, dup, unknown


def unfence(value):
    """GitHub renders a `render: markdown` textarea inside a markdown code fence; remove that one wrapper."""
    lines = value.split(ex.NL)
    if len(lines) >= 2 and re.fullmatch(r"```\s*markdown\s*", lines[0]) and lines[-1].strip() == "```":
        return ex.NL.join(lines[1:-1])
    return value


def check_issue(text, repo, cand_ids, launch, codes):
    fields = form_fields(repo)
    sections, dup, unknown = split_issue(text.replace("\r\n", ex.NL), set(fields))
    if dup:
        codes.add("form_heading_duplicated")
    if unknown:
        codes.add("form_heading_unknown")
    values = {}
    for label, (fid, ftype, required, options) in fields.items():
        raw = sections.get(label)
        value = None if raw is None or raw == NO_RESPONSE else raw
        values[fid] = value
        if ftype == "checkboxes":
            ticks = [bool(re.search(r"^- \[[xX]\] " + re.escape(o["label"]) + r"\s*$", raw or "", re.M))
                     for o in options]
            for tick, code in zip(ticks, ("grant_box_unticked", "consent_box_unticked", "never_post_box_unticked")):
                if not tick:
                    codes.add(code)
        elif required and blank(value):
            codes.add(f"form_field_missing:{fid}")
    check_input_set(values.get("input_set"), launch, codes)
    codes.add("rights_unresolved" if unresolved_rights(values.get("rights")) else "rights_declared")
    answer = unfence(values.get("answer") or "")
    if not answer.strip():
        codes.add("answer_empty")
    return classify_answer(answer, cand_ids, codes)


def revision(repo):
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, check=True,
                              text=True).stdout.strip()
    except (subprocess.CalledProcessError, OSError):
        return "unknown"


def validate(route, data, number, version, repo=ex.REPO):
    """The typed result for one response. `data` is bytes; nothing from it is copied into the result."""
    codes, assessments, checked = set(), {}, True
    if route == "issue":
        version = hashlib.sha256(data).hexdigest()
    cands, _ = ex.manifest_at_tag(repo)
    cand_ids = list(cands)
    launch = ex.git(repo, "rev-parse", f"{ex.TAG}^{{commit}}").strip()
    if len(data) > MAX_BYTES:
        codes.add("not_checked_too_large")
        checked = False
    else:
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            codes.add("not_checked_not_utf8")
            checked = False
            text = None
        if text is not None:
            got = (check_issue(text, repo, cand_ids, launch, codes) if route == "issue"
                   else check_file(text.replace("\r\n", ex.NL), cand_ids, launch, codes))
            if got is None:
                checked = "not_checked_yaml_limits" not in codes
            else:
                assessments = got
    counts = {s: sum(1 for v in assessments.values() if v == s) for s in sorted(STATUSES)}
    result = {"schema": SCHEMA, "route": route, "number": int(number), "version": version,
              "validator_revision": revision(repo), "checked": checked, "codes": sorted(codes),
              "assessments": assessments, "counts": counts}
    problems = schema_problems(result, cand_ids)
    if problems:
        raise AssertionError(f"the validator built an invalid result: {problems}")
    return result


def schema_problems(result, cand_ids):
    """Strict schema check, shared by the validator and the renderer. Returns a list of problems (empty if valid)."""
    p = []
    if not isinstance(result, dict) or set(result) != RESULT_KEYS:
        return ["keys"]
    if result["schema"] != SCHEMA:
        p.append("schema")
    if result["route"] not in ("file", "issue"):
        p.append("route")
    if not isinstance(result["number"], int) or isinstance(result["number"], bool) or not 0 < result["number"] < 10**7:
        p.append("number")
    if not isinstance(result["version"], str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", result["version"]):
        p.append("version")
    if not isinstance(result["validator_revision"], str) or not re.fullmatch(r"[0-9a-f]{40}|unknown",
                                                                             result["validator_revision"]):
        p.append("validator_revision")
    if not isinstance(result["checked"], bool):
        p.append("checked")
    codes = result["codes"]
    if not isinstance(codes, list) or len(codes) > 80 or not all(
            isinstance(c, str) and (c in CODES or (FIELD_CODE.match(c) and c.split(":")[1] in
                                                   set(TEMPLATE_FIELDS) | FORM_IDS)) for c in codes):
        p.append("codes")
    a = result["assessments"]
    if not isinstance(a, dict) or not all(k in cand_ids and v in STATUSES for k, v in a.items()) or (
            a and set(a) != set(cand_ids)):
        p.append("assessments")
    c = result["counts"]
    if not isinstance(c, dict) or set(c) != STATUSES or not all(
            isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= len(cand_ids) for v in c.values()):
        p.append("counts")
    return p


FORM_IDS = {"who", "name", "input_set", "model", "added_instructions", "interventions", "relay", "operator",
            "rights", "exposure", "answer", "consent"}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("route", choices=("file", "issue"))
    ap.add_argument("path")
    ap.add_argument("--number", type=int, required=True)
    ap.add_argument("--version", default="0" * 40, help="the pull request's head SHA (file route)")
    ap.add_argument("--repo", default=str(ex.REPO))
    a = ap.parse_args(argv)
    data = Path(a.path).read_bytes()[:MAX_BYTES + 1]
    print(json.dumps(validate(a.route, data, a.number, a.version, Path(a.repo)), sort_keys=True))


if __name__ == "__main__":
    main()
