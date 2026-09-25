# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Roadmap step 16 (proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md), as designed in proposals/2026-09-25-claude-opus-5-5-launch-export.md, applying the rights check's decision D1 and the privacy sweep's dispositions S6 and S7. Revision 2 applies GPT-6's LX1-LX3 (topic launch-export, round 1); revision 3 its round 2 follow-ups; revision 4 its round 3 LX1 (every value of a repeated JSON key, and layered escapes in raw text and paths); revision 5 shares the escape-layer rule with the exporter and names every kind of archive finding.
# license: MIT (LICENSE-CODE)
"""Build the launch tree: the tracked tree at one pre-launch commit, transformed for publication.

Usage:
    python tools/build_launch_tree.py CONFIG OUT_DIR

CONFIG is a private JSON file. It is never published; the manifest names only its opaque "version". It holds:
    version          an opaque identifier, published
    source_commit    the pre-launch commit C whose tracked tree is built
    identifiers      provider-issued identifiers to withhold (privacy sweep S6)
    literals         other literal texts to withhold, such as application instructions (privacy sweep S7)
    grok_summaries   a JSON file: {path of a Grok answer: the editor's summary of it}
    notes            optional {path: a sentence added to that file's stub}
    remove           paths removed from the tree (rights check D1: the Grok screenshot and its sidecar)
    archive_dir      optional: the exporter's output folder, merged into the tree and verified, never changed
    prerequisites    commands run at the source commit, in a temporary worktree, before the build (default: the
                     extraction and packet checks); each must print a last line of "check: OK". [] runs none, and
                     the manifest then says the checks are unverified

Transforms, and nothing else:
    T1  every listed identifier, and any prefix of it at least 8 characters long that ends at a token boundary,
        becomes "(provider-issued identifier withheld)"; every listed literal becomes
        "(application instruction withheld)".
    T2  Grok's output (rights check, D1).
        - A file whose front matter names developer xAI becomes a stub: its body is replaced by a notice, the
          SHA-256 of the withheld body, and, for an answer, the editor's summary headed as the editor's words.
          Front-matter fields that hold Grok's words (conditions, basis, rewording) become markers; positions
          and provenance stay; a "withheld" field records the reason.
        - Everywhere else, a 40-character run whose earliest source is a Grok answer is Grok's. Sources are
          ordered by the stage they were written (STAGES); composite files (prompts, packets, the index) are not
          sources, and a non-Grok source wins a tie. Each maximal stretch of Grok's runs, widened to word
          boundaries, becomes "(Grok quotation withheld under the rights check, D1)". Front matter is changed
          through its parsed values and dumped again; bodies are changed in place. Text is compared after
          normalizing whitespace and curly quotes.
Markers contain no brackets and no ": ", so they are valid wherever they land in YAML.

Checks before anything is written (GPT-6 LX1-LX3):
    - the prerequisites pass at the source commit, and their output is recorded in the manifest;
    - the archive matches its own manifest, sessions/manifest.md: the same file set, and every hash;
    - every front matter still parses, with the same keys; keys are transformed like values, and a collision stops
      the build;
    - scan(): no Grok span and no listed identifier or literal remains in any file or path. Every text is read in
      the exporter's alternative forms (export_archive.views: escapes, percent-encoding, entities, JSON nested in
      strings), with front-matter keys and values; every value of a repeated JSON key is read; the raw text of a
      structured file, and every path, are decoded layer by layer to the exporter's depth limit; nesting or
      layering past the limit, and structured content that doesn't decode, count as findings;
    - every Markdown file passes tools/check_headers.py, and index.md's rows equal a build from the new tree.
The output folder must not exist. launch-manifest.md lists every file with its disposition and hashes.
"""
import argparse
import fnmatch
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_index  # noqa: E402
import check_headers  # noqa: E402
import export_archive  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
RULES_VERSION = "4"
PREREQUISITES = ("tools/extract_round_02_assessments.py --check", "tools/build_round_02_packets.py --check")
NL = chr(10)
W = 40
MIN_PREFIX = 8
ID_MARK = "(provider-issued identifier withheld)"
LITERAL_MARK = "(application instruction withheld)"
GROK_MARK = "(Grok quotation withheld under the rights check, D1)"
FIELD_MARK = "(withheld under the rights check, D1)"
GROK_FIELDS = ("conditions", "basis", "rewording")
DECISION = "critiques/2026-09-25-claude-opus-5-5--rights-check.md"
QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"'}
DUMP = {"sort_keys": False, "allow_unicode": True, "width": 105}
# Where each source text sits in the order of writing. Lower is earlier.
# Every text a Grok answer was shown is a source at the stage it was written, so that what Grok repeated from its
# prompt (an identity line, the scope) is not taken for Grok's own words. What those prompts copied from earlier
# answers still traces to the earlier answer, because it is earlier.
STAGES = (
    (0, ("statement.md", "rounds/00-initial/prompt.md", "proposals/2026-09-24-claude-opus-5-5-round-0-prompt.md")),
    (1, ("rounds/00-initial/responses/*.md",)),
    (2, ("rounds/01-deliberation/prompt.md", "proposals/2026-09-24-claude-opus-5-5-round-1-design.md")),
    (3, ("rounds/01-deliberation/responses/*.md",)),
    (4, ("propositions/*.md", "questions/*.md")),
    (5, ("rounds/02-deliberation/prompt.md", "rounds/02-deliberation/packets/*.md",
         "proposals/2026-09-24-claude-opus-5-5-round-2-design.md")),
    (6, ("rounds/02-deliberation/responses/*.md",)),
    (7, ("critiques/2026-09-25-grok-4-7--alternate-appointment.md", "moderation/2026-09-25-alternate-appointment.md")),
)
TEXT_SUFFIXES = {".md", ".py", ".yml", ".yaml", ".json", ".jsonl", ".txt", ".sse", ".svg", ".xml", ".html", ".css",
                 ".js", ".sh", ".toml", ".cfg", ".ini", ""}


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


