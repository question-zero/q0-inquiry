# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Founder, verbatim: "go ahead with the header checker". Revision 2 applies GPT-6 findings HC1-HC5; revision 3 applies its round 2 findings on HC2 and HC4; revision 4 adds the round-prompt type (GPT-6 finding RP3); revision 5 counts only standalone body markers (RP3, round 2); revision 6 reads comment headers in SVG and XML files; revision 7 skips complete XML doctypes, including internal subsets (GPT-6 finding AA1); revision 8 skips processing instructions inside them (AA1, round 2); revision 9 treats round packets as generated files (GPT-6 RPK1); revision 10 adds CONTRIBUTING.md as a shared document (GPT-6 C4) and archived payloads under sessions/ and rounds/*/evidence/ as sidecar files, excluding their sidecars, the manifest and README files (publication policy, GPT-6 PP4); revision 11 requires archive sidecars to be transcripts and treats Markdown placed directly in those folders as explanatory documents (GPT-6 LD2); revision 12 adds summary.md and THIRD-PARTY-NOTICES.md as shared documents (protocol revision 24); revision 13 adds launch-manifest.md as a generated file (the launch-export design).
# license: MIT (LICENSE-CODE)
"""Check that files carry the provenance required by protocol.md, section 6.

Usage:
    python tools/check_headers.py            # check every file tracked by git
    python tools/check_headers.py FILE ...   # check only the given files

Exit status is 1 if any error is found, and 0 otherwise. Warnings never fail
the check. Requires PyYAML.

This checks the presence and form of provenance, not its truth. A passing
file may still misstate its author, model, exposure, or independence
(protocol section 5). A passing run also doesn't replace review of changes to
this checker itself.
"""
import datetime as dt
import re
import subprocess
import sys
from pathlib import Path

import yaml

REQUIRED = [
    "type", "title", "author", "model", "developer", "participant_id", "run",
    "attribution", "date", "prompt", "exposure", "human_interventions",
    "samples", "lifecycle",
]
# Required fields that may say "unknown" (section 6: "When a field applies but
# its value isn't known, write unknown"). type, title, attribution, and lifecycle
# always have a knowable value.
UNKNOWN_OK = {
    "author", "model", "developer", "participant_id", "run", "date", "prompt",
    "exposure", "human_interventions", "samples",
}
TYPES = {
    "protocol", "statement", "readme", "proposal", "proposition", "case",
    "critique", "question", "simulation", "input", "round-prompt",
    "round-response", "transcript", "moderation",
}
BEGIN_MARK = "<!-- BEGIN PARTICIPANT TEXT -->"
END_MARK = "<!-- END PARTICIPANT TEXT -->"
SUBTYPES = {"critique", "review", "response", "conflict", "assessment"}
LIFECYCLES = {"draft", "active", "superseded", "withdrawn"}
ATTRIBUTIONS = ("verified", "reported", "self-declared")
POSITIONS = {"support", "reject", "conditional", "uncertain"}

# Shared documents (section 3): these paths, plus every record in moderation/.
SHARED = {"README.md", "summary.md", "CONTRIBUTING.md", "THIRD-PARTY-NOTICES.md", "protocol.md", "statement.md"}
# Generated files (section 2), by repository-relative path. "line": the first
# line names the generator and source commit. "sidecar": the generator writes
# <name>.meta.md.
GENERATED = {"index.md": "line", "sessions/manifest.md": "line", "launch-manifest.md": "line"}
# Round packets (section 9, packet mode) are generated files with a first line (GPT-6 RPK1).
GENERATED_PATTERNS = ((re.compile(r"rounds/[^/]+/packets/[^/]+\.md"), "line"),)


# Archived payloads (publication policy, protocol section 6): exported files of any format under these folders carry
# a sidecar of type transcript. Payloads go in subfolders. Markdown placed directly in sessions/ or a round's
# evidence/ is an authored explanatory document under the normal rules; the sidecars and the generated manifest
# also keep their own rules, so a sidecar never needs a sidecar of its own (GPT-6 PP4, LD2).
ARCHIVE = re.compile(r"(sessions|rounds/[^/]+/evidence)/.+")
ARCHIVE_TOP_LEVEL = re.compile(r"(sessions|rounds/[^/]+/evidence)/[^/]+")


def is_archive_sidecar(rel):
    return bool(ARCHIVE.fullmatch(rel)) and rel.endswith(".meta.md")


