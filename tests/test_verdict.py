"""Tests for the acceptance gate.

WHAT: unit tests for `bin/verdict` — parsing, the defect checks, the blocking
      classes and the owner's override.
WHY:  this gate is the only part of the acceptance phase that cannot be talked
      out of anything, which makes it the one part that must be right. Every
      test below is a rule the skill's prose merely describes.
HOW:  `python3 -m unittest discover -s tests` from the repo root. Stdlib only.
"""

import importlib.machinery
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

# `bin/verdict` has no `.py` extension (it is a command, not a module), so it
# is loaded by path. Registering it in `sys.modules` BEFORE executing it is
# required, not tidiness: `@dataclass` looks its own module up there while the
# class body is being processed, and a module missing from the table crashes
# the decorator.
ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("aikit_verdict", str(ROOT / "bin" / "verdict"))
_spec = importlib.util.spec_from_loader("aikit_verdict", _loader)
v = importlib.util.module_from_spec(_spec)
sys.modules["aikit_verdict"] = v
_loader.exec_module(v)


def report(**over):
    """A complete, passing report. Each test breaks exactly one thing."""
    data = {
        "milestone": "m52",
        "round": 1,
        "checklist": [
            {"item": "the client can be created by email alone", "passed": True,
             "evidence": ["screen:007-saved.png", "db:SELECT id FROM customers → 1 row"]}
        ],
        "findings": [],
        "beyond_checklist": dict.fromkeys(v.PROBES, "nothing unusual"),
        "not_checked": "did not reach the billing screen — ran out of actions",
        "spend": {"actions": 42, "minutes": 12},
    }
    data.update(over)
    return v.parse(data)


class TestParse(unittest.TestCase):
    def test_minimal_report_parses(self):
        self.assertEqual(report().milestone, "m52")

    def test_report_must_be_an_object(self):
        with self.assertRaises(v.BadReport):
            v.parse([1, 2, 3])

    def test_milestone_is_required(self):
        with self.assertRaises(v.BadReport):
            v.parse({"milestone": "  "})

    def test_empty_checklist_is_rejected(self):
        with self.assertRaises(v.BadReport):
            report(checklist=[])

    def test_unknown_finding_class_is_rejected(self):
        with self.assertRaises(v.BadReport):
            report(findings=[{"class": "meh", "what": "x"}])

    def test_russian_class_names_still_parse(self):
        """Reports written before aikit existed are Russian and must keep working."""
        parsed = report(findings=[{"class": "не работает", "what": "button does nothing",
                                   "evidence": ["screen:1.png"]}])
        self.assertEqual(parsed.findings[0].klass, v.BROKEN)

    def test_russian_probe_keys_still_parse(self):
        parsed = report(beyond_checklist={
            label: "fine" for label in
            ("пустое поле", "очень длинный текст", "двойное нажатие",
             "отказ на полпути", "кнопка назад")
        })
        self.assertEqual(set(parsed.probes), set(v.PROBES))


