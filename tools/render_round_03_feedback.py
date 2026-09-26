# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: D2 of proposals/2026-09-26-claude-opus-5-5-github-automation.md (revision 3, cleared at design level by GPT-6). The publisher's half: it accepts only a result that passes the validator's strict schema, bound to the expected item, version and route, and writes the comment from fixed templates only. Revision 2 applies GPT-6's AC4 and AC8 (critiques/2026-09-26-gpt-6--automation-code-review.md): the version is bound for both routes and the result must come from the pinned trusted revision; the rights sentences are GPT-6's; the launch commit, candidate count and closing time come from the trusted checkout, never from constants or submissions. Revision 3 adds the resource-limit sentence and says plainly when a header failure stopped the assessment check (GPT-6 round 2).
# license: MIT (LICENSE-CODE)
"""Render one advisory feedback comment from a validator result. Fixed templates only.

Usage: python tools/render_round_03_feedback.py RESULT.json --route R --number N --version V --revision SHA [--repo DIR]

The result is re-checked against the validator's schema and must match the expected route, number, version and
trusted revision, which the publisher takes from the triggering event, its own re-read of the item and its own pinned
checkout, not from the result. Every word of the comment comes from this file or from the trusted checkout's pinned
manifest: codes and statuses map to fixed sentences, and nothing else from the result is printed except the item's
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
NEVER_POST = ("This does not authorize posting output you cannot publish under CC BY 4.0; follow the form's Never "
              "post rules.")

SENTENCES = {
    "not_checked_too_large": "The response is larger than this tool checks (512 KB). **It was not checked**; this is not a rejection.",
    "not_checked_not_utf8": "The response is not valid UTF-8 text, so **it was not checked**; this is not a rejection.",
    "not_checked_yaml_limits": "The header uses YAML features or a size this tool doesn't check (anchors, aliases, tags, or very deep or large structures). **It was not checked**; this is not a rejection.",
    "form_heading_duplicated": "A form heading appears more than once outside the answer, so this tool can't tell which section is which. **It was not checked**; check the issue's layout.",
    "pr_file_not_regular_or_too_large": "The response file is not a regular file at this commit, or is larger than this tool checks, so **it was not checked**; this is not a rejection.",
    "incomplete_retrieval": "This tool could not retrieve everything it needed from GitHub, so **it was not checked**; this is not a rejection.",
    "no_current_response": "This tool no longer finds a Round 3 response here, so any earlier feedback no longer applies.",
    "not_checked_resources": "Checking stopped at this tool's time or memory limit, so **it was not checked**; this is not a rejection.",
    "header_missing": "No front-matter header was found, so the assessments were not checked. A response file starts with `---`, the header, and `---` (see the template in PARTICIPATE.md).",
    "header_unparseable": "The header could not be read as YAML, so the assessments were not checked.",
    "header_not_a_mapping": "The header is not a set of `field: value` lines, so the assessments were not checked.",
    "type_not_round_response": "The header's `type` is not `round-response`.",
    "round_not_03_open": "The header's `round` is not `03-open`.",
    "samples_malformed": "The header's `samples` should give `generated` and `submitted` as numbers, or `unknown`, as in the template.",
    "receipt_present": "The header has a `receipt` field. The editor adds that at intake; leave it out.",
    "input_set_ok": "`input_set` names the tag and its commit.",
    "input_set_missing": "`input_set` is empty.",
    "rights_declared": "The rights field contains text. This tool cannot determine whether the declaration or publication rights are complete or valid.",
    "rights_unresolved": "The rights declaration looks incomplete or unknown. An incomplete declaration is returned for completion and is not merged until the required grant and consent are recorded. " + NEVER_POST,
    "grant_box_unticked": "The grant box is unticked: the declaration is incomplete until the grant is made. " + NEVER_POST,
    "consent_box_unticked": "The publication-consent box is unticked: the declaration is incomplete until consent is recorded. " + NEVER_POST,
    "never_post_box_unticked": "The \"Never post\" box is unticked. It is required.",
    "form_prefix_text": "There is text before the form's first heading. Check that the issue's layout is the form's.",
    "form_heading_unexpected": "There is a `###` heading this tool doesn't recognize outside the answer. It was treated as part of the section above it.",
    "answer_empty": "The answer section is empty.",
    "no_assessment_found": "No assessment block was found. That's allowed (partial answers are welcome), but if you meant to assess propositions, check the block format in PARTICIPATE.md.",
    "pr_several_response_files": "This pull request changes more than one response file; only the first was checked. Send one response per pull request.",
}
# Sentences that need the trusted checkout's own values.
TRUSTED_SENTENCES = {
    "input_set_mismatch": "`input_set` does not match `{tag} @ {launch}`. Unless you answered a different text, copy it from the template.",
    "assessment_ids_not_candidates": "At least one assessment block uses an ID that is not one of this round's {count} candidates.",
}
FIXED_FIELDS = {"type", "round", "prompt", "input_set", "lifecycle", "samples"}
STATUS_WORDS = {"read": "read", "not_assessed": "not assessed", "unparseable": "could not be parsed",
                "incomplete": "incomplete (a required line is missing)", "conflicting": "more than one block"}


def field_sentence(code):
    kind, field = code.split(":", 1)
    if kind == "form_field_missing":
        if field == "model":
            return "The form section for a model or an agent is empty. It is required when a model or agent answers."
        if field == "relay":
            return "The relaying section is empty. It is required when relaying someone else's answer."
        return f"The required form field `{field}` is empty."
    where = "has no" if kind == "field_missing" else "has an empty"
    fix = "copy it from the template" if field in FIXED_FIELDS else "write `unknown` if you don't know"
    return f"The header {where} `{field}` field; {fix}."


def render(result, route, number, version, revision, repo=ex.REPO):
    cand_ids, launch, closes = v.trusted_inputs(repo)
    problems = v.schema_problems(result, cand_ids)
    if problems:
        raise ValueError(f"refused: the result fails its schema ({', '.join(problems)})")
    if (result["route"], result["number"], result["version"]) != (route, number, version):
        raise ValueError("refused: the result is not for the expected item and version")
    if result["validator_revision"] != revision:
        raise ValueError("refused: the result was not produced by the pinned trusted revision")
    what = "this pull request's head commit" if route == "file" else "this issue's body (SHA-256)"
    lines = [MARKER, "", "**Round 3 advisory check** (automatic; procedure only)", "",
             f"Checked {what}: `{result['version']}`, with validator revision `{result['validator_revision'][:12]}`. "
             "If the response changes, this comment is updated for the new version.", ""]
    notes = []
    for code in result["codes"]:
        if ":" in code:
            notes.append(field_sentence(code))
        elif code in TRUSTED_SENTENCES:
            notes.append(TRUSTED_SENTENCES[code].format(tag=ex.TAG, launch=launch, count=len(cand_ids)))
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
              f"stands at the close ({closes.strftime('%Y-%m-%dT%H:%M:%SZ')}) and checks procedure only."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split(chr(10))[0])
    ap.add_argument("result")
    ap.add_argument("--route", choices=("file", "issue"), required=True)
    ap.add_argument("--number", type=int, required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--revision", required=True)
    ap.add_argument("--repo", default=str(ex.REPO))
    a = ap.parse_args(argv)
    with open(a.result, "rb") as f:
        raw = f.read(64 * 1024 + 1)
    if len(raw) > 64 * 1024:
        raise SystemExit("refused: the result is larger than any valid result")
    sys.stdout.write(render(json.loads(raw), a.route, a.number, a.version, a.revision, Path(a.repo)))


if __name__ == "__main__":
    main()
