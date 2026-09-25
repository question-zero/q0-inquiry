# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Founder, verbatim: "go ahead". Extracts the Round 3 assessment blocks under the launch package (proposals/2026-09-25-claude-opus-5-5-round-3-launch.md, "Extraction"), reusing Round 2's block rules (proposals/2026-09-24-claude-opus-5-5-round-2-design.md, decision 8).
# license: MIT (LICENSE-CODE)
"""Extract the Round 3 assessment blocks into critiques/.

Usage: python tools/extract_round_03_assessments.py [--dry-run | --check]

Mechanical and verbatim, with Round 2's block rules: a block starts at a line that is exactly a proposition ID
(markdown decoration around it ignored) followed by a Position line, and its field values are copied as written.
Nothing is inferred. Round 3 differs in four ways:
  - the candidates are the manifest's `candidates` list in rounds/03-open/prompt.md, read at the tag;
  - each target is `<candidate path> @ <the tag's commit>`;
  - a response is extracted only if its input_set names the tag and that exact commit, and its receipt (added by
    the editor at intake) says it was on time; otherwise it is reported and skipped;
  - a candidate with no block is reported as not assessed, and no file is written for it.
A duplicated, unparseable or incomplete block is reported with its reason, and no file is written.

--dry-run reports what would be written; --check rebuilds in memory and fails unless every assessment file on disk
has exactly the extracted bytes and none is missing.
"""
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


def candidates_at_tag(repo):
    fm, _ = front_and_body(git(repo, "show", f"{TAG}:rounds/{ROUND}/prompt.md"))
    return {c["id"]: c["path"] for c in fm["candidates"]}


def on_time(receipt):
    return isinstance(receipt, dict) and receipt.get("on_time") is True


def extract(repo, dry=False):
    """(files {path: text}, notes [(slug, pid or '-', kind, reason)], table [(slug, {pid: result})])."""
    launch = git(repo, "rev-parse", f"{TAG}^{{commit}}").strip()
    cands = candidates_at_tag(repo)
    files, notes, table = {}, [], []
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
        if not on_time(fm.get("receipt")):
            kind = "late" if isinstance(fm.get("receipt"), dict) else "no receipt"
            notes.append((slug, "-", kind, "not extracted in this round (launch package, decision 2 of the design)"))
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
                "human_interventions": ("None in the assessment's text. The editor copied this block verbatim from the "
                                        "committed response record named in source, under the Round 3 launch package, "
                                        "and wrote this file. Field values are as written, with markdown decoration "
                                        "around the labels removed; the full block is reproduced below. The "
                                        "extraction creates no new participant, sample, or endorsement."),
                "samples": {"generated": 1, "submitted": 1, "note": "part of the participant's one Round 3 response"},
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