class TestDefects(unittest.TestCase):
    def test_clean_report_has_no_defects(self):
        self.assertEqual(v.defects(report()), ())

    def test_missing_not_checked_line_is_a_defect(self):
        self.assertTrue(v.defects(report(not_checked="")))

    def test_missing_probe_is_a_defect(self):
        probes = dict.fromkeys(v.PROBES, "fine")
        del probes["browser_back"]
        found = v.defects(report(beyond_checklist=probes))
        self.assertTrue(any("browser_back" in d for d in found))

    def test_passed_without_evidence_is_a_defect(self):
        found = v.defects(report(checklist=[{"item": "x", "passed": True, "evidence": []}]))
        self.assertTrue(any("no evidence" in d for d in found))

    def test_failed_without_evidence_is_not_a_defect(self):
        """Only a PASS needs proof. "I could not get there" is itself the finding."""
        found = v.defects(report(
            checklist=[{"item": "x", "passed": False, "evidence": []}],
            findings=[{"class": "broken", "what": "500 on save",
                       "evidence": ["screen:1.png", "db:SELECT → 0 rows"]}],
        ))
        # No EVIDENCE defect: that is what this test is about, and it holds.
        self.assertFalse(any("no evidence" in d for d in found), found)
        # It does still block, on a separate ground: a "done when" line that
        # did not pass means the milestone is not done. The gate used to
        # consult only findings and defects, so a report could fail its whole
        # checklist, file nothing, and be told it may merge.
        self.assertTrue(any("did not pass" in d for d in found), found)

    def test_a_failed_item_blocks_even_with_no_finding(self):
        """The hole the rule above closes: sloppy reports fail an item and
        forget to file anything, and the milestone is not done either way."""
        found = v.defects(report(
            checklist=[{"item": "the thing works", "passed": False,
                        "evidence": ["screen:007-saved.png", "db:SELECT → 1 row"]}],
            findings=[],
        ))
        self.assertTrue(any("did not pass" in d for d in found), found)

    def test_no_screenshot_anywhere_is_a_defect(self):
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True, "evidence": ["db:SELECT → 1 row"]}]))
        self.assertTrue(any("screen:" in d for d in found))

    def test_no_db_row_anywhere_is_a_defect(self):
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True, "evidence": ["screen:1.png"]}]))
        self.assertTrue(any("db:" in d for d in found))

    def test_no_db_requirement_can_be_switched_off(self):
        """A project with no database the acceptance role can read."""
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True, "evidence": ["screen:1.png"]}]),
            require_db=False)
        self.assertEqual(found, ())


class TestPassedIsABoolean(unittest.TestCase):
    """`bool("false")` is True. So is `bool("нет")`. This format is written by
    a model, in either language, and a string here read as PASSED — which was
    also the way out of the failed-item defect."""

    def test_a_stringified_boolean_is_refused(self):
        for value in ("false", "no", "нет", "not checked", 0.0001, []):
            with self.assertRaises(v.BadReport):
                v.parse({"milestone": "m", "round": 1,
                         "checklist": [{"item": "x", "passed": value,
                                        "evidence": ["screen:a.png"]}],
                         "beyond_checklist": dict.fromkeys(v.PROBES, "ok"),
                         "not_checked": "n", "spend": {}})

    def test_real_booleans_still_work(self):
        for value in (True, False):
            r = v.parse({"milestone": "m", "round": 1,
                         "checklist": [{"item": "x", "passed": value,
                                        "evidence": ["screen:a.png"]}],
                         "beyond_checklist": dict.fromkeys(v.PROBES, "ok"),
                         "not_checked": "n", "spend": {}})
            self.assertIs(r.checklist[0].passed, value)

    def test_a_malformed_block_is_a_report_error_not_a_traceback(self):
        """The agent is handed the parse error and asked to fix its report; an
        AttributeError reaches it as a traceback instead."""
        for bad in ({"beyond_checklist": []}, {"spend": "12 actions"}):
            data = {"milestone": "m", "round": 1,
                    "checklist": [{"item": "x", "passed": True,
                                   "evidence": ["screen:a.png"]}],
                    "beyond_checklist": dict.fromkeys(v.PROBES, "ok"),
                    "not_checked": "n", "spend": {}}
            data.update(bad)
            with self.assertRaises(v.BadReport):
                v.parse(data)


class TestWritePath(unittest.TestCase):
    """`--write` truncates whatever it is pointed at, and it used to be pointed
    at the owner's own ledger of what acceptance missed."""

    def test_the_verdict_does_not_overwrite_the_owners_ledger(self):
        root = pathlib.Path(tempfile.mkdtemp())
        tracker = root / "tracker"
        (tracker / "e1").mkdir(parents=True)
        ledger = tracker / "e1" / "acceptance.md"
        ledger.write_text("- acceptance missed this one\n", encoding="utf-8")
        ev = root / "ev" / "e1"
        ev.mkdir(parents=True)
        (ev / "001-a.png").write_bytes(b"\x89PNG")
        (ev / "verdict.json").write_text(json.dumps({
            "milestone": "e1", "round": 1,
            "checklist": [{"item": "works", "passed": True,
                           "evidence": ["screen:001-a.png", "db:SELECT → 1 row"]}],
            "findings": [], "beyond_checklist": dict.fromkeys(v.PROBES, "ok"),
            "not_checked": "n", "spend": {"actions": 1, "minutes": 1}}),
            encoding="utf-8")
        rc = v.run_gate("e1", write=True, tracker=tracker, root=root / "ev",
                        lang="en", require_db=True)
        self.assertEqual(rc, 0)
        self.assertEqual(ledger.read_text(encoding="utf-8"),
                         "- acceptance missed this one\n")
        self.assertTrue((tracker / "e1" / "acceptance-verdict.md").is_file())


