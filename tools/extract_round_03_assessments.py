# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Founder, verbatim: "go ahead". Extracts the Round 3 assessment blocks under the launch package (proposals/2026-09-25-claude-opus-5-5-round-3-launch.md, "Extraction"), reusing Round 2's block rules (proposals/2026-09-24-claude-opus-5-5-round-2-design.md, decision 8). Revision 2 applies GPT-6's R3L1-R3L3 (topic round-3-launch): stale outputs fail --check, receipts are validated against the tagged deadline and bound to the captured version, and the source's samples and interventions are kept.
# license: MIT (LICENSE-CODE)
"""Extract the Round 3 assessment blocks into critiques/.

Usage: python tools/extract_round_03_assessments.py [--dry-run | --check]

Mechanical and verbatim, with Round 2's block rules: a block starts at a line that is exactly a proposition ID
(markdown decoration around it ignored) followed by a Position line, and its field values are copied as written.
Nothing is inferred. Round 3 differs in these ways:
  - the candidates are the manifest's `candidates` list in rounds/03-open/prompt.md, read at the tag, and the
    closing time is its `closes_utc`;
  - each target is `<candidate path> @ <the tag's commit>`;
  - a response is extracted only if its input_set names the tag and that exact commit, and its receipt (added by
    the editor at intake) is complete, on time, consistent with the tagged deadline, and bound to the version
    captured at the close (see receipt_problem); otherwise it is reported and skipped;
  - a response that another eligible response names in its `replaces` field is reported as replaced and skipped:
    a change after capture is a replacement, never an edit (protocol section 4), and both stay in the record;
  - a candidate with no block is reported as not assessed, and no file is written for it;
  - the source's samples and human_interventions are copied as they are; the extraction is recorded separately.
A duplicated, unparseable or incomplete block is reported with its reason, and no file is written.

--dry-run reports what would be written; --check rebuilds in memory and fails if any assessment file is missing or
differs, or if a Round 3 assessment file exists that extraction no longer produces. Such a stale file is reported
for the editor to resolve under the recording rules; it is never deleted here.
"""
import hashlib
from datetime import datetime
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
NL = chr(10)
ROUND = "03-open"
TAG = f"round/{ROUND}/v1"
POSITIONS = {"support", "reject", "conditional", "uncertain"}
COPIED = ("author", "model", "developer", "participant_id", "run", "operator", "submitting_account", "rights")


def git(repo, *a):
    return subprocess.run(["git", "-C", str(repo), *a], capture_output=True, check=True).stdout.decode("utf-8")


# ---- Round 2's block rules, unchanged (tools/extract_round_02_assessments.py) ----

def undecorate(line):
    """Strip markdown decoration around a label or ID: leading #, >, list markers."""
    s = line.strip()
    s = re.sub(r"^(?:[#>]+\s*)+", "", s)
    s = re.sub(r"^[-+]\s+", "", s)
    return s


def label_value(line):
    """(label, value) if the line is 'Label: value', allowing **Label:** or **Label**: decoration."""
    s = undecorate(line)
    m = re.match(r"^[*_`]*(Position|Conditions|Basis|Rewording)[*_`]*\s*:\s*[*_`]*\s*(.*)$", s)
    if not m:
        return None
    return m.group(1), m.group(2)


def header_id(line):
    s = undecorate(line).strip("*_` ")
    m = re.fullmatch(r"(p\d{3})", s)
    return m.group(1) if m else None


def blocks(body):
    """(lines, [(pid, start, end)]). A header counts only if the next non-empty line is a Position line."""
    lines = body.split(NL)
    heads = []
    for i, line in enumerate(lines):
        pid = header_id(line)
        if not pid:
            continue
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and (label_value(lines[j]) or (None,))[0] == "Position":
            heads.append((pid, i))
    out = []
    for k, (pid, i) in enumerate(heads):
        end = heads[k + 1][1] if k + 1 < len(heads) else len(lines)
        j = i + 1
        while j < end:
            s = lines[j].strip()
            if j > i + 1 and not label_value(lines[j]) and (
                    re.match(r"^#{1,6}\s", s) or re.fullmatch(r"[-*_]{3,}", s) or re.match(r"^(`{3,}|~{3,})", s)):
                break  # a heading, a horizontal rule, or a code fence ends the block
            j += 1
        while j > i + 1 and not lines[j - 1].strip():
            j -= 1
        out.append((pid, i, j))
    return lines, out


def parse(lines, i, j):
    """Fields from lines i+1..j-1: each label starts a field; later unlabeled lines continue the previous field."""
    fields, current = {}, None
    for line in lines[i + 1:j]:
        lv = label_value(line)
        if lv:
            label, value = lv
            if label in fields:
                return None, f"the {label} line appears twice"
            current = label
            fields[label] = [value.rstrip()]
        elif current:
            fields[current].append(line.rstrip())
        elif line.strip():
            return None, "text before the Position line"
    clean = {}
    for k, v in fields.items():
        text = NL.join(v).strip()
        text = re.sub(r"^[*_]+|[*_]+$", "", text) if k == "Position" else text
        clean[k] = text
    return clean, None


