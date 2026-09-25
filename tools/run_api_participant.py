# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Founder, verbatim: "if more rounds require llms participation, we can just start by generating api keys for each one of the paid services (openai, xai, byteplus etc..)". Round 1 design decision 8 (proposals/2026-09-24-claude-opus-5-5-round-1-design.md), which GPT-6 supported with prerequisites. Revision 2 applies GPT-6 findings API1-API4 (topic api-runner); revision 3 closes API4 (keys split across reads; sanitized errors); revision 7 applies GPT-6 RPK1 and RPK2 (the manifest's assignment is checked for the provider and model); revision 6 adds --packet for per-participant packets; revision 5 requires ModelArk token IDs (GPT-6 R1API1); revision 4 adds BytePlus ModelArk, after the founder reported: "deepseek-v4-pro-ga-260813 is also active and api key in env file"; revision 8 adds OpenAI (Chat Completions, streamed) for GPT-5.6 Sol in the Round 3 panel, after the founder reported: "apikey added"; revision 9 applies GPT-6 R3P1 and R3P2 (topic round-3-panel): an evidence prefix inside the repository is refused, and streamed refusal text is kept, with refused and content-filtered outcomes recorded as such.
# license: MIT (LICENSE-CODE)
"""Run one round participant through a provider API and keep the evidence.

Usage:
    python tools/run_api_participant.py PROVIDER MODEL EVIDENCE_PREFIX
        [--tag round/01-deliberation/v1]
        [--history-record RECORD_PATH [--history-tag round/00-initial/v1]]
        [--max-output-tokens N] [--max-input-tokens N] [--keys-file PATH]

PROVIDER is gemini (Google Gemini API, streamGenerateContent), xai (xAI chat completions),
modelark (BytePlus ModelArk chat completions, OpenAI-compatible), or openai (OpenAI Chat Completions; the
input is counted by the Responses API's input-token endpoint, and a reasoning model's reasoning text is not
returned, only its token count in usage).

Keys come from a private file of KEY=value lines (default: .private/api-keys.env
next to the repository folder). A key is sent only in a request header and never
put in a URL. Everything saved from a response is checked for the active key
first, and any occurrence is replaced by a marker; a redacted file records that it
is no longer byte-exact (API4). The stream is checked across reads, so a key split
between two reads is caught. A failed run raises GenerationFailure, whose message
and fields are redacted and which carries no original exception chain.

Evidence files, each created exclusively, so nothing is ever overwritten:
    PREFIX.preflight.json  model metadata, the request body, history provenance, and
                           an input count from the provider's counting endpoint (no
                           generation), written before anything is generated
    PREFIX.attempt.json    the attempt record, written BEFORE the request
    PREFIX.stream.sse      the response bytes exactly as received (API2), apart from
                           any recorded redaction
    PREFIX.result.json     the outcome: completed, incomplete, or provider-blocked;
                           answer, thought summary or reasoning if returned, finish
                           reason, transport completion, usage, returned model and
                           response IDs, response headers
    PREFIX.failure.json    a transport or HTTP failure after the attempt started:
                           error, HTTP status, body and headers, partial output, and
                           any metadata already observed

Limits (API1). --max-input-tokens and --max-output-tokens must be positive
integers when given. The input count must be a valid, positive number, or the run
stops before generation. For xAI, the count covers the message texts only, not the
chat formatting; the record says so.

Streams are parsed as server-sent events (API2): data lines are joined within an
event, and an event is dispatched at a blank line. Answer completion (the finish
reason) and transport completion (for xAI and ModelArk, the [DONE] marker; for
Gemini, a clean end after a dispatched final event) are recorded separately.

With --history-record, the participant's earlier exchange is sent first: the
earlier round's participant text (from --history-tag), then the earlier answer,
taken from the committed record body. Each provider's own roles are used (Gemini:
user/model; xAI: user/assistant).

No sampling or thinking settings are overridden, so provider defaults apply, and
they are recorded as omitted, not as known values. No tools, search, or system
instruction are sent. That does not prove the provider adds nothing.

One run is one attempt. The script never retries. A provider block is an outcome,
not a reason for another attempt. If any evidence file already exists, it refuses
to start.
"""
import argparse
import json
import platform
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_local_participant import (committed_record_body, outside_repository, participant_input, pinned_prompt,  # noqa: E402
                                   sha256, write_exclusive)

