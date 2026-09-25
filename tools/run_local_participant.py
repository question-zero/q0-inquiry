# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Founder, verbatim: "download ollama and all three models". Revision 2 applies GPT-6 findings LR1-LR3 and its system-prompt and thinking recommendations; revision 3 applies its round 2 findings (complete failure capture; weight verification as a precondition); revision 4 adds Round 1 support: prompts for any round, Round 0 history, render-only prompt capture, and a context budget checked before inference (proposals/2026-09-24-claude-opus-5-5-round-1-design.md; GPT-6 findings R1D2 and R1D3); revision 5 applies GPT-6 findings RV1-RV3 (probe evidence, budget validation, exact history); revision 6 closes RV1 (probe requests saved before sending; bodies kept when a response isn't valid JSON); revision 7 adds --packet, for per-participant packets (proposals/2026-09-24-claude-opus-5-5-round-2-design.md); revision 8 applies GPT-6 RPK1 and RPK2 (generated packets; the manifest's assignment checked for the recipient).
# license: MIT (LICENSE-CODE)
"""Run one round participant on a local Ollama model and keep the evidence.

Usage:
    python tools/run_local_participant.py MODEL_TAG EVIDENCE_PREFIX
        [--system packaged|empty] [--think default|true|false] [--seed N]
        [--tag round/00-initial/v1] [--verify-weights]
        [--history EARLIER_RESULT_JSON --history-record RECORD_PATH [--history-tag round/00-initial/v1]]
        [--max-rendered-bytes N]
        [--num-ctx N] [--num-predict N] [--strict-context] [--max-input-tokens N]

The participant text comes from rounds/<name>/prompt.md at the commit that the
tag round/<name>/v1 points to. It lies between the markers and must match the
file's participant_text_sha256.

Packet mode (--packet PATH, GPT-6 RPK1 and RPK2). The round's prompt.md is then
the manifest, and a run without --packet is refused. At the same resolved
commit, the manifest must assign exactly this packet path to this route
("ollama" here) and this requested model, and the packet, a generated file with
no front matter, must hold one marker pair whose text has the manifest's hash.
Any mismatch stops the run before any request or evidence file. The verified
assignment goes into the preflight record.

With --history, the participant's earlier exchange is sent before the new text:
the earlier round's participant text (from --history-tag), then the earlier
answer. The answer is taken from the private result file and must equal the
committed record's body exactly. Thinking is never sent as history.

Before any inference, the request is rendered with Ollama's _debug_render_only
option, and the rendered prompt and its hash go into the preflight record. The
run stops before inference if rendering fails, if the render response shows any
sign of generation (content, thinking, tool calls, or count fields), or if the
rendered prompt exceeds --max-rendered-bytes. The render option is relied on only
for the Ollama versions in SUPPORTED_RENDER_VERSIONS. Probe output is never
discarded: if a probe generates anything, it is kept and the run stops.

Context budget (GPT-6 R1D3). --num-ctx and --num-predict go into the request
options. --strict-context sets truncate=false and shift=false, so Ollama may not
shorten the history or shift the context. With --max-input-tokens, the model is
loaded with a load-only request (no prompt), the loaded context length is
checked against --num-ctx, and the complete rendered prompt is counted by the
/tokenize endpoint of the llama-server process that Ollama started for this
weight file. /tokenize does not generate. The run stops before inference if
counting is unavailable, if the context differs, if the input exceeds the
limit, or if input plus --num-predict exceeds the context. Budget values must be
positive integers, and budget mode requires --num-ctx, --num-predict, and
--strict-context; invalid settings are rejected before any request (RV2).
Finding the llama-server process uses Windows process information.

Evidence files, each created exclusively, so nothing is ever overwritten:
    PREFIX.probes.jsonl    every preflight probe (render, load, context, tokenize): a start entry with the
                           request, written and flushed BEFORE the probe is sent, then its full response or
                           error (with HTTP status and body, also for bodies that aren't valid JSON) (RV1)
    PREFIX.preflight.json  model/runtime snapshot and artifact verification, written before anything is sent
    PREFIX.attempt.json    the attempt record, written BEFORE the chat request
    PREFIX.stream.jsonl    every streamed chunk, archived as raw bytes before decoding
    PREFIX.result.json     generation completed: answer, thinking, final chunk, post-run verification status
    PREFIX.failure.json    an error after the attempt started: error, HTTP status/body, partial output

With --verify-weights, inference runs only if the local manifest's SHA-256 equals
the server's digest AND the weight layer hashes to its declared digest. Otherwise
the run stops after preflight, and no chat request is sent (GPT-6 finding LR2, round 2).

One run is one attempt. The script never retries (protocol section 9, operator rule 3).
If any evidence file already exists, the script refuses to start.
"""
import argparse
import hashlib
import json
import platform
import re
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
import urllib.error
import urllib.request

