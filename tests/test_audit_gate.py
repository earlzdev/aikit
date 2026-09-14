"""Tests for the security-audit gate (`verdict security`).

WHAT: parsing an audit report, the defect checks, and the exit code — 0 clean,
      1 exploitable found, 2 the run cannot be trusted.
WHY:  this gate is what makes "exploitable" mean something. An exploitable
      finding has to carry a proof of concept that is on disk and that the
      refuter confirmed; without that rule "exploitable" is just the hunter's
      word, which is the exact thing the audit is built not to trust.
HOW:  `python3 -m unittest discover -s tests`. Stdlib only.
"""

import importlib.machinery
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("aikit_verdict", str(ROOT / "bin" / "verdict"))
_spec = importlib.util.spec_from_loader("aikit_verdict", _loader)
v = importlib.util.module_from_spec(_spec)
sys.modules["aikit_verdict"] = v
_loader.exec_module(v)


def finding(**over):
    base = dict(**{"class": "exploitable", "severity": "critical",
                   "title": "IDOR on GET /api/orders/{id}",
                   "attacker": "any authenticated tenant",
                   "entry_point": "GET /api/orders/{id}",
                   "boundary": "tenant isolation",
                   "impact": "read another tenant's orders",
                   "poc": "006-idor.http", "refuter": "confirmed",
                   "evidence": ["db:SELECT tenant_id → tenantB, returned to tenantA"]})
    base.update(over)
    return base


def report(**over):
    data = {
        "target": "http://localhost:3000",
        "box": "black",
        "round": 1,
        "findings": [],
        "not_reached": "admin 2FA flow — could not seed a TOTP secret",
        "spend": {"requests": 61, "minutes": 12},
    }
    data.update(over)
    return v.parse_security(data)


class TestParse(unittest.TestCase):
    def test_clean_report_parses(self):
        self.assertEqual(report().target, "http://localhost:3000")

    def test_report_must_be_an_object(self):
        with self.assertRaises(v.BadReport):
            v.parse_security([1, 2, 3])

    def test_target_is_required(self):
        with self.assertRaises(v.BadReport):
            v.parse_security({"target": "  "})

    def test_empty_findings_is_valid(self):
        self.assertEqual(len(report(findings=[]).findings), 0)

    def test_unknown_class_is_rejected(self):
        with self.assertRaises(v.BadReport):
            report(findings=[finding(**{"class": "scary"})])

    def test_bad_severity_is_rejected(self):
        with self.assertRaises(v.BadReport):
            report(findings=[finding(severity="apocalyptic")])

    def test_each_required_field_must_be_present(self):
        for key in ("title", "attacker", "entry_point", "boundary", "impact"):
            with self.assertRaises(v.BadReport, msg=key):
                report(findings=[finding(**{key: ""})])

    def test_russian_class_names_parse(self):
        parsed = report(findings=[finding(**{"class": "эксплуатируется"})])
        self.assertEqual(parsed.findings[0].klass, v.EXPLOITABLE)


