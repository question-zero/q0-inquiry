# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: GPT-6 RPK2, verbatim: "The Fable wrapper needs the same validation, ideally through the shared loader." Replaces the editor's uncommitted Round 2 wrapper with a reviewed tool that uses the Rounds 0 and 1 isolation flags. Revision 2 applies GPT-6 RPK3 (evidence kept on failure; an explicit outcome; the JSON result's shape checked).
# license: MIT (LICENSE-CODE)
"""Run one round participant in a fresh headless Claude Code CLI session and keep the evidence.

Usage:
    python tools/run_claude_cli_participant.py MODEL PREFIX --cli PATH_TO_CLAUDE_EXECUTABLE
        [--tag round/02-deliberation/v1] [--packet rounds/02-deliberation/packets/<participant>.md]
        [--timeout SECONDS]

The session is new (its own --session-id) and runs in a new, empty folder outside
the repository, with the isolation flags of Rounds 0 and 1: no tools, an empty
system prompt, strict MCP configuration, and no setting sources. The participant
text goes to stdin as exact UTF-8 bytes, with nothing added.

The text is read by the shared loader in run_local_participant.py. In packet mode
(GPT-6 RPK2), the manifest at the tag must assign the given packet to route
"claude-code-cli" and MODEL, and the packet's text must have the manifest's hash.
This is checked before any file is written or any process is started, and the
verified assignment goes into the preflight record.

Evidence files, each created exclusively, so nothing is ever overwritten:
    PREFIX.preflight.json    input set and assignment, CLI version and flags, session ID and folder,
                             written before the participant's session starts
    PREFIX.stdout.json       the CLI's stdout, raw bytes, also from a run that timed out or failed
    PREFIX.stderr.txt        the CLI's stderr, raw bytes, likewise
    PREFIX.transcript.jsonl  the session transcript the CLI saved, when it is found, likewise
    PREFIX.result.json       the process returned: exit code, outcome ("completed", or "incomplete" with
                             reasons), returned session ID, answer, usage, and what evidence was kept
    PREFIX.failure.json      the launch raised (for example a timeout): outcome "failed", the error, and
                             what evidence was kept
A run is "completed" only if the CLI exits 0 and prints one JSON object with is_error false, subtype
"success" and a text result; anything else is recorded as it is (GPT-6 RPK3). An evidence file that
can't be written is reported in the record rather than hiding the run's own outcome.
One run is one attempt. The script never retries.
"""
import argparse
import json
import secrets
import subprocess
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_local_participant import participant_input, sha256, write_exclusive  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
ROUTE = "claude-code-cli"  # this runner's route in a packet-mode manifest
EVIDENCE = ("preflight.json", "stdout.json", "stderr.txt", "transcript.jsonl", "result.json", "failure.json")


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=2)


