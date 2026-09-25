# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: The founder chose, verbatim, "Publish everything, redacted" (roadmap step 10). Implements the export process of proposals/2026-09-24-claude-opus-5-5-publication-policy.md, revision 3, reviewed by GPT-6 in topic publication-policy. Revision 2 applies GPT-6 EX1-EX5 (topic export-tool); revision 3 applies its round 2 cases; revision 4 applies its round 3 EX2 cases; revision 5 its export-tool-2 round 1 cases; revision 6 withholds fetched third-party content (GPT-6 RC4, topic rights-check); revision 7 withholds Grok's output by the launch builder's rule (rights check D1); revision 8 redacts identifier prefixes as the builder does and classifies standalone tool results by their call (GPT-6 RC4, round 2); revision 9 withholds a string whose alternative readings show Grok's text or an identifier (GPT-6 LX1); revision 10 applies the quotation rule in those readings too (LX1, round 2); revision 11 reads every value of a repeated JSON key (LX1, round 3); revision 12 withholds a string whose escapes are layered past the limit, by the rule the launch builder's scan applies (found by the first final build).
# license: MIT (LICENSE-CODE)
"""Export private evidence and transcripts for publication, redacted, under the publication policy.

Usage:
    python tools/export_archive.py CONFIG OUT_DIR

CONFIG is a private JSON file. It is never published; the manifest names only its opaque "version". It holds:
    version            an opaque identifier, published
    source_commit      the repository commit the export describes
    cutoff_utc         the cutoff time (policy PP3)
    keys_file          a KEY=value file; every value is redacted as a secret wherever it occurs, and is never written
    terms              [{"text": ..., "category": ...}]: literal private strings, replaced wherever they occur
    withhold_terms     [{"text": ..., "category": ...}]: a text part containing one of these is withheld whole
    cleared_reasoning  providers whose terms allow publishing their returned reasoning (class B); default none
    withhold_tool_results  extra tool calls whose results are withheld as class D: "Name" or "Name:description
                       substring" (the input's description), fnmatch patterns; FETCH_TOOLS are always withheld
    grok               optional {"repo", "commit"}: Grok's output is found in every string by the rule of
                       tools/build_launch_tree.py (rights check D1) and replaced by a marker
    identifiers        provider-issued identifiers; each, and any prefix of 8 or more characters, is redacted as
                       account-id wherever it occurs, as the launch builder does (privacy sweep S6)
A source may carry "tool_result_of": {"transcripts": [paths], "id": tool_use_id}: a tool result saved as its own file.
It is withheld whole as class D when its call, found in those transcripts, fetched content (as in a transcript),
and withheld as unclassified when its call cannot be found.
    sources            [{"path", "dest", "format", "reasoning_class", "provider", "sidecar": {front-matter fields}}]

Fetched third-party content (policy PP1 class D, GPT-6 RC4): in a Claude transcript, the result of a call to a
web or browser tool (FETCH_TOOLS), or to a configured call, is withheld whole. The call itself, with its URL or
query, stays as the source reference.

Formats (policy PP1 and PP2): claude-transcript, codex-run, json, sse, ollama-jsonl, text, withhold. Transcripts are
normalized to an allowlist of visible conversation, tool calls and results (linked by export-local IDs); everything
else is withheld or dropped, with counts. Model reasoning is class B (withheld unless its provider is cleared) or
class C (the editor's and reviewer's own; always withheld).

Every string, in every format and at any depth, goes through one pipeline:
    injected <system-reminder> context is withheld, including an unterminated one (class C);
    a string that is itself a JSON object or array is decoded, processed, and re-encoded (a structural change);
    a data URI of any kind, an image or document object, or a long base64-like run is withheld (class D);
    a withhold term withholds the whole string; literal terms, key values, emails, key-shaped tokens and
    dotted quads are replaced (every dotted quad is treated as a possible network identifier, including a
    version number that looks like one: a deliberate fail-closed choice, counted separately);
    finally the result is read again in its alternative forms (Unicode escapes, percent-encoding, HTML
    entities, and every string decoded from JSON inside it, to MAX_DEPTH levels; an object that repeats a key is
    read with every value, not only the last). If any reading still shows a detection, JSON nested past the limit,
    escapes layered past the limit (escape_readings), a reminder, encoded content, or JSON with a reasoning field or
    a repeated key (however it is wrapped), the whole string is withheld.
Object keys go through the same pipeline, and colliding keys are kept apart with a numbered suffix. A text source
is decoded as JSON when it is JSON, and line by line otherwise, after multi-line reminders are removed.

Streamed text (SSE deltas, Gemini parts, Ollama chunks) is classified before cleaning, on the original text
assembled separately for each channel, choice or candidate, and thought or answer part: any piece that overlaps a
detection, an injected-context block, or encoded content is withheld; if an alternative reading of the assembled
text shows a detection or a protected construct (the same check as a string's final reading), or the text contains
a data URI, the whole group is withheld. Every event shape is processed, not only objects; only the [DONE] sentinel
passes unchanged. The processed stream is assembled and checked again.

Nothing is written until every destination, reason and sidecar value is checked, in all its alternative readings:
destinations must be in a subfolder of sessions/ or rounds/*/evidence/, free of private data, unique
case-insensitively across payloads, sidecars and the manifest, free of Windows reserved names, and never a file
where another output needs a folder. Files are created exclusively. Every sidecar must pass tools/check_headers.py.
At the end, every written file and path is rescanned in all its readings, including the parsed YAML values of
every sidecar and the manifest; the file set is compared with the manifest, and each hash is re-checked. Any
failure stops with an error, and the output folder must then be discarded. This rescan is one method; the
policy's second, independent review happens separately.
"""
import copy
import fnmatch
import hashlib
import html
import json
import re
import sys
import urllib.parse
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_headers  # noqa: E402