EVIDENCE = ("preflight.json", "attempt.json", "stream.sse", "result.json", "failure.json")
DEFAULT_KEYS = Path(__file__).resolve().parents[2] / ".private" / "api-keys.env"
REDACTED = "[REDACTED: active API key]"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class HttpFailure(Exception):
    """An HTTP error or an unparseable body, with status, body, and headers kept for the record."""

    def __init__(self, status, body, headers=None, note=None):
        super().__init__(f"HTTP {status}" + (f": {note}" if note else ""))
        self.status, self.body, self.headers = status, body, headers or {}


class PreflightError(Exception):
    """A preflight check failed. No generation request was sent."""


class GenerationFailure(Exception):
    """The generation attempt failed. Every field is redacted, and it is raised without the original
    exception chain, so a traceback can't show an echoed key (API4)."""

    def __init__(self, message, status=None, body=None, headers=None, original_type=None):
        super().__init__(message)
        self.status, self.body, self.headers, self.original_type = status, body, headers, original_type


def clean_headers(h):
    return {k: v for k, v in (h.items() if h else []) if k.lower() != "set-cookie"}


class Http:
    """Thin HTTPS wrapper, replaced in tests. Request headers are never recorded."""

    def __init__(self):
        self.last_headers = {}

    def json(self, method, url, headers, body=None, timeout=120):
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                status, raw, rh = r.status, r.read(), clean_headers(r.headers)
        except urllib.error.HTTPError as e:
            raise HttpFailure(e.code, e.read().decode("utf-8", "replace"), clean_headers(e.headers)) from e
        text = raw.decode("utf-8", "replace")
        try:
            return json.loads(text)
        except ValueError as e:
            raise HttpFailure(status, text, rh, "body is not valid JSON") from e

    def stream(self, url, headers, body, timeout=3600):
        req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST", headers=headers)
        try:
            r = urllib.request.urlopen(req, timeout=timeout)
        except urllib.error.HTTPError as e:
            self.last_headers = clean_headers(e.headers)
            raise HttpFailure(e.code, e.read().decode("utf-8", "replace"), self.last_headers) from e
        self.last_headers = clean_headers(r.headers)
        with r:
            for line in r:
                yield line


def load_key(keys_file, name):
    for line in Path(keys_file).read_text(encoding="utf-8-sig").splitlines():
        k, sep, v = line.strip().partition("=")
        if sep and k.strip() == name and v.strip():
            return v.strip().strip('"').strip("'")
    raise ValueError(f"{name} is missing or empty in the keys file")


class Redactor:
    """Removes the active key from anything saved or printed, and counts what it removed (API4)."""

    def __init__(self, key):
        self.key, self.count = key, 0

    def text(self, s):
        if isinstance(s, str) and self.key and self.key in s:
            self.count += s.count(self.key)
            return s.replace(self.key, REDACTED)
        return s

    def obj(self, o):
        if isinstance(o, str):
            return self.text(o)
        if isinstance(o, list):
            return [self.obj(x) for x in o]
        if isinstance(o, dict):
            return {self.text(k): self.obj(v) for k, v in o.items()}
        return o

    def raw(self, b):
        kb = self.key.encode("utf-8")
        if kb and kb in b:
            self.count += b.count(kb)
            return b.replace(kb, REDACTED.encode("utf-8"))
        return b


class StreamRedactor:
    """Redacts the key across reads (API4). Bytes that could be the start of a key are held back until
    the next read shows whether they are; flush() releases the rest at the end or on failure."""

    def __init__(self, redactor):
        self.r, self.kb, self.buf = redactor, redactor.key.encode("utf-8"), b""

    def feed(self, raw):
        self.buf = self.r.raw(self.buf + raw)
        hold = 0
        for n in range(min(len(self.kb) - 1, len(self.buf)), 0, -1):
            if self.buf.endswith(self.kb[:n]):
                hold = n
                break
        out, self.buf = self.buf[:len(self.buf) - hold], self.buf[len(self.buf) - hold:]
        return out

    def flush(self):
        out, self.buf = self.r.raw(self.buf), b""
        return out


def error_record(e, redact):
    return redact.obj({"error": repr(e), "http_status": getattr(e, "status", None),
                       "http_body": getattr(e, "body", None), "http_headers": getattr(e, "headers", None)})


def positive(name, v):
    if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v <= 0):
        raise ValueError(f"{name} must be a positive integer, got {v!r}")
    return v


# ---- providers ----