class Tree:
    """The tracked tree at one commit, read with git."""

    def __init__(self, repo, commit):
        self.repo = repo
        self.commit = self.git("rev-parse", commit).decode().strip()
        self.paths = sorted(p for p in self.git("ls-tree", "-r", "--name-only", "-z", self.commit).decode().split("\0")
                            if p)

    def git(self, *a):
        return subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, check=True).stdout

    def blob(self, path):
        return self.git("show", f"{self.commit}:{path}")


def split_front(text):
    """(front-matter text or None, body)."""
    if text.startswith("---" + NL):
        parts = text.split("---" + NL, 2)
        if len(parts) == 3:
            return parts[1], parts[2]
    return None, text


def load_front(fm_text):
    try:
        v = yaml.safe_load(fm_text)
    except yaml.YAMLError:
        return None
    return v if isinstance(v, dict) else None


def is_grok(fm):
    return isinstance(fm, dict) and str(fm.get("developer", "")).strip().lower().startswith("xai")


def normalize(text):
    """(normalized text, index in text of each normalized character): whitespace runs become one space, curly
    quotes become straight ones."""
    out, pos, i = [], [], 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            j = i
            while j < len(text) and text[j].isspace():
                j += 1
            out.append(" ")
            pos.append(i)
            i = j
            continue
        out.append(QUOTES.get(c, c))
        pos.append(i)
        i += 1
    return "".join(out), pos


# Quotation forms (GPT-6 RC2, round 2): curly and straight double quotes, curly and straight single quotes (a
# straight one only between a boundary and a non-letter, so apostrophes don't pair up), and backticks.
# Straight quotes and backticks don't say which way they face, so their content must start and end with a
# non-space character; otherwise the closing mark of one quotation pairs with the opening mark of the next.
QUOTED = (re.compile(r"“([^”]{1,2000}?)”"), re.compile(r'"([^"\s](?:[^"\n]{0,1998}[^"\s])?)"'),
          re.compile(r"‘([^’\n]{1,2000}?)’(?![A-Za-z])"),
          re.compile(r"(?:(?<=^)|(?<=[\s(\[]))'([^'\s](?:[^'\n]{0,1998}[^'\s])?)'(?![A-Za-z])", re.M),
          re.compile(r"`([^`\s](?:[^`\n]{0,1998}[^`\s])?)`"))
BLOCKQUOTE = re.compile(r"(?m)^(?:[ \t]*>[^\n]*(?:\n|$))+")
NAMED = re.compile(r"(?i)\bgrok")
CONTEXT = 1500  # characters on each side of a quotation that are read for its attribution
MARKERS = re.compile(r"\((?:Grok quotation withheld|withheld under the rights check)[^)]*\)|\[WITHHELD: [^\]]*\]")