RULES_VERSION = "12"
NL = chr(10)
MAX_DEPTH = 8
CATEGORIES = ("contact", "secret", "personal", "confidential", "account-id", "network")
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")
DOTTED_QUAD = re.compile(r"(?<![\d.])(?!127\.0\.0\.1(?![\d.]))(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}(?![\d.])")
KEY_SHAPES = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|xai-[A-Za-z0-9]{20,}|AIza[0-9A-Za-z_-]{35}|ghp_[A-Za-z0-9]{30,}"
                        r"|github_pat_[A-Za-z0-9_]{30,})\b")
ENCODED = re.compile(r"\bdata:[A-Za-z0-9.+/;=-]*,|[A-Za-z0-9+/_-]{200,}={0,2}")
REMINDER_OPEN = "<system-reminder>"
REMINDER = re.compile(r"<system-reminder>.*?(?:</system-reminder>|\Z)", re.S)
REASONING_KEY = re.compile(r"(?i)thinking|reasoning|thought")
NOT_REASONING = {"packaged_thinking", "thinking_note", "thinkingConfig", "includeThoughts", "thoughtsTokenCount",
                 "reasoning_tokens", "thinking_tokens", "thinkingTokens"}
IMAGE_TYPES = {"image", "image_url", "input_image", "document", "file", "audio"}
RESERVED = re.compile(r"(?i)^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\..*)?$")
DATA_URI = re.compile(r"\bdata:[A-Za-z0-9.+/;=-]*,")
DONE = object()  # the SSE [DONE] sentinel, kept apart from any parsed event value
FETCH_TOOLS = ("WebFetch", "WebSearch", "mcp__Claude_Browser__*", "mcp__claude-in-chrome__*", "mcp__*fetch*",
               "mcp__*browser*", "mcp__*search*")


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


def safe_label(x):
    """A label derived from source content, safe to publish: a short plain token, or 'unknown'."""
    return x if isinstance(x, str) and re.fullmatch(r"[A-Za-z0-9_.-]{1,40}", x) else "unknown"


def reasoning_field(k, x):
    """A reasoning field: a reasoning-named key, not a known setting or count, holding a non-empty value that is not a
    number or flag. walk() and protected_reading() share this test, so wrapped and direct structures agree."""
    return (isinstance(k, str) and bool(REASONING_KEY.search(k)) and k not in NOT_REASONING
            and not isinstance(x, (bool, int, float)) and x not in (None, "", [], {}))


def thought_part(p):
    """A Gemini thought part: a content part flagged as a thought, with non-empty text."""
    return isinstance(p, dict) and bool(p.get("thought")) and p.get("text") not in (None, "")


def strings_in(v):
    """Every string in a JSON-like value: keys and values, at any depth."""
    stack, out = [v], []
    while stack:
        x = stack.pop()
        if isinstance(x, dict):
            stack += list(x.keys()) + list(x.values())
        elif isinstance(x, list):
            stack += x
        elif isinstance(x, str):
            out.append(x)
    return out


class RepeatedKeys(list):
    """A JSON object that repeats a key, kept as its [key, value] pairs. json.loads would keep only the last value,
    so a reading would miss the others (GPT-6 LX1, launch-export round 3)."""


def all_pairs(pairs):
    keys = [k for k, _ in pairs]
    return dict(pairs) if len(set(keys)) == len(keys) else RepeatedKeys([k, v] for k, v in pairs)


def load_all(s):
    """json.loads for reading: an object that repeats a key becomes RepeatedKeys, so every value is read."""
    return json.loads(s, object_pairs_hook=all_pairs)


ESCAPE_FORMS = 64  # at most this many distinct escape-level readings of one text


def unescapings(x):
    """One layer of each escape views() undoes, without decoding JSON."""
    return (re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), x), urllib.parse.unquote(x),
            html.unescape(x))


def escape_readings(text):
    """(readings, too_deep): the escape-level readings of text, without decoding JSON: Unicode escapes,
    percent-encoding and HTML entities, undone layer by layer and in every order, to MAX_DEPTH (GPT-6 LX1,
    launch-export round 3). too_deep is True if a new reading still appears past that depth, or the readings exceed
    ESCAPE_FORMS: the text can't be checked safely. The launch builder reads raw text and paths with this rule, and
    the exporter withholds a string it refuses, so the builder never meets one in the archive."""
    out, seen, layer = [], {text}, [text]
    for depth in range(1, MAX_DEPTH + 2):
        found = [alt for x in layer for alt in unescapings(x) if alt not in seen]
        if not found:
            return out, False
        if depth > MAX_DEPTH:
            return out, True
        layer = []
        for alt in found:
            if alt not in seen:
                seen.add(alt)
                out.append(alt)
                layer.append(alt)
        if len(out) > ESCAPE_FORMS:
            return out, True
    return out, True