import yaml

API = "http://127.0.0.1:11434"
BEGIN, END = "<!-- BEGIN PARTICIPANT TEXT -->", "<!-- END PARTICIPANT TEXT -->"
ROUTE = "ollama"  # this runner's route in a packet-mode manifest
DEFAULT_MAX_RENDERED_BYTES = 90_000  # about 20,000 tokens at the ~4.5 bytes per token measured in Round 0
EVIDENCE = ("probes.jsonl", "preflight.json", "attempt.json", "stream.jsonl", "result.json", "failure.json")
SUPPORTED_RENDER_VERSIONS = ("0.34.4",)  # _debug_render_only behavior checked for these versions only
# The sentence a response record carries in human_interventions when the editor added the file's final newline.
FINAL_NEWLINE_NOTE = "The answer did not end with a newline; one was added at the end of the file."


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def sha256(data):
    return hashlib.sha256(data if isinstance(data, bytes) else data.encode("utf-8")).hexdigest()


class HttpFailure(Exception):
    """An HTTP error from Ollama, with its status and body kept for the record."""

    def __init__(self, status, body):
        super().__init__(f"HTTP {status}")
        self.status, self.body = status, body


class BadResponse(Exception):
    """A response whose body could not be parsed. The status and the received body are kept (RV1)."""

    def __init__(self, status, body, error):
        super().__init__(f"unparseable response (HTTP {status}): {error}")
        self.status, self.body = status, body


class PreflightError(Exception):
    """Artifact verification failed. No chat request was sent."""


