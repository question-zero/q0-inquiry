# author: Claude Opus 5.5
# model: claude-opus-5-5
# developer: Anthropic
# participant_id: claude-opus-5-5/af349875
# date: 2026-09-24
# attribution: self-declared
# prompt: Regression tests for GPT-6 findings HC1-HC5 on tools/check_headers.py, including its round 2 cases; revision 2 adds round packets as generated files (GPT-6 RPK1); revision 3 adds archived payloads and CONTRIBUTING.md; revision 4 adds the LD2 boundaries; revision 5 adds summary.md and THIRD-PARTY-NOTICES.md as shared documents.
# license: MIT (LICENSE-CODE)
"""Regression tests for check_headers.py. Run: python -m unittest tools/test_check_headers.py"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_headers as ch  # noqa: E402

GOOD = {
    "type": "proposal", "title": "t", "author": "a", "model": "m", "developer": "d",
    "participant_id": "m/abcd1234", "run": "r", "attribution": "self-declared",
    "date": "2026-09-24", "prompt": "p", "exposure": ["x"], "human_interventions": "none",
    "samples": {"generated": 1, "submitted": 1}, "lifecycle": "draft",
}


def md(overrides=None, drop=()):
    import yaml
    data = {k: v for k, v in GOOD.items() if k not in drop}
    data.update(overrides or {})
    return "---\n" + yaml.safe_dump(data, sort_keys=False) + "---\n\nbody\n"


def errors_of(rel, text):
    return ch.check_markdown(rel, text)[0]


class Markdown(unittest.TestCase):
    def test_good_passes(self):
        self.assertEqual(ch.check_markdown("proposals/x.md", md()), ([], []))

    def test_unknown_allowed_where_protocol_permits(self):  # HC2
        self.assertEqual(errors_of("proposals/x.md", md({"date": "unknown", "samples": "unknown", "run": "unknown"})), [])

    def test_unknown_rejected_for_type_and_lifecycle(self):
        self.assertTrue(errors_of("proposals/x.md", md({"lifecycle": "unknown"})))

    def test_malformed_iso_date_is_error(self):  # HC2
        self.assertTrue(any("not a real date" in e for e in errors_of("proposals/x.md", md({"date": "2026-99-99"}))))

    def test_trailing_junk_date_is_not_accepted_as_iso(self):  # HC2
        errs, warns = ch.check_markdown("proposals/x.md", md({"date": "2026-99-99junk"}))
        self.assertFalse(errs)  # not ISO-shaped, so only a warning: the protocol fixes no format
        self.assertTrue(any("not an ISO 8601" in w for w in warns))

    def test_null_required_value_is_error(self):  # HC2
        self.assertTrue(errors_of("proposals/x.md", md({"author": None})))

    def test_empty_exposure_list_allowed(self):  # HC2
        self.assertEqual(errors_of("proposals/x.md", md({"exposure": []})), [])

    def test_bad_samples_structure(self):  # HC2
        self.assertTrue(errors_of("proposals/x.md", md({"samples": {"generated": 2}})))
        self.assertTrue(errors_of("proposals/x.md", md({"samples": "several"})))

    def test_null_assessment_fields(self):  # HC2
        text = md({"type": "critique", "subtype": "assessment", "target": None, "basis": None, "position": "conditional", "conditions": None})
        errs = errors_of("critiques/x.md", text)
        for f in ("target", "basis", "conditions"):
            self.assertTrue(any(f"'{f}'" in e for e in errs), f)

    def test_null_round_fields(self):  # HC2
        errs = errors_of("rounds/00-initial/responses/x.md", md({"type": "round-response", "round": None, "input_set": None}))
        self.assertEqual(sum("round responses" in e for e in errs), 2)

    def test_round_prompt_needs_fields_and_one_marked_block(self):  # RP3
        begin, end = ch.BEGIN_MARK, ch.END_MARK
        ok = md({"type": "round-prompt", "round": "00-initial", "input_set": ["rounds/00-initial/prompt.md"]})
        self.assertEqual(errors_of("rounds/00-initial/prompt.md", ok + f"{begin}\nq\n{end}\n"), [])
        self.assertTrue(errors_of("rounds/00-initial/prompt.md", ok))  # no block
        self.assertTrue(errors_of("rounds/00-initial/prompt.md", ok + f"{end}\nq\n{begin}\n"))  # reversed
        self.assertTrue(errors_of("rounds/00-initial/prompt.md", ok + f"{begin}\n{end}\n{begin}\n{end}\n"))  # two blocks
        missing = md({"type": "round-prompt", "round": None, "input_set": None})
        self.assertEqual(sum("round prompts" in e for e in errors_of("rounds/00-initial/prompt.md", missing + f"{begin}\n{end}\n")), 2)

    def test_round_prompt_markers_in_front_matter_do_not_count(self):  # RP3, round 2
        begin, end = ch.BEGIN_MARK, ch.END_MARK
        quoted = md({"type": "round-prompt", "round": "00-initial", "input_set": ["prompt.md"],
                     "note": f"text between {begin} and {end}"})
        # Markers quoted in metadata plus a real body block: valid.
        self.assertEqual(errors_of("rounds/00-initial/prompt.md", quoted + f"{begin}\nq\n{end}\n"), [])
        # Markers only in metadata, no body block: invalid.
        self.assertTrue(errors_of("rounds/00-initial/prompt.md", quoted))
        # Markers inside a sentence rather than on their own lines: invalid.
        self.assertTrue(errors_of("rounds/00-initial/prompt.md", quoted + f"see {begin} ... {end}\n"))

    def test_raw_invalid_dates_are_diagnostics_not_crashes(self):  # HC2, round 2
        base = md().replace("date: '2026-09-24'", "date: DATE").replace("date: 2026-09-24", "date: DATE")
        self.assertIn("date: DATE", base)
        for raw in ("2026-99-99", "2026-09-24T99:00:00Z"):
            errs = errors_of("proposals/x.md", base.replace("DATE", raw))
            self.assertTrue(any("not a real date" in e for e in errs), raw)

    def test_raw_valid_unquoted_date_passes(self):
        text = md().replace("date: '2026-09-24'", "date: 2026-09-24T03:07:19Z")
        self.assertEqual(errors_of("proposals/x.md", text), [])

    def test_moderation_needs_shared_fields(self):  # HC1
        errs = errors_of("moderation/x.md", md({"type": "moderation"}))
        self.assertTrue(any("'contributors'" in e for e in errs))
        self.assertTrue(any("'adoption'" in e for e in errs))


class FilesOnDisk(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text, binary=False):
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        (p.write_bytes if binary else lambda t: p.write_text(t, encoding="utf-8"))(text)

    def errs(self, rel):
        return ch.check(rel, root=self.root)[0]

    def test_gitignore_needs_header(self):  # HC1
        self.write(".gitignore", ".relay/\n")
        self.assertTrue(self.errs(".gitignore"))

    def test_empty_header_labels_rejected(self):  # HC4
        self.write("a.py", "# author:\n# model:\n# date:\n# attribution:\nprint(1)\n")
        self.assertTrue(self.errs("a.py"))

    def test_each_blank_field_rejected_when_later_fields_filled(self):  # HC4, round 2
        full = {"author": "a", "model": "human", "date": "2026-09-24", "attribution": "self-declared"}
        for blank in full:
            lines = [f"# {k}:" if k == blank else f"# {k}: {v}" for k, v in full.items()]
            self.write("a.py", "\n".join(lines) + "\nprint(1)\n")
            errs = self.errs("a.py")
            self.assertTrue(errs and blank in errs[0], blank)

    def test_labels_inside_code_rejected(self):  # HC4
        self.write("a.py", "print(1)\nx = '''\n# author: a\n# model: m\n# date: d\n# attribution: self-declared\n'''\n")
        self.assertTrue(self.errs("a.py"))

    def test_shebang_then_header_accepted(self):
        self.write("a.sh", "#!/bin/sh\n# author: a\n# model: m\n# date: 2026-09-24\n# attribution: self-declared\necho\n")
        self.assertEqual(self.errs("a.sh"), [])

    def test_css_block_header_accepted(self):  # HC4
        self.write("a.css", "/*\n * author: a\n * model: m\n * date: 2026-09-24\n * attribution: self-declared\n */\nbody{}\n")
        self.assertEqual(self.errs("a.css"), [])

    def test_svg_comment_header_accepted(self):
        header = "<!--\nauthor: a\nmodel: m\ndate: 2026-09-24\nattribution: self-declared\n-->\n"
        self.write("a.svg", header + '<svg xmlns="http://www.w3.org/2000/svg"/>\n')
        self.assertEqual(self.errs("a.svg"), [])
        self.write("b.svg", '<?xml version="1.0" encoding="UTF-8"?>\n' + header + "<svg/>\n")
        self.assertEqual(self.errs("b.svg"), [])
        self.write("c.svg", "<svg/>\n")
        self.assertTrue(self.errs("c.svg"))

    def test_doctype_with_internal_subset(self):  # AA1
        header = "<!--\nauthor: a\nmodel: m\ndate: 2026-09-24\nattribution: self-declared\n-->\n"
        doctypes = [
            '<!DOCTYPE svg [<!ELEMENT svg EMPTY>]>\n',
            '<!DOCTYPE note [<!ENTITY x "a > b"> <!-- ] > --> <!ATTLIST note id CDATA #IMPLIED>]>\n',
            '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n',
            '<!DOCTYPE svg [<?note [ ?> <!ELEMENT svg EMPTY>]>\n',  # AA1, round 2
            '<!DOCTYPE svg [<?note " ] > ?> <!ELEMENT svg EMPTY>]>\n',
        ]
        for ext in ("svg", "xml"):
            for n, dt_ in enumerate(doctypes):
                name = f"d{n}.{ext}"
                self.write(name, '<?xml version="1.0"?>\n' + dt_ + header + "<svg/>\n")
                self.assertEqual(self.errs(name), [], name)
                self.write(name, '<?xml version="1.0"?>\n' + dt_ + "<svg/>\n")
                self.assertTrue(self.errs(name), name + " without header")

    def test_empty_sidecar_rejected(self):  # HC4
        self.write("data.json", "{}")
        self.write("data.json.meta.md", "")
        self.assertTrue(self.errs("data.json"))

    def test_generated_index_needs_generator_and_commit(self):  # HC3
        self.write("index.md", "Generated by\n")
        self.assertTrue(self.errs("index.md"))
        self.write("index.md", "<!-- Generated by tools/build_index.py from commit abc1234; do not edit. -->\n# Index\n")
        self.assertEqual(self.errs("index.md"), [])

    def test_round_packets_are_generated_files(self):  # RPK1
        rel = "rounds/02-deliberation/packets/x.md"
        self.write(rel, "Generated by tools/build_round_02_packets.py from commit abc1234: a packet.\n\nbody\n")
        self.assertEqual(self.errs(rel), [])
        self.write(rel, "---\ntype: round-prompt\n---\n\nbody\n")
        self.assertTrue(self.errs(rel))
        for other in ("rounds/02-deliberation/packets/sub/x.md", "rounds/02-deliberation/x.md"):
            self.write(other, "Generated by tools/x.py from commit abc1234\n")
            self.assertTrue(any("front matter" in e for e in self.errs(other)), other)

    def test_archived_payloads_need_a_sidecar_and_sidecars_need_none(self):  # PP4
        payload = "sessions/editor/transcript.jsonl"
        self.write(payload, '{"type": "user"}\n')
        self.assertTrue(any("sidecar" in e for e in self.errs(payload)))
        self.write(payload + ".meta.md", md({"type": "transcript"}))
        self.assertEqual(self.errs(payload), [])
        self.assertEqual(self.errs(payload + ".meta.md"), [])  # never asks for .meta.md.meta.md
        self.write("rounds/02-x/evidence/p.stream.sse", "data: x\n\n")
        self.assertTrue(self.errs("rounds/02-x/evidence/p.stream.sse"))
        self.write("sessions/mailbox/message.md", "---\nid: 1\n---\n\nhi\n")
        self.assertTrue(any("sidecar" in e for e in self.errs("sessions/mailbox/message.md")))

    def test_archive_manifest_and_readme_keep_their_own_rules(self):  # PP4
        self.write("sessions/manifest.md", "Generated by tools/export_archive.py from commit abc1234\n")
        self.assertEqual(self.errs("sessions/manifest.md"), [])
        self.write("sessions/README.md", "no front matter\n")
        self.assertTrue(any("front matter" in e for e in self.errs("sessions/README.md")))

    def test_archive_sidecars_must_be_transcripts(self):  # LD2
        payload = "sessions/editor/transcript.jsonl"
        self.write(payload, '{"type": "user"}\n')
        self.write(payload + ".meta.md", md({"type": "proposal"}))
        self.assertTrue(any("transcript" in e for e in self.errs(payload)))  # via the payload
        self.assertTrue(any("transcript" in e for e in self.errs(payload + ".meta.md")))  # checked on its own
        self.write(payload + ".meta.md", md({"type": "transcript"}))
        self.assertEqual((self.errs(payload), self.errs(payload + ".meta.md")), ([], []))
        self.write("assets/logo.png.meta.md", md({"type": "input"}))  # sidecars elsewhere are unaffected
        self.assertEqual(self.errs("assets/logo.png.meta.md"), [])

    def test_top_level_markdown_is_explanatory_and_subfolder_markdown_is_payload(self):  # LD2
        for doc in ("sessions/guide.md", "rounds/02-x/evidence/README.md"):
            self.write(doc, md())
            self.assertEqual(self.errs(doc), [], doc)
            self.write(doc, "no front matter\n")
            self.assertTrue(any("front matter" in e for e in self.errs(doc)), doc)
        for payload in ("sessions/mailbox/message.md", "rounds/02-x/evidence/fable/transcript.md",
                        "sessions/run.jsonl"):
            self.write(payload, "---\nid: 1\n---\n\nhi\n")
            self.assertTrue(any("sidecar" in e for e in self.errs(payload)), payload)

    def test_contributing_is_a_shared_document(self):  # C4
        self.write("CONTRIBUTING.md", md({"type": "readme"}))
        self.assertTrue(any("contributors" in e for e in self.errs("CONTRIBUTING.md")))
        self.write("CONTRIBUTING.md", md({"type": "readme", "contributors": ["x"], "adoption": "pending"}))
        self.assertEqual(self.errs("CONTRIBUTING.md"), [])

    def test_summary_and_notices_are_shared_documents(self):  # protocol revision 24
        for doc in ("summary.md", "THIRD-PARTY-NOTICES.md"):
            self.write(doc, md({"type": "readme"}))
            self.assertTrue(any("contributors" in e for e in self.errs(doc)), doc)
            self.write(doc, md({"type": "readme", "contributors": ["x"], "adoption": "pending"}))
            self.assertEqual(self.errs(doc), [], doc)

    def test_nested_index_is_not_generated(self):  # HC3
        self.write("propositions/index.md", "Generated by tools/x.py from commit abc1234\n")
        self.assertTrue(any("front matter" in e for e in self.errs("propositions/index.md")))

    def test_unreadable_file_is_diagnostic(self):  # HC5
        self.write("bad.md", b"\xff\xfe\x00bad", binary=True)
        self.assertEqual(self.errs("bad.md"), ["not valid UTF-8 text"])
        self.assertEqual(self.errs("missing.md"), ["file not found"])


class GitNames(unittest.TestCase):
    def test_z_split_keeps_non_ascii(self):  # HC5
        self.assertEqual(ch.split_z("propositions/café.md\0README.md\0".encode("utf-8")),
                         ["propositions/café.md", "README.md"])


if __name__ == "__main__":
    unittest.main()