def generated_kind(rel):
    if rel in GENERATED:
        return GENERATED[rel]
    if ARCHIVE.fullmatch(rel) and not rel.endswith(".meta.md") \
            and not (ARCHIVE_TOP_LEVEL.fullmatch(rel) and rel.endswith(".md")):
        return "sidecar"
    return next((kind for pattern, kind in GENERATED_PATTERNS if pattern.fullmatch(rel)), None)
# Exemptions listed in protocol section 6. Keep the two lists identical.
EXEMPT = {"LICENSE", "LICENSE-CODE"}

HASH_COMMENT = ("#",)
COMMENT_BY_SUFFIX = {
    ".py": "#", ".sh": "#", ".yml": "#", ".yaml": "#", ".toml": "#",
    ".js": "//", ".ts": "//", ".mjs": "//", ".css": "/*", ".html": "<!--",
    ".svg": "<!--", ".xml": "<!--",
}
COMMENT_BY_NAME = {".gitignore": "#", ".gitattributes": "#"}
HEADER_KEYS = ("author", "model", "date", "attribution")
ISO_LIKE = re.compile(r"^\d{4}-\d{2}-\d{2}([T ][0-9:.]+(Z|[+-]\d{2}:?\d{2})?)?$")


class _Loader(yaml.SafeLoader):
    """SafeLoader that keeps dates and times as strings, so check_date() validates them.

    PyYAML's implicit timestamp constructor raises ValueError on values like
    2026-99-99, before any checking can happen (GPT-6 finding HC2, round 2).
    """


_Loader.yaml_implicit_resolvers = {
    key: [r for r in resolvers if r[0] != "tag:yaml.org,2002:timestamp"]
    for key, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}

GENERATED_LINE = re.compile(r"generated by\s+`?([\w./-]+)`?.*?\bcommit\s+`?([0-9a-f]{7,40})\b", re.I)


def split_z(raw):
    """Split `git ls-files -z` output into paths, keeping non-ASCII names intact."""
    return [p.decode("utf-8", errors="surrogateescape") for p in raw.split(b"\0") if p]


def tracked_files():
    out = subprocess.run(["git", "ls-files", "-z"], capture_output=True, check=True)
    return split_z(out.stdout)


def is_empty(value):
    return value is None or (isinstance(value, str) and not value.strip()) or (isinstance(value, (list, dict)) and not value)


def is_unknown(value):
    return isinstance(value, str) and value.strip().lower() == "unknown"


def front_matter(text):
    """Return (dict, error). dict is None when front matter is missing or invalid."""
    if not text.startswith(("---\n", "---\r\n")):
        return None, "no YAML front matter (the file must start with '---')"
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", text, re.S)
    if not m:
        return None, "front matter is not closed with '---'"
    try:
        data = yaml.load(m.group(1), Loader=_Loader)
    except yaml.YAMLError as e:
        return None, f"front matter is not valid YAML: {e}"
    except (ValueError, TypeError) as e:
        return None, f"front matter could not be read: {e}"
    if not isinstance(data, dict):
        return None, "front matter is not a mapping of fields"
    return data, None


def check_date(value, errors, warnings):
    if is_unknown(value):
        return
    if isinstance(value, (dt.date, dt.datetime)):
        return
    s = str(value).strip()
    if not ISO_LIKE.match(s):
        warnings.append(f"date '{s}' is not an ISO 8601 date; the protocol doesn't fix a format, but ISO is expected")
        return
    try:
        if len(s) == 10:
            dt.date.fromisoformat(s)
        else:
            dt.datetime.fromisoformat(s.replace("Z", "+00:00").replace(" ", "T"))
    except ValueError:
        errors.append(f"date '{s}' looks like ISO 8601 but is not a real date or time")


def check_samples(value, errors):
    if is_unknown(value):
        return
    ok_count = lambda v: (isinstance(v, int) and not isinstance(v, bool) and v >= 0) or is_unknown(v)
    if isinstance(value, dict) and "generated" in value and "submitted" in value \
            and ok_count(value["generated"]) and ok_count(value["submitted"]):
        return
    errors.append("samples must be 'unknown' or give 'generated' and 'submitted' as counts or 'unknown'")