class Http:
    """Thin wrapper around the Ollama HTTP API and its llama-server processes, replaced in tests."""

    def json(self, path, payload=None, timeout=120):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(API + path, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status, raw = r.status, r.read()
        except urllib.error.HTTPError as e:
            raise HttpFailure(e.code, e.read().decode("utf-8", "replace")) from e
        return parse_body(status, raw)

    def stream(self, path, payload, timeout=7200):
        req = urllib.request.Request(API + path, data=json.dumps(payload).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            raise HttpFailure(e.code, e.read().decode("utf-8", "replace")) from e
        with r:
            for line in r:
                yield line

    def runner_port(self, weights_hex):
        """Port of the llama-server process that Ollama started for this weight blob, or None."""
        if not weights_hex:
            return None
        out = subprocess.run(["powershell", "-NoProfile", "-Command",
                              "Get-CimInstance Win32_Process -Filter \"Name='llama-server.exe'\" | "
                              "ForEach-Object { $_.CommandLine }"], capture_output=True, text=True).stdout
        for line in out.splitlines():
            model_arg = line.split("--model", 1)[1].split(" --", 1)[0] if "--model" in line else ""
            m = re.search(r"--port (\d+)", line)
            if weights_hex in model_arg and m:
                return int(m.group(1))
        return None

    def tokenize(self, port, text):
        """Token IDs from llama-server's /tokenize endpoint, which does not generate."""
        req = urllib.request.Request(f"http://127.0.0.1:{port}/tokenize",
                                     data=json.dumps({"content": text, "add_special": True,
                                                      "parse_special": True}).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            status, raw = r.status, r.read()
        body = parse_body(status, raw)
        if not isinstance(body, dict) or not isinstance(body.get("tokens"), list):
            raise BadResponse(status, raw.decode("utf-8", "replace"), "no token list")
        return body["tokens"]


def parse_body(status, raw):
    """Decode and parse a JSON body, keeping the received text if that fails (RV1)."""
    text = raw.decode("utf-8", "replace")
    try:
        return json.loads(text)
    except ValueError as e:
        raise BadResponse(status, text, repr(e)) from e


# ---- participant text from the pinned body, never from front matter (LR3) ----

def extract_participant_text(blob):
    """Return (text, front_matter) from a prompt.md blob, or raise ValueError."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n", blob, re.S)
    if not m:
        raise ValueError("prompt has no front matter")
    front = yaml.safe_load(m.group(1))
    body = blob[m.end():]
    begins, ends, offset = [], [], 0
    for line in body.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == BEGIN:
            begins.append((offset, offset + line.index(BEGIN) + len(BEGIN)))
        elif stripped == END:
            ends.append((offset + line.index(END), offset + len(line)))
        offset += len(line)
    if len(begins) != 1 or len(ends) != 1 or begins[0][0] > ends[0][0]:
        raise ValueError("prompt body must contain exactly one ordered pair of standalone markers")
    return body[begins[0][1]:ends[0][0]], front


def prompt_path(tag):
    """round/01-deliberation/v1 -> rounds/01-deliberation/prompt.md"""
    parts = tag.split("/")
    if len(parts) != 3 or parts[0] != "round":
        raise ValueError(f"not a round tag: {tag}")
    return f"rounds/{parts[1]}/prompt.md"


def git_commit(tag):
    return subprocess.run(["git", "rev-parse", f"{tag}^{{commit}}"], capture_output=True,
                          check=True, text=True).stdout.strip()


def git_blob(commit, path):
    """A committed blob, never the working tree."""
    return subprocess.run(["git", "show", f"{commit}:{path}"], capture_output=True,
                          check=True).stdout.decode("utf-8")


def pinned_prompt(tag):
    """The participant text at the tag, from the round's prompt.md. A packet-mode round is refused here."""
    commit = git_commit(tag)
    text, front = extract_participant_text(git_blob(commit, prompt_path(tag)))
    if "packets" in front:
        raise ValueError(f"{tag} is a packet-mode round: pass --packet, whose assignment is checked")
    digest = sha256(text)
    if digest != front.get("participant_text_sha256"):
        raise ValueError(f"participant text hash mismatch: {digest}")
    return text, digest, commit


# ---- packet mode (GPT-6 RPK1, RPK2) ----

GENERATED_LINE = re.compile(r"generated by\s+`?([\w./-]+)`?.*?\bcommit\s+`?([0-9a-f]{7,40})\b", re.I)
PACKET_PATH = re.compile(r"rounds/([0-9]{2}-[a-z0-9-]+)/packets/([a-z0-9][a-z0-9.-]*)\.md")
TOKEN = re.compile(r"[a-z0-9][a-z0-9.:-]*")
HEX64 = re.compile(r"[0-9a-f]{64}")


def check_packet_path(tag, packet):
    """Only the one canonical spelling of a packet path in the tag's round is accepted."""
    m = PACKET_PATH.fullmatch(packet or "")
    if not m or ".." in packet or m.group(1) != prompt_path(tag).split("/")[1]:
        raise ValueError(f"a packet must be rounds/<this round>/packets/<participant>.md, spelled exactly: {packet}")


def extract_generated_packet(blob):
    """Return (text, first line) from a generated packet: line 1 names the generator and source commit,
    there is no front matter, and the file holds each marker exactly once, each as a whole line, BEGIN first.
    The text is the exact characters strictly between the markers."""
    first = blob.split("\n", 1)[0]
    if blob.startswith("---") or not GENERATED_LINE.search(first):
        raise ValueError("a packet is a generated file: line 1 must name the generator and source commit, "
                         "with no front matter")
    if blob.count(BEGIN) != 1 or blob.count(END) != 1:
        raise ValueError("a packet must contain each marker exactly once")
    b, e = blob.index(BEGIN), blob.index(END)
    if not (0 < b < e and blob[b - 1] == "\n" and blob[b + len(BEGIN)] == "\n" and blob[e - 1] == "\n"
            and blob[e + len(END):] in ("", "\n")):
        raise ValueError("a packet's markers must be whole lines, BEGIN before END, with END on the last line")
    return blob[b + len(BEGIN):e], first


def read_assignments(front, round_name):
    """The manifest's packet assignments, validated as a whole: every field present and well formed,
    each path the canonical one for its participant, and no participant, path or recipient listed twice."""
    rows = front.get("packets")
    if not isinstance(rows, list) or not rows:
        raise ValueError("the manifest has no packet assignments")
    seen = {"participant": set(), "packet": set(), "recipient": set()}
    out = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"malformed assignment: {row!r}")
        a = {k: row.get(k) for k in ("participant", "route", "requested_model", "packet", "participant_text_sha256")}
        if not all(isinstance(v, str) for v in a.values()) or not TOKEN.fullmatch(a["participant"]) \
                or not TOKEN.fullmatch(a["route"]) or not TOKEN.fullmatch(a["requested_model"]) \
                or a["packet"] != f"rounds/{round_name}/packets/{a['participant']}.md" \
                or not HEX64.fullmatch(a["participant_text_sha256"]):
            raise ValueError(f"malformed assignment: {row!r}")
        for key, value in (("participant", a["participant"]), ("packet", a["packet"]),
                           ("recipient", (a["route"], a["requested_model"]))):
            if value in seen[key]:
                raise ValueError(f"the manifest lists a {key} twice: {value}")
            seen[key].add(value)
        out.append(a)
    return out


def pinned_packet(tag, packet, route, model):
    """(text, digest, commit, assignment) for one packet-mode run (RPK2). The manifest at the tag must assign
    exactly this packet path to this route and requested model, and the text between the packet's markers
    must have the manifest's hash. Everything is read at the same resolved commit, before any request."""
    check_packet_path(tag, packet)
    if not route or not model:
        raise ValueError("packet mode needs the route and the requested model")
    commit = git_commit(tag)
    manifest_path = prompt_path(tag)
    manifest_blob = git_blob(commit, manifest_path)
    shared, front = extract_participant_text(manifest_blob)
    if sha256(shared) != front.get("participant_text_sha256"):
        raise ValueError("the manifest's shared-text hash does not match its marker block")
    rows = [a for a in read_assignments(front, manifest_path.split("/")[1])
            if a["route"] == route and a["requested_model"] == model]
    if len(rows) != 1:
        raise ValueError(f"the manifest at {tag} assigns no packet to route {route}, model {model}")
    a = rows[0]
    if a["packet"] != packet:
        raise ValueError(f"the manifest assigns {a['packet']} to route {route}, model {model}, not {packet}")
    text, first = extract_generated_packet(git_blob(commit, packet))
    digest = sha256(text)
    if digest != a["participant_text_sha256"]:
        raise ValueError(f"packet text hash {digest} differs from the manifest's {a['participant_text_sha256']}")
    return text, digest, commit, dict(a, manifest=manifest_path, manifest_blob_sha256=sha256(manifest_blob),
                                      shared_text_sha256=front["participant_text_sha256"],
                                      packet_first_line=first)


def participant_input(args, route, prompt=None):
    """(text, digest, commit, assignment) for a run. In packet mode the packet and its assignment are always
    read and checked at the tag; a supplied prompt is refused rather than trusted."""
    packet = getattr(args, "packet", None)
    if packet:
        if prompt is not None:
            raise ValueError("packet mode reads the packet at the tag; a supplied prompt is not accepted")
        return pinned_packet(args.tag, packet, route, args.model)
    text, digest, commit = prompt or pinned_prompt(args.tag)
    return text, digest, commit, None


# ---- model artifact and runtime (LR2) ----

def manifest_info(model_tag):
    name, _, tag = model_tag.partition(":")
    path = Path.home() / ".ollama" / "models" / "manifests" / "registry.ollama.ai" / "library" / name / (tag or "latest")
    if not path.exists():
        return {"path": str(path), "present": False}
    raw = path.read_bytes()
    doc = json.loads(raw)
    return {"path": str(path), "present": True, "manifest_sha256": sha256(raw),
            "layers": [{"mediaType": l.get("mediaType"), "digest": l.get("digest"), "size": l.get("size")}
                       for l in doc.get("layers", [])]}


def verify_weight_layer(manifest):
    """Hash the model weight blob and compare it with its declared digest."""
    for layer in manifest.get("layers", []):
        if layer["mediaType"] and layer["mediaType"].endswith(".model"):
            blob = Path.home() / ".ollama" / "models" / "blobs" / layer["digest"].replace(":", "-")
            if not blob.exists():
                return {"layer_digest": layer["digest"], "computed": None, "matches": False, "error": "blob missing"}
            h = hashlib.sha256()
            with open(blob, "rb") as f:
                for chunk in iter(lambda: f.read(1 << 24), b""):
                    h.update(chunk)
            computed = "sha256:" + h.hexdigest()
            return {"layer_digest": layer["digest"], "computed": computed, "matches": computed == layer["digest"]}
    return {"layer_digest": None, "computed": None, "matches": False, "error": "no model layer in manifest"}


def runtime_info():
    info = {"os": platform.platform(), "python": platform.python_version()}
    try:
        info["gpu"] = subprocess.run(["nvidia-smi", "--query-gpu=name,driver_version,memory.total",
                                      "--format=csv,noheader"], capture_output=True, text=True).stdout.strip()
    except OSError:
        info["gpu"] = "unknown"
    return info


def runner_identity():
    here = Path(__file__).resolve()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(here)], capture_output=True, text=True).stdout.strip()
    return {"path": "tools/run_local_participant.py", "sha256": sha256(here.read_bytes()),
            "repo_head": head, "runner_uncommitted_changes": bool(dirty)}


