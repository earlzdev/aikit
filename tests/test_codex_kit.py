"""Codex adapter contracts; no API calls, commits or user configuration writes."""
import argparse
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("aikit_codex_kit", str(ROOT / "bin/codex-kit"))
spec = importlib.util.spec_from_loader(loader.name, loader)
kit = importlib.util.module_from_spec(spec)
loader.exec_module(kit)

FAKE = '''#!/usr/bin/env python3
import json, pathlib, subprocess, sys, time
args = sys.argv[1:]
brief = sys.stdin.read()
out = pathlib.Path(args[args.index("-o") + 1])
(out.parent / "invocation.json").write_text(json.dumps({"args": args, "brief": brief, "cwd": str(pathlib.Path.cwd())}))
if brief == "timeout":
    subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    time.sleep(30)
if brief == "fail":
    sys.exit(7)
thread = args[-2] if "resume" in args else "12345678-1234-1234-1234-123456789abc"
print(json.dumps({"type": "thread.started", "thread_id": thread}), flush=True)
if brief != "missing report":
    out.write_text("VERDICT: CLEAN\\n")
print(json.dumps({"type": "turn.failed" if brief == "failed event" else "turn.completed"}))
'''


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.project = self.base / "project"
        self.project.mkdir()
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)
        (self.project / ".gitignore").write_text(".acceptance/\n")
        self.source = self.project / "source.txt"
        self.source.write_text("original\n")
        # Index only in the disposable fixture; never commit, even in fixtures.
        subprocess.run(["git", "add", "."], cwd=self.project, check=True)


class TestSnapshots(Fixture):
    def test_uncommitted_step_includes_new_deleted_and_binary_files(self):
        before = kit.capture(self.project)
        index = (self.project / ".git/index").read_bytes()
        self.source.unlink()
        (self.project / "new file.txt").write_text("new\n")
        (self.project / "binary").write_bytes(b"\0\xff")
        after = kit.capture(self.project)
        diff = kit.content_diff(before, after)
        self.assertIn("deleted file", diff)
        self.assertIn("new file.txt", diff)
        self.assertIn("binary content", diff)
        self.assertEqual((self.project / ".git/index").read_bytes(), index)
        self.assertIsNone(kit.head(self.project))

    def test_second_step_does_not_re_review_first_step(self):
        self.source.write_text("first step\n")
        before = kit.capture(self.project)
        (self.project / "second.txt").write_text("second step\n")
        diff = kit.content_diff(before, kit.capture(self.project))
        self.assertNotIn("source.txt", diff)
        self.assertIn("second.txt", diff)

    def test_ignore_evidence_but_include_untracked_content_edits(self):
        evidence = self.project / ".acceptance"
        evidence.mkdir()
        (evidence / "shot.png").write_bytes(b"image")
        extra = self.project / "extra"
        extra.write_text("a\n")
        before = kit.capture(self.project)
        extra.write_text("b\n")
        diff = kit.content_diff(before, kit.capture(self.project))
        self.assertNotIn("shot.png", diff)
        self.assertIn("-a\n+b\n", diff)

    def test_mode_and_symlink_changes(self):
        before = kit.capture(self.project)
        self.source.chmod(0o755)
        (self.project / "link").symlink_to("/outside/not-read")
        diff = kit.content_diff(before, kit.capture(self.project))
        self.assertIn("100644 file -> 100755 file", diff)
        self.assertIn("new symlink mode 120000", diff)

    def test_output_must_be_ignored_or_outside_project(self):
        with self.assertRaises(ValueError):
            kit.safe_artifact(self.project, self.project / "evidence")
        self.assertEqual(kit.safe_artifact(self.project, self.project / ".acceptance/run"),
                         self.project / ".acceptance/run")
        self.assertEqual(kit.safe_artifact(self.project, self.base / "evidence"), self.base / "evidence")

    def test_ignored_directory_with_forced_tracked_file_is_not_writable_evidence(self):
        evidence = self.project / ".acceptance"
        evidence.mkdir()
        (evidence / "tracked.txt").write_text("do not grant write access")
        subprocess.run(["git", "add", "-f", ".acceptance/tracked.txt"], cwd=self.project, check=True)
        with self.assertRaises(ValueError):
            kit.safe_artifact(self.project, evidence)

    def test_snapshot_never_overwrites_or_accepts_other_project(self):
        baseline = self.base / "before.json"
        self.assertEqual(kit.main(["snapshot", "--project", str(self.project), "--output", str(baseline)]), 0)
        self.assertEqual(kit.main(["snapshot", "--project", str(self.project), "--output", str(baseline)]), 2)
        contents = json.loads(baseline.read_text())
        contents["project"] = "/other"
        baseline.write_text(json.dumps(contents))
        self.assertEqual(kit.main(["diff", "--project", str(self.project), "--baseline", str(baseline)]), 2)