class TestEvidenceOnDisk(unittest.TestCase):
    """A `screen:` prefix is spelling; the file being there is the evidence.

    Checking only the prefix let a run pay for every checklist item with a
    filename it made up — the same "checked, works" the gate already refuses,
    one colon later.
    """

    def _dir(self, *names):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        d = pathlib.Path(tmp.name)
        for n in names:
            (d / n).write_bytes(b"\x89PNG")
        return d

    def test_named_screenshot_that_exists_is_fine(self):
        d = self._dir("007-saved.png")
        self.assertEqual(v.defects(report(), evidence_dir=d), ())

    def test_named_screenshot_that_is_absent_is_a_defect(self):
        d = self._dir()   # empty
        found = v.defects(report(), evidence_dir=d)
        self.assertTrue(any("did not happen" in x for x in found), found)
        self.assertTrue(any("007-saved.png" in x for x in found), found)

    def test_a_bare_screen_prefix_is_a_defect(self):
        """The cheapest bypass: it satisfies "at least one screenshot" and
        names nothing to go looking for."""
        d = self._dir("007-saved.png")
        for bare in ("screen:", "screen:   "):
            found = v.defects(report(checklist=[
                {"item": "x", "passed": True,
                 "evidence": [bare, "db:SELECT → 1 row"]}]), evidence_dir=d)
            self.assertTrue(any("plain capture filename" in x for x in found),
                            (bare, found))

    def test_a_path_cannot_stand_in_for_a_capture(self):
        """The third defeat of this check: `evidence_dir / "/etc/hosts"` is
        `/etc/hosts` — pathlib discards the left side — so any file on the
        machine paid for a checklist item. A name is a name, not a path."""
        d = self._dir("007-saved.png")
        (d.parent / "elsewhere.png").write_bytes(b"\x89PNG")
        for path in ("/etc/hosts", "../elsewhere.png", "sub/007-saved.png",
                     "..", ".", "\\\\host\\share.png"):
            found = v.defects(report(checklist=[
                {"item": "x", "passed": True,
                 "evidence": [f"screen:{path}", "db:SELECT → 1 row"]}]),
                evidence_dir=d)
            self.assertTrue(any("plain capture filename" in x for x in found),
                            (path, found))

    def test_prose_cannot_pay_for_a_passed_item(self):
        """The fourth defeat, and the one that made the others cheap: the
        `screen:`/`db:` requirements are report-wide, while an item was
        satisfied by any non-empty string. One real capture paid for the whole
        checklist, and "checked, works" went through untouched."""
        d = self._dir("007-saved.png")
        for cheat in ("checked, works", "007-saved.png", "screenshot shows it",
                      "Screen:007-saved.png".replace("Screen:", "screen "),):
            found = v.defects(report(checklist=[
                {"item": "real", "passed": True,
                 "evidence": ["screen:007-saved.png", "db:SELECT → 1 row"]},
                {"item": "cheated", "passed": True, "evidence": [cheat]}]),
                evidence_dir=d)
            self.assertTrue(any("neither" in x for x in found), (cheat, found))

    def test_prefixes_are_matched_case_insensitively(self):
        """`Screen:` skipped every check for want of a `.lower()` — it failed
        the prefix test, so nothing downstream ever looked at it."""
        d = self._dir("007-saved.png")
        self.assertEqual(v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": ["Screen:007-saved.png", "DB:SELECT → 1 row"]}]),
            evidence_dir=d), ())
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": ["Screen:invented.png", "db:SELECT → 1 row"]}]),
            evidence_dir=d)
        self.assertTrue(any("not on disk did not happen" in x or "are not in" in x
                            for x in found), found)

    def test_the_name_must_match_the_file_on_disk_exactly(self):
        """`is_file()` is case-insensitive on macOS, which made "named exactly
        as the driver wrote it" false. The check reads the directory instead."""
        d = self._dir("007-saved.png")
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": ["screen:007-SAVED.PNG", "db:SELECT → 1 row"]}]),
            evidence_dir=d)
        self.assertTrue(any("are not in" in x for x in found), found)

    def test_the_report_cannot_pay_for_itself(self):
        """The fifth defeat, and the only one needing no filesystem access:
        the gate reads the report FROM the directory it then searches, so
        `verdict.json` is guaranteed present in every project on every run."""
        d = self._dir("007-saved.png")
        (d / v.REPORT_NAME).write_text("{}", encoding="utf-8")
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": [f"screen:{v.REPORT_NAME}", "db:SELECT → 1 row"]}]),
            evidence_dir=d)
        self.assertTrue(any("plain capture filename" in x for x in found), found)

    def test_a_directory_is_not_a_capture(self):
        """`os.listdir` counted `mkdir 008-fake.png` as evidence."""
        d = self._dir("007-saved.png")
        (d / "008-fake.png").mkdir()
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": ["screen:008-fake.png", "db:SELECT → 1 row"]}]),
            evidence_dir=d)
        self.assertTrue(any("are not in" in x for x in found), found)

    def test_a_db_row_with_no_payload_is_a_defect(self):
        """`db:` alone is the bare-prefix defeat one prefix over: it satisfies
        both the per-item rule and the report-wide db requirement."""
        d = self._dir("007-saved.png")
        for bare in ("db:", "db:   "):
            found = v.defects(report(checklist=[
                {"item": "x", "passed": True,
                 "evidence": ["screen:007-saved.png", bare]}]), evidence_dir=d)
            self.assertTrue(any("nothing after it" in x for x in found), (bare, found))

    def test_a_normalisation_difference_is_not_a_missing_capture(self):
        """`shot_name` passes non-ASCII through and `language: ru` is shipped,
        so an NFD/NFC mismatch would block a blameless run on a message that
        names a file the directory visibly contains."""
        import unicodedata
        d = self._dir(unicodedata.normalize("NFC", "009-Сохранёно.png"))
        nfd = unicodedata.normalize("NFD", "009-Сохранёно.png")
        self.assertEqual(v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": [f"screen:{nfd}", "db:SELECT → 1 row"]}]),
            evidence_dir=d), ())

    def test_each_passed_item_needs_a_capture_of_its_own(self):
        """The sixth defeat: `db:` paid for every item while the single
        report-wide `screen:` requirement was met by a screenshot hanging off
        a non-blocking `clumsy` finding. Defeat #4's shape, one prefix over."""
        d = self._dir("001-home.png")
        found = v.defects(report(
            checklist=[{"item": f"line {i}", "passed": True,
                        "evidence": ["db:checked, works"]} for i in range(3)],
            findings=[{"class": "clumsy", "what": "odd label",
                       "evidence": ["screen:001-home.png"]}]),
            evidence_dir=d)
        self.assertTrue(any("no capture of its own" in x for x in found), found)

    def test_a_db_row_is_an_extra_claim_not_a_substitute(self):
        """A capture alone is enough; a row alone is not."""
        d = self._dir("001-home.png")
        self.assertEqual(v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": ["screen:001-home.png", "db:SELECT → 1 row"]}]),
            evidence_dir=d), ())
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True, "evidence": ["db:SELECT → 1 row"]},
            {"item": "y", "passed": True, "evidence": ["screen:001-home.png"]}]),
            evidence_dir=d)
        self.assertTrue(any("no capture of its own" in x for x in found), found)

    def test_an_items_own_capture_must_itself_be_real(self):
        """The per-item rule reuses the name validation, so an item cannot pay
        itself with a malformed capture the report-wide check would refuse."""
        d = self._dir("001-home.png")
        for bad in ("screen:verdict.json", "screen:/etc/hosts", "screen:"):
            found = v.defects(report(checklist=[
                {"item": "x", "passed": True, "evidence": [bad, "db:1 row"]},
                {"item": "y", "passed": True, "evidence": ["screen:001-home.png"]}]),
                evidence_dir=d)
            self.assertTrue(any("no capture of its own" in x for x in found),
                            (bad, found))

    def test_prose_in_a_finding_is_refused_not_misread_as_a_filename(self):
        """A `clumsy` finding whose prose began "Screen: the field loses
        focus…" was parsed as a capture name and blocked the merge. Findings
        are now held to the same prefix rule, so prose is refused as prose."""
        d = self._dir("007-saved.png")
        found = v.defects(report(
            checklist=[{"item": "x", "passed": True,
                        "evidence": ["screen:007-saved.png", "db:SELECT → 1 row"]}],
            findings=[{"class": "clumsy", "what": "focus lost",
                       "evidence": ["Screen: the field loses focus after each key"]}]),
            evidence_dir=d)
        # Told it is prose, rather than hunted for on disk and reported
        # missing — which was a blameless block with a baffling message.
        self.assertTrue(any("not a plain capture filename" in x for x in found),
                        found)
        self.assertFalse(any("are not in" in x for x in found), found)

    def test_a_finding_s_evidence_is_checked_too(self):
        d = self._dir("007-saved.png")
        found = v.defects(report(findings=[
            {"class": "broken", "what": "save does nothing", "where": "form",
             "evidence": ["screen:012-invented.png"]}]), evidence_dir=d)
        self.assertTrue(any("012-invented.png" in x for x in found), found)

    def test_db_rows_are_not_checked_against_disk(self):
        """The gate has no database; only the screenshot half is verifiable.

        A `db:` line that looks exactly like a filename still passes — proving
        the check keys on the prefix, not on anything resembling a path.
        """
        d = self._dir("007-saved.png")
        found = v.defects(report(checklist=[
            {"item": "x", "passed": True,
             "evidence": ["screen:007-saved.png", "db:no-such-file.png → 1 row"]}]),
            evidence_dir=d)
        self.assertEqual(found, ())

    def test_without_a_directory_the_check_is_skipped(self):
        """Callers that do not know where evidence lives still get the rest."""
        self.assertEqual(v.defects(report()), ())

    def test_gate_blocks_on_an_invented_screenshot(self):
        d = self._dir()
        decision = v.gate(report(), evidence_dir=d)
        self.assertTrue(decision.blocked)

    def test_an_owner_override_cannot_lift_an_invented_screenshot(self):
        """Same rule as every other defect: an incomplete run is not an opinion."""
        d = self._dir()
        decision = v.gate(report(), overrides=("007-saved.png",), evidence_dir=d)
        self.assertTrue(decision.blocked)