def snapshot(http, model):
    tags = {m["name"]: m for m in http.json("/api/tags")["models"]}
    if model not in tags:
        raise ValueError(f"model {model} is not pulled")
    return {"tags_entry": tags[model], "show": http.json("/api/show", {"model": model})}


def write_exclusive(path, content, binary=False):
    with open(path, "xb" if binary else "x", **({} if binary else {"encoding": "utf-8", "newline": "\n"})) as f:
        f.write(content)


def best_effort_write(path, obj):
    try:
        write_exclusive(path, json.dumps(obj, ensure_ascii=False, indent=2))
        return True
    except Exception:
        return False


def record_raw_body(blob):
    """A response record's body after the blank line that follows the front matter, unchanged."""
    m = re.match(r"^---\n.*?\n---\n\n", blob, re.S)
    if not m:
        raise ValueError("unexpected record layout")
    return blob[m.end():]


def record_body(blob):
    """The record body without its final newline (the convention used to embed answers in prompts)."""
    raw = record_raw_body(blob)
    if not raw.endswith("\n"):
        raise ValueError("unexpected record layout: no final newline")
    return raw[:-1]


def committed_blob(record_path):
    return subprocess.run(["git", "show", f"HEAD:{record_path}"], capture_output=True,
                          check=True).stdout.decode("utf-8")