def check_markdown(rel, text):
    errors, warnings = [], []
    data, err = front_matter(text)
    if err:
        return [err], warnings

    for f in REQUIRED:
        v = data.get(f)
        if f not in data or (is_empty(v) and not (f == "exposure" and v == [])):
            errors.append(f"required field '{f}' is missing or empty")
        elif is_unknown(v) and f not in UNKNOWN_OK:
            errors.append(f"'{f}' can't be 'unknown'")

    ftype = str(data.get("type", ""))
    if ftype and ftype not in TYPES:
        errors.append(f"type '{ftype}' is not one of: {', '.join(sorted(TYPES))}")
    if is_archive_sidecar(rel) and ftype != "transcript":
        errors.append("an archived payload's sidecar has type 'transcript' (section 6)")

    lifecycle = str(data.get("lifecycle", ""))
    if lifecycle and lifecycle not in LIFECYCLES:
        errors.append(f"lifecycle '{lifecycle}' is not one of: {', '.join(sorted(LIFECYCLES))}")
    if lifecycle == "superseded" and is_empty(data.get("superseded_by")):
        errors.append("lifecycle is 'superseded' but superseded_by is missing or empty")

    attribution = str(data.get("attribution") or "").strip().lower()
    if attribution and not attribution.startswith(ATTRIBUTIONS):
        errors.append("attribution must start with 'verified', 'reported', or 'self-declared'")

    if not is_empty(data.get("date")):
        check_date(data["date"], errors, warnings)
    if not is_empty(data.get("samples")):
        check_samples(data["samples"], errors)

    pid = data.get("participant_id")
    if isinstance(pid, str) and not is_unknown(pid) and not re.match(r"^[a-z0-9][a-z0-9.\-]*/[A-Za-z0-9\-]+$", pid):
        warnings.append(f"participant_id '{pid}' does not have the form <model-or-human>/<run> (section 5)")

    def need(fields, why):
        for f in fields:
            if is_empty(data.get(f)):
                errors.append(f"'{f}' is missing or empty ({why})")

    if ftype == "critique":
        subtype = str(data.get("subtype") or "")
        if not subtype:
            errors.append("critiques need a subtype")
        elif subtype not in SUBTYPES:
            errors.append(f"subtype '{subtype}' is not one of: {', '.join(sorted(SUBTYPES))}")
        if subtype == "assessment":
            need(("target", "position", "basis"), "assessments, section 7")
            position = str(data.get("position") or "")
            if position and position not in POSITIONS:
                errors.append(f"position '{position}' is not one of: {', '.join(sorted(POSITIONS))}")
            if position == "conditional":
                need(("conditions",), "conditional assessments, section 7")
        if not rel.startswith("critiques/"):
            warnings.append("critiques belong in critiques/ (section 2)")

    if ftype == "round-response":
        need(("round", "input_set"), "round responses, section 9")

    if ftype == "round-prompt":
        need(("round", "input_set"), "round prompts, section 9")
        # Only standalone marker lines in the body count; markers quoted in the
        # front matter or inside other lines don't (GPT-6 finding RP3, round 2).
        body = re.match(r"^---\r?\n.*?\r?\n---\r?\n(.*)$", text, re.S).group(1)
        lines = [line.strip() for line in body.splitlines()]
        begins = [i for i, line in enumerate(lines) if line == BEGIN_MARK]
        ends = [i for i, line in enumerate(lines) if line == END_MARK]
        if len(begins) != 1 or len(ends) != 1 or begins[0] > ends[0]:
            errors.append("round prompts need exactly one participant-text block in the body, "
                          f"'{BEGIN_MARK}' before '{END_MARK}', each on its own line (section 9)")

    if rel in SHARED or rel.startswith("moderation/"):
        need(("contributors", "adoption"), "shared documents, sections 3 and 6")

    return errors, warnings


def comment_header(text, marker):
    """Return the text of the file's leading comment block, or None."""
    lines = text.splitlines()
    if lines and lines[0].startswith("#!"):
        lines = lines[1:]
    if marker in ("#", "//"):
        block = []
        for line in lines:
            s = line.strip()
            if s.startswith(marker):
                block.append(s[len(marker):])
            elif s == "" and not block:
                continue
            else:
                break
        return "\n".join(block) if block else None
    close = "*/" if marker == "/*" else "-->"
    rest = "\n".join(lines).lstrip()
    # An XML declaration and/or a doctype may come before the header comment.
    if marker == "<!--" and rest.startswith("<?xml"):
        rest = rest.split("?>", 1)[1].lstrip() if "?>" in rest else ""
    if marker == "<!--" and rest.lower().startswith("<!doctype"):
        rest = skip_doctype(rest)
    if not rest.startswith(marker) or close not in rest:
        return None
    body = rest[len(marker):rest.index(close)]
    return "\n".join(l.strip().lstrip("*").strip() for l in body.splitlines())


