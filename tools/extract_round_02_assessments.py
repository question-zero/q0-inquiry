# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Founder, verbatim: "go ahead with round 2 as proposed". Extracts the Round 2 assessment blocks under proposals/2026-09-24-claude-opus-5-5-round-2-design.md, decision 8. Revision 2 applies GPT-6 R2R1: each file carries the source's operator and a pinned setup reference, and its attribution points to the source record's evidence.
# license: MIT (LICENSE-CODE)
"""Extract the Round 2 assessment blocks into critiques/ (Round 2 design, decision 8).

Mechanical and verbatim: a block starts at a line that is exactly a proposition ID (markdown decoration such as
#, >, * or backticks around it is ignored) and is followed by a Position line. Field values are copied as written,
decoration around the label removed. Nothing is inferred: an absent, duplicated, unparseable or incomplete block
goes to the editor's extraction note instead of an assessment file.

Usage: python tools/extract_round_02_assessments.py [--dry-run | --check]

Writes critiques/2026-09-24-<participant>--round-2-assessment-pNNN.md from the committed response records.
--dry-run reports what would be written; --check rebuilds in memory and fails unless every file on disk has
exactly the extracted bytes and no assessment file is missing.
"""
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[1]
NL = chr(10)
ROUND = "02-deliberation"
SET_COMMIT = "563d1205966812545e5bea2505d810f106080cbe"
POSITIONS = {"support", "reject", "conditional", "uncertain"}
LABELS = ("Position", "Conditions", "Basis", "Rewording")
DRY = "--dry-run" in sys.argv
CHECK = "--check" in sys.argv


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, check=True).stdout.decode("utf-8")


PROPS = {Path(p).name[:4]: p for p in git("ls-tree", "--name-only", f"{SET_COMMIT}:propositions").split()
         if re.match(r"p\d{3}-", p)}
PROPS = {k: f"propositions/{v}" for k, v in sorted(PROPS.items())}
assert list(PROPS) == [f"p{i:03d}" for i in range(1, 14)], PROPS


def undecorate(line):
    """Strip markdown decoration around a label or ID: leading #, >, list markers, and * or ` wrappers."""
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
    value = m.group(2)
    return m.group(1), value


def header_id(line):
    s = undecorate(line).strip("*_` ")
    m = re.fullmatch(r"(p\d{3})", s)
    return m.group(1) if m else None


def blocks(body):
    """[(pid, start, end)] line ranges. A header counts only if the next non-empty line is a Position line."""
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
        # a block also ends at the first heading, rule, or code fence after its header
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
    fields, order, current = {}, [], None
    for line in lines[i + 1:j]:
        lv = label_value(line)
        if lv:
            label, value = lv
            if label in fields:
                return None, f"the {label} line appears twice"
            current = label
            fields[label] = [value.rstrip()]
            order.append(label)
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


def source_attribution(text):
    """The source record's attribution, with its pointer to evidence "below" redirected to the source record (R2R1)."""
    out = (text.replace("(the raw response stream and records below)",
                        "(the raw response stream and records listed in the source record's evidence field)")
               .replace("identified below.", "identified in the source record's evidence field."))
    assert "below" not in out, out
    return out


def fence(text):
    run = max((len(m) for m in re.findall(r"`+", text)), default=0)
    return "`" * max(3, run + 1)


def record_front(path):
    blob = (REPO / path).read_text(encoding="utf-8")
    fm = yaml.safe_load(blob.split("---" + NL, 2)[1])
    body = blob.split("---" + NL, 2)[2]
    assert body.startswith(NL)
    return fm, body[1:]