def views(s):
    """(readings, too_deep): s, its Unicode-unescaped, percent-decoded and HTML-unescaped forms, and every string
    decoded from JSON inside any of them (whole string, SSE data lines, JSON-looking lines), to MAX_DEPTH levels,
    every value of a repeated key included (load_all). too_deep is True if JSON is still nested at the limit."""
    out, seen, todo, too_deep = [], set(), [(s, 0)], False
    while todo:
        x, depth = todo.pop()
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
        for alt in (re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), x),
                    urllib.parse.unquote(x), html.unescape(x)):
            if alt != x:
                todo.append((alt, depth))
        lines = x.split(NL)
        candidates = {x.strip()} | {ln[5:].strip() for ln in lines if ln.startswith("data:")} \
            | {ln.strip() for ln in lines if ln.strip()[:1] in ("{", "[", '"')}
        for c in candidates:
            if not c or c[0] not in ("{", "[", '"'):
                continue
            try:
                v = load_all(c)
            except ValueError:
                continue
            if depth >= MAX_DEPTH:
                too_deep = True
                continue
            for leaf in strings_in(v):
                todo.append((leaf, depth + 1))
    return out, too_deep


class Redactor:
    """Detects and replaces private data. Counts go to the manifest; values never do."""

    def __init__(self, config):
        self.terms = [(t["text"], t["category"]) for t in config.get("terms", [])]
        self.withhold_terms = [(t["text"].lower(), t["category"]) for t in config.get("withhold_terms", [])]
        for text, cat in self.terms + self.withhold_terms:
            if cat not in CATEGORIES or not text:
                raise ValueError("a configured term needs text and a known category")
        self.secrets = []
        keys_file = config.get("keys_file")
        if keys_file:
            for line in Path(keys_file).read_text(encoding="utf-8-sig").splitlines():
                _, sep, v = line.strip().partition("=")
                if sep and v.strip():
                    self.secrets.append(v.strip())
        self.literals = sorted([(s, "secret") for s in self.secrets] + self.terms, key=lambda x: -len(x[0]))
        self.counts = {}

    def count(self, key, n=1):
        self.counts[key] = self.counts.get(key, 0) + n

    def spans(self, text):
        """[(start, end, category)] of every detection in text."""
        out = []
        for lit, cat in self.literals:
            start = text.find(lit)
            while start != -1:
                out.append((start, start + len(lit), cat))
                start = text.find(lit, start + 1)
        low = text.lower()
        for term, cat in self.withhold_terms:
            start = low.find(term)
            while start != -1:
                out.append((start, start + len(term), cat))
                start = low.find(term, start + 1)
        for rx, cat in ((EMAIL, "contact"), (KEY_SHAPES, "secret"), (DOTTED_QUAD, "network")):
            out += [(m.start(), m.end(), cat) for m in rx.finditer(text)]
        return out

    def detect(self, text, ignore=()):
        """The categories detected in text, after removing the exact marker strings this export emitted."""
        for marker in sorted(ignore, key=len, reverse=True):
            text = text.replace(marker, "")
        return sorted({cat for _, _, cat in self.spans(text)})

    def detect_all(self, text, ignore=()):
        """Categories detected in any reading of text, plus 'nested too deep' when decoding hits the limit."""
        readings, too_deep = views(text)
        found = set()
        for r in readings:
            found |= set(self.detect(r, ignore))
        if too_deep:
            found.add("nested too deep")
        return sorted(found)

    def replace(self, s, marker):
        """Replace literals and patterns in s (no withholding)."""
        for lit, cat in self.literals:
            if lit in s:
                self.count(cat, s.count(lit))
                s = s.replace(lit, marker(f"REDACTED: {cat}"))
        for rx, cat, label in ((KEY_SHAPES, "secret", "secret"), (EMAIL, "contact", "contact"),
                               (DOTTED_QUAD, "network", "network (dotted quad; may be a version number)")):
            s, n = rx.subn(marker(f"REDACTED: {cat}"), s)
            if n:
                self.count(label, n)
        return s