def committed_record_body(record_path):
    return record_body(committed_blob(record_path))


def load_history(result_path, record_path, history_tag, prompt=None, blob=None):
    """Return (messages, info) for the participant's earlier exchange, or raise ValueError.

    Exact equality (RV3). The bytes of a record can't show whether a final newline belongs to the
    answer or was added by the editor, so the record's own statement decides: if its human_interventions
    carries FINAL_NEWLINE_NOTE, the body must be the answer plus one newline and the answer must not end
    with a newline; otherwise the body must be the answer exactly."""
    raw = Path(result_path).read_bytes()
    result = json.loads(raw.decode("utf-8"))
    if result.get("generation_status") != "completed" or not result.get("complete"):
        raise ValueError("history result is not a completed answer")
    answer = result["answer"]
    blob = committed_blob(record_path) if blob is None else blob
    body = record_raw_body(blob)
    front = yaml.safe_load(re.match(r"^---\n(.*?)\n---\n", blob, re.S).group(1)) or {}
    newline_added = FINAL_NEWLINE_NOTE in str(front.get("human_interventions", ""))
    if newline_added and answer.endswith("\n"):
        raise ValueError("the record says a final newline was added, but the answer already ends with one")
    expected = answer + "\n" if newline_added else answer
    if body != expected:
        raise ValueError("history answer differs from the committed record body")
    text, digest, commit = prompt or pinned_prompt(history_tag)
    messages = [{"role": "user", "content": text}, {"role": "assistant", "content": answer}]
    info = {"result_file": Path(result_path).name, "result_sha256": sha256(raw),
            "attempt_id": result.get("attempt_id"), "record": record_path, "answer_sha256": sha256(answer),
            "earlier_input_set": {"tag": history_tag, "commit": commit},
            "earlier_participant_text_sha256": digest, "record_final_newline_added": newline_added,
            "note": "the earlier answer is sent as assistant content only; its thinking is not sent"}
    return messages, info


def build_request(text, show, system_mode, think_mode, seed, history=None, num_ctx=None, num_predict=None,
                  strict_context=False):
    if show.get("messages"):
        raise ValueError("model has stored conversation messages; refusing (record and decide explicitly)")
    messages = []
    if system_mode == "empty":
        messages.append({"role": "system", "content": ""})
    messages.extend(history or [])
    messages.append({"role": "user", "content": text})
    request = {"model": None, "messages": messages, "stream": True, "options": {"seed": seed}}
    if num_ctx is not None:
        request["options"]["num_ctx"] = num_ctx
    if num_predict is not None:
        request["options"]["num_predict"] = num_predict
    if think_mode != "default":
        request["think"] = think_mode == "true"
    if strict_context:
        request["truncate"] = False
        request["shift"] = False
    return request


def verify_artifact(before, manifest, verify_weights):
    """Return (ok, details). With verify_weights, every check must pass."""
    server_digest = (before["tags_entry"].get("digest") or "").removeprefix("sha256:")
    details = {"required": bool(verify_weights), "server_digest": server_digest,
               "manifest_present": manifest.get("present", False),
               "manifest_matches_server": manifest.get("manifest_sha256") == server_digest if manifest.get("present") else False}
    if not verify_weights:
        details["weights"] = "not required"
        return True, details
    details["weights"] = verify_weight_layer(manifest) if manifest.get("present") else {"matches": False, "error": "manifest missing"}
    ok = details["manifest_present"] and details["manifest_matches_server"] and details["weights"].get("matches") is True
    return ok, details


class ProbeLog:
    """Exclusive, append-only record of every preflight probe (RV1). For each probe, a start entry with
    the request is written and flushed before the probe is sent; then an end entry holds the full
    response, or the error with its HTTP status and received body. A start entry without an end entry
    marks a probe whose outcome is unknown. If the start entry can't be written, the probe isn't sent."""

    def __init__(self, path):
        self.path, self.f, self.n = Path(path), None, 0

    def _write(self, entry):
        if self.f is None:
            self.f = open(self.path, "x", encoding="utf-8", newline="\n")
        self.f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self.f.flush()

    def start(self, kind, request):
        self.n += 1
        self._write({"utc": now(), "event": "start", "probe": self.n, "kind": kind, "request": request})
        return self.n

    def end(self, n, kind, response=None, error=None):
        entry = {"utc": now(), "event": "end", "probe": n, "kind": kind}
        if error is not None:
            entry.update({"error": repr(error), "http_status": getattr(error, "status", None),
                          "http_body": getattr(error, "body", None)})
        else:
            entry["response"] = response
        self._write(entry)

    def close(self):
        if self.f is not None:
            self.f.close()