class GrokText:
    """Grok's output as it appears in the tree's source texts, and how to find it in any other text.

    Sources are ordered by stage and, within a stage, non-Grok first. A span of text is Grok's when its earliest
    source is a Grok answer. Two kinds of span are found: every 40-character run (unmarked copying), and every known
    quotation of Grok, in double quotes or a blockquote, at any length (GPT-6 RC2; see quotes_grok)."""

    def __init__(self, tree):
        sources = []
        for stage, patterns in STAGES:
            for path in tree.paths:
                if path.endswith(".meta.md") or not any(fnmatch.fnmatchcase(path, p) for p in patterns):
                    continue
                fm_text, body = split_front(tree.blob(path).decode("utf-8"))
                sources.append((stage, is_grok(load_front(fm_text) if fm_text else None), normalize(body)[0]))
        self.sources = sorted(sources, key=lambda s: (s[0], s[1]))
        self.grok_all = NL.join(t for _, grok, t in self.sources if grok)
        self.folded = [(grok, t.lower()) for _, grok, t in self.sources]
        self.grok_folded = self.grok_all.lower()
        first = {}
        for _, grok, text in self.sources:
            for i in range(len(text) - W + 1):
                first.setdefault(text[i:i + W], grok)
        self.windows = {w for w, grok in first.items() if grok}

    def origin_is_grok(self, snippet):
        """True if the earliest source holding snippet, ignoring case, is a Grok answer."""
        snippet = snippet.lower()
        if snippet not in self.grok_folded:
            return False
        return next((grok for grok, text in self.folded if snippet in text), False)

    def quotes_grok(self, snippet, before, after="", block=False, strict=False):
        """A known quotation of Grok: two or more words whose earliest source is Grok, and either long enough to be
        a quotation on its own (three words and 15 characters) or attributed to Grok nearby: earlier or later in its
        paragraph, or, for a blockquote, in the paragraph that introduces it. A two-word snippet naming Grok is a
        model label, not a quotation."""
        words = snippet.split()
        if len(words) < 2 or (len(words) == 2 and "grok" in snippet.lower()):
            return False
        if not self.origin_is_grok(snippet):
            return False
        if strict or (len(words) >= 3 and len(snippet) >= 15):
            return True
        paragraphs = before.rstrip().split(NL + NL)
        near = paragraphs[-1][-200:] + " " + after.split(NL + NL, 1)[0][:200]
        if block:  # the introduction may be its own paragraph, just before the blockquote
            near += " " + NL.join(paragraphs[-2:])[-400:]
        return bool(NAMED.search(MARKERS.sub(" ", near)))  # a withholding marker is not an attribution

    def spans(self, text, strict=False):
        """(start, end) stretches of text that are Grok's, merged and in order. strict, for the archive: a
        quotation of two or more words whose earliest source is Grok counts without an attribution, so the result
        doesn't depend on how much context surrounds a string (a transcript nests strings inside strings)."""
        found = sorted(window_spans(text, self.windows) + self.quote_spans(text, strict))
        merged = []
        for a, b in found:
            if merged and a <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(b, merged[-1][1]))
            else:
                merged.append((a, b))
        return merged

    def quote_spans(self, text, strict=False):
        spans = []
        for pattern in QUOTED:
            for m in pattern.finditer(text):
                inner = m.group(1)
                snippet = normalize(inner)[0].strip()
                if NL + NL in inner:
                    continue
                if self.quotes_grok(snippet, text[max(0, m.start() - CONTEXT):m.start()], text[m.end():m.end() + CONTEXT],
                                    strict=strict):
                    lead = len(inner) - len(inner.lstrip())
                    spans.append((m.start(1) + lead, m.start(1) + len(inner.rstrip())))
        for m in BLOCKQUOTE.finditer(text):
            lines = m.group(0).rstrip(NL).split(NL)
            content = " ".join(re.sub(r"^[ \t]*>[ \t]?", "", line) for line in lines)
            snippet = normalize(content)[0].strip()
            if self.quotes_grok(snippet, text[max(0, m.start() - CONTEXT):m.start()], text[m.end():m.end() + CONTEXT],
                               block=True, strict=strict):
                first = re.match(r"[ \t]*>[ \t]?", lines[0]).end()
                spans.append((m.start() + first, m.start() + len(m.group(0).rstrip(NL))))
        return spans


def word_char(c):
    return c.isalnum() or c in "_'-"


