"""Tests for the acceptance driver's core.

WHAT: the parts of `bin/drive` that decide whether a run can be trusted —
      budgets, evidence naming, honest truncation, target parsing.
WHY:  these are the rules; the Playwright calls are just how they reach a page.
      Keeping them separable is what makes them testable at all, and an
      untested budget is a budget that quietly does not apply.
HOW:  `python3 -m unittest discover -s tests`. No browser, no network.
"""

import importlib.machinery
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("aikit_drive", str(ROOT / "bin" / "drive"))
_spec = importlib.util.spec_from_loader("aikit_drive", _loader)
d = importlib.util.module_from_spec(_spec)
sys.modules["aikit_drive"] = d
_loader.exec_module(d)


def run(**over):
    base = dict(milestone="m52", cdp="http://127.0.0.1:9222", started=1_000_000.0,
                max_actions=3, minutes=10)
    base.update(over)
    return d.Run(**base)


class TestBudget(unittest.TestCase):
    def test_charge_counts_actions(self):
        r = run()
        r.charge(now=r.started)
        r.charge(now=r.started)
        self.assertEqual(r.actions, 2)

    def test_action_cap_raises_before_acting(self):
        """Checked BEFORE the action: a run that clicks and only then notices
        it is over budget has changed the stand without reporting what it saw."""
        r = run(max_actions=1)
        r.charge(now=r.started)
        with self.assertRaises(d.Exhausted):
            r.charge(now=r.started)
        self.assertEqual(r.actions, 1)

    def test_time_cap_raises(self):
        r = run(minutes=5)
        with self.assertRaises(d.Exhausted) as caught:
            r.charge(now=r.started + 5 * 60)
        self.assertIn("time budget", str(caught.exception))

    def test_exhausted_message_says_could_not_not_good(self):
        r = run(max_actions=0)
        with self.assertRaises(d.Exhausted) as caught:
            r.charge(now=r.started)
        self.assertIn("could not", str(caught.exception))

    def test_step_advances_with_actions(self):
        r = run()
        r.charge(now=r.started)
        r.charge(now=r.started)
        self.assertEqual(r.step, 2)


class TestState(unittest.TestCase):
    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            original = run(actions=7, step=7)
            d.save(root, original)
            self.assertEqual(d.load(root).actions, 7)
            self.assertEqual(d.load(root).milestone, "m52")

    def test_load_without_a_run_exits_with_advice(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as caught:
                d.load(pathlib.Path(tmp))
            self.assertIn("drive begin", str(caught.exception))


class TestShotName(unittest.TestCase):
    def test_ordered_and_slugged(self):
        self.assertEqual(d.shot_name(run(step=7), "saved the client"),
                         "007-saved-the-client.png")

    def test_sequence_is_zero_padded_so_evidence_sorts(self):
        self.assertEqual(d.shot_name(run(step=1), "a"), "001-a.png")
        self.assertEqual(d.shot_name(run(step=120), "a"), "120-a.png")

    def test_empty_name_still_produces_a_file(self):
        self.assertEqual(d.shot_name(run(step=3), ""), "003-step.png")

    def test_unsafe_characters_do_not_reach_the_filesystem(self):
        self.assertEqual(d.shot_name(run(step=1), "../../etc/passwd"),
                         "001-etc-passwd.png")


class TestTarget(unittest.TestCase):
    def test_role_and_name(self):
        self.assertEqual(d.parse_target("button=Save"), ("button", "Save"))

    def test_css_escape_hatch(self):
        self.assertEqual(d.parse_target("css=input[type=file]"),
                         ("css", "input[type=file]"))

    def test_missing_equals_is_rejected_with_the_valid_forms(self):
        with self.assertRaises(d.BadTarget) as caught:
            d.parse_target("Save")
        self.assertIn("role=name", str(caught.exception))

    def test_empty_side_is_rejected(self):
        with self.assertRaises(d.BadTarget):
            d.parse_target("button=")


class TestTree(unittest.TestCase):
    def test_short_tree_is_untouched(self):
        self.assertEqual(d.truncate_tree("a\nb\nc", limit=10), "a\nb\nc")

    def test_truncation_says_how_much_it_hid(self):
        """Silent truncation makes the agent believe an element is absent when
        it is merely below the fold."""
        text = "\n".join(str(i) for i in range(50))
        out = d.truncate_tree(text, limit=10)
        self.assertIn("40 more lines hidden", out)
        self.assertEqual(len(out.splitlines()), 11)

    def test_flatten_renders_role_and_name(self):
        snapshot = {"role": "WebArea", "name": "Home", "children": [
            {"role": "button", "name": "Save"},
            {"role": "textbox", "name": "Title", "value": "hi"},
        ]}
        lines = d.flatten(snapshot)
        self.assertEqual(lines[0], 'WebArea "Home"')
        self.assertEqual(lines[1], '  button "Save"')
        self.assertIn("textbox \"Title\" = 'hi'", lines[2])

    def test_flatten_tolerates_junk(self):
        self.assertEqual(d.flatten(None), [])
        self.assertEqual(d.flatten({}), [])


class TestCli(unittest.TestCase):
    def test_begin_then_end_needs_no_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["--evidence-root", tmp]
            self.assertEqual(d.main(argv + ["begin", "m52", "--max-actions", "5"]), 0)
            self.assertTrue((pathlib.Path(tmp) / "m52").is_dir())
            self.assertEqual(d.main(argv + ["end"]), 0)
            self.assertFalse(d.state_path(pathlib.Path(tmp)).exists())

    def test_action_without_begin_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                d.main(["--evidence-root", tmp, "click", "button=Save"])

    def test_spent_budget_returns_2_without_opening_a_browser(self):
        """The refusal must happen before any browser is touched, or a run with
        no budget left still mutates the stand."""
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            d.save(root, run(max_actions=1, actions=1))
            self.assertEqual(d.main(["--evidence-root", tmp, "click", "button=Save"]), 2)


if __name__ == "__main__":
    unittest.main()