class TestDefects(unittest.TestCase):
    def evidence(self, tmp, *names):
        d = pathlib.Path(tmp)
        for n in names:
            (d / n).write_text("### aikit probe transcript\n> GET http://localhost:3000/x\n")
        return d

    def test_a_confirmed_exploit_with_its_poc_on_disk_has_no_defects(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.evidence(tmp, "006-idor.http")
            found = v.security_defects(report(findings=[finding()]), evidence_dir=d)
            self.assertEqual(found, ())

    def test_missing_not_reached_is_a_defect(self):
        found = v.security_defects(report(not_reached=""))
        self.assertTrue(any("could not reach" in d for d in found))

    def test_exploitable_without_poc_is_a_defect(self):
        found = v.security_defects(report(findings=[finding(poc="")]))
        self.assertTrue(any("no proof of concept" in d for d in found))

    def test_exploitable_not_confirmed_is_a_defect(self):
        found = v.security_defects(report(findings=[finding(refuter="disproven")]))
        self.assertTrue(any("did not confirm" in d for d in found))

    def test_poc_not_on_disk_is_a_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.evidence(tmp)  # empty dir
            found = v.security_defects(report(findings=[finding()]), evidence_dir=d)
            self.assertTrue(any("not in" in d and "replay" in d for d in found))

    def test_poc_with_a_path_is_a_defect(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.evidence(tmp, "006-idor.http")
            found = v.security_defects(report(findings=[finding(poc="../../etc/passwd")]),
                                       evidence_dir=d)
            self.assertTrue(any("plain transcript filename" in d for d in found))

    def test_confirmed_but_not_classed_exploitable_is_a_defect(self):
        """A refuter 'confirmed' on a non-exploitable finding is an unreconciled report."""
        with tempfile.TemporaryDirectory() as tmp:
            d = self.evidence(tmp, "006-idor.http")
            found = v.security_defects(
                report(findings=[finding(**{"class": "hardening", "refuter": "confirmed"})]),
                evidence_dir=d)
            self.assertTrue(any("is not classed" in d for d in found))

    def test_unproven_finding_needs_no_poc(self):
        f = finding(**{"class": "unproven", "refuter": "", "poc": ""})
        self.assertEqual(v.security_defects(report(findings=[f])), ())

    def test_tree_moved_is_a_defect(self):
        found = v.security_defects(report(), tree=("aaa", "bbb", ("src/app.py",)))
        self.assertTrue(any("changed during the audit" in d for d in found))

    def test_untrackable_tree_fails_closed(self):
        found = v.security_defects(report(), tree=("aaa", "", ()))
        self.assertTrue(any("could not be fingerprinted" in d for d in found))


class TestGateDecision(unittest.TestCase):
    def poc_dir(self, tmp):
        d = pathlib.Path(tmp)
        (d / "006-idor.http").write_text("### t\n> GET http://localhost:3000/x\n")
        return d

    def test_confirmed_exploit_blocks(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.poc_dir(tmp)
            decision = v.security_gate(report(findings=[finding()]), evidence_dir=d)
            self.assertTrue(decision.blocked)
            self.assertEqual(len(decision.exploitable), 1)
            self.assertEqual(decision.defects, ())

    def test_clean_report_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            decision = v.security_gate(report(findings=[]), evidence_dir=pathlib.Path(tmp))
            self.assertFalse(decision.blocked)

    def test_only_hardening_does_not_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = finding(**{"class": "hardening", "severity": "low", "refuter": "", "poc": ""})
            decision = v.security_gate(report(findings=[f]), evidence_dir=pathlib.Path(tmp))
            self.assertFalse(decision.blocked)
            self.assertEqual(len(decision.hardening), 1)


class TestRunGateExitCodes(unittest.TestCase):
    def write(self, root, run, data):
        d = pathlib.Path(root) / run
        d.mkdir(parents=True, exist_ok=True)
        (d / v.SEC_REPORT_NAME).write_text(json.dumps(data), encoding="utf-8")
        return d

    def full(self, **over):
        data = {"target": "http://localhost:3000", "box": "black", "round": 1,
                "findings": [], "not_reached": "x", "spend": {"requests": 1, "minutes": 1}}
        data.update(over)
        return data

    def test_clean_returns_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "audit", self.full())
            self.assertEqual(v.run_security_gate("audit", write=False,
                             tracker=pathlib.Path(tmp), root=pathlib.Path(tmp), lang="en"), 0)

    def test_confirmed_exploit_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = self.write(tmp, "audit", self.full(findings=[finding()]))
            (d / "006-idor.http").write_text("### t\n> GET http://localhost:3000/x\n")
            self.assertEqual(v.run_security_gate("audit", write=False,
                             tracker=pathlib.Path(tmp), root=pathlib.Path(tmp), lang="en"), 1)

    def test_defective_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "audit", self.full(not_reached=""))  # missing mandatory line
            self.assertEqual(v.run_security_gate("audit", write=False,
                             tracker=pathlib.Path(tmp), root=pathlib.Path(tmp), lang="en"), 2)

    def test_missing_report_returns_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(v.run_security_gate("nope", write=False,
                             tracker=pathlib.Path(tmp), root=pathlib.Path(tmp), lang="en"), 2)

    def test_write_emits_a_verdict_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.write(tmp, "audit", self.full())
            v.run_security_gate("audit", write=True, tracker=pathlib.Path(tmp),
                                root=pathlib.Path(tmp), lang="en")
            self.assertTrue((pathlib.Path(tmp) / "audit" / "audit-verdict.md").is_file())


if __name__ == "__main__":
    unittest.main()