def window_spans(text, windows):
    """Maximal stretches of text covered by 40-character windows, as (start, end), widened to word boundaries."""
    norm, pos = normalize(text)
    covered = []
    for i in range(len(norm) - W + 1):
        if norm[i:i + W] in windows:
            if covered and i <= covered[-1][1]:
                covered[-1][1] = i + W
            else:
                covered.append([i, i + W])
    spans = []
    for a, b in covered:
        start, end = pos[a], pos[b - 1] + 1
        while start > 0 and word_char(text[start - 1]) and word_char(text[start]):
            start -= 1
        while end < len(text) and word_char(text[end - 1]) and word_char(text[end]):
            end += 1
        while start < end and text[start].isspace():
            start += 1
        while end > start and text[end - 1].isspace():
            end -= 1
        if spans and start <= spans[-1][1]:
            spans[-1] = (spans[-1][0], max(end, spans[-1][1]))
        elif end > start:
            spans.append((start, end))
    return spans


def replace_spans(text, spans, mark):
    out, last = [], 0
    for a, b in spans:
        out += [text[last:a], mark]
        last = b
    return "".join(out + [text[last:]])


def id_pattern(identifiers):
    alts = sorted({i[:k] for i in identifiers for k in range(MIN_PREFIX, len(i) + 1)}, key=len, reverse=True)
    return re.compile(r"(?<![A-Za-z0-9_-])(?:" + "|".join(map(re.escape, alts)) + r")(?![A-Za-z0-9_])") if alts else None


class Builder:
    def __init__(self, cfg, tree):
        self.cfg, self.tree = cfg, tree
        self.ids = id_pattern(cfg.get("identifiers", []))
        self.literals = list(cfg.get("literals", []))
        self.grok = GrokText(tree)
        self.summaries = json.loads(Path(cfg["grok_summaries"]).read_text(encoding="utf-8"))
        self.notes = cfg.get("notes", {})
        self.remove = set(cfg.get("remove", []))

    def t1(self, text):
        n = 0
        if self.ids:
            text, n = self.ids.subn(ID_MARK, text)
        for lit in self.literals:
            n += text.count(lit)
            text = text.replace(lit, LITERAL_MARK)
        return text, n

    def t2(self, text):
        spans = self.grok.spans(text)
        return replace_spans(text, spans, GROK_MARK), len(spans)

    def walk(self, v, fn):
        """Apply fn to every string in a parsed front matter; returns (value, count)."""
        if isinstance(v, str):
            return fn(v)
        if isinstance(v, dict):
            out, n = {}, 0
            for k, x in v.items():
                key, m = fn(k) if isinstance(k, str) else (k, 0)  # keys are transformed like values (LX1)
                if key in out:
                    raise ValueError(f"two front-matter keys would be the same after the transform: {key!r}")
                out[key], m2 = self.walk(x, fn)
                n += m + m2
            return out, n
        if isinstance(v, list):
            out, n = [], 0
            for x in v:
                y, m = self.walk(x, fn)
                out.append(y)
                n += m
            return out, n
        return v, 0

    def stub(self, path, fm, body):
        withheld = {"decision": "rights check, D1", "record": DECISION, "body_sha256": sha256(body)}
        fm = dict(fm)
        for k in GROK_FIELDS:
            if k in fm:
                fm[k] = FIELD_MARK
        fm["withheld"] = withheld
        title = str(fm.get("title", path))
        lines = [f"# Withheld: {title}", "",
                 f"This file held text written by {str(fm.get('author', 'Grok')).split(' (')[0]}. Under the founder's "
                 f"decision D1 in the rights check (`{DECISION}`), Grok's output is not published: xAI's API terms bar "
                 "the customer from permitting anyone to train AI models on it. The original stays in the founder's "
                 "private archive.", "",
                 f"- **SHA-256 of the withheld body:** `{withheld['body_sha256']}`"]
        if fm.get("subtype") == "assessment":
            lines += ["- **Kept:** the position, in the front matter, as a fact about the record. The conditions, "
                      "basis and rewording are withheld."]
            source = str(fm.get("source", "")).split(" @ ")[0]
            if source in self.summaries:
                lines += [f"- **The editor's summary** of the whole answer is in `{source}`."]
        if path in self.notes:
            lines += ["", self.notes[path]]
        if path in self.summaries:
            lines += ["", "## Summary, in the editor's words", "", self.summaries[path], "",
                      "This summary is the editor's reading, not Grok's text."]
        return fm, NL + NL.join(lines) + NL

    def transform(self, path, text):
        """(new text, changes) for one tracked text file."""
        changes = {}
        fm_text, body = split_front(text)
        fm = load_front(fm_text) if fm_text is not None else None
        if fm_text is not None and fm is None and path.endswith(".md"):
            raise ValueError(f"{path}: front matter does not parse at the source commit")
        grok = is_grok(fm)
        if grok:
            fm, body = self.stub(path, fm, body)
            changes["Grok file withheld"] = 1
        if fm is not None:
            fm2, n = self.walk(fm, self.t2)
            if n:
                changes["Grok quotations"] = changes.get("Grok quotations", 0) + n
            fm2, m = self.walk(fm2, self.t1)
            if m:
                changes["identifiers or literals"] = m
            if grok or n or m:
                fm_text = yaml.safe_dump(fm2, **DUMP)
            if set((load_front(fm_text) or {}).keys()) != set(fm2.keys()):
                raise ValueError(f"{path}: front matter changed shape")
        if not grok:
            body, n = self.t2(body)
            if n:
                changes["Grok quotations"] = changes.get("Grok quotations", 0) + n
        body, m = self.t1(body)
        if m:
            changes["identifiers or literals"] = changes.get("identifiers or literals", 0) + m
        out = ("---" + NL + fm_text + "---" + NL + body) if fm_text is not None else body
        return out, changes

    def leftovers(self, text, strict=False, quotes=True):
        """What a finished text still holds: Grok runs and listed identifiers or literals, counted. quotes=False
        is for the raw text of a JSON file, where JSON's own string delimiters would read as quotation marks; its
        decoded strings are checked with quotations."""
        found = len(self.grok.spans(text, strict) if quotes else window_spans(text, self.grok.windows))
        found += len(self.ids.findall(text)) if self.ids else 0
        found += sum(text.count(lit) for lit in self.literals)
        return found

    def scan(self, path, data, strict=False):
        """Findings left in one finished file and its path (GPT-6 LX1, rounds 1 and 2). See reading_set()."""
        texts, plain, problems = reading_set(path, data)
        return (problems + sum(self.leftovers(t, strict) for t in texts)
                + sum(self.leftovers(t, strict, quotes=False) for t in plain))