class TestGate(unittest.TestCase):
    def test_clean_report_passes(self):
        self.assertFalse(v.gate(report()).blocked)

    def test_broken_blocks(self):
        decision = v.gate(report(findings=[
            {"class": "broken", "what": "save button does nothing",
             "evidence": ["screen:1.png"]}]))
        self.assertTrue(decision.blocked)
        self.assertEqual(len(decision.blockers), 1)

    def test_lies_blocks(self):
        decision = v.gate(report(findings=[
            {"class": "lies", "what": "says saved, database unchanged",
             "evidence": ["db:SELECT → old value"]}]))
        self.assertTrue(decision.blocked)

    def test_clumsy_does_not_block(self):
        """A gate where every class blocks becomes a gate nobody runs."""
        decision = v.gate(report(findings=[
            {"class": "clumsy", "what": "focus lost after each keystroke",
             "evidence": ["screen:1.png"]}]))
        self.assertFalse(decision.blocked)
        self.assertEqual(len(decision.advisory), 1)

    def test_defective_report_blocks_even_with_no_findings(self):
        self.assertTrue(v.gate(report(not_checked="")).blocked)

    def test_owner_override_lifts_a_blocker(self):
        finding = {"class": "broken", "what": "save button does nothing",
                   "evidence": ["screen:1.png"]}
        decision = v.gate(report(findings=[finding]),
                          overrides=("save button does nothing",))
        self.assertFalse(decision.blocked)
        self.assertEqual(len(decision.lifted), 1)

    def test_override_must_match_verbatim(self):
        decision = v.gate(
            report(findings=[{"class": "broken", "what": "save button does nothing",
                              "evidence": ["screen:1.png"]}]),
            overrides=("save button is broken",))
        self.assertTrue(decision.blocked)

    def test_override_cannot_lift_a_report_defect(self):
        """An owner may disagree with a finding. An incomplete run is not a finding."""
        decision = v.gate(
            report(not_checked="", findings=[{"class": "broken", "what": "x",
                                              "evidence": ["screen:1.png"]}]),
            overrides=("x",))
        self.assertTrue(decision.blocked)
        self.assertEqual(decision.blockers, ())
        self.assertTrue(decision.defects)


