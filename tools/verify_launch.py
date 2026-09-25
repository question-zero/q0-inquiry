# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-25
# attribution: self-declared
# prompt: Roadmap step 17 (proposals/2026-09-24-claude-opus-5-5-roadmap-to-public.md): verify the exact export in a fresh checkout, as listed in proposals/2026-09-25-claude-opus-5-5-launch-export.md. Revision 2 applies GPT-6's LX1, LX2 and the link-containment correction (topic launch-export, round 1); revision 3 its round 2 follow-ups.
# license: MIT (LICENSE-CODE)
"""Verify a launch commit in a fresh clone (roadmap step 17). Prints results and counts only, never a private value.

Usage:
    python tools/verify_launch.py LAUNCH_REPO [--private CONFIG]

LAUNCH_REPO is a git repository holding the launch commit. It is cloned into a temporary folder and checked there:
    1. exactly one commit, with no parent, and no refs other than the default branch
    2. launch-manifest.md parses strictly (no malformed or repeated row, no unknown disposition, a hash for every
       file but itself); the file set equals its list, and every launch hash matches
    3. the archive matches its own manifest, sessions/manifest.md: the same files and every output hash (LX2)
    4. the manifest records that the archive-only checks ran at the source commit and printed "check: OK" (LX3)
    5. tools/check_headers.py, every unit test, and build_index.py --tree --check pass
    6. every relative Markdown link resolves to a file inside the tree
    7. with --private: the launch builder's scan() finds nothing in any file or path (strict for the archive), the
       exporter's detector finds nothing in any archive file in any reading, and no withhold term appears anywhere
Exit status 0 only if every check passes.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_launch_tree as bl  # noqa: E402
import export_archive  # noqa: E402

LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
DISPOSITIONS = {"unchanged", "transformed", "withheld-stub", "added by the exporter", "removed", "generated"}
ROW = re.compile(r"\| `([^`]+)` \| ([^|]+) \|([^|]*)\|([^|]*)\| (?:`([0-9a-f]{64})`)? \|$")


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def manifest_rows(text):
    """{path: (disposition, launch hash or None)} and a list of problems (GPT-6 LX2)."""
    rows, problems = {}, []
    for line in text.splitlines():
        if not line.startswith("| `"):
            continue
        m = ROW.match(line)
        if not m:
            problems.append(f"malformed row: {line[:60]}")
            continue
        path, disp, digest = m.group(1), m.group(2).strip(), m.group(5)
        if path in rows:
            problems.append(f"repeated row: {path}")
        if disp not in DISPOSITIONS:
            problems.append(f"unknown disposition {disp!r}: {path}")
        if disp not in ("removed", "generated") and not digest:
            problems.append(f"no launch hash: {path}")
        rows[path] = (disp, digest)
    return rows, problems


def check(clone, private):
    results = []

    def record(name, ok, detail=""):
        results.append((name, ok, detail))

    commits = run(["git", "rev-list", "--all", "--parents"], clone).stdout.split("\n")
    commits = [c for c in commits if c]
    refs = [r for r in run(["git", "for-each-ref", "--format=%(refname)"], clone).stdout.split() if r]
    record("one root commit", len(commits) == 1 and len(commits[0].split()) == 1, f"{len(commits)} commit(s)")
    record("no other refs", all(r in ("refs/heads/main", "refs/remotes/origin/main", "refs/remotes/origin/HEAD")
                                for r in refs), ", ".join(refs))
    files = sorted(p.relative_to(clone).as_posix() for p in clone.rglob("*")
                   if p.is_file() and ".git" not in p.relative_to(clone).parts)
    manifest = (clone / "launch-manifest.md").read_text(encoding="utf-8")
    rows, problems = manifest_rows(manifest)
    record("the launch manifest parses strictly", not problems, "; ".join(problems[:3]))
    listed = {p for p, (d, _) in rows.items() if d != "removed"}
    record("file set equals the manifest", set(files) == listed,
           f"{len(set(files) - listed)} unlisted, {len(listed - set(files))} missing")
    bad = [p for p in files if p != "launch-manifest.md" and
           (p not in rows or not rows[p][1] or hashlib.sha256((clone / p).read_bytes()).hexdigest() != rows[p][1])]
    record("every launch hash matches", not bad, f"{len(bad)} mismatched or missing")
    archive_files = [p for p in files if p.startswith("sessions/") or re.match(r"rounds/[^/]+/evidence/", p)]
    declared = "its own manifest is `sessions/manifest.md`" in manifest
    if archive_files or declared:  # an archive without its manifest fails; it never skips the check (LX2)
        try:
            bl.check_archive(clone, {p: (clone / p).read_bytes() for p in files})
            record("the archive matches its own manifest", True)
        except ValueError as e:
            record("the archive matches its own manifest", False, str(e)[:120])
    checks = re.findall(r"`([^`]+)` printed `check: OK`", manifest)
    record("archive-only checks recorded as run", all(any(c == x for c in checks) for x in bl.PREREQUISITES),
           f"{len(checks)} recorded")
    r = run([sys.executable, "tools/check_headers.py"], clone)
    record("header check", r.returncode == 0, (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else "")
    r = run([sys.executable, "-m", "unittest", "discover", "-s", "tools", "-p", "test_*.py"], clone)
    tail = [ln for ln in (r.stdout + r.stderr).splitlines() if ln.startswith(("Ran ", "OK", "FAILED"))]
    record("unit tests", r.returncode == 0, " ".join(tail))
    r = run([sys.executable, "tools/build_index.py", "--tree", "--check"], clone)
    record("index rows match the tree", r.returncode == 0, r.stdout.strip())
    broken = []
    for p in files:
        if p.endswith(".md"):
            for m in LINK.finditer((clone / p).read_text(encoding="utf-8", errors="replace")):
                target = m.group(1)
                if "://" in target or target.startswith(("mailto:", "/")) or re.match(r"[A-Za-z]:[/\\]", target):
                    continue  # external, or an absolute local path recorded as evidence: not a link in the tree
                resolved = (clone / p).parent.joinpath(target).resolve()
                if not resolved.exists() or not resolved.is_relative_to(clone.resolve()):
                    broken.append(f"{p} -> {target}")  # missing, or outside the tree
    record("relative links resolve", not broken, f"{len(broken)} broken" + (f": {broken[:5]}" if broken else ""))
    if private:
        cfg = json.loads(Path(private["launch"]).read_text(encoding="utf-8"))
        tree = bl.Tree(Path(private["repo"]), cfg["source_commit"])
        builder = bl.Builder(cfg, tree)
        export = json.loads(Path(private["export"]).read_text(encoding="utf-8")) if private.get("export") else {}
        terms = [t["text"] for t in export.get("terms", [])]  # redacted in the archive; the tree may publish some
        withhold = [t["text"] for t in export.get("withhold_terms", [])]  # withheld everywhere
        keys = []
        if export.get("keys_file"):
            keys = [ln.split("=", 1)[1].strip().strip('"') for ln in
                    Path(export["keys_file"]).read_text(encoding="utf-8").splitlines() if "=" in ln]
            keys = [k for k in keys if len(k) >= 8]
        found = {"identifiers, literals or Grok spans": 0, "configured terms": 0, "key values": 0,
                 "the exporter's detector, on archive files": 0}
        red = export_archive.Redactor(export) if export else None
        for p in files:
            data = (clone / p).read_bytes()
            archive = p.startswith("sessions/") or "/evidence/" in p
            found["identifiers, literals or Grok spans"] += builder.scan(p, data, strict=archive)
            texts, plain, _ = bl.reading_set(p, data)
            for t in texts + plain:  # every reading, the path included, in the tree and the archive (LX1)
                low = t.lower()
                found["configured terms"] += sum(low.count(x.lower()) for x in withhold + (terms if archive else []))
                found["key values"] += sum(t.count(k) for k in keys)
            if red is not None and archive:
                for t in bl.readings(p, data):
                    found["the exporter's detector, on archive files"] += len(red.detect_all(t, set()))
        for k, n in found.items():
            record(f"private scan: {k}", n == 0, f"{n} found")
    return results


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("launch_repo")
    ap.add_argument("--private", help="JSON: {repo, launch (builder config), export (exporter config)}")
    args = ap.parse_args(argv)
    private = json.loads(Path(args.private).read_text(encoding="utf-8")) if args.private else None
    with tempfile.TemporaryDirectory() as tmp:
        clone = Path(tmp) / "clone"
        r = subprocess.run(["git", "clone", "-q", "--no-local", args.launch_repo, str(clone)], capture_output=True, text=True)
        if r.returncode:
            print("clone failed:", r.stderr.strip())
            sys.exit(1)
        results = check(clone, private)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  ({detail})" if detail else ""))
    sys.exit(0 if all(ok for _, ok, _ in results) else 1)


if __name__ == "__main__":
    main()
