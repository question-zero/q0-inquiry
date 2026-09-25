# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Founder, verbatim: "go ahead with round 2 as proposed". Builds the Round 2 packets and manifest under proposals/2026-09-24-claude-opus-5-5-round-2-design.md (packet mode, amendment A1). Revision 2 applies GPT-6 RPK1 and RPK2: packets are generated files without front matter, and the manifest lists each packet's route and requested model. Revision 3 makes --check compare raw bytes (GPT-6, optional, runner-packet round 2).
# license: MIT (LICENSE-CODE)
"""Build the Round 2 manifest and per-participant packets from pinned sources.

Usage: python tools/build_round_02_packets.py [--check]

Sources, all read with git at the pinned commits below (never from the working tree):
  Part A  statement.md body @ STATEMENT_COMMIT
  Part B  propositions/*.md and questions/*.md bodies @ SET_COMMIT, in ID order
  Part C  one Round 1 response record body per packet, at its record commit
  text    the shared instructions, from the design proposal @ DESIGN_COMMIT (the block under
          "Instructions text"), with {{IDENTITY_LINE}} filled per participant
Every source is also checked to be identical at SNAPSHOT, the commit each packet's first line names.

Writes rounds/02-deliberation/packets/<slug>.md, generated files (protocol section 6): line 1 names this
generator and the source commit, there is no front matter, and one marker pair holds the participant text.
Writes rounds/02-deliberation/prompt.md, the round's manifest (section 9, type round-prompt): its front
matter lists each packet's participant, route, requested model, path and hash, which the runners check
(GPT-6 RPK2), and its marker block holds the shared text with the placeholders {{IDENTITY_LINE}} and
{{PART_C}}. It is never sent. With --check, rebuilds in memory and fails unless every file on disk has exactly
the generated UTF-8 bytes.
"""
import hashlib
import re
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
NL = chr(10)
BEGIN, END = "<!-- BEGIN PARTICIPANT TEXT -->", "<!-- END PARTICIPANT TEXT -->"
ROUND = "02-deliberation"
STATEMENT_COMMIT = "e959df1"
SET_COMMIT = "563d120"
DESIGN = "proposals/2026-09-24-claude-opus-5-5-round-2-design.md"
DESIGN_COMMIT = "ad1a1c1"
SNAPSHOT = DESIGN_COMMIT

PARTICIPANTS = [
    # slug, label, route, requested model (exact string given to the runner), identity line,
    # Part C record, record commit
    ("claude-fable-5-1", "Claude Fable 5.1 (Anthropic)", "claude-code-cli", "fable",
     "The operator records this run as Claude Fable 5.1, by Anthropic. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/claude-fable-5-1.md", "90b141a"),
    ("gemini-3-6-flash", "Gemini 3.6 Flash (Google)", "gemini", "gemini-3.6-flash",
     "The operator records this run as Gemini 3.6 Flash, by Google, reached through its API. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/gemini-3-6-flash.md", "d226d9f"),
    ("grok-4-6", "Grok 4.6 (xAI)", "xai", "grok-4.6",
     "The operator records this run as Grok 4.6, by xAI, reached through its API. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/grok-4-6.md", "d226d9f"),
    ("grok-4-7", "Grok 4.7 (xAI)", "xai", "grok-4.7",
     "The operator records this run as Grok 4.7, by xAI, reached through its API. Part C is an earlier participant's second-round answer from Grok 4.6, an earlier version of your model line.",
     "rounds/01-deliberation/responses/grok-4-6.md", "d226d9f"),
    ("mistral-small-3-2-24b", "Mistral Small 3.2 24B (Mistral AI)", "ollama", "mistral-small3.2:24b",
     "The operator records this run as Mistral Small 3.2 24B, by Mistral AI, run locally. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/mistral-small-3-2-24b.md", "90b141a"),
    ("qwen3-6-27b", "Qwen3.6 27B (Alibaba Cloud)", "ollama", "qwen3.6:27b",
     "The operator records this run as Qwen3.6 27B, by Alibaba Cloud's Qwen team, run locally. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/qwen3-6-27b.md", "90b141a"),
    ("olmo-3-32b-think", "OLMo 3 32B Think (Ai2)", "ollama", "olmo-3:32b",
     "The operator records this run as OLMo 3 32B Think, by Ai2, run locally. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/olmo-3-32b-think.md", "90b141a"),
    ("deepseek-v4-pro", "DeepSeek V4 Pro (DeepSeek)", "modelark", "deepseek-v4-pro-ga-260813",
     "The operator records this run as DeepSeek V4 Pro, by DeepSeek, reached through BytePlus ModelArk. Part C is an earlier participant's second-round answer from that model.",
     "rounds/01-deliberation/responses/deepseek-v4-pro.md", "6173ca0"),
]


def git(*a):
    return subprocess.run(["git", "-C", str(REPO), *a], capture_output=True, check=True)