class Gemini:
    name, key_name = "gemini", "GEMINI_API_KEY"
    base = "https://generativelanguage.googleapis.com/v1beta"
    count_scope = "the complete contents, by the provider's countTokens endpoint"

    def headers(self, key):
        return {"x-goog-api-key": key, "Content-Type": "application/json"}

    def model_info(self, http, model, key):
        return http.json("GET", f"{self.base}/models/{model}", self.headers(key))

    def build(self, model, history, text, max_output_tokens):
        turns = [("user" if m["role"] == "user" else "model", m["content"]) for m in history] + [("user", text)]
        body = {"contents": [{"role": r, "parts": [{"text": t}]} for r, t in turns],
                "generationConfig": {"thinkingConfig": {"includeThoughts": True}}}
        if max_output_tokens is not None:
            body["generationConfig"]["maxOutputTokens"] = max_output_tokens
        return body

    def count(self, http, model, key, body):
        r = http.json("POST", f"{self.base}/models/{model}:countTokens", self.headers(key),
                      {"contents": body["contents"]})
        n = r.get("totalTokens") if isinstance(r, dict) else None
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError(f"countTokens returned no valid positive totalTokens: {r!r}")
        return n, r

    def stream_url(self, model):
        return f"{self.base}/models/{model}:streamGenerateContent?alt=sse"

    def parse(self, event, state):
        for cand in event.get("candidates") or []:
            for part in (cand.get("content") or {}).get("parts") or []:
                if "text" in part:
                    (state["thinking"] if part.get("thought") else state["answer"]).append(part["text"])
            if cand.get("finishReason"):
                state["finish_reason"] = cand["finishReason"]
        feedback = event.get("promptFeedback") or {}
        if feedback.get("blockReason"):
            state["block"] = feedback
        for src, dst in (("usageMetadata", "usage"), ("modelVersion", "returned_model"), ("responseId", "response_id")):
            if event.get(src):
                state[dst] = event[src]

    def complete(self, state):
        return state.get("finish_reason") == "STOP"

    def transport_complete(self, state):
        return state["clean_end"] and not state["partial_event"]


class XAI:
    name, key_name = "xai", "XAI_API_KEY"
    base = "https://api.x.ai/v1"
    count_scope = ("the message texts joined by blank lines, by the provider's tokenize-text endpoint; chat "
                   "formatting tokens are not counted, so this is not a complete request budget")

    def headers(self, key):
        return {"Authorization": "Bearer " + key, "Content-Type": "application/json"}

    def model_info(self, http, model, key):
        return http.json("GET", f"{self.base}/models/{model}", self.headers(key))

    def build(self, model, history, text, max_output_tokens):
        body = {"model": model,
                "messages": [{"role": m["role"], "content": m["content"]} for m in history]
                + [{"role": "user", "content": text}],
                "stream": True, "stream_options": {"include_usage": True}}
        if max_output_tokens is not None:
            body["max_tokens"] = max_output_tokens
        return body

    def count(self, http, model, key, body):
        text = "\n\n".join(m["content"] for m in body["messages"])
        r = http.json("POST", f"{self.base}/tokenize-text", self.headers(key), {"model": model, "text": text})
        ids = r.get("token_ids") if isinstance(r, dict) else None
        if not isinstance(ids, list) or not ids:
            raise ValueError("tokenize-text returned no token list for a non-empty text")
        return len(ids), r

    def stream_url(self, model):
        return f"{self.base}/chat/completions"

    def parse(self, event, state):
        for choice in event.get("choices") or []:
            delta = choice.get("delta") or {}
            if delta.get("content"):
                state["answer"].append(delta["content"])
            if delta.get("reasoning_content"):
                state["thinking"].append(delta["reasoning_content"])
            if delta.get("refusal"):  # OpenAI streams a refusal apart from content (GPT-6 R3P2)
                state["refusal"].append(delta["refusal"])
            if choice.get("finish_reason"):
                state["finish_reason"] = choice["finish_reason"]
        for src, dst in (("usage", "usage"), ("model", "returned_model"), ("id", "response_id"),
                         ("system_fingerprint", "system_fingerprint")):
            if event.get(src):
                state[dst] = event[src]

    def complete(self, state):
        return state.get("finish_reason") == "stop"

    def transport_complete(self, state):
        return state["done_marker"] and not state["partial_event"]