def probe(http, log, kind, path, payload, timeout=1800):
    """One logged preflight request: saved before sending, and its full response or error saved before
    anything is checked."""
    n = log.start(kind, {"path": path, "payload": payload})
    try:
        r = http.json(path, payload, timeout=timeout)
    except Exception as e:
        log.end(n, kind, error=e)
        raise
    log.end(n, kind, response=r)
    return r


def generation_signs(r, allowed_done_reason=None):
    """Names of every field that shows a probe produced output or ran inference."""
    if not isinstance(r, dict):
        return ["response is not an object"]
    msg = r.get("message")
    if msg is not None and not isinstance(msg, dict):
        return ["message is not an object"]
    msg = msg or {}
    signs = [k for k in ("eval_count", "prompt_eval_count", "eval_duration", "prompt_eval_duration") if k in r]
    if "done_reason" in r and r["done_reason"] != allowed_done_reason:
        signs.append(f"done_reason={r['done_reason']!r}")
    signs += [f"message.{k}" for k in ("content", "thinking", "tool_calls", "images") if msg.get(k)]
    signs += [k for k in ("response", "thinking", "tool_calls") if r.get(k)]
    return signs


def render(http, log, request, max_bytes, version):
    """Render the request without inference. Return (ok, details)."""
    details = {"max_rendered_bytes": max_bytes, "server_version": version,
               "supported_versions": list(SUPPORTED_RENDER_VERSIONS)}
    if version not in SUPPORTED_RENDER_VERSIONS:
        details["error"] = "the render-only option is not validated for this Ollama version; nothing was probed"
        return False, details
    try:
        r = probe(http, log, "render", "/api/chat", dict(request, stream=False, _debug_render_only=True))
    except Exception as e:
        details["error"] = repr(e)
        return False, details
    signs = generation_signs(r)
    info = r.get("_debug_info") if isinstance(r, dict) else None
    rendered = info.get("rendered_template") if isinstance(info, dict) else None
    details.update({"response_keys": sorted(r.keys()) if isinstance(r, dict) else None,
                    "rendered_template": rendered if isinstance(rendered, str) else None,
                    "rendered_sha256": sha256(rendered) if isinstance(rendered, str) else None,
                    "rendered_bytes": len(rendered.encode("utf-8")) if isinstance(rendered, str) else None,
                    "generation_signs": signs})
    if signs:
        details["error"] = "the render probe produced output or ran inference; it is kept in probes.jsonl"
    ok = isinstance(rendered, str) and not signs and details["rendered_bytes"] <= max_bytes
    return ok, details


def weights_hex(manifest):
    for layer in manifest.get("layers", []):
        if layer.get("mediaType") and layer["mediaType"].endswith(".model"):
            return (layer.get("digest") or "").removeprefix("sha256:") or None
    return None


def count_input(http, log, model, rendered, weights, num_ctx, num_predict, max_tokens):
    """Load the model without a prompt, check its context, and count the rendered input. Return (ok, details)."""
    details = {"max_input_tokens": max_tokens, "num_ctx": num_ctx, "num_predict": num_predict}
    try:
        load = {"model": model, "keep_alive": "30m", "options": {"num_ctx": num_ctx}}
        r = probe(http, log, "load", "/api/generate", load)
        details["load_response"] = {k: r.get(k) for k in ("done", "done_reason", "response")} if isinstance(r, dict) else r
        signs = generation_signs(r, allowed_done_reason="load")
        if signs or r.get("done_reason") != "load":
            details["error"] = f"the load-only request did not return a plain load: {signs}; kept in probes.jsonl"
            return False, details
        ps = probe(http, log, "context", "/api/ps", None)
        loaded = [m for m in ps.get("models", []) if m.get("name") == model]
        details["loaded_context_length"] = loaded[0].get("context_length") if loaded else None
        port = http.runner_port(weights)
        details["runner_port"] = port
        if port is None:
            details["error"] = "no llama-server process found for this weight file; cannot count without generating"
            return False, details
        tok_request = {"port": port, "endpoint": "/tokenize", "add_special": True, "parse_special": True,
                       "content_sha256": sha256(rendered)}
        k = log.start("tokenize", tok_request)
        try:
            tokens = http.tokenize(port, rendered)
        except Exception as e:
            log.end(k, "tokenize", error=e)
            raise
        log.end(k, "tokenize", response={"tokens": tokens})
        n = len(tokens)
    except Exception as e:
        details["error"] = repr(e)
        return False, details
    details["input_tokens"] = n
    ctx = details["loaded_context_length"]
    checks = {"within_input_limit": n <= max_tokens,
              "context_matches": num_ctx is None or ctx == num_ctx,
              "fits_with_output": ctx is not None and (num_predict is None or n + num_predict <= ctx)}
    details["checks"] = checks
    return all(checks.values()), details


