"""Broker scope, protocol, and actual subprocess dispatch with an offline CLI fixture."""
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
from unittest.mock import patch

from test_codex_kit import FAKE, Fixture

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("aikit_mcp_tests", str(ROOT / "bin/codex-mcp"))
spec = importlib.util.spec_from_loader(loader.name, loader)
mcp = importlib.util.module_from_spec(spec)
loader.exec_module(mcp)


class TestBroker(Fixture):
    def setUp(self):
        super().setUp()
        executable = self.base / "codex"
        executable.write_text(FAKE)
        executable.chmod(0o755)
        self.env = patch.dict(os.environ, {"PATH": str(self.base) + os.pathsep + os.environ["PATH"]})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.broker = mcp.Broker(self.project, self.project / ".acceptance")

    def test_role_runs_in_bound_project_and_resumes_exact_builder(self):
        first = self.broker.run_role({"role": "implementer", "brief": "original task"})
        self.assertEqual(first["status"], "completed")
        second = self.broker.run_role({"role": "implementer", "brief": "fix finding", "resume": first["run_id"]})
        self.assertEqual(first["session_id"], second["session_id"])
        output = Path(second["state_path"]).parent
        invocation = json.loads((output / "invocation.json").read_text())
        self.assertEqual(invocation["cwd"], str(self.project))
        self.assertEqual(invocation["brief"], "fix finding")
        self.assertIn('default_permissions=":workspace"', invocation["args"])
        self.assertTrue(any("Do not stage, stash, commit" in value for value in invocation["args"]))

    def test_reviewers_cannot_resume_and_failure_is_tool_error(self):
        first = self.broker.run_role({"role": "reviewer", "brief": "review only"})
        with self.assertRaises(ValueError):
            self.broker.run_role({"role": "reviewer", "brief": "review again", "resume": first["run_id"]})
        result = self.broker.request("tools/call", {"name": "run_role", "arguments": {"role": "implementer", "brief": "fail"}})
        self.assertTrue(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"])["exit_code"], 7)

    def test_no_arbitrary_workspace_executable_or_publish_mode(self):
        for key, value in (("project", "/other"), ("codex", "/evil"), ("git_mode", "checkpoint"), ("command", "anything")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.broker.run_role({"role": "implementer", "brief": "build", key: value})
        with self.assertRaises(ValueError):
            self.broker.run_role({"role": "implementer", "brief": "fix", "resume": "../../elsewhere"})

    def test_protocol_and_timeout_validation(self):
        initialized = self.broker.request("initialize", {"protocolVersion": "2025-03-26"})
        self.assertEqual(initialized["protocolVersion"], "2025-03-26")
        tools = self.broker.request("tools/list", {})["tools"]
        self.assertEqual([tool["name"] for tool in tools], ["run_role"])
        for timeout in (True, 0, 601, "10"):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                self.broker.run_role({"role": "implementer", "brief": "build", "timeout": timeout})