class Export:
    def __init__(self, config, out_dir):
        self.config = config
        self.out = Path(out_dir)
        self.cleared = set(config.get("cleared_reasoning", []))
        self.rows = []
        self.emitted = set()
        self.red = Redactor(config)
        self.w = {}
        self.grok = None
        self.id_re = None
        if config.get("identifiers"):
            import build_launch_tree
            self.id_re = build_launch_tree.id_pattern(config["identifiers"])
        if config.get("grok"):
            import build_launch_tree  # the launch builder's rule, so the tree and the archive agree
            g = config["grok"]
            self.grok = build_launch_tree.GrokText(build_launch_tree.Tree(Path(g["repo"]), g["commit"]))
            self.window_spans = build_launch_tree.window_spans

    # ---- markers and counts ----

    def marker(self, body):
        m = f"[{body}]"
        self.emitted.add(m)
        return m

    def withheld(self, what):
        return self.marker(f"WITHHELD: {what}; see manifest")

    def note(self, what, n=1):
        self.w[what] = self.w.get(what, 0) + n

    # ---- the uniform string and value pipeline ----

    def clean(self, s, depth=0):
        if not isinstance(s, str):
            s = str(s)
        if REMINDER_OPEN in s:
            self.note("C, injected context", len(REMINDER.findall(s)))
            s = REMINDER.sub(lambda _: self.withheld("C, injected context"), s)
        result = None
        stripped = s.strip()
        if stripped[:1] in ("{", "[") and len(stripped) > 1:
            try:
                decoded = json.loads(stripped)
            except ValueError:
                decoded = None
            if isinstance(decoded, (dict, list)):
                if depth >= MAX_DEPTH:
                    self.note("D, JSON nested too deep")
                    return self.withheld("D, JSON nested too deep")
                self.note("structural: nested JSON decoded and re-encoded")
                result = json.dumps(self.walk(decoded, depth + 1), ensure_ascii=False)
        if result is None and self.grok is not None:
            spans = self.grok.spans(s, strict=True)
            if spans:
                self.note("withheld: Grok quotation (rights check, D1)", len(spans))
                mark = self.withheld("rights check D1, Grok output")
                s = "".join(part for i, (a, b) in enumerate(spans) for part in
                            (s[spans[i - 1][1] if i else 0:a], mark)) + s[spans[-1][1]:]
        if result is None and self.id_re is not None:
            s, n = self.id_re.subn(lambda _: self.marker("REDACTED: account-id"), s)
            if n:
                self.red.count("account-id", n)
        if result is None:
            low = s.lower()
            for term, cat in self.red.withhold_terms:
                if term in low:
                    self.red.count(f"withheld: {cat}")
                    return self.withheld(cat)
            if ENCODED.search(s):
                self.note("D, encoded content")
                return self.withheld("D, encoded content")
            result = self.red.replace(s, self.marker)
        leftover = self.red.detect_all(result, self.emitted)
        if leftover:
            self.note("withheld: private data or deep nesting found in an alternative reading")
            return self.withheld("encoded or escaped content")
        if escape_readings(result)[1]:
            self.note("D, escapes layered past the limit")
            return self.withheld("D, escapes layered past the limit")
        protected = self.protected_reading(result)
        if protected:
            self.note(f"withheld: {protected} found in an alternative reading")
            return self.withheld(protected)
        if self.hidden_in_readings(result):
            self.note("withheld: Grok's text or an identifier found in an alternative reading")
            return self.withheld("rights check D1 or an identifier, in an alternative reading")
        return result

    def hidden_in_readings(self, text):
        """Grok's text or a listed identifier visible only in an alternative reading of text (an escape, an
        encoding, JSON inside the string), as the launch builder's scan reads it (GPT-6 LX1)."""
        if self.grok is None and self.id_re is None:
            return False
        for v in views(text)[0][1:]:
            if self.grok is not None and self.grok.spans(v, strict=True):  # runs and known quotations
                return True
            if self.id_re is not None and self.id_re.search(v):
                return True
        return False

    def protected_reading(self, text):
        """Class C or D content, or reasoning, visible in any alternative reading of text, with this export's own
        markers removed (GPT-6 EX2, rounds 3 and export-tool-2): an escaped reminder, an encoded component, or JSON
        holding a reasoning field or thought part, however wrapped, classified as walk() classifies it. JSON that
        repeats a key is withheld too, since a reader could miss a reasoning field under an earlier value (LX1,
        launch-export round 3)."""
        readings, _ = views(text)
        publish_reasoning = self.source.get("reasoning_class", "C") == "B" and self.source.get("provider") in self.cleared
        for r in readings:
            for m in sorted(self.emitted, key=len, reverse=True):
                r = r.replace(m, "")
            low = r.lower()
            if "<system-reminder" in low or "system-reminder>" in low:
                return "C, injected context"
            if ENCODED.search(r):
                return "D, encoded content"
            s = r.strip()
            if not publish_reasoning and s[:1] in ("{", "["):
                try:
                    v = load_all(s)
                except ValueError:
                    continue
                stack = [v]
                while stack:
                    x = stack.pop()
                    if isinstance(x, RepeatedKeys):
                        return "D, repeated JSON key"
                    if isinstance(x, dict):
                        if thought_part(x) or any(reasoning_field(k, val) for k, val in x.items()):
                            return f"{self.source.get('reasoning_class', 'C')}, nested reasoning"
                        stack += list(x.values())
                    elif isinstance(x, list):
                        stack += x
        return None

    def reasoning(self, what):
        """A reasoning part: None if it may be published (class B, provider cleared); otherwise its marker."""
        cls = self.source.get("reasoning_class", "C")
        if cls == "B" and self.source.get("provider") in self.cleared:
            return None
        label = safe_label(what)
        self.note(f"{cls}, {label}")
        return self.withheld(f"{cls}, {label}")

    def walk(self, v, depth=0):
        if isinstance(v, str):
            return self.clean(v, depth)
        if isinstance(v, bool) or v is None:
            return v
        if isinstance(v, (int, float)):
            if any(str(v) == lit for lit, _ in self.red.literals):
                self.note("structural: private number replaced by a marker")
                return self.clean(str(v), depth)
            return v
        if isinstance(v, list):
            return [self.walk(x, depth) for x in v]
        if isinstance(v, dict):
            if v.get("type") in IMAGE_TYPES or "media_type" in v or ("mime_type" in v and "data" in v):
                self.note("D, image, document or file object")
                return self.withheld("D, image, document or file object")
            out = {}
            for k, x in v.items():
                key = self.clean(str(k), depth)
                if key in out:
                    n = 2
                    while f"{key} #{n}" in out:
                        n += 1
                    key = f"{key} #{n}"
                    self.note("structural: colliding keys numbered")
                if k == "parts" and isinstance(x, list):
                    out[key] = [self.part(p, depth) for p in x]
                elif reasoning_field(k, x):
                    r = self.reasoning(k)
                    out[key] = r if r is not None else self.walk(x, depth)
                else:
                    out[key] = self.walk(x, depth)
            return out
        return self.clean(str(v), depth)

    def part(self, p, depth):
        """A Gemini content part: a thought part is reasoning."""
        if thought_part(p):
            r = self.reasoning("thought summary")
            return dict(self.walk({k: x for k, x in p.items() if k != "text"}, depth), text=r) if r is not None \
                else self.walk(p, depth)
        return self.walk(p, depth)

    # ---- streams: classify assembled text per channel and identity, before and after cleaning ----

    STREAM_PATHS = (
        (("choices", "*", "delta", "content"), "content"),
        (("choices", "*", "delta", "reasoning_content"), "reasoning"),
        (("candidates", "*", "content", "parts", "*", "text"), "text"),
        (("message", "content"), "content"),
        (("message", "thinking"), "reasoning"),
    )

    def _leaves(self, obj, pattern, path=()):
        if not pattern:
            if isinstance(obj, str):
                yield path
            return
        head, rest = pattern[0], pattern[1:]
        if head == "*" and isinstance(obj, list):
            for i, x in enumerate(obj):
                yield from self._leaves(x, rest, path + (i,))
        elif isinstance(obj, dict) and head in obj:
            yield from self._leaves(obj[head], rest, path + (head,))

    @staticmethod
    def _get(obj, path):
        for p in path:
            obj = obj[p]
        return obj

    @staticmethod
    def _set(obj, path, value):
        for p in path[:-1]:
            obj = obj[p]
        obj[path[-1]] = value

    @staticmethod
    def identity(ev, path):
        """Which stream a piece belongs to: the choice or candidate (by its index field), and thought or answer."""
        if path[0] in ("choices", "candidates"):
            item = ev[path[0]][path[1]]
            ident = item.get("index", path[1]) if isinstance(item, dict) else path[1]
            thought = False
            if path[0] == "candidates":
                part = ev["candidates"][path[1]]["content"]["parts"][path[4]]
                thought = isinstance(part, dict) and bool(part.get("thought"))
            return (path[0], json.dumps(ident), thought)
        return (path[0],)

    def classify(self, events, processed):
        """Pieces to withhold: those overlapping a detection, an injected-context block or encoded content in their
        group's assembled text; and every piece of a group whose other readings show a detection or a protected
        construct, or whose text holds a data URI."""
        groups = {}
        for ei, ev in enumerate(events):
            if not isinstance(ev, dict):
                continue
            for pattern, channel in self.STREAM_PATHS:
                for path in self._leaves(ev, pattern):
                    groups.setdefault((channel, self.identity(ev, path)), []).append((ei, path))
        marks = []
        for (channel, _), pieces in groups.items():
            texts = [self._get(events[ei], path) for ei, path in pieces]
            text = "".join(texts)
            if processed:  # our own markers are not detections; blank them out, keeping offsets
                for m in sorted(self.emitted, key=len, reverse=True):
                    text = text.replace(m, " " * len(m))
            hits = [(s, e) for s, e, _ in self.red.spans(text)]
            hits += [(m.start(), m.end()) for m in REMINDER.finditer(text)]
            hits += [(m.start(), m.end()) for m in ENCODED.finditer(text)]
            masked = list(text)
            for s, e in hits:
                masked[s:e] = " " * (e - s)
            rest = "".join(masked)
            # the whole group is withheld if another reading of it shows a detection or a protected construct split
            # across pieces (an escaped reminder or data URI, wrapped reasoning), or if it holds a data URI, whose
            # end can't be located across pieces
            whole = bool(self.red.detect_all(rest)) or bool(self.protected_reading(rest)) or bool(DATA_URI.search(text))
            pos = 0
            for (ei, path), t in zip(pieces, texts):
                start, end = pos, pos + len(t)
                pos = end
                if whole or any(s < end and start < e for s, e in hits):
                    marks.append((ei, path, channel))
        return marks

    def stream(self, events):
        """events: parsed stream events (dicts), or other values kept as they are. Returns processed events."""
        events = copy.deepcopy(events, {id(DONE): DONE})
        for ei, path, channel in self.classify(events, processed=False):
            self._set(events[ei], path, self.withheld(f"stream {channel} text"))
            self.note(f"withheld: {channel} piece in a stream detection or protected block")
        processed = [e if e is DONE else self.walk(e) for e in events]  # every event shape is processed
        for ei, path, channel in self.classify(processed, processed=True):
            if self._get(processed[ei], path) not in self.emitted:
                self._set(processed[ei], path, self.withheld(f"stream {channel} text"))
                self.note(f"withheld: {channel} piece joining a detection after cleaning")
        return processed

    # ---- format handlers ----

    def fetched(self, name, tool_input):
        """Whether a tool call's result is fetched third-party content (class D)."""
        desc = str((tool_input or {}).get("description", "")) if isinstance(tool_input, dict) else ""
        if any(fnmatch.fnmatchcase(str(name), pat) for pat in FETCH_TOOLS):
            return True
        for pat in self.config.get("withhold_tool_results", []):
            tool, _, want = pat.partition(":")
            if fnmatch.fnmatchcase(str(name), tool) and (not want or want in desc):
                return True
        return False

    def claude_transcript(self, raw):
        out, ids, calls = [], {}, {}

        def local_id(original):
            if original not in ids:
                ids[original] = f"call-{len(ids) + 1}"
            return ids[original]

        for i, line in enumerate(raw.decode("utf-8").splitlines()):
            try:
                e = json.loads(line)
            except ValueError:
                self.note("unparseable line")
                continue
            t = e.get("type")
            if t in ("user", "assistant"):
                if e.get("isCompactSummary") or e.get("isMeta"):
                    self.note("C, injected summary or meta message")
                    continue
                msg = e.get("message") or {}
                blocks = msg.get("content")
                if isinstance(blocks, str):
                    blocks = [{"type": "text", "text": blocks}]
                kept = []
                for b in blocks or []:
                    bt = b.get("type") if isinstance(b, dict) else None
                    if bt == "text":
                        kept.append({"type": "text", "text": self.clean(b.get("text", ""))})
                    elif bt == "thinking":
                        r = self.reasoning("thinking")
                        kept.append({"type": "text", "text": r} if r is not None
                                    else {"type": "thinking", "text": self.clean(b.get("thinking", ""))})
                    elif bt == "tool_use":
                        calls[b.get("id")] = (b.get("name"), b.get("input"))
                        kept.append({"type": "tool_use", "call": local_id(b.get("id")), "tool": safe_label(b.get("name")),
                                     "input": self.walk(b.get("input"))})
                    elif bt == "tool_result" and self.fetched(*calls.get(b.get("tool_use_id"), (None, None))):
                        self.note("D, fetched third-party content")
                        kept.append({"type": "tool_result", "call": local_id(b.get("tool_use_id")),
                                     "is_error": bool(b.get("is_error")),
                                     "text": self.withheld("D, fetched third-party content")})
                    elif bt == "tool_result":
                        content = b.get("content")
                        parts = content if isinstance(content, list) else [{"type": "text", "text": content or ""}]
                        res = []
                        for p in parts:
                            if isinstance(p, dict) and p.get("type") == "text":
                                res.append(self.clean(str(p.get("text", ""))))
                            else:
                                self.note("D, image or non-text tool output")
                                res.append(self.withheld("D, image or non-text tool output"))
                        kept.append({"type": "tool_result", "call": local_id(b.get("tool_use_id")),
                                     "is_error": bool(b.get("is_error")), "text": NL.join(res)})
                    else:
                        label = safe_label(bt)
                        self.note(f"D, {label} block")
                        kept.append({"type": "text", "text": self.withheld(f"D, {label} block")})
                item = {"i": i, "timestamp": self.clean(str(e.get("timestamp"))), "role": safe_label(msg.get("role") or t),
                        "content": kept}
                if t == "assistant" and msg.get("model"):
                    item["model"] = self.clean(str(msg["model"]))
                out.append(item)
            elif t == "attachment" and (e.get("attachment") or {}).get("type") == "queued_command":
                prompt = (e["attachment"] or {}).get("prompt")
                text = prompt if isinstance(prompt, str) else json.dumps(prompt, ensure_ascii=False)
                out.append({"i": i, "timestamp": self.clean(str(e.get("timestamp"))), "role": "user", "queued": True,
                            "content": [{"type": "text", "text": self.clean(text)}]})
            elif t == "attachment":
                kind = safe_label((e.get("attachment") or {}).get("type"))
                cls = "D" if kind in ("file", "edited_text_file", "compact_file_reference") else "C"
                self.note(f"{cls}, {kind} attachment")
            elif t == "system":
                self.note("C, system entry")
            else:
                self.note(f"metadata entry not exported: {safe_label(t)}")
        self.note("structural: normalized to the transcript allowlist")
        return (NL.join(json.dumps(x, ensure_ascii=False) for x in out) + NL).encode("utf-8")

    def codex_run(self, raw):
        out = []
        keep_fields = {"agent_message": ("text",), "command_execution": ("command", "aggregated_output", "exit_code", "status"),
                       "file_change": ("changes", "status"), "web_search": ("query", "action"), "error": ("message",)}
        for i, line in enumerate(raw.decode("utf-8", errors="replace").splitlines()):
            try:
                e = json.loads(line)
            except ValueError:
                self.note("unparseable line")
                continue
            item = e.get("item")
            event = safe_label(e.get("type"))
            if isinstance(item, dict):
                it = item.get("type")
                if it == "reasoning":
                    out.append({"i": i, "event": event, "item": {"type": "reasoning", "text": self.reasoning("reasoning") or ""}})
                    continue
                keep = keep_fields.get(it)
                if keep is None:
                    self.note(f"D, {safe_label(it)} item")
                    continue
                out.append({"i": i, "event": event, "item": {"type": it, **{k: self.walk(item.get(k)) for k in keep if k in item}}})
            elif e.get("type") in ("thread.started", "turn.started", "turn.completed"):
                out.append({"i": i, "event": event, "data": self.walk({k: v for k, v in e.items() if k != "type"})})
            else:
                self.note(f"metadata entry not exported: {event}")
        self.note("structural: normalized to the transcript allowlist")
        return (NL.join(json.dumps(x, ensure_ascii=False) for x in out) + NL).encode("utf-8")

    def json_file(self, raw):
        return (json.dumps(self.walk(json.loads(raw.decode("utf-8"))), ensure_ascii=False, indent=2) + NL).encode("utf-8")

    def ollama_jsonl(self, raw):
        events = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
        processed = self.stream(events)
        return (NL.join(json.dumps(e, ensure_ascii=False) for e in processed) + NL).encode("utf-8")

    def sse(self, raw):
        blocks, data = [], []
        for line in raw.decode("utf-8").split("\n"):
            line = line.rstrip("\r")
            if line.startswith("data:"):
                data.append(line[5:].lstrip(" "))
            elif line == "" and data:
                blocks.append(NL.join(data))
                data = []
            elif line and not line.startswith(":"):
                self.note("dropped non-data SSE line")
        if data:
            blocks.append(NL.join(data))
        events = []
        for b in blocks:
            if b.strip() == "[DONE]":
                events.append(DONE)
                continue
            try:
                events.append(json.loads(b))
            except ValueError:
                self.note("D, unparseable SSE event")
                events.append(self.withheld("D, unparseable SSE event"))
        processed = self.stream(events)
        self.note("structural: SSE re-serialized, one data line per event")
        lines = ["data: [DONE]" if p is DONE else "data: " + json.dumps(p, ensure_ascii=False) for p in processed]
        return ((NL + NL).join(lines) + NL + NL).encode("utf-8")

    def text_file(self, raw):
        text = raw.decode("utf-8")
        if REMINDER_OPEN in text:  # multi-line blocks first, so no body line survives on its own
            self.note("C, injected context", len(REMINDER.findall(text)))
            text = REMINDER.sub(lambda _: self.withheld("C, injected context"), text)
        stripped = text.strip()
        if stripped[:1] in ("{", "["):
            try:
                decoded = json.loads(stripped)
            except ValueError:
                decoded = None
            if isinstance(decoded, (dict, list)):
                self.note("structural: JSON text decoded and re-encoded")
                return (json.dumps(self.walk(decoded), ensure_ascii=False, indent=2) + NL).encode("utf-8")
        if self.grok is not None:  # Grok's text may be wrapped across lines: find it in the whole text first
            spans = self.grok.spans(text, strict=True)
            if spans:
                self.note("withheld: Grok quotation (rights check, D1)", len(spans))
                mark = self.withheld("rights check D1, Grok output")
                text = "".join(part for i, (a, b) in enumerate(spans) for part in
                               (text[spans[i - 1][1] if i else 0:a], mark)) + text[spans[-1][1]:]
        return NL.join(self.clean(line) for line in text.split(NL)).encode("utf-8")

    # ---- paths ----

    def check_dest(self, dest):
        if not isinstance(dest, str) or "\\" in dest or ".." in dest.split("/") \
                or not re.fullmatch(r"(sessions|rounds/[^/]+/evidence)/[^/]+/.+", dest):
            raise ValueError(f"an export destination must be in a subfolder of sessions/ or rounds/*/evidence/: {dest!r}")
        for part in dest.split("/"):
            if not part or RESERVED.match(part) or part != part.rstrip(". ") or re.search(r'[<>:"|?*\x00-\x1f]', part):
                raise ValueError(f"an export destination has an unsafe path component: {dest!r}")
        if dest.endswith(".meta.md"):
            raise ValueError(f"an export destination may not be a sidecar name: {dest!r}")
        if self.red.detect_all(dest):
            raise ValueError("an export destination contains private data; rename it in the configuration")

    def preflight(self):
        if self.out.exists():
            raise FileExistsError(f"output folder exists: {self.out}")
        taken = {"sessions/manifest.md"}
        for source in self.config["sources"]:
            dest = source["dest"]
            self.check_dest(dest)
            for p in (dest, dest + ".meta.md"):
                if p.lower() in taken:
                    raise ValueError(f"two outputs would share the path {p!r} (case-insensitive)")
                taken.add(p.lower())
            for field in ("reason", "missing_reason"):
                if source.get(field) is not None and self.red.detect_all(str(source[field])):
                    raise ValueError(f"a configured {field} for {dest!r} contains private data")
            for s in strings_in(source.get("sidecar", {})):
                if self.red.detect_all(s):
                    raise ValueError(f"the sidecar metadata for {dest!r} contains private data or deep nesting")
        for p in taken:  # a file may not sit where another output needs a folder
            parts = p.split("/")
            for i in range(1, len(parts)):
                if "/".join(parts[:i]) in taken:
                    raise ValueError(f"an output path would need the file {'/'.join(parts[:i])!r} as a folder")
        return taken

    def write(self, rel, data):
        path = self.out / rel
        root = self.out.resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        if root not in path.resolve().parents:
            raise ValueError(f"an output path resolves outside the export folder: {rel!r}")
        with open(path, "xb") as f:
            f.write(data)

    def standalone_result(self, source):
        """For a tool result saved as its own file: a reason to withhold it, or None to export it (GPT-6 RC4)."""
        spec = source.get("tool_result_of")
        if not spec:
            return None
        for path in spec.get("transcripts", []):
            for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
                if spec["id"] not in line:
                    continue
                try:
                    e = json.loads(line)
                except ValueError:
                    continue
                blocks = (e.get("message") or {}).get("content")
                for b in blocks if isinstance(blocks, list) else []:
                    if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("id") == spec["id"]:
                        if self.fetched(b.get("name"), b.get("input")):
                            return "D, fetched third-party content saved as a standalone tool result"
                        return None
        return "unclassified standalone tool result: its call was not found"

    # ---- driver ----

    def run(self):
        taken = self.preflight()
        handlers = {"claude-transcript": self.claude_transcript, "codex-run": self.codex_run, "json": self.json_file,
                    "sse": self.sse, "ollama-jsonl": self.ollama_jsonl, "text": self.text_file}
        for source in self.config["sources"]:
            self.source, self.w = source, {}
            self.red.counts = {}
            src, dest = Path(source["path"]), source["dest"]
            row = {"dest": dest, "format": safe_label(source["format"])}
            if not src.exists():
                row.update(disposition="missing", reason=source.get("missing_reason", "source not found"))
                self.rows.append(row)
                continue
            raw = src.read_bytes()
            row["source_sha256"] = sha256(raw)
            if source["format"] not in handlers:
                row.update(disposition="withheld", reason=source.get("reason", f"format {row['format']} not exported"))
                self.rows.append(row)
                continue
            standalone = self.standalone_result(source)
            if standalone:
                row.update(disposition="withheld", reason=standalone)
                self.rows.append(row)
                continue
            data = handlers[source["format"]](raw)
            self.write(dest, data)
            row.update(disposition="published", output_sha256=sha256(data),
                       redactions=dict(sorted(self.red.counts.items())), withheld=dict(sorted(self.w.items())))
            self.write_sidecar(source, row)
            self.rows.append(row)
        self.write_manifest()
        self.verify()
        return self.rows

    def write_sidecar(self, source, row):
        fm = dict(source["sidecar"])
        fm["human_interventions"] = (str(fm.get("human_interventions", "none")).rstrip(".") + ". Exported and redacted "
                                     "by the exporter named here, under the publication policy; the redactions and "
                                     "withheld parts are counted below and in the manifest.")
        fm.update({
            "type": "transcript",
            "exporter": f"tools/export_archive.py @ {self.config['source_commit']} (rules version {RULES_VERSION})",
            "private_configuration": self.config["version"],
            "cutoff_utc": self.config["cutoff_utc"],
            "source_sha256": row["source_sha256"],
            "output_sha256": row["output_sha256"],
            "redactions": row["redactions"] or "none",
            "withheld": row["withheld"] or "none",
        })
        fm.setdefault("lifecycle", "active")
        text = "---" + NL + yaml.safe_dump(fm, sort_keys=False, allow_unicode=True, width=110) + "---" + NL + NL
        text += (f"Exported payload `{row['dest']}`. Redactions are marked `[REDACTED: <category>]` and withheld parts "
                 f"`[WITHHELD: <class or category>; see manifest]`. See `sessions/manifest.md`." + NL)
        errors, _ = check_headers.check_markdown(row["dest"] + ".meta.md", text)
        if errors:
            raise ValueError(f"the sidecar for {row['dest']} would fail the header check: {errors}")
        self.write(row["dest"] + ".meta.md", text.encode("utf-8"))

    def write_manifest(self):
        fmt = lambda d: "; ".join(f"{k}: {v}" for k, v in d.items()) if d else "none"
        lines = [f"Generated by tools/export_archive.py from commit {self.config['source_commit']}. Do not edit this "
                 "file; rerun the exporter.", "", "# Export Manifest", "",
                 f"- **Exporter rules version:** {RULES_VERSION}",
                 f"- **Private configuration version:** {self.config['version']} (the configuration itself is private)",
                 f"- **Cutoff:** {self.config['cutoff_utc']}", "",
                 "Every in-scope artifact is listed with its disposition. `source_sha256` identifies the private source "
                 "(the hash its record cites); `output_sha256` identifies the published bytes. The two hashes identify "
                 "a claimed transformation; checking it against the source requires the private archive. Every dotted "
                 "quad is redacted as a possible network identifier, including version numbers that look like one.", "",
                 "| Export path | Format | Disposition | Source SHA-256 | Output SHA-256 | Redactions | Withheld |",
                 "|---|---|---|---|---|---|---|"]
        for r in self.rows:
            lines.append(f"| `{r['dest']}` | {r['format']} | {r['disposition']}"
                         + (f" ({r['reason']})" if r.get("reason") else "")
                         + f" | `{r.get('source_sha256', '-')}` | `{r.get('output_sha256', '-')}` | "
                         + f"{fmt(r.get('redactions'))} | {fmt(r.get('withheld'))} |")
        self.write("sessions/manifest.md", (NL.join(lines) + NL).encode("utf-8"))

    def verify(self):
        """Rescan every written file and path in all readings; compare the file set and hashes with the manifest."""
        written = {p.relative_to(self.out).as_posix() for p in self.out.rglob("*") if p.is_file()}
        expected = {"sessions/manifest.md"}
        for r in self.rows:
            if r["disposition"] == "published":
                expected |= {r["dest"], r["dest"] + ".meta.md"}
        if written != expected:
            raise RuntimeError(f"fail closed: the written files differ from the manifest: {sorted(written ^ expected)}")
        for r in self.rows:
            if r["disposition"] == "published" and sha256((self.out / r["dest"]).read_bytes()) != r["output_sha256"]:
                raise RuntimeError(f"fail closed: {r['dest']} no longer matches its recorded hash")
        for rel in sorted(written):
            text = (self.out / rel).read_text(encoding="utf-8")
            found = set(self.red.detect_all(rel, self.emitted)) | set(self.red.detect_all(text, self.emitted))
            if rel.endswith(".md") and text.startswith("---" + NL):
                try:
                    front = yaml.safe_load(text.split("---" + NL, 2)[1])
                except yaml.YAMLError:
                    # A payload's own header need not be valid YAML (mailbox messages are transport); its raw text
                    # was scanned above. Sidecars and the manifest are written here and must parse.
                    if rel.endswith(".meta.md") or rel == "sessions/manifest.md":
                        raise
                    front = None
                for s in strings_in(front):
                    found |= set(self.red.detect_all(s, self.emitted))
            if found:
                raise RuntimeError(f"fail closed: {rel} still contains detected categories {sorted(found)}")


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 2:
        raise SystemExit(__doc__)
    config = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    for r in Export(config, argv[1]).run():
        print(f"{r['disposition']:9s} {r['dest']}")


if __name__ == "__main__":
    main()