def git_show(commit, path):
    return git("show", f"{commit}:{path}").stdout.decode("utf-8")


def full(commit):
    return git("rev-parse", commit).stdout.decode().strip()


def same_at_snapshot(commit, path):
    """The pinned source must be byte-identical at SNAPSHOT, so line 1 of each packet can name it."""
    if git("rev-parse", f"{commit}:{path}").stdout != git("rev-parse", f"{SNAPSHOT}:{path}").stdout:
        raise SystemExit(f"{path} @ {commit} differs at the snapshot {SNAPSHOT}")


def split(blob):
    """(front matter dict, body without the blank line after the front matter)."""
    m = re.match(r"^---\n(.*?)\n---\n\n", blob, re.S)
    return yaml.safe_load(m.group(1)), blob[m.end():]


def listing(commit, folder):
    out = git("ls-tree", "--name-only", f"{commit}:{folder}").stdout.decode().split()
    return sorted(f"{folder}/{n}" for n in out if n.endswith(".md"))


def shared_instructions():
    same_at_snapshot(DESIGN_COMMIT, DESIGN)
    design = git_show(DESIGN_COMMIT, DESIGN)
    block = design.split("## Instructions text", 1)[1].split("```text" + NL, 1)[1].split(NL + "```", 1)[0]
    assert block.count("{{IDENTITY_LINE}}") == 1
    return block


def parts_ab():
    same_at_snapshot(STATEMENT_COMMIT, "statement.md")
    _, stmt = split(git_show(STATEMENT_COMMIT, "statement.md"))
    out = [NL + "===== PART A: THE FOUNDERS' STATEMENT =====", "", stmt.rstrip(NL), "",
           "===== PART B: CANDIDATE PROPOSITIONS AND OPEN QUESTIONS =====", ""]
    for folder in ("propositions", "questions"):
        if listing(SET_COMMIT, folder) != listing(SNAPSHOT, folder):
            raise SystemExit(f"the {folder} set differs at the snapshot")
    for path in listing(SET_COMMIT, "propositions") + listing(SET_COMMIT, "questions"):
        same_at_snapshot(SET_COMMIT, path)
        fm, b = split(git_show(SET_COMMIT, path))
        out += [f"----- {fm['id']} -----", "", b.rstrip(NL), ""]
    return NL.join(out)


def part_c(record, commit):
    same_at_snapshot(commit, record)
    fm, b = split(git_show(commit, record))
    answer = b[:-1] if b.endswith(NL) else b  # the record body without the file's final newline
    header = (f"===== PART C: AN EARLIER PARTICIPANT'S ANSWER =====" + NL + NL +
              f"Recorded as participant {fm['participant_id']}: {fm['title'].removeprefix('Round 1 response: ')}, "
              f"second round." + NL + NL + "----- ANSWER BEGINS -----" + NL + NL)
    return header + answer + NL + NL + "----- ANSWER ENDS -----" + NL + NL + "===== END OF PACKET =====" + NL, fm


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assemble(identity, part_c_text):
    text = (NL + shared_instructions().replace("{{IDENTITY_LINE}}", identity).rstrip(NL) + NL + parts_ab() + NL
            + part_c_text)
    if BEGIN in text or END in text:
        raise SystemExit("a marker appears inside the participant text")
    return text


def manifest_front(sources, packets, shared):
    return {
        "type": "round-prompt", "title": "Round 2 manifest",
        "author": "Claude Opus 5.5 (editor); tables and hashes computed by tools/build_round_02_packets.py",
        "model": "claude-opus-5-5", "developer": "Anthropic",
        "participant_id": "claude-opus-5-5/af349875", "participant_alias": "claude-opus-5-5/a94fb166",
        "run": "Claude Code session a94fb166-05a4-4540-9f8b-aae1aa74ece3 (continuing af349875)",
        "setup": {"application": "Claude Code desktop app", "platform": "Windows", "effort": "unknown"},
        "operator": "human/alileus", "role": "editor", "attribution": "self-declared", "date": "2026-09-24",
        "prompt": ("Founder, verbatim: \"go ahead with round 2 as proposed\"; on Grok 4.7, \"ok run both\". "
                   f"Built under {DESIGN} @ {DESIGN_COMMIT}."),
        "exposure": [sources["statement"], sources["propositions_and_questions"],
                     "the Round 1 response records named in packets"],
        "human_interventions": "none in the content; written by the builder from pinned sources",
        "samples": {"generated": 1, "submitted": 1},
        "generator": "tools/build_round_02_packets.py",
        "round": ROUND,
        "input_set": ["rounds/02-deliberation/packets/<participant>.md, the text between its markers only, "
                      "one packet per participant, as assigned in packets",
                      sources["statement"], sources["propositions_and_questions"],
                      "the Round 1 response records named in packets"],
        "sources": sources,
        "participant_text_sha256": shared,
        "participant_text_hash_scope": ("UTF-8, LF, all text strictly between the two markers: the shared text, with "
                                        "the literal placeholders {{IDENTITY_LINE}} and {{PART_C}}; this text is "
                                        "never sent"),
        "packets": packets,
        "lifecycle": "active",
    }