def run(args, launch=subprocess.run, projects=None, empty_root=None):
    text, digest, commit, assignment = participant_input(args, ROUTE)  # before any file or process
    prefix = Path(args.prefix)
    paths = {k: Path(f"{prefix}.{k}") for k in EVIDENCE}
    existing = [str(p) for p in paths.values() if p.exists()]
    if existing:
        raise FileExistsError(f"evidence already exists, refusing to start: {existing}")
    cwd = Path(empty_root or tempfile.gettempdir()).resolve() / f"empty-{secrets.token_hex(3)}"
    if cwd == REPO or REPO in cwd.parents:
        raise ValueError(f"the session folder must be outside the repository: {cwd}")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    cwd.mkdir()
    session = str(uuid.uuid4())
    flags = ["-p", "--model", args.model, "--tools", "", "--system-prompt", "", "--strict-mcp-config",
             "--setting-sources", "", "--output-format", "json", "--session-id", session]
    version = launch([args.cli, "--version"], capture_output=True, text=True).stdout.strip()
    write_exclusive(paths["preflight.json"], dump({
        "checked_utc": now(), "route": ROUTE, "requested_model": args.model,
        "input_set": {"tag": args.tag, "commit": commit, "packet": getattr(args, "packet", None),
                      "assignment": assignment},
        "participant_text_sha256": digest, "participant_text_bytes": len(text.encode("utf-8")),
        "cli": str(args.cli), "cli_version": version, "flags": flags, "session_id": session, "cwd": str(cwd),
        "cwd_contents_before": sorted(p.name for p in cwd.iterdir()),
        "stdin": "the participant text, exact UTF-8 bytes, nothing added",
        "runner": {"path": "tools/run_claude_cli_participant.py", "sha256": sha256(Path(__file__).read_bytes())}}))
    projects = Path(projects or Path.home() / ".claude" / "projects")
    started = now()
    try:
        p = launch([args.cli, *flags], input=text.encode("utf-8"), capture_output=True, cwd=str(cwd),
                   timeout=args.timeout)
    except BaseException as e:  # RPK3: keep whatever the interrupted run produced, then re-raise; never retry
        failed = now()
        try:
            evidence = archive_session(paths, getattr(e, "stdout", None), getattr(e, "stderr", None),
                                       projects, cwd, session)
            write_exclusive(paths["failure.json"], dump({
                "started_utc": started, "failed_utc": failed, "outcome": "failed", "retried": False,
                "error_type": type(e).__name__, "error": repr(e), "evidence": evidence}))
        except Exception as note:
            e.add_note(f"recording the failure also failed: {note!r}")
        raise
    ended = now()
    evidence = archive_session(paths, p.stdout, p.stderr, projects, cwd, session)
    out, problem = parse_result(p.stdout)
    reasons = [r for r in (
        f"exit code {p.returncode}" if p.returncode != 0 else None,
        problem,
        None if problem or out.get("is_error") is False else f"is_error is {out.get('is_error')!r}",
        None if problem or out.get("subtype") == "success" else f"subtype is {out.get('subtype')!r}",
        None if problem or isinstance(out.get("result"), str) else "no answer text in the result",
    ) if r]
    result = {"started_utc": started, "ended_utc": ended, "exit_code": p.returncode,
              "outcome": "incomplete" if reasons else "completed", "outcome_reasons": reasons, "retried": False,
              "session_id_returned": out.get("session_id"), "is_error": out.get("is_error"),
              "subtype": out.get("subtype"), "answer": out.get("result") if isinstance(out.get("result"), str) else None,
              "result_uuid": out.get("uuid"), "model_usage": out.get("modelUsage"), "usage": out.get("usage"),
              "evidence": evidence}
    write_exclusive(paths["result.json"], dump(result))
    return result


def archive(path, data):
    """Write one evidence file exclusively. Reports the outcome instead of raising, so that one archival
    problem can't hide another or the run's own failure (RPK3)."""
    if data is None:
        return "unavailable"
    if not isinstance(data, bytes):
        data = str(data).encode("utf-8")
    try:
        write_exclusive(path, data, binary=True)
        return f"archived, {len(data)} bytes"
    except Exception as e:
        return f"not archived: {e!r}"


def archive_session(paths, stdout, stderr, projects, cwd, session):
    """Archive the raw streams and the session transcript, whatever the run's outcome, and say what was kept."""
    evidence = {"stdout": archive(paths["stdout.json"], stdout), "stderr": archive(paths["stderr.txt"], stderr),
                "transcript_file": None}
    try:
        transcript = next(projects.glob(f"*{cwd.name}/{session}.jsonl"), None)
        if transcript is None:
            evidence["transcript"] = "not found"
        else:
            evidence["transcript_file"] = str(transcript)
            evidence["transcript"] = archive(paths["transcript.jsonl"], transcript.read_bytes())
    except Exception as e:
        evidence["transcript"] = f"not read: {e!r}"
    try:
        evidence["cwd_contents_after"] = sorted(q.name for q in cwd.iterdir())
    except Exception as e:
        evidence["cwd_contents_after"] = f"unavailable: {e!r}"
    return evidence


def parse_result(stdout):
    """(fields, problem). The CLI's result must be one JSON object; anything else is recorded, never trusted."""
    if not stdout or not stdout.strip():
        return {}, "stdout is empty"
    try:
        out = json.loads(stdout.decode("utf-8"))
    except ValueError as e:  # includes UnicodeDecodeError
        return {}, f"stdout is not UTF-8 JSON: {e!r}"
    if not isinstance(out, dict):
        return {}, f"stdout JSON is a {type(out).__name__}, not an object"
    return out, None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("model", help="the exact --model value given to the CLI, such as the alias fable")
    ap.add_argument("prefix")
    ap.add_argument("--cli", required=True, help="path to the Claude Code executable")
    ap.add_argument("--tag", default="round/02-deliberation/v1")
    ap.add_argument("--packet", help="this model's packet in the round's packets/ folder, read at the tag and "
                                     "checked against the manifest's assignment for route 'claude-code-cli' and MODEL")
    ap.add_argument("--timeout", type=int, default=3600)
    args = ap.parse_args(argv)
    r = run(args)
    print(json.dumps({k: v for k, v in r.items() if k not in ("answer", "usage")}, indent=1))
    print("answer chars:", len(r["answer"] or ""))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