JSONISH = (".json", ".jsonl", ".sse")


def simple_alternatives(text):
    """(readings, too_deep) of raw text or a path: export_archive.escape_readings, the rule the exporter also applies
    to every string (GPT-6 LX1, round 3). too_deep is a finding: the text can't be checked safely."""
    return export_archive.escape_readings(text)


def json_strings(path, text):
    """(decoded strings, malformed units) of a JSON, JSON Lines or server-sent-events file. A unit that doesn't
    decode is counted, so content that can't be checked safely is a finding (GPT-6 LX1, round 2). Every value of a
    repeated key is kept (export_archive.load_all; LX1, round 3)."""
    strings, bad = [], 0
    if path.endswith(".json"):
        units = [text] if text.strip() else []
    elif path.endswith(".jsonl"):
        units = [ln for ln in text.splitlines() if ln.strip()]
    else:
        units = [ln[5:].strip() for ln in text.splitlines() if ln.startswith("data:") and ln[5:].strip() != "[DONE]"]
    for unit in units:
        try:
            strings += list(strings_in(export_archive.load_all(unit)))
        except ValueError:
            bad += 1
    return strings, bad


def reading_set(path, data):
    """(texts, plain, problems): everything a final scan reads in one file (GPT-6 LX1).
    texts: the texts a person reads (a Markdown body, each front-matter key and value, each decoded JSON string,
      or the plain text) with every alternative reading of each (export_archive.views). Quotation rules apply.
    plain: the raw text of a structured file, and the path, with their escape-level alternatives, layer by layer
      (simple_alternatives). Only runs, identifiers and literals are checked, because JSON's and YAML's own quotes
      are not quotation marks.
    problems: nesting or escape layers past the exporter's limit, and structured content that doesn't decode."""
    text = data.decode("utf-8", errors="replace")
    fm_text, body = split_front(text) if path.endswith(".md") else (None, text)
    fm = load_front(fm_text) if fm_text is not None else None
    problems = 0
    if path.endswith(JSONISH):
        quotable, bad = json_strings(path, text)
        problems += bad
        raw = [text]
    elif fm is not None:
        quotable, raw = [body] + list(strings_in(fm)), [text]
    else:
        quotable, raw = [text], []
    texts = []
    for t in quotable:
        alternatives, too_deep = export_archive.views(t)
        problems += int(too_deep)
        texts += alternatives
    plain = []
    for t in raw + [path]:
        alternatives, too_deep = simple_alternatives(t)
        problems += int(too_deep)
        plain += [t] + alternatives
    return texts, plain, problems


