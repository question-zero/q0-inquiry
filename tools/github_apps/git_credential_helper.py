# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-26
# attribution: self-declared
# prompt: GPT-6's AC1 (critiques/2026-09-26-gpt-6--automation-code-review.md, topic automation-code): a git credential helper that answers only `get`, over HTTPS, for the exact approved host and repository path, reading the token and the approved destination from its environment.
# license: MIT (LICENSE-CODE)
"""Git credential helper for one approved destination. Used only by tools/github_apps/app_token.py.

Git runs it as `<helper> get|store|erase` with `key=value` lines on standard input. It answers only `get`, only for
protocol https, the exact host and the exact owner/repository path in Q0_APP_DEST (for example
`github.com/question-zero/q0-inquiry`), and only when Q0_APP_TOKEN is set. Everything else gets no answer: no other
host, port, protocol or path, and nothing is ever stored or erased. app_token.py enables `credential.useHttpPath`, so
Git sends the path.
"""
import os
import sys


def answer(operation, text, env):
    """The helper's output for one request; empty when it declines."""
    if operation != "get":
        return ""
    token, dest = env.get("Q0_APP_TOKEN", ""), env.get("Q0_APP_DEST", "")
    host, _, path = dest.partition("/")
    if not token or not host or not path or "\n" in token:
        return ""
    fields = {}
    for line in text.splitlines():
        if not line:
            break
        key, sep, value = line.partition("=")
        if sep:
            fields[key] = value
    got = fields.get("path", "")
    got = got[:-4] if got.endswith(".git") else got
    if fields.get("protocol") != "https" or fields.get("host") != host or got.strip("/") != path:
        return ""
    return f"username=x-access-token\npassword={token}\n"


def main():
    operation = sys.argv[1] if len(sys.argv) > 1 else ""
    sys.stdout.write(answer(operation, sys.stdin.read(64 * 1024), os.environ))


if __name__ == "__main__":
    main()