class TestRuns(Fixture):
    def setUp(self):
        super().setUp()
        self.fake = self.base / "fake-codex"
        self.fake.write_text(FAKE)
        self.fake.chmod(0o755)
        self.brief = self.base / "brief.txt"
        self.brief.write_text("original task, verbatim")

    def args(self, **changes):
        values = dict(role="implementer", project=self.project, output=self.base / "build",
                      brief=self.brief, resume=None, model="codex-model", git_mode="local",
                      timeout=5, codex=str(self.fake), evidence_root=None)
        values.update(changes)
        return argparse.Namespace(**values)

    def test_resume_holds_exact_builder_and_task(self):
        first = self.args()
        self.assertEqual(kit.run(first), 0)
        state = json.loads((first.output / "state.json").read_text())
        self.brief.write_text("fix this exact finding")
        second = self.args(output=self.base / "fix", resume=first.output)
        self.assertEqual(kit.run(second), 0)
        call = json.loads((second.output / "invocation.json").read_text())
        self.assertIn("resume", call["args"])
        self.assertEqual(call["args"][-2], state["session_id"])
        self.assertEqual(call["brief"], "fix this exact finding")
        self.assertEqual(call["cwd"], str(self.project))

    def test_reviewers_are_fresh_and_sandboxed_without_escalation(self):
        args = self.args(role="reviewer")
        self.assertEqual(kit.run(args), 0)
        call = json.loads((args.output / "invocation.json").read_text())["args"]
        self.assertIn('permissions.aikit-reviewer.extends=":read-only"', call)
        self.assertIn('approval_policy="never"', call)
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", call)
        with self.assertRaises(ValueError):
            kit.run(self.args(role="reviewer", resume=args.output, output=self.base / "again"))

    def test_acceptance_starts_without_project_instruction_loading(self):
        args = self.args(role="acceptance")
        self.assertEqual(kit.run(args), 0)
        call = json.loads((args.output / "invocation.json").read_text())
        self.assertIn("project_doc_max_bytes=0", call["args"])
        self.assertNotIn("resume", call["args"])
        self.assertEqual(call["brief"], self.brief.read_text())
        self.assertIn('permissions.aikit-acceptance.network.enabled=true', call['args'])

    def test_failed_and_missing_reports_fail_closed(self):
        for message, expected in (("fail", 7), ("missing report", 1), ("failed event", 1)):
            with self.subTest(message=message):
                self.brief.write_text(message)
                args = self.args(output=self.base / message)
                self.assertEqual(kit.run(args), expected)
                self.assertNotEqual(json.loads((args.output / "state.json").read_text())["status"], "completed")
                with self.assertRaises(ValueError):
                    kit.run(self.args(output=self.base / (message + "-resume"), resume=args.output))

    def test_timeout_stops_worker(self):
        self.brief.write_text("timeout")
        args = self.args(timeout=0.2)
        self.assertEqual(kit.run(args), 124)
        self.assertEqual(json.loads((args.output / "state.json").read_text())["status"], "timed_out")

    def test_resume_cannot_change_role_project_model_or_git_mode(self):
        first = self.args()
        kit.run(first)
        for field, value in (("role", "security-hunter"), ("model", "different-model"), ("git_mode", "checkpoint")):
            with self.subTest(field=field), self.assertRaises(ValueError):
                kit.run(self.args(output=self.base / field, resume=first.output, **{field: value}))

    def test_rejects_claude_alias_and_existing_output(self):
        with self.assertRaises(ValueError):
            kit.run(self.args(model="sonnet"))
        self.assertFalse((self.base / "build").exists())
        kit.run(self.args())
        with self.assertRaises(FileExistsError):
            kit.run(self.args())

    def test_project_runtime_config_fails_closed(self):
        config = self.project / ".codex/config.toml"
        config.parent.mkdir()
        config.write_text('[mcp_servers.unsafe]\ncommand="anything"\n')
        with self.assertRaises(ValueError):
            kit.run(self.args())
        self.assertFalse((self.base / "build").exists())

    def test_refuter_requires_evidence_and_source_readonly_profile(self):
        with self.assertRaises(ValueError):
            kit.run(self.args(role="security-refuter"))
        evidence = self.project / ".acceptance"
        evidence.mkdir()
        args = self.args(role="security-refuter", evidence_root=evidence)
        self.assertEqual(kit.run(args), 0)
        call = json.loads((args.output / "invocation.json").read_text())["args"]
        self.assertIn('permissions.aikit-security-refuter.extends=":read-only"', call)
        self.assertIn('permissions.aikit-security-refuter.network.enabled=true', call)
        self.assertTrue(any(str(evidence) in value for value in call if "filesystem=" in value))


class TestBuild(unittest.TestCase):
    def test_package_is_self_contained_and_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "distribution"
            package = kit.build(output)
            self.assertEqual(len(list((package / "skills").glob("*/SKILL.md"))), 6)
            self.assertEqual(len(list((package / "agents").glob("*.md"))), 5)
            self.assertTrue((package / "docs/codex-runtime.md").is_file())
            self.assertTrue((package / "bin/verdict").is_file())
            for skill in (ROOT / "skills").glob("*/SKILL.md"):
                self.assertEqual(skill.read_bytes(), (package / skill.relative_to(ROOT)).read_bytes())
            manifest = json.loads((package / "plugin.json").read_text())
            self.assertEqual(manifest["name"], "aikit")
            marketplace = json.loads((output / ".agents/plugins/marketplace.json").read_text())
            source = marketplace["plugins"][0]["source"]["path"]
            self.assertEqual((output / source).resolve(), package)
            with self.assertRaises(ValueError):
                kit.build(output)
            result = subprocess.run([sys.executable, str(package / "bin/codex-kit"), "--help"], capture_output=True)
            self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