def readings(path, data):
    """The text of a file, and for JSON-like files the decoded strings too, every value of a repeated key
    included."""
    text = data.decode("utf-8", errors="replace")
    out = [text]
    if path.endswith(JSONISH):
        for line in text.splitlines() or [text]:
            line = line[5:].strip() if line.startswith("data:") else line
            try:
                out += list(strings_in(export_archive.load_all(line)))
            except ValueError:
                continue
        try:
            out += list(strings_in(export_archive.load_all(text)))
        except ValueError:
            pass
    return out


MANIFEST_ROW = re.compile(r"\| `([^`]+)` \| ([^|]+) \| ([^|]+) \| (?:`([0-9a-f]{64}|-)`)? \| (?:`([0-9a-f]{64}|-)`)? \|")


def archive_manifest(text):
    """The exporter's manifest rows: {dest: (disposition, output SHA-256 or None)}. A malformed or repeated row is
    an error."""
    rows = {}
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        m = MANIFEST_ROW.match(line)
        if not m or m.group(1) in rows:
            raise ValueError(f"the archive manifest has a malformed or repeated row: {line[:80]!r}")
        out = m.group(5) if m.group(5) not in (None, "-") else None
        rows[m.group(1)] = (m.group(3).strip(), out)
    return rows


def check_archive(root, files):
    """The archive part of a tree must match its own manifest exactly (GPT-6 LX2): every published file and its
    sidecar present with the recorded hash, nothing else under sessions/ or rounds/*/evidence/."""
    if "sessions/manifest.md" not in files:
        raise ValueError("the archive has no manifest (sessions/manifest.md)")
    rows = archive_manifest(files["sessions/manifest.md"].decode("utf-8"))
    expected = {"sessions/manifest.md"}
    for dest, (disposition, out) in rows.items():
        if disposition == "published":
            if not out:
                raise ValueError(f"the archive manifest gives no output hash for {dest}")
            expected |= {dest, dest + ".meta.md"}
            if dest not in files or sha256(files[dest]) != out:
                raise ValueError(f"{dest} does not match its hash in the archive manifest")
    present = {f for f in files if f.startswith("sessions/") or re.match(r"rounds/[^/]+/evidence/", f)}
    if present != expected:
        raise ValueError(f"the archive's files differ from its manifest: {sorted(present ^ expected)[:5]}")
    return rows


def run_prerequisites(repo, commit, commands):
    """Run each command in a temporary worktree at commit (GPT-6 LX3). Returns [(command, last line)]."""
    import tempfile
    results = []
    if not commands:
        return results
    with tempfile.TemporaryDirectory() as tmp:
        wt = Path(tmp) / "wt"
        subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "--detach", str(wt), commit], check=True,
                       capture_output=True)
        try:
            for cmd in commands:
                r = subprocess.run([sys.executable, *cmd.split()], cwd=wt, capture_output=True, text=True)
                last = ((r.stdout + r.stderr).strip().splitlines() or [""])[-1]
                if r.returncode or last != "check: OK":
                    raise ValueError(f"prerequisite failed at {commit[:7]}: {cmd}: {last}")
                results.append((cmd, last))
        finally:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], capture_output=True)
    return results


def strings_in(v):
    stack = [v]
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            stack += list(x.keys()) + list(x.values())
        elif isinstance(x, list):
            stack += x
        elif isinstance(x, str):
            yield x


