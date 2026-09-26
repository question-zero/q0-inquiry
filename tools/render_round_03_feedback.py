# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6). The publisher's half: it accepts only a result that passes the validator's strict schema, bound to the expected item, version and route, and writes the comment from fixed templates only.
# license: MIT (LICENSE-CODE)
"""Render one advisory feedback comment from a validator result. Fixed templates only.

Usage: python tools/render_round_03_feedback.py RESULT.json --route R --number N --version V [--repo DIR]

The result is re-checked against the validator's schema and must match the expected route, number and version,
which the publisher takes from the triggering event, not from the result. Every word of the comment comes from this
file: codes and statuses map to fixed sentences, and nothing else from the result is printed except the item's
version, the validator's revision and proposition IDs, each re-checked against a strict pattern.
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import extract_round_03_assessments as ex  # noqa: E402
import validate_round_03_response as v  # noqa: E402

MARKER = "<!-- q0-round3-feedback -->"
CLOSES = "2026-10-26T23:59:59Z"

SENTENCES = {
    "not_checked_too_large": "The response is larger than this tool checks (512 KB). **It was not checked**; this is not a rejection.",
    "not_checked_not_utf8": "The response is not valid UTF-8 text, so **it was not checked**; this is not a rejection.",
    "not_checked_yaml_limits": "The header uses YAML features or a size this tool doesn't check (anchors, aliases, tags, or very deep or large structures). **It was not checked**; this is not a rejection.",
    "header_missing": "No front-matter header was found. A response file starts with `---`, the header, and `---` (see the template in PARTICIPATE.md).",
    "header_unparseable": "The header could not be read as YAML.",
    "header_not_a_mapping": "The header is not a set of `field: value` lines.",
    "type_not_round_response": "The header's `type` is not `round-response`.",
    "receipt_present": "The header has a `receipt` field. The editor adds that at intake; leave it out.",
    "input_set_ok": "`input_set` names the tag and its commit.",
    "input_set_mismatch": "`input_set` does not match `round/03-open/v1 @ 1ea6bf4cdae494d4198e81d5cfb07f0cc0e46d0d`. Unless you answered a different text, copy it from the template.",
    "input_set_missing": "`input_set` is empty.",
    "rights_declared": "Rights are declared. This tool does not check who holds them or whether the grant is valid.",
    "rights_unresolved": "The rights declaration looks incomplete or unknown. That is allowed to send, but the answer is returned for completion and not merged until the grant is recorded (PARTICIPATE.md).",
    "grant_box_unticked": "The grant box is unticked: the declaration is incomplete until the grant is made.",
    "consent_box_unticked": "The publication-consent box is unticked: the declaration is incomplete until consent is recorded.",
    "never_post_box_unticked": "The \"Never post\" box is unticked. It is required.",
    "form_heading_duplicated": "A form heading appears more than once, so this tool could not tell which section is which. Check the issue's layout.",
    "form_heading_unknown": "There is text before the form's first heading, or a heading this tool doesn't recognize.",
    "answer_empty": "The answer section is empty.",
    "no_assessment_found": "No assessment block was found. That's allowed (partial answers are welcome), but if you meant to assess propositions, check the block format in PARTICIPATE.md.",
    "assessment_ids_not_candidates": "At least one assessment block uses an ID that is not one of this round's 18 candidates.",
    "pr_several_response_files": "This pull request changes more than one response file; only the first was checked. Send one response per pull request.",
    "pr_file_not_regular_or_too_large": "The response file is not a regular file, or is larger than this tool checks, so **it was not checked**; this is not a rejection.",
}
FIELD_SENTENCE = {"field_missing": "The header has no `{}` field. Write `unknown` if you don't know.",
                  "form_field_missing": "The required form field `{}` is empty."}
STATUS_WORDS = {"read": "read", "not_assessed": "not assessed", "unparseable": "could not be parsed",
                "incomplete": "incomplete (a required line is missing)", "conflicting": "more than one block"}


def render(result, route, number, version, repo=ex.REPO):
    cands, _ = ex.manifest_at_tag(repo)
    cand_ids = list(cands)
    problems = v.schema_problems(result, cand_ids)
    if problems:
        raise ValueError(f"refused: the result fails its schema ({', '.join(problems)})")
    if result["route"] != route or result["number"] != number or (route == "file" and result["version"] != version):
        raise ValueError("refused: the result is not for the expected item and version")
    what = "this pull request's head commit" if route == "file" else "this issue's body"
    lines = [MARKER, "", "**Round 3 advisory check** (automatic; procedure only)", "",
             f"Checked {what}: `{result['version']}`, with validator revision `{result['validator_revision'][:12]}`. "
             "If the response changes, this comment is updated for the new version.", ""]
    notes = []
    for code in result["codes"]:
        if ":" in code:
            kind, field = code.split(":", 1)
            notes.append(FIELD_SENTENCE[kind].format(field))
        else:
            notes.append(SENTENCES[code])
    if notes:
        lines += [f"- {n}" for n in notes] + [""]
    if result["assessments"]:
        c = result["counts"]
        lines.append(f"**Assessment blocks:** {c['read']} read, {c['not_assessed']} not assessed, "
                     f"{c['unparseable']} could not be parsed, {c['incomplete']} incomplete, "
                     f"{c['conflicting']} with more than one block.")
        problems_by_id = [f"`{pid}`: {STATUS_WORDS[s]}" for pid, s in result["assessments"].items()
                          if s in ("unparseable", "incomplete", "conflicting")]
        if problems_by_id:
            lines += ["", "Blocks to check: " + "; ".join(problems_by_id) + "."]
        lines.append("")
    lines += ["This is advice, not intake. It doesn't decide eligibility, doesn't check rights or identity, and "
              "never reports positions. Partial answers are welcome. The editor records every response as it "
              f"stands at the close ({CLOSES}) and checks procedure only."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("result")
    ap.add_argument("--route", choices=("file", "issue"), required=True)
    ap.add_argument("--number", type=int, required=True)
    ap.add_argument("--version", default="")
    ap.add_argument("--repo", default=str(ex.REPO))
    a = ap.parse_args(argv)
    raw = Path(a.result).read_bytes()
    if len(raw) > 64 * 1024:
        raise SystemExit("refused: the result is larger than any valid result")
    sys.stdout.write(render(json.loads(raw), a.route, a.number, a.version, Path(a.repo)))


if __name__ == "__main__":
    main()
