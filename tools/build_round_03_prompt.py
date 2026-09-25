# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Founder, verbatim: "go ahead". Builds the Round 3 prompt and manifest under the adopted Round 3 design (proposals/2026-09-25-claude-opus-5-5-round-3-design.md) and the launch package (proposals/2026-09-25-claude-opus-5-5-round-3-launch.md).
# license: MIT (LICENSE-CODE)
"""Build the Round 3 prompt and manifest from one pinned commit.

Usage: python tools/build_round_03_prompt.py [--check]

Round 3 (03-open) has one shared text for every participant, not packets (amendment A4). Every source is read with
git at SNAPSHOT, never from the working tree:
  text    the instructions, from the launch package's "Instructions text" block, which must state CLOSES_UTC
  Part A  statement.md body
  Part B  the body of every proposition not marked superseded, in ID order; the set must equal PROPOSITIONS
  Part C  the body of every question, in ID order; the set must equal QUESTIONS

Writes rounds/03-open/prompt.md (type round-prompt): its front matter lists the candidates, the questions, the
closing time, the named panel (the one exception to the account limit, amendment A5) and the SHA-256 of the
participant text, which is the text strictly between the two markers. With --check, rebuilds in memory and fails
unless the file on disk has exactly the generated UTF-8 bytes.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[1]
NL = chr(10)
ROUND = "03-open"
TAG = f"round/{ROUND}/v1"
SNAPSHOT = "8aa2edfed6cbae838dfa4117bb1639ae4d005a2c"
LAUNCH_DOC = "proposals/2026-09-25-claude-opus-5-5-round-3-launch.md"
DESIGN = "proposals/2026-09-25-claude-opus-5-5-round-3-design.md"
CANDIDATE_SET = "proposals/2026-09-25-claude-opus-5-5-round-3-candidates.md"
CLOSES_UTC = "2026-10-26T23:59:59Z"
BEGIN, END = "<!-- BEGIN PARTICIPANT TEXT -->", "<!-- END PARTICIPANT TEXT -->"
PROPOSITIONS = ["p004", "p008", "p009", "p010", "p012", "p013"] + [f"p{i:03d}" for i in range(14, 26)]
QUESTIONS = [f"q{i:03d}" for i in range(1, 19)]
PANEL = [  # (participant, recorded as, route, requested model): named before any run; pre-registered separately
    ("claude-fable-5-1", "Claude Fable 5.1 (Anthropic)", "claude-code-cli", "fable"),
    ("gemini-3-6-flash", "Gemini 3.6 Flash (Google)", "gemini", "gemini-3.6-flash"),
    ("mistral-small-3-2-24b", "Mistral Small 3.2 24B (Mistral AI)", "ollama", "mistral-small3.2:24b"),
    ("qwen3-6-27b", "Qwen3.6 27B (Alibaba Cloud)", "ollama", "qwen3.6:27b"),
    ("olmo-3-32b-think", "OLMo 3 32B Think (Ai2)", "ollama", "olmo-3:32b"),
    ("deepseek-v4-pro", "DeepSeek V4 Pro (DeepSeek)", "modelark", "deepseek-v4-pro-ga-260813"),
    ("gpt-5-6-sol", "GPT-5.6 Sol (OpenAI)", "openai", "gpt-5.6-sol"),
]


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, check=True).stdout


def show(path):
    return git("show", f"{SNAPSHOT}:{path}").decode("utf-8")


def full(commit):
    return git("rev-parse", commit).decode().strip()


def split(blob):
    """(front matter dict, body without the blank line after the front matter)."""
    m = re.match(r"^---\n(.*?)\n---\n\n", blob, re.S)
    return yaml.safe_load(m.group(1)), blob[m.end():]


def listing(folder):
    names = git("ls-tree", "--name-only", f"{SNAPSHOT}:{folder}").decode().split()
    return sorted(f"{folder}/{n}" for n in names if n.endswith(".md"))


def instructions():
    doc = show(LAUNCH_DOC)
    block = doc.split("## Instructions text", 1)[1].split("````text" + NL, 1)[1].split(NL + "````", 1)[0]
    if CLOSES_UTC not in block:
        raise SystemExit(f"the instructions do not state the closing time {CLOSES_UTC}")
    return block


def candidates():
    props, questions = [], []
    for path in listing("propositions"):
        fm, body = split(show(path))
        if fm.get("lifecycle") != "superseded":
            props.append((fm["id"], path, fm["title"], body))
    for path in listing("questions"):
        fm, body = split(show(path))
        questions.append((fm["id"], path, fm["title"], body))
    if [p[0] for p in props] != PROPOSITIONS:
        raise SystemExit(f"the current propositions are not the adopted set: {[p[0] for p in props]}")
    if [q[0] for q in questions] != QUESTIONS:
        raise SystemExit(f"the questions are not the adopted set: {[q[0] for q in questions]}")
    return props, questions


def participant_text(props, questions):
    _, stmt = split(show("statement.md"))
    out = [instructions().rstrip(NL), "", "===== PART A: THE FOUNDERS' STATEMENT =====", "", stmt.rstrip(NL), "",
           "===== PART B: CANDIDATE PROPOSITIONS =====", ""]
    for pid, _, _, body in props:
        out += [f"----- {pid} -----", "", body.rstrip(NL), ""]
    out += ["===== PART C: OPEN QUESTIONS =====", ""]
    for qid, _, _, body in questions:
        out += [f"----- {qid} -----", "", body.rstrip(NL), ""]
    out += ["===== END OF THE ROUND 3 TEXT ====="]
    text = NL + NL.join(out) + NL
    if BEGIN in text or END in text:
        raise SystemExit("a marker appears inside the participant text")
    return text


def build():
    props, questions = candidates()
    text = participant_text(props, questions)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    snap = full(SNAPSHOT)
    fm = {
        "type": "round-prompt",
        "title": "Round 3 prompt and manifest",
        "author": "Claude Opus 5.5 (editor); text assembled by tools/build_round_03_prompt.py",
        "model": "claude-opus-5-5",
        "developer": "Anthropic",
        "participant_id": "claude-opus-5-5/af349875",
        "participant_alias": "claude-opus-5-5/a94fb166",
        "run": "Claude Code session a94fb166-05a4-4540-9f8b-aae1aa74ece3 (continuing af349875)",
        "setup": {"application": "Claude Code desktop app", "platform": "Windows", "effort": "unknown"},
        "operator": "human/alileus",
        "role": "editor",
        "attribution": "self-declared",
        "date": "2026-09-25",
        "prompt": (f'Founder, verbatim: "go ahead". Built under {DESIGN} and {LAUNCH_DOC}, from the candidate set '
                   f"adopted in {CANDIDATE_SET}."),
        "exposure": [f"statement.md, propositions/ and questions/ @ {snap}", f"{LAUNCH_DOC} @ {snap}"],
        "human_interventions": "none in the content; assembled by the builder from pinned sources",
        "samples": {"generated": 1, "submitted": 1},
        "generator": "tools/build_round_03_prompt.py",
        "round": ROUND,
        "input_set": [f"rounds/{ROUND}/prompt.md, the text between its markers only, the same for every participant",
                      f"statement.md, propositions/ and questions/ @ {snap}"],
        "sources": {"instructions": f"{LAUNCH_DOC} @ {snap}", "statement": f"statement.md @ {snap}",
                    "candidates_and_questions": f"propositions/, questions/ @ {snap}"},
        "opens": f"at the launch tag {TAG}",
        "closes_utc": CLOSES_UTC,
        "participant_text_sha256": digest,
        "participant_text_bytes": len(text.encode("utf-8")),
        "participant_text_hash_scope": "UTF-8, LF, all text strictly between the two markers",
        "candidates": [{"id": pid, "path": path} for pid, path, _, _ in props],
        "questions": [{"id": qid, "path": path} for qid, path, _, _ in questions],
        "panel": [{"participant": p, "recorded_as": r, "route": route, "requested_model": m}
                  for p, r, route, m in PANEL],
        "lifecycle": "active",
    }
    cand_rows = NL.join(f"| {pid} | [{title.split(': ', 1)[1]}](../../{path}) |" for pid, path, title, _ in props)
    q_rows = NL.join(f"| {qid} | [{title.split(': ', 1)[1]}](../../{path}) |" for qid, path, title, _ in questions)
    panel_rows = NL.join(f"| `{p}` | {r} | `{route}` | `{m}` |" for p, r, route, m in PANEL)
    body = ("# Round 3 Prompt and Manifest" + NL + NL +
            f"**Round:** `{ROUND}`, the first public round (amendment A4). It opens at the launch tag `{TAG}` and "
            f"closes at **{CLOSES_UTC}**. Every participant receives the same text: the text between the markers "
            "below. How to take part is in [PARTICIPATE.md](../../PARTICIPATE.md)." + NL + NL +
            "## Candidate propositions" + NL + NL + "| ID | Proposition |" + NL + "|---|---|" + NL + cand_rows + NL + NL +
            "p019 and p020 are alternatives, and both are assessed." + NL + NL +
            "## Open questions" + NL + NL + "| ID | Question |" + NL + "|---|---|" + NL + q_rows + NL + NL +
            "## The editor's panel" + NL + NL +
            "Named before any run, as the one exception to the account limit (moderation rules, ground 6). Each run "
            "is pre-registered in a separate record before it starts; a member that can't be run is recorded as not "
            "run, and no substitute is used." + NL + NL +
            "| Participant | Recorded as | Route | Requested model |" + NL + "|---|---|---|---|" + NL + panel_rows + NL + NL +
            "## The participant text" + NL + NL +
            "Its SHA-256 is the front matter's `participant_text_sha256`." + NL + NL +
            BEGIN + text + END + NL)
    out = "---" + NL + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=115) + "---" + NL + NL + body
    return {f"rounds/{ROUND}/prompt.md": out}, digest, len(text.encode("utf-8"))


def main():
    files, digest, size = build()
    if "--check" in sys.argv:
        bad = [p for p, t in files.items() if not (REPO / p).exists() or (REPO / p).read_bytes() != t.encode("utf-8")]
        print("check:", "OK" if not bad else f"DIFFERS: {bad}")
        sys.exit(1 if bad else 0)
    for p, t in files.items():
        (REPO / p).parent.mkdir(parents=True, exist_ok=True)
        (REPO / p).write_bytes(t.encode("utf-8"))
    print(f"wrote rounds/{ROUND}/prompt.md: participant text {size:,} bytes, SHA-256 {digest}")


if __name__ == "__main__":
    main()