def build(cfg, out, repo=REPO):
    tree = Tree(repo, cfg["source_commit"])
    b = Builder(cfg, tree)
    if out.exists():
        raise FileExistsError(out)
    checks = run_prerequisites(repo, tree.commit, cfg.get("prerequisites", list(PREREQUISITES)))
    files, rows = {}, []
    for path in tree.paths:
        data = tree.blob(path)
        if path in b.remove:
            rows.append((path, "removed", "rights check, D1", "", ""))
            continue
        if Path(path).suffix.lower() not in TEXT_SUFFIXES and not path.startswith("."):
            files[path] = data
            rows.append((path, "unchanged", "", sha256(data), sha256(data)))
            continue
        text = data.decode("utf-8")
        new, changes = b.transform(path, text)
        files[path] = new.encode("utf-8")
        if b.scan(path, new.encode("utf-8")):
            raise ValueError(f"{path}: Grok text or a listed identifier remains after the transform")
        disp = "withheld-stub" if "Grok file withheld" in changes else ("transformed" if changes else "unchanged")
        detail = "; ".join(f"{k}: {v}" for k, v in sorted(changes.items()) if k != "Grok file withheld")
        rows.append((path, disp, detail, sha256(data), sha256(files[path])))
    archive = Path(cfg["archive_dir"]) if cfg.get("archive_dir") else None
    if archive:
        check_archive(archive, {p.relative_to(archive).as_posix(): p.read_bytes()
                                for p in archive.rglob("*") if p.is_file()})
        for p in sorted(archive.rglob("*")):
            if p.is_file():
                rel = p.relative_to(archive).as_posix()
                if rel in files:
                    raise ValueError(f"{rel}: the archive would overwrite a tracked file")
                data = p.read_bytes()
                if b.scan(rel, data, strict=True):
                    raise ValueError(f"{rel}: the archive holds Grok text, a listed identifier or literal, or content "
                                     "that can't be checked safely (nesting or escapes past the limit, or JSON that "
                                     "doesn't decode)")
                files[rel] = data
                rows.append((rel, "added by the exporter", "see sessions/manifest.md", "", sha256(data)))
    manifest = render_manifest(cfg, tree, rows, checks)
    files["launch-manifest.md"] = manifest.encode("utf-8")
    out.mkdir(parents=True)
    try:
        for rel, data in files.items():
            dest = out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "xb") as fh:
                fh.write(data)
        verify(out, files)
    except Exception:
        shutil.rmtree(out)
        raise
    return rows


def render_manifest(cfg, tree, rows, checks=()):
    lines = [f"Generated by tools/build_launch_tree.py from commit {tree.commit}. Do not edit this file; rerun the "
             "builder.", "", "# Launch Manifest", "",
             f"- **Builder rules version:** {RULES_VERSION}",
             f"- **Private configuration version:** {cfg['version']} (the configuration itself is private)",
             f"- **Source commit:** `{tree.commit}`, a pre-launch commit held in the private archive",
             "- **Archive export:** its own manifest is `sessions/manifest.md`" if cfg.get("archive_dir") else
             "- **Archive export:** none in this build",
             "- **Checks that need the private archive,** run by this build in a temporary worktree at the source "
             "commit: " + ("; ".join(f"`{c}` printed `{last}`" for c, last in checks) if checks else
                           "none were run for this build, so they are unverified"), "",
             "Every file in the launch commit is listed. Hashes are SHA-256. A removed file is listed without a hash.",
             "", "| Path | Disposition | Changes | At the source commit | At launch |", "|---|---|---|---|---|"]
    for path, disp, detail, src, dst in sorted(rows) + [("launch-manifest.md", "generated", "this file", "", "")]:
        lines.append(f"| `{path}` | {disp} | {detail} | {('`' + src + '`') if src else ''} | "
                     f"{('`' + dst + '`') if dst else ''} |")
    return NL.join(lines) + NL


def verify(out, files):
    """Header checks on every Markdown file, and the index rows against the new tree."""
    errors = []
    for rel in sorted(files):
        if rel.endswith(".md") or rel in (".gitignore",) or rel.endswith((".py", ".yml")):
            errs, _ = check_headers.check(rel, root=out)
            errors += [f"{rel}: {e}" for e in errs]
    if errors:
        raise ValueError("header check failed:" + NL + NL.join(errors[:20]))
    index = (out / "index.md").read_bytes()
    rows = build_index.build(None, root=out).encode("utf-8").split(b"\n", 1)[1]
    if index.split(b"\n", 1)[1:] != [rows]:
        raise ValueError("index.md's rows differ from a build of the launch tree")
    if (out / "sessions/manifest.md").exists():
        check_archive(out, {rel: (out / rel).read_bytes() for rel in files})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config")
    ap.add_argument("out")
    args = ap.parse_args(argv)
    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    rows = build(cfg, Path(args.out))
    counts = {}
    for r in rows:
        counts[r[1]] = counts.get(r[1], 0) + 1
    print("built", args.out, "|", ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))


if __name__ == "__main__":
    main()
