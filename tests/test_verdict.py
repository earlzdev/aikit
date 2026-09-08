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
        "milestone": "e52",
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
        self.assertEqual(report().milestone, "e52")

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
        self.assertEqual(found, ())

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
        data = dict(v.TEMPLATE, milestone="e52")
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
    """The acceptance agent can edit code — it holds every tool the project has.
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