def main():
    responses = sorted((REPO / f"rounds/{ROUND}/responses").glob("*.md"))
    notes, written, table, mismatched = [], [], [], []
    for rec in responses:
        slug = rec.stem
        rel = f"rounds/{ROUND}/responses/{rec.name}"
        rec_commit = git("log", "-1", "--format=%H", "--", rel).strip() or ("0" * 40 if DRY else "")
        assert rec_commit, f"{rel} is not committed"
        assert DRY or not git("status", "--porcelain", "--", rel).strip(), f"{rel} has uncommitted changes"
        fm, body = record_front(rel)
        lines, found = blocks(body)
        seen = {}
        for pid, i, j in found:
            seen.setdefault(pid, []).append((i, j))
        row = {}
        for pid in PROPS:
            spans = seen.get(pid, [])
            if not spans:
                notes.append((slug, pid, "absent", "no block for this proposition was found", None))
                row[pid] = "absent"
                continue
            if len(spans) > 1:
                raw = (NL + "...\n").join(NL.join(lines[i:j]) for i, j in spans)
                notes.append((slug, pid, "conflicting", f"{len(spans)} blocks for this proposition", raw))
                row[pid] = "conflicting"
                continue
            i, j = spans[0]
            raw = NL.join(lines[i:j])
            fields, err = parse(lines, i, j)
            if err:
                notes.append((slug, pid, "unparseable", err, raw))
                row[pid] = "unparseable"
                continue
            pos = fields.get("Position", "")
            if pos not in POSITIONS:
                notes.append((slug, pid, "unparseable", f"the position is not exactly one of the four values: {pos!r}", raw))
                row[pid] = "unparseable"
                continue
            cond = fields.get("Conditions")
            if not fields.get("Basis"):
                notes.append((slug, pid, "incomplete", "no Basis line", raw))
                row[pid] = "incomplete"
                continue
            if pos == "conditional" and (not cond or cond.strip().strip('"').lower() == "none"):
                notes.append((slug, pid, "incomplete", "conditional, but no conditions are given", raw))
                row[pid] = "incomplete"
                continue
            row[pid] = pos
            a = {
                "type": "critique",
                "subtype": "assessment",
                "title": f"Round 2 assessment of {pid} by {fm['author'].split(' (')[0]}",
                "author": fm["author"],
                "model": fm["model"],
                "developer": fm["developer"],
                "participant_id": fm["participant_id"],
                "run": fm["run"],
                "operator": fm["operator"],
                "setup": f"as recorded in the setup field of {rel} @ {rec_commit} (the source record)",
                "attribution": source_attribution(fm["attribution"]),
                "date": fm["date"],
                "prompt": fm["prompt"],
                "round": ROUND,
                "input_set": fm["input_set"],
                "target": f"{PROPS[pid]} @ {SET_COMMIT}",
                "position": pos,
                "conditions": cond if cond is not None else "not stated",
                "basis": fields["Basis"],
            }
            if fields.get("Rewording"):
                a["rewording"] = fields["Rewording"]
            a.update({
                "source": f"{rel} @ {rec_commit}, block {pid}",
                "exposure": fm["exposure"],
                "recorder": "claude-opus-5-5/af349875 (editor): extraction only",
                "human_interventions": ("None in the assessment's text. The editor copied this block verbatim from the "
                                        "committed response record named in source, under the Round 2 design "
                                        "(decision 8), and wrote this file. Field values are as written, with markdown "
                                        "decoration around the labels removed; the full block is reproduced below. "
                                        "The extraction creates no new participant, sample, or endorsement."),
                "samples": {"generated": 1, "submitted": 1, "note": "part of the participant's one Round 2 response"},
                "lifecycle": "active",
            })
            f = fence(raw)
            text = ("---" + NL + yaml.safe_dump(a, sort_keys=False, allow_unicode=True, width=105) + "---" + NL + NL
                    + f"# Round 2 Assessment of {pid}: {fm['author'].split(' (')[0]}" + NL + NL
                    + f"The block below is copied verbatim from `{rel}` at `{rec_commit[:7]}`. It concerns "
                    + f"`{PROPS[pid]}` as written at `{SET_COMMIT[:7]}`." + NL + NL
                    + f + "text" + NL + raw + NL + f + NL)
            out = REPO / "critiques" / f"2026-09-24-{slug}--round-2-assessment-{pid}.md"
            written.append(out)
            if CHECK:
                if not out.exists() or out.read_bytes() != text.encode("utf-8"):
                    mismatched.append(out.name)
            elif not DRY:
                if out.exists():
                    raise FileExistsError(out)
                out.write_bytes(text.encode("utf-8"))
        table.append((slug, fm["participant_id"], row))
    print(f"assessment files: {len(written)}{' (dry run)' if DRY else ''}")
    for slug, pidn, row in table:
        print(f"{slug:24s} " + " ".join(f"{p[1:]}:{v[:4]}" for p, v in row.items()))
    for n in notes:
        print("NOTE", n[0], n[1], n[2], "-", n[3])
    if CHECK:
        print("check:", "OK" if not mismatched else f"DIFFERS: {mismatched}")
        sys.exit(1 if mismatched else 0)


if __name__ == "__main__":
    main()