class ModelArk(XAI):
    """BytePlus ModelArk. Its single-model endpoint returns an empty body, so model metadata is the
    model's entry in the model list; the model must be listed."""
    name, key_name = "modelark", "MODELARK_API_KEY"
    base = "https://ark.ap-southeast.bytepluses.com/api/v3"
    count_scope = ("the message texts joined by blank lines, by the provider's tokenization endpoint; chat "
                   "formatting tokens are not counted, so this is not a complete request budget")

    def model_info(self, http, model, key):
        r = http.json("GET", f"{self.base}/models", self.headers(key))
        for m in (r.get("data") or []) if isinstance(r, dict) else []:
            if isinstance(m, dict) and m.get("id") == model:
                return m
        raise ValueError(f"model {model} is not in the provider's model list")

    def count(self, http, model, key, body):
        text = "\n\n".join(m["content"] for m in body["messages"])
        r = http.json("POST", f"{self.base}/tokenization", self.headers(key), {"model": model, "text": [text]})
        data = r.get("data") if isinstance(r, dict) else None
        first = data[0] if isinstance(data, list) and data and isinstance(data[0], dict) else {}
        n, ids = first.get("total_tokens"), first.get("token_ids")
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("tokenization returned no valid positive total_tokens")
        if not isinstance(ids, list) or len(ids) != n:
            raise ValueError("tokenization returned no token_ids list matching total_tokens")  # R1API1
        return n, r


class OpenAI(XAI):
    """OpenAI Chat Completions, streamed. A reasoning model takes max_completion_tokens rather than max_tokens, and
    this endpoint returns none of its reasoning text: only the reasoning token count, in usage. No reasoning effort
    is sent, so the provider's default applies. The input is counted, without generating, by the Responses API's
    input-token endpoint, over the same messages."""
    name, key_name = "openai", "OPENAI_API_KEY"
    base = "https://api.openai.com/v1"
    count_scope = ("the same messages as a Responses API input, by the provider's input-token endpoint "
                   "(POST /v1/responses/input_tokens); the chat endpoint may frame messages slightly differently, "
                   "so this is not a complete request budget")
    thinking_note = "OpenAI Chat Completions returns no reasoning text; its token count is in usage"

    def complete(self, state):
        return state.get("finish_reason") == "stop" and not state["refusal"]

    def build(self, model, history, text, max_output_tokens):
        body = super().build(model, history, text, None)
        if max_output_tokens is not None:
            body["max_completion_tokens"] = max_output_tokens
        return body

    def count(self, http, model, key, body):
        r = http.json("POST", f"{self.base}/responses/input_tokens", self.headers(key),
                      {"model": model, "input": [{"role": m["role"], "content": m["content"]} for m in body["messages"]]})
        n = r.get("input_tokens") if isinstance(r, dict) else None
        if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
            raise ValueError("the input-token endpoint returned no valid positive input_tokens")
        return n, r


PROVIDERS = {"gemini": Gemini, "xai": XAI, "modelark": ModelArk, "openai": OpenAI}


class SSE:
    """Server-sent events: data lines joined within an event, dispatched at a blank line (API2)."""

    def __init__(self):
        self.data, self.buf = [], b""

    def feed(self, raw):
        """Return the data strings of the events completed by these bytes."""
        self.buf += raw
        events = []
        while True:
            i = self.buf.find(b"\n")
            if i < 0:
                break
            line, self.buf = self.buf[:i].rstrip(b"\r").decode("utf-8"), self.buf[i + 1:]
            if line == "":
                if self.data:
                    events.append("\n".join(self.data))
                    self.data = []
            elif line.startswith(":"):
                continue
            else:
                field, _, value = line.partition(":")
                if field == "data":
                    self.data.append(value[1:] if value.startswith(" ") else value)
        return events

    def pending(self):
        """True if bytes or data remain that never formed a complete event."""
        return bool(self.data or self.buf.strip())


def runner_identity():
    here = Path(__file__).resolve()
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain", "--", str(here)], capture_output=True, text=True).stdout.strip()
    return {"path": "tools/run_api_participant.py", "sha256": sha256(here.read_bytes()),
            "repo_head": head, "runner_uncommitted_changes": bool(dirty)}