def render(fm, body_text):
    return "---" + NL + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=105) + "---" + NL + NL + body_text


def build():
    files, packets = {}, []
    sources = {"statement": f"statement.md @ {full(STATEMENT_COMMIT)}",
               "propositions_and_questions": f"propositions/, questions/ @ {full(SET_COMMIT)}",
               "instructions": f"{DESIGN} @ {full(DESIGN_COMMIT)}",
               "snapshot": f"every source is identical at {full(SNAPSHOT)}"}
    for slug, label, route, model, identity, record, commit in PARTICIPANTS:
        pc_text, pc_fm = part_c(record, commit)
        text = assemble(identity, pc_text)
        path = f"rounds/{ROUND}/packets/{slug}.md"
        first = (f"Generated by tools/build_round_02_packets.py from commit {full(SNAPSHOT)}: the Round 2 packet "
                 f"for {label}, route {route}, requested model {model}. Part C: {record} @ {full(commit)}. "
                 f"Only the text between the markers is sent; rounds/{ROUND}/prompt.md assigns this packet.")
        files[path] = first + NL + NL + BEGIN + text + END + NL
        packets.append({"participant": slug, "route": route, "requested_model": model, "packet": path,
                        "participant_text_sha256": sha(text), "bytes": len(text.encode("utf-8")),
                        "recorded_as": label, "identity_line": identity,
                        "part_c": f"{record} @ {full(commit)}", "part_c_participant": pc_fm["participant_id"]})
    template = assemble("{{IDENTITY_LINE}}", "{{PART_C}}" + NL)
    shared = sha(template)
    assign = NL.join(f"| `{p['participant']}` | `{p['route']}` | `{p['requested_model']}` "
                     f"| `packets/{p['participant']}.md` | `{p['participant_text_sha256']}` |" for p in packets)
    source_rows = NL.join(f"| `packets/{p['participant']}.md` | {p['recorded_as']} | `{p['part_c_participant']}` "
                          f"| {p['bytes']:,} |" for p in packets)
    mbody = ("# Round 2 Manifest" + NL + NL +
             "**Round:** `02-deliberation`, packet mode (proposed protocol amendment A1). The launch commit is tagged "
             "`round/02-deliberation/v1`. Each participant receives only the text between the markers of its own "
             "packet. Nothing in this file is sent." + NL + NL +
             "## Assignments" + NL + NL +
             "The runners read the `packets` list in the front matter at the launch tag. A run is refused unless its "
             "route and requested model match exactly one entry, the packet path is that entry's path spelled "
             "exactly, and the text between the packet's markers has that entry's SHA-256. The requested model is "
             "the exact string given to the runner; `fable` is a Claude Code alias. The resolved model is recorded "
             "from each run." + NL + NL +
             "| Participant | Route | Requested model | Packet | SHA-256 of the participant text |" + NL +
             "|---|---|---|---|---|" + NL + assign + NL + NL +
             "## Packets" + NL + NL +
             "Each packet is a generated file: line 1 names the generator and the source commit, and it has no front "
             "matter. Part C is the named participant's Round 1 answer." + NL + NL +
             "| Packet | Recorded as | Part C participant | Bytes sent |" + NL + "|---|---|---|---|" + NL +
             source_rows + NL + NL +
             "## Shared text" + NL + NL +
             "Between the markers below is the text common to every packet, with the literal placeholders "
             "`{{IDENTITY_LINE}}` and `{{PART_C}}`. Its SHA-256 is the front matter's `participant_text_sha256`. "
             "This block is a record, not a packet, and no runner sends it." + NL + NL +
             BEGIN + template + END + NL)
    files[f"rounds/{ROUND}/prompt.md"] = render(manifest_front(sources, packets, shared), mbody)
    return files, packets, shared


def main():
    files, packets, shared = build()
    if "--check" in sys.argv:
        bad = [p for p, t in files.items() if not (REPO / p).exists() or (REPO / p).read_bytes() != t.encode("utf-8")]
        print("check:", "OK" if not bad else f"DIFFERS: {bad}")
        sys.exit(1 if bad else 0)
    for p, t in files.items():
        (REPO / p).parent.mkdir(parents=True, exist_ok=True)
        (REPO / p).write_bytes(t.encode("utf-8"))
    for p in packets:
        print(f"{p['participant']:24s} {p['bytes']:7,} bytes  {p['participant_text_sha256'][:16]}  "
              f"{p['route']}/{p['requested_model']}  Part C {p['part_c_participant']}")
    print("shared text", shared)


if __name__ == "__main__":
    main()