def fence(text):
    run = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, run + 1)


# ---- Round 3 ----

def front_and_body(blob):
    parts = blob.split("---" + NL, 2)
    fm = yaml.safe_load(parts[1])
    body = parts[2]
    return fm, body[1:] if body.startswith(NL) else body


def manifest_at_tag(repo):
    """({id: path} of the candidates, the closing time) from the manifest at the tag."""
    fm, _ = front_and_body(git(repo, "show", f"{TAG}:rounds/{ROUND}/prompt.md"))
    return {c["id"]: c["path"] for c in fm["candidates"]}, utc(fm["closes_utc"])


def utc(value):
    """A datetime from 'YYYY-MM-DDTHH:MM:SSZ', or None."""
    try:
        return datetime.strptime(str(value), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def without_receipt(fm):
    return {k: v for k, v in fm.items() if k != "receipt"}


def receipt_problem(repo, rel, fm, body, closes):
    """(kind, reason) if the editor's receipt doesn't establish an on-time response bound to its captured version,
    else None. The receipt is the editor's own record; this checks it for completeness and consistency (GPT-6 R3L2).
      route            'pull request #N', 'issue #N', or 'editor panel (pre-registered)'
      created_utc      when GitHub records the pull request or issue as created (for the panel, when the run started)
      on_time          must agree with created_utc and the tagged closing time
      captured_commit  a pull request: the head commit captured (at merge, or at the close if still open); the
                       response at that commit must equal this record except for the receipt itself
      captured_sha256  an issue: the SHA-256 of the answer as captured at the close; it must equal this record's body
    """
    r = fm.get("receipt")
    if not isinstance(r, dict):
        return "no receipt", "the editor has not recorded a receipt"
    route, created, flag = str(r.get("route", "")), utc(r.get("created_utc")), r.get("on_time")
    if not route or created is None or not isinstance(flag, bool):
        return "incomplete receipt", "route, created_utc (YYYY-MM-DDTHH:MM:SSZ) and on_time are all required"
    if flag != (created <= closes):
        return "contradictory receipt", f"on_time is {flag}, but created_utc {r['created_utc']} is " + (
            "before" if created <= closes else "after") + " the close"
    if not flag:
        return "late", "created after the close; kept, not extracted in this round"
    if route.startswith("pull request #"):
        commit = str(r.get("captured_commit", ""))
        if not re.fullmatch(r"[0-9a-f]{40}", commit):
            return "incomplete receipt", "a pull request needs captured_commit, the full head commit captured"
        try:
            captured = git(repo, "show", f"{commit}:{rel}")
        except subprocess.CalledProcessError:
            return "unbound receipt", "the captured commit does not hold this response"
        cfm, cbody = front_and_body(captured)
        if without_receipt(cfm) != without_receipt(fm) or cbody != body:
            return "unbound receipt", "this record differs from the version captured at the close"
        return None
    if route.startswith("issue #"):
        digest = str(r.get("captured_sha256", ""))
        if not re.fullmatch(r"[0-9a-f]{64}", digest):
            return "incomplete receipt", "an issue needs captured_sha256, the SHA-256 of the answer as captured"
        if hashlib.sha256(body.encode("utf-8")).hexdigest() != digest:
            return "unbound receipt", "this record's answer differs from the captured issue text"
        return None
    if route == "editor panel (pre-registered)":
        return None
    return "incomplete receipt", f"unknown route {route!r}"


def extract(repo, dry=False):
    """(files {path: text}, notes [(slug, pid or '-', kind, reason)], table [(slug, {pid: result})])."""
    launch = git(repo, "rev-parse", f"{TAG}^{{commit}}").strip()
    cands, closes = manifest_at_tag(repo)
    files, notes, table = {}, [], []
    eligible, replaced = [], {}
    for rec in sorted((repo / f"rounds/{ROUND}/responses").glob("*.md")):
        slug = rec.stem
        rel = f"rounds/{ROUND}/responses/{rec.name}"
        rec_commit = git(repo, "log", "-1", "--format=%H", "--", rel).strip() or ("0" * 40 if dry else "")
        if not rec_commit:
            raise SystemExit(f"{rel} is not committed")
        if not dry and git(repo, "status", "--porcelain", "--", rel).strip():
            raise SystemExit(f"{rel} has uncommitted changes")
        fm, body = front_and_body(rec.read_text(encoding="utf-8"))
        if str(fm.get("input_set", "")).split() != [TAG, "@", launch]:
            notes.append((slug, "-", "wrong input set", f"input_set must be '{TAG} @ {launch}'"))
            table.append((slug, {}))
            continue
        problem = receipt_problem(repo, rel, fm, body, closes)
        if problem:
            notes.append((slug, "-", problem[0], problem[1]))
            table.append((slug, {}))
            continue
        eligible.append((rec, slug, rel, rec_commit, fm, body))
        if fm.get("replaces"):
            replaced[str(fm["replaces"]).strip()] = rel
    for rec, slug, rel, rec_commit, fm, body in eligible:
        if rel in replaced:
            notes.append((slug, "-", "replaced", f"replaced by {replaced[rel]}; kept in the record, not extracted"))
            table.append((slug, {}))
            continue
        lines, found = blocks(body)
        seen = {}
        for pid, i, j in found:
            seen.setdefault(pid, []).append((i, j))
        for pid in sorted(set(seen) - set(cands)):
            notes.append((slug, pid, "not a candidate", "this ID is not in the round's candidate list"))
        row = {}
        for pid, path in cands.items():
            spans = seen.get(pid, [])
            if not spans:
                row[pid] = "not assessed"
                continue
            if len(spans) > 1:
                notes.append((slug, pid, "conflicting", f"{len(spans)} blocks for this proposition"))
                row[pid] = "conflicting"
                continue
            i, j = spans[0]
            raw = NL.join(lines[i:j])
            fields, err = parse(lines, i, j)
            if err:
                notes.append((slug, pid, "unparseable", err))
                row[pid] = "unparseable"
                continue
            pos = fields.get("Position", "")
            if pos not in POSITIONS:
                notes.append((slug, pid, "unparseable", f"the position is not exactly one of the four values: {pos!r}"))
                row[pid] = "unparseable"
                continue
            cond = fields.get("Conditions")
            if not fields.get("Basis"):
                notes.append((slug, pid, "incomplete", "no Basis line"))
                row[pid] = "incomplete"
                continue
            if pos == "conditional" and (not cond or cond.strip().strip('"').lower() == "none"):
                notes.append((slug, pid, "incomplete", "conditional, but no conditions are given"))
                row[pid] = "incomplete"
                continue
            row[pid] = pos
            name = str(fm.get("author", "unknown")).split(" (")[0]
            a = {"type": "critique", "subtype": "assessment",
                 "title": f"Round 3 assessment of {pid} by {name}"}
            for k in COPIED:
                a[k] = fm.get(k, "unknown")
            a.update({
                "setup": f"as recorded in the setup field of {rel} @ {rec_commit} (the source record)",
                "attribution": fm.get("attribution", "unknown"),
                "date": str(fm.get("date", "unknown")),
                "prompt": fm.get("prompt", "unknown"),
                "round": ROUND,
                "input_set": f"{TAG} @ {launch}",
                "target": f"{path} @ {launch}",
                "position": pos,
                "conditions": cond if cond is not None else "not stated",
                "basis": fields["Basis"],
            })
            if fields.get("Rewording"):
                a["rewording"] = fields["Rewording"]
            a.update({
                "source": f"{rel} @ {rec_commit}, block {pid}",
                "receipt": fm["receipt"],
                "exposure": fm.get("exposure", "unknown"),
                "recorder": "claude-opus-5-5/af349875 (editor): extraction only",
                "human_interventions": fm.get("human_interventions", "unknown"),
                "samples": fm.get("samples", "unknown"),
                "extraction": ("The editor copied this block verbatim from the committed response record named in "
                               "source, under the Round 3 launch package, and wrote this file. Field values are as "
                               "written, with markdown decoration around the labels removed; the full block is "
                               "reproduced below. The extraction adds no intervention to the participant's text, and "
                               "creates no new participant, sample, or endorsement."),
                "lifecycle": "active",
            })
            f = fence(raw)
            text = ("---" + NL + yaml.safe_dump(a, sort_keys=False, allow_unicode=True, width=105) + "---" + NL + NL
                    + f"# Round 3 Assessment of {pid}: {name}" + NL + NL
                    + f"The block below is copied verbatim from `{rel}` at `{rec_commit[:7]}`. It concerns `{path}` "
                    + f"as written at `{launch[:7]}`, the commit tagged `{TAG}`." + NL + NL
                    + f + "text" + NL + raw + NL + f + NL)
            day = re.sub(r"[^0-9-]", "", str(fm.get("date", "")))[:10] or "undated"
            files[f"critiques/{day}-{slug}--round-3-assessment-{pid}.md"] = text
        table.append((slug, row))
    return files, notes, table


def main(argv=None, repo=REPO):
    argv = sys.argv[1:] if argv is None else argv
    dry, check = "--dry-run" in argv, "--check" in argv
    files, notes, table = extract(repo, dry=dry)
    mismatched = []
    if check:
        produced = {p.relative_to(repo).as_posix() for p in (repo / "critiques").glob("*--round-3-assessment-p*.md")}
        stale = sorted(produced - set(files))
        for rel in stale:
            print("STALE", rel, "- extraction no longer produces this file; resolve it under the recording rules")
        mismatched += stale
    for rel, text in files.items():
        path = repo / rel
        if check:
            if not path.exists() or path.read_bytes() != text.encode("utf-8"):
                mismatched.append(rel)
        elif not dry:
            if path.exists():
                raise FileExistsError(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
    print(f"assessment files: {len(files)}{' (dry run)' if dry else ''}")
    for slug, row in table:
        print(f"{slug:28s} " + " ".join(f"{p[1:]}:{v[:4]}" for p, v in row.items()))
    for n in notes:
        print("NOTE", *n[:3], "-", n[3])
    if check:
        print("check:", "OK" if not mismatched else f"DIFFERS: {mismatched}")
        return 1 if mismatched else 0
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