def run(args, http=None, prompt=None, history=None, key=None):
    max_in = positive("max_input_tokens", getattr(args, "max_input_tokens", None))  # before any file or request
    max_out = positive("max_output_tokens", getattr(args, "max_output_tokens", None))
    http = http or Http()
    provider = PROVIDERS[args.provider]()
    text, digest, commit, assignment = participant_input(args, provider.name, prompt)
    prefix = Path(args.prefix)
    outside_repository(prefix)
    paths = {k: Path(f"{prefix}.{k}") for k in EVIDENCE}
    existing = [str(p) for p in paths.values() if p.exists()]
    if existing:
        raise FileExistsError(f"evidence already exists, refusing to start: {existing}")
    prefix.parent.mkdir(parents=True, exist_ok=True)
    key = key or load_key(args.keys_file, provider.key_name)
    redact = Redactor(key)

    history_info = None
    if history is None and args.history_record:
        earlier_text, earlier_digest, earlier_commit = pinned_prompt(args.history_tag)
        answer = committed_record_body(args.history_record)
        history = [{"role": "user", "content": earlier_text}, {"role": "assistant", "content": answer}]
        history_info = {"record": args.history_record, "answer_sha256": sha256(answer),
                        "earlier_input_set": {"tag": args.history_tag, "commit": earlier_commit},
                        "earlier_participant_text_sha256": earlier_digest,
                        "note": ("the earlier answer is the committed record body without the blank line after "
                                 "the front matter and without the final newline; no earlier reasoning is sent")}
    history = history or []

    # Preflight: model metadata and a no-generation input count. Nothing is generated yet.
    body = provider.build(args.model, history, text, max_out)
    stages, errors = {}, []
    try:
        stages["model_metadata"] = {"response": redact.obj(provider.model_info(http, args.model, key))}
    except Exception as e:
        stages["model_metadata"] = error_record(e, redact)
        errors.append("model metadata unavailable")
    input_tokens = None
    try:
        input_tokens, count_response = provider.count(http, args.model, key, body)
        stages["input_count"] = {"input_tokens": input_tokens, "scope": provider.count_scope,
                                 "response": redact.obj(count_response)}
    except Exception as e:
        stages["input_count"] = dict(error_record(e, redact), scope=provider.count_scope)
        errors.append("input count unavailable or invalid")
    checks = {}
    if max_in is not None and input_tokens is not None:
        checks["within_input_limit"] = input_tokens <= max_in
    ok = not errors and all(checks.values())
    preflight = {
        "checked_utc": now(),
        "provider": provider.name,
        "requested_model": args.model,
        "input_set": {"tag": args.tag, "commit": commit, "packet": getattr(args, "packet", None),
                      "assignment": assignment},
        "participant_text_sha256": digest,
        "operator_choices": {"max_output_tokens": max_out, "max_input_tokens": max_in,
                             "max_input_tokens_scope": provider.count_scope,
                             "sampling": "omitted; provider defaults apply and are not recorded as known values",
                             "thinking": ("omitted except includeThoughts=true; the provider's default thinking "
                                          "applies" if provider.name == "gemini"
                                          else "omitted; the provider's default reasoning applies"),
                             "tools": "none sent", "system_instruction": "none sent"},
        "history": history_info,
        "request_body": body,
        "request_body_sha256": sha256(json.dumps(body, ensure_ascii=False, sort_keys=True)),
        "stages": stages,
        "checks": checks,
        "errors": errors,
        "passed": ok,
        "redactions": redact.count,
        "runtime": {"os": platform.platform(), "python": platform.python_version()},
        "runner": runner_identity(),
    }
    write_exclusive(paths["preflight.json"], json.dumps(preflight, ensure_ascii=False, indent=2))
    if not ok:
        raise PreflightError(f"preflight failed; no generation request sent: {errors or checks}")

    attempt = {"attempt_id": str(uuid.uuid4()), "status": "started", "started_utc": now(),
               "preflight": paths["preflight.json"].name, "provider": provider.name, "requested_model": args.model,
               "request_body_sha256": preflight["request_body_sha256"]}
    write_exclusive(paths["attempt.json"], json.dumps(attempt, ensure_ascii=False, indent=2))

    state = {"answer": [], "thinking": [], "refusal": [], "done_marker": False, "clean_end": False,
             "partial_event": False}
    sse, n = SSE(), 0
    stream_redact = StreamRedactor(redact)
    count_before_stream = redact.count

    def consume(chunk):
        nonlocal n
        s.write(chunk)  # the bytes as received, unless a redaction was recorded
        s.flush()
        for data in sse.feed(chunk):
            if data.strip() == "[DONE]":
                state["done_marker"] = True
                continue
            event = json.loads(data)
            n += 1
            if isinstance(event, dict) and event.get("error"):
                raise HttpFailure(None, redact.text(json.dumps(event["error"])), None, "error event in stream")
            provider.parse(event, state)

    s = open(paths["stream.sse"], "xb")
    try:
        try:
            for raw in http.stream(provider.stream_url(args.model), provider.headers(key), body):
                consume(stream_redact.feed(raw if isinstance(raw, bytes) else raw.encode("utf-8")))
            consume(stream_redact.flush())
        except Exception:
            s.write(stream_redact.flush())  # keep held-back bytes, redacted, before recording the failure
            s.flush()
            raise
        state["clean_end"] = True
        state["partial_event"] = sse.pending()
        if not state.get("finish_reason") and not state.get("block"):
            raise RuntimeError("stream ended without a finish reason or a provider block")
    except Exception as e:  # keep everything; never retry
        s.close()
        stream_redactions = redact.count - count_before_stream
        write_exclusive(paths["failure.json"], json.dumps(redact.obj({
            "attempt_id": attempt["attempt_id"], "generation_status": "failed", "failed_utc": now(),
            **error_record(e, redact),
            "events_parsed": n, "partial_event": sse.pending(),
            "partial_answer": "".join(state["answer"]), "partial_thinking": "".join(state["thinking"]),
            "partial_refusal": "".join(state["refusal"]),
            "finish_reason": state.get("finish_reason"), "returned_model": state.get("returned_model"),
            "response_id": state.get("response_id"), "usage": state.get("usage"),
            "response_headers": getattr(http, "last_headers", {}),
            "stream_redactions": stream_redactions,
            "stream_byte_exact": stream_redactions == 0,
        }), ensure_ascii=False, indent=2))
        rec = error_record(e, redact)
        raise GenerationFailure(f"generation failed: {rec['error']}", rec["http_status"], rec["http_body"],
                                rec["http_headers"], type(e).__name__) from None
    s.close()
    stream_redactions = redact.count - count_before_stream

    blocked = bool(state.get("block")) and not state["answer"]
    refusal = "".join(state["refusal"])
    status = ("provider_blocked" if blocked else "refused" if refusal
              else "content_filtered" if state.get("finish_reason") == "content_filter" else "completed")
    result = redact.obj({
        "attempt_id": attempt["attempt_id"],
        "generation_status": status,
        "refusal": refusal or None,
        "ended_utc": now(),
        "block": state.get("block"),
        "finish_reason": state.get("finish_reason"),
        "complete": provider.complete(state),
        "transport_complete": provider.transport_complete(state),
        "done_marker": state["done_marker"],
        "partial_final_event": state["partial_event"],
        "answer": "".join(state["answer"]),
        "thinking": "".join(state["thinking"]),
        "thinking_note": getattr(provider, "thinking_note", None) or (
            "Gemini returns thought summaries, not raw reasoning" if provider.name == "gemini"
            else f"{provider.name} reasoning_content, if the model returns it"),
        "events": n,
        "returned_model": state.get("returned_model"),
        "response_id": state.get("response_id"),
        "system_fingerprint": state.get("system_fingerprint"),
        "usage": state.get("usage"),
        "response_headers": getattr(http, "last_headers", {}),
        "stream_redactions": stream_redactions,
        "stream_byte_exact": stream_redactions == 0,
    })
    write_exclusive(paths["result.json"], json.dumps(result, ensure_ascii=False, indent=2))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("provider", choices=sorted(PROVIDERS))
    ap.add_argument("model")
    ap.add_argument("prefix")
    ap.add_argument("--tag", default="round/01-deliberation/v1")
    ap.add_argument("--packet", help="this model's packet in the round's packets/ folder, read at the tag and "
                                     "checked against the manifest's assignment for PROVIDER and MODEL")
    ap.add_argument("--history-record")
    ap.add_argument("--history-tag", default="round/00-initial/v1")
    ap.add_argument("--max-output-tokens", type=int)
    ap.add_argument("--max-input-tokens", type=int)
    ap.add_argument("--keys-file", default=str(DEFAULT_KEYS))
    args = ap.parse_args(argv)
    for name in ("max_input_tokens", "max_output_tokens"):
        try:
            positive(name, getattr(args, name))
        except ValueError as e:
            ap.error(str(e))
    r = run(args)
    print(f"{args.provider} {args.model}: status={r['generation_status']} finish={r['finish_reason']} "
          f"complete={r['complete']} transport_complete={r['transport_complete']} answer={len(r['answer'])} chars "
          f"thinking={len(r['thinking'])} chars returned_model={r['returned_model']}")


if __name__ == "__main__":
    main()
