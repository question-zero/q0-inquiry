# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Founder, verbatim: "Can u spin another session and decide on gpt6"; asked which model, the founder chose "Grok 4.7, Gemini as backup (Recommended)". The moderation alternate of moderation/rules.md, section 7. Revision 2 records the founder's change of alternate, verbatim: "Gemini becomes alternate (Recommended)" (critiques/2026-09-25-claude-opus-5-5--rights-check.md, D4).
# license: MIT (LICENSE-CODE)
"""Run the moderation alternate on one committed case file, and keep the evidence.

Usage:
    python tools/run_moderation_alternate.py PROVIDER MODEL CASE_PATH EVIDENCE_PREFIX
        [--commit REV] [--max-output-tokens N] [--max-input-tokens N] [--keys-file PATH]

The alternate (protocol section 1; moderation/rules.md, section 7) is Gemini 3.6 Flash through the Gemini API.
It replaced Grok 4.7 after the founder chose not to publish Grok's output (rights check, D1 and D4). There is no backup:
when the alternate can't decide, section 7's fallback applies. No other provider or model is accepted. Each case
is a fresh session with no history.

The case is a committed Markdown file in moderation/ with front matter and one marker pair. Only the text between
the markers is sent, and it must match the file's participant_text_sha256. The file is read with git at the
resolved commit (default HEAD), never from the working tree.

This script only supplies the input. Everything else is the reviewed machinery of tools/run_api_participant.py:
the evidence files, the key's redaction, the input count, one attempt and no retries. Before the run, it also
writes PREFIX.case.json, exclusively, naming the case path, the commit and the text's hash.
"""
import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import run_api_participant as ra  # noqa: E402
import run_local_participant as rl  # noqa: E402

ALTERNATES = {("gemini", "gemini-3.6-flash"): "the alternate"}
CASE_PATH = re.compile(r"moderation/[A-Za-z0-9][A-Za-z0-9._-]*\.md")


def load_case(path, rev):
    """(text, digest, commit) for a case file at a commit, or ValueError."""
    if not CASE_PATH.fullmatch(path or "") or ".." in path:
        raise ValueError(f"a case must be a Markdown file directly in moderation/: {path}")
    commit = rl.git_commit(rev)
    text, front = rl.extract_participant_text(rl.git_blob(commit, path))
    digest = rl.sha256(text)
    if digest != front.get("participant_text_sha256"):
        raise ValueError(f"case text hash {digest} differs from the file's participant_text_sha256")
    return text, digest, commit


def run(args, http=None, key=None):
    role = ALTERNATES.get((args.provider, args.model))
    if role is None:
        raise ValueError(f"{args.provider} {args.model} is not the recorded moderation alternate")
    text, digest, commit = load_case(args.case, args.commit)
    prefix = Path(args.prefix)
    case_file = Path(f"{prefix}.case.json")
    existing = [str(p) for p in [case_file] + [Path(f"{prefix}.{k}") for k in ra.EVIDENCE] if p.exists()]
    if existing:
        raise FileExistsError(f"evidence already exists, refusing to start: {existing}")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    rl.write_exclusive(case_file, json.dumps({
        "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "role": role, "provider": args.provider, "requested_model": args.model,
        "case": args.case, "commit": commit, "case_text_sha256": digest,
        "case_text_bytes": len(text.encode("utf-8")),
        "runner": {"path": "tools/run_moderation_alternate.py", "sha256": rl.sha256(Path(__file__).read_bytes())},
    }, indent=2))
    run_args = argparse.Namespace(
        provider=args.provider, model=args.model, prefix=args.prefix, tag=f"case {args.case}", packet=None,
        history_record=None, history_tag=None, max_output_tokens=args.max_output_tokens,
        max_input_tokens=args.max_input_tokens, keys_file=args.keys_file)
    return ra.run(run_args, http, (text, digest, commit), None, key=key)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("provider", choices=sorted({p for p, _ in ALTERNATES}))
    ap.add_argument("model")
    ap.add_argument("case", help="a committed Markdown file in moderation/ with one marker pair")
    ap.add_argument("prefix")
    ap.add_argument("--commit", default="HEAD")
    ap.add_argument("--max-output-tokens", type=int)
    ap.add_argument("--max-input-tokens", type=int)
    ap.add_argument("--keys-file", default=str(ra.DEFAULT_KEYS))
    args = ap.parse_args(argv)
    for name in ("max_input_tokens", "max_output_tokens"):
        try:
            ra.positive(name, getattr(args, name))
        except ValueError as e:
            ap.error(str(e))
    r = run(args)
    print(f"{args.provider} {args.model}: status={r['generation_status']} finish={r['finish_reason']} "
          f"complete={r['complete']} transport_complete={r['transport_complete']} answer={len(r['answer'])} chars "
          f"returned_model={r['returned_model']}")


if __name__ == "__main__":
    main()