def skip_doctype(rest):
    """Return the text after a complete doctype declaration, or "" if it never closes.

    The doctype may carry an internal subset in brackets, with its own
    declarations, comments, and quoted strings that contain ">" (GPT-6 finding
    AA1). Nothing external is resolved.
    """
    i, depth, quote = len("<!doctype"), 0, None
    while i < len(rest):
        c = rest[i]
        if quote:
            if c == quote:
                quote = None
        elif rest.startswith("<!--", i):
            end = rest.find("-->", i + 4)
            if end < 0:
                return ""
            i = end + 3
            continue
        elif rest.startswith("<?", i):  # processing instruction, skipped opaquely (AA1, round 2)
            end = rest.find("?>", i + 2)
            if end < 0:
                return ""
            i = end + 2
            continue
        elif c in "\"'":
            quote = c
        elif c == "[":
            depth += 1
        elif c == "]":
            depth -= 1
        elif c == ">" and depth <= 0:
            return rest[i + 1:].lstrip()
        i += 1
    return ""


def check_comment_header(text, marker):
    head = comment_header(text, marker)
    if head is None:
        return [f"no leading comment header (section 6 requires {', '.join(HEADER_KEYS)})"], []
    missing = []
    for k in HEADER_KEYS:
        m = re.search(rf"^[ \t]*{k}[ \t]*:[ \t]*(\S.*)$", head, re.M | re.I)
        if not m:
            missing.append(k)
    if missing:
        return [f"comment header is missing or empty: {', '.join(missing)} (section 6)"], []
    return [], []


def read_text(path):
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, "file not found"
    except UnicodeDecodeError:
        return None, "not valid UTF-8 text"
    except OSError as e:
        return None, f"cannot read file: {e.strerror or e}"


def check(rel, root=Path("."), checked=frozenset()):
    """Check one file, given its repository-relative path. Returns (errors, warnings)."""
    rel = rel.replace("\\", "/")
    path = root / rel
    if rel in EXEMPT:
        return [], []

    kind = generated_kind(rel)
    if kind:
        if kind == "sidecar":
            return check_sidecar(rel, root, checked)
        text, err = read_text(path)
        if err:
            return [err], []
        first = text.splitlines()[0] if text else ""
        if not GENERATED_LINE.search(first):
            return ["generated file: line 1 must name the generator and the source commit, e.g. "
                    "'Generated by tools/build_index.py from commit abc1234'"], []
        return [], []

    suffix = Path(rel).suffix
    name = Path(rel).name
    if suffix == ".md":
        text, err = read_text(path)
        return ([err], []) if err else check_markdown(rel, text)
    marker = COMMENT_BY_NAME.get(name) or COMMENT_BY_SUFFIX.get(suffix)
    if marker:
        text, err = read_text(path)
        return ([err], []) if err else check_comment_header(text, marker)
    return check_sidecar(rel, root, checked)


def check_sidecar(rel, root, checked):
    side_rel = rel + ".meta.md"
    side = root / side_rel
    if not side.exists():
        return [f"no provenance: add a sidecar {side_rel} (section 6)"], []
    if side_rel in checked:
        return [], []  # checked on its own in this run
    text, err = read_text(side)
    if err:
        return [f"sidecar {side_rel}: {err}"], []
    errors, warnings = check_markdown(side_rel, text)
    return [f"sidecar {side_rel}: {e}" for e in errors], [f"sidecar {side_rel}: {w}" for w in warnings]


def main(argv):
    files = [f.replace("\\", "/") for f in argv[1:]] or tracked_files()
    checked = frozenset(files)
    n_err = n_warn = 0
    for f in files:
        errors, warnings = check(f, checked=checked)
        for e in errors:
            print(f"ERROR   {f}: {e}")
        for w in warnings:
            print(f"warning {f}: {w}")
        n_err += len(errors)
        n_warn += len(warnings)
    print(f"\nChecked {len(files)} files: {n_err} errors, {n_warn} warnings.")
    return 1 if n_err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