def budget_settings(args):
    """Validate the budget options before any request (RV2). Absent means None; zero or negative is an error."""
    vals = {k: getattr(args, k, None) for k in ("num_ctx", "num_predict", "max_input_tokens", "max_rendered_bytes")}
    for k, v in vals.items():
        if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v <= 0):
            raise ValueError(f"{k} must be a positive integer, got {v!r}")
    if vals["max_rendered_bytes"] is None:
        vals["max_rendered_bytes"] = DEFAULT_MAX_RENDERED_BYTES
    strict = bool(getattr(args, "strict_context", False))
    if vals["max_input_tokens"] is not None and (vals["num_ctx"] is None or vals["num_predict"] is None or not strict):
        raise ValueError("budget mode (max_input_tokens) needs a positive num_ctx, a positive num_predict, "
                         "and strict_context")
    vals["strict_context"] = strict
    return vals


def run(args, http=None, prompt=None, history=None):
    budget = budget_settings(args)  # before any file or request
    http = http or Http()
    text, digest, commit, assignment = participant_input(args, ROUTE, prompt)
    if history is None and getattr(args, "history", None):
        history = load_history(args.history, args.history_record, args.history_tag)
    history_messages, history_info = history or (None, None)
    prefix = Path(args.prefix)
    paths = {k: Path(f"{prefix}.{k}") for k in EVIDENCE}
    existing = [str(p) for p in paths.values() if p.exists()]
    if existing:
        raise FileExistsError(f"evidence already exists, refusing to start: {existing}")
    prefix.parent.mkdir(parents=True, exist_ok=True)

    # Preflight: snapshot, request, and artifact verification. Nothing is sent to the model yet.
    before = snapshot(http, args.model)
    version = http.json("/api/version")["version"]
    request = build_request(text, before["show"], args.system, args.think, args.seed, history_messages,
                            budget["num_ctx"], budget["num_predict"], budget["strict_context"])
    request["model"] = args.model
    manifest = manifest_info(args.model)
    ok, verification = verify_artifact(before, manifest, args.verify_weights)
    max_tokens = budget["max_input_tokens"]
    log = ProbeLog(paths["probes.jsonl"])
    try:
        rendered_ok, rendering = (render(http, log, request, budget["max_rendered_bytes"], version) if ok
                                  else (False, {"skipped": "artifact verification failed"}))
        if max_tokens is None:
            counted_ok, counting = True, {"skipped": "no max_input_tokens"}
        elif ok and rendered_ok:
            counted_ok, counting = count_input(http, log, args.model, rendering["rendered_template"],
                                               weights_hex(manifest), budget["num_ctx"], budget["num_predict"],
                                               max_tokens)
        else:
            counted_ok, counting = False, {"skipped": "earlier preflight check failed"}
    finally:
        log.close()
    preflight = {
        "checked_utc": now(),
        "input_set": {"tag": args.tag, "commit": commit, "packet": getattr(args, "packet", None),
                      "assignment": assignment},
        "participant_text_sha256": digest,
        "operator_choices": {"system": args.system, "think": args.think, "seed": args.seed,
                             "verify_weights": bool(args.verify_weights),
                             "num_ctx": budget["num_ctx"], "num_predict": budget["num_predict"],
                             "strict_context": budget["strict_context"], "max_input_tokens": max_tokens,
                             "max_rendered_bytes": budget["max_rendered_bytes"]},
        "packaged_system_prompt": before["show"].get("system", ""),
        "packaged_thinking": before["show"].get("thinking"),
        "effective_settings_note": "Effective sampling combines Ollama runtime defaults, the model's packaged parameters, and request options. Values not listed here are unknown.",
        "request": request,
        "history": history_info,
        "model_before": before,
        "manifest": manifest,
        "artifact_verification": verification,
        "rendered_prompt": rendering,
        "input_budget": counting,
        "passed": ok and rendered_ok and counted_ok,
        "ollama_version": version,
        "probes": paths["probes.jsonl"].name if paths["probes.jsonl"].exists() else None,
        "runtime": runtime_info(),
        "runner": runner_identity(),
    }
    write_exclusive(paths["preflight.json"], json.dumps(preflight, ensure_ascii=False, indent=2))
    if not ok:
        raise PreflightError(f"artifact verification failed; no chat request sent: {verification}")
    if not rendered_ok:
        raise PreflightError("render-only check failed; no chat request sent: "
                             + json.dumps({k: v for k, v in rendering.items() if k != "rendered_template"}))
    if not counted_ok:
        raise PreflightError(f"input budget check failed; no chat request sent: {json.dumps(counting)}")

    attempt = {"attempt_id": str(uuid.uuid4()), "status": "started", "started_utc": now(),
               "preflight": str(paths["preflight.json"].name), "request": request}
    write_exclusive(paths["attempt.json"], json.dumps(attempt, ensure_ascii=False, indent=2))

    content, thinking, last, n = [], [], None, 0
    try:
        with open(paths["stream.jsonl"], "xb") as s:
            for raw in http.stream("/api/chat", request):
                raw = raw if isinstance(raw, bytes) else raw.encode("utf-8")
                if not raw.strip():
                    continue
                s.write(raw if raw.endswith(b"\n") else raw + b"\n")  # archive the bytes before decoding
                s.flush()
                n += 1
                chunk = json.loads(raw.decode("utf-8"))
                msg = chunk.get("message") or {}
                content.append(msg.get("content") or "")
                thinking.append(msg.get("thinking") or "")
                last = chunk
                if chunk.get("error"):
                    raise RuntimeError(f"server error: {chunk['error']}")
        if not last or not last.get("done"):
            raise RuntimeError("stream ended without a final done chunk")
    except Exception as e:  # keep everything; never retry
        best_effort_write(paths["failure.json"], {
            "attempt_id": attempt["attempt_id"], "generation_status": "failed", "failed_utc": now(),
            "error": repr(e), "http_status": getattr(e, "status", None), "http_body": getattr(e, "body", None),
            "chunks_archived": n, "partial_answer": "".join(content), "partial_thinking": "".join(thinking),
        })
        raise

    # Generation completed. Post-run verification is recorded separately and never discards the answer.
    result = {
        "attempt_id": attempt["attempt_id"],
        "generation_status": "completed",
        "ended_utc": now(),
        "done_reason": last.get("done_reason"),
        "complete": last.get("done_reason") == "stop",
        "answer": "".join(content),
        "thinking": "".join(thinking),
        "chunks": n,
        "final_chunk": last,
    }
    try:
        after = snapshot(http, args.model)
        unchanged = after["tags_entry"].get("digest") == before["tags_entry"].get("digest")
        result.update({"post_run_check": "completed", "digest_unchanged": unchanged,
                       "model_after_tags_entry": after["tags_entry"],
                       "artifact_attribution": "verified" if (unchanged and ok and args.verify_weights) else
                       ("unresolved: digest changed" if not unchanged else "not verified (verification not required)")})
    except Exception as e:
        result.update({"post_run_check": f"unavailable: {e!r}", "digest_unchanged": None,
                       "artifact_attribution": "unresolved: post-run check unavailable"})
    if not best_effort_write(paths["result.json"], result):
        raise RuntimeError("generation completed but result.json could not be written; the attempt and stream files remain")
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("model")
    ap.add_argument("prefix")
    ap.add_argument("--system", choices=["packaged", "empty"], default="packaged")
    ap.add_argument("--think", choices=["default", "true", "false"], default="default")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--tag", default="round/00-initial/v1")
    ap.add_argument("--packet", help="this model's packet in the round's packets/ folder, read at the tag and "
                                     "checked against the manifest's assignment for route 'ollama' and MODEL_TAG")
    ap.add_argument("--verify-weights", action="store_true")
    ap.add_argument("--history", help="private result JSON of the participant's earlier answer")
    ap.add_argument("--history-record", help="committed response record of that answer, checked exactly")
    ap.add_argument("--history-tag", default="round/00-initial/v1")
    ap.add_argument("--max-rendered-bytes", type=int)
    ap.add_argument("--num-ctx", type=int)
    ap.add_argument("--num-predict", type=int, help="maximum generated tokens, including thinking")
    ap.add_argument("--strict-context", action="store_true", help="send truncate=false and shift=false")
    ap.add_argument("--max-input-tokens", type=int)
    args = ap.parse_args(argv)
    if bool(args.history) != bool(args.history_record):
        ap.error("--history and --history-record go together")
    try:
        budget_settings(args)
    except ValueError as e:
        ap.error(str(e))
    r = run(args)
    print(f"{args.model}: done_reason={r['done_reason']} complete={r['complete']} answer={len(r['answer'])} chars "
          f"thinking={len(r['thinking'])} chars attribution={r['artifact_attribution']}")


if __name__ == "__main__":
    main()