class TestOverrideFile(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as tmp:
            path = pathlib.Path(tmp) / "acceptance-override.md"
            path.write_text(text, encoding="utf-8")
            return v.read_overrides(path)

    def test_missing_file_is_no_overrides(self):
        self.assertEqual(v.read_overrides(pathlib.Path("/nope/nothing.md")), ())

    def test_english_prefix(self):
        self.assertEqual(
            self.read("- lifted by owner: save button does nothing — known, ships later\n"),
            ("save button does nothing",))

    def test_russian_prefix_is_accepted_whatever_the_language(self):
        self.assertEqual(
            self.read("- снято владельцем: кнопка не жмётся — известно\n"),
            ("кнопка не жмётся",))

    def test_reason_is_optional(self):
        self.assertEqual(self.read("- lifted by owner: something\n"), ("something",))

    def test_prose_around_the_lines_is_ignored(self):
        text = "# Overrides\n\nSome prose.\n\n- lifted by owner: x — y\n\nMore prose.\n"
        self.assertEqual(self.read(text), ("x",))


class TestTemplate(unittest.TestCase):
    def test_skeleton_parses_and_passes_its_own_gate(self):
        """The contract handed to an agent must be self-consistent, or the
        first run fights the parser instead of the feature."""
        data = dict(v.TEMPLATE, milestone="m52")
        decision = v.gate(v.parse(data))
        self.assertFalse(decision.blocked, decision.defects)

    def test_skeleton_is_valid_json(self):
        json.dumps(v.TEMPLATE)


class TestRender(unittest.TestCase):
    def test_blocked_report_says_so_in_russian(self):
        decision = v.gate(report(findings=[
            {"class": "broken", "what": "кнопка не жмётся", "evidence": ["screen:1.png"]}]))
        text = v.render(report(), decision, "ru")
        self.assertIn("ЗАБЛОКИРОВАНО", text)

    def test_clean_report_says_good_in_english(self):
        text = v.render(report(), v.gate(report()), "en")
        self.assertIn("GOOD", text)

    def test_not_checked_line_always_appears(self):
        self.assertIn("ran out of actions", v.render(report(), v.gate(report()), "en"))


if __name__ == "__main__":
    unittest.main()


class TestWorkingTree(unittest.TestCase):
    """The acceptance agent can edit code — a shell alone is enough for that.
    "You only report" is an instruction, so the gate checks rather than trusts."""

    def test_unchanged_tree_is_no_defect(self):
        self.assertEqual(v.defects(report(), tree=("abc123", "abc123", ())), ())

    def test_changed_tree_blocks(self):
        decision = v.gate(report(), tree=("abc123", "def456", ("src/cart.py",)))
        self.assertTrue(decision.blocked)
        self.assertTrue(any("changed during the acceptance run" in d for d in decision.defects))

    def test_the_defect_names_what_moved(self):
        """"The tree moved" that cannot say what moved is a block nobody can act on."""
        decision = v.gate(report(), tree=("a", "b", ("src/cart.py", "src/tax.py")))
        self.assertTrue(any("src/cart.py" in d and "src/tax.py" in d for d in decision.defects))

    def test_many_moved_paths_are_truncated(self):
        paths = tuple(f"f{i}.py" for i in range(9))
        decision = v.gate(report(), tree=("a", "b", paths))
        self.assertTrue(any("…" in d for d in decision.defects))

    def test_unfingerprintable_tree_fails_closed(self):
        """A check that could not run is not a check that passed."""
        decision = v.gate(report(), tree=("abc123", "", ()))
        self.assertTrue(decision.blocked)
        self.assertTrue(any("could not be fingerprinted" in d for d in decision.defects))

    def test_owner_override_cannot_lift_a_changed_tree(self):
        """An owner may disagree with a finding. A void run is not a finding."""
        decision = v.gate(report(), tree=("abc123", "def456", ("x.py",)), overrides=("anything",))
        self.assertTrue(decision.blocked)

    def test_no_tree_argument_means_no_check(self):
        """Projects that do not record a digest keep the previous behaviour."""
        self.assertFalse(v.gate(report()).blocked)

    def test_digest_is_stable_and_short(self):
        a, b = v.tree_digest(ROOT), v.tree_digest(ROOT)
        self.assertEqual(a, b)
        self.assertEqual(len(a), 16)


class TestTreeIgnore(unittest.TestCase):
    """Using a product mutates a repository. Found the first time this ran for
    real: a reviewer ran the suite, Python wrote a .pyc, and a run that edited
    nothing was called void."""

    def test_bare_name_matches_any_component(self):
        self.assertTrue(v._matches("src/__pycache__/cart.pyc", "__pycache__"))
        self.assertTrue(v._matches("__pycache__/x.pyc", "__pycache__"))

    def test_bare_name_does_not_match_a_substring(self):
        self.assertFalse(v._matches("src/cache/x.py", "__pycache__"))

    def test_a_glob_with_a_slash_matches_the_whole_path(self):
        self.assertTrue(v._matches("build/out.js", "build/*"))
        self.assertFalse(v._matches("src/build/out.js", "build/*"))

    def test_extension_glob(self):
        self.assertTrue(v._matches("src/a/b.pyc", "*.pyc"))

    def test_ignoring_changes_the_digest_it_reports(self):
        """The ignore list must actually reach the fingerprint, not just the
        message — otherwise a run is still voided by a stray .pyc."""
        plain = v.tree_digest(ROOT)
        wide = v.tree_digest(ROOT, ignore=("*",))
        self.assertNotEqual(plain, wide) if v.tree_state(ROOT)[1] else self.assertEqual(plain, wide)


class TestVerifiedFixed(unittest.TestCase):
    """Round >= 2 needs somewhere to say "this is fixed". Without it an agent
    files the confirmation as a `clumsy` finding — observed in a real run."""

    def test_absent_by_default(self):
        self.assertEqual(report().verified_fixed, ())

    def test_parsed_when_present(self):
        r = report(verified_fixed=["Save now writes a row", "empty name refused"])
        self.assertEqual(len(r.verified_fixed), 2)

    def test_never_blocks(self):
        self.assertFalse(v.gate(report(verified_fixed=["anything"])).blocked)

    def test_rendered_in_its_own_section(self):
        r = report(verified_fixed=["Save now writes a row"])
        text = v.render(r, v.gate(r), "en")
        self.assertIn("Fixed since the previous round", text)
        self.assertIn("Save now writes a row", text)

    def test_not_counted_as_a_finding(self):
        r = report(verified_fixed=["fixed thing"])
        self.assertEqual(v.gate(r).advisory, ())

    def test_rejects_a_non_list(self):
        with self.assertRaises(v.BadReport):
            report(verified_fixed="a string, not a list")

    def test_template_carries_the_key(self):
        self.assertIn("verified_fixed", v.TEMPLATE)
