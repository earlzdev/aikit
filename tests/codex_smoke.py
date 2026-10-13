#!/usr/bin/env python3
"""Opt-in local CLI smoke checks: no inference, network, auth, or global install.

Run `python3 tests/codex_smoke.py`. It uses a disposable CODEX_HOME and project.
Sandbox startup may require running outside another nested sandbox.
"""
import json
import http.server
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="aikit-codex-smoke-") as temporary:
        base = Path(temporary)
        codex_home = base / "codex-home"
        codex_home.mkdir(mode=0o700)
        env = dict(os.environ, CODEX_HOME=str(codex_home))
        env.pop("CODEX_API_KEY", None)
        env.pop("OPENAI_API_KEY", None)

        def call(*args, cwd=ROOT, input=None):
            result = subprocess.run(args, cwd=cwd, env=env, capture_output=True,
                                    text=True, timeout=60, input=input)
            if result.returncode:
                raise RuntimeError(f"{args[0:3]} exited {result.returncode}: {result.stderr[-2000:]} {result.stdout[-1000:]}")
            return result.stdout

        distribution = base / "distribution"
        call(sys.executable, str(ROOT / "bin/codex-kit"), "build", "--output", str(distribution))
        call("codex", "--no-daemon", "plugin", "marketplace", "add", str(distribution), "--json")
        call("codex", "--no-daemon", "plugin", "add", "aikit@aikit-local", "--json")
        listing = call("codex", "--no-daemon", "plugin", "list", "--marketplace", "aikit-local", "--json")
        if "aikit" not in listing:
            raise RuntimeError("installed plugin was not discoverable")
        print("PASS: generated package installs in a disposable Codex home")

        project = base / "project"
        project.mkdir()
        sentinel = project / "source.txt"
        sentinel.write_text("unchanged")
        call("git", "init", "-q", str(project))
        (project / ".gitignore").write_text(".acceptance/\n")
        handshake = "\n".join(json.dumps(request) for request in (
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        )) + "\n"
        responses = call(sys.executable, str(distribution / "aikit/bin/codex-mcp"),
                         "--project", str(project), input=handshake, cwd=project)
        listed = json.loads(responses.splitlines()[1])["result"]["tools"]
        if [tool["name"] for tool in listed] != ["run_role"]:
            raise RuntimeError("packaged role broker was not usable")
        print("PASS: packaged project-bound role broker initializes and exposes only role dispatch")
        scratch = base / "scratch"
        scratch.mkdir()
        probe = '''import errno, pathlib, sys
p = pathlib.Path("source.txt")
assert p.read_text() == "unchanged"
pathlib.Path(sys.argv[1], "verification-cache").write_text("scratch is writable")
try:
    p.write_text("changed")
except OSError as error:
    if error.errno not in (errno.EACCES, errno.EPERM, errno.EROFS):
        raise
    print("source write denied")
    sys.exit(0)
sys.exit("read-only sandbox allowed a source write")
'''
        call("codex", "--no-daemon", "sandbox", "--permission-profile", "aikit-reviewer",
             "-c", 'permissions.aikit-reviewer.extends=":read-only"',
             "-c", 'permissions.aikit-reviewer.filesystem={' + json.dumps(str(scratch)) + '="write"}',
             "-C", str(project), "--", sys.executable, "-c", probe, str(scratch), cwd=project)
        if sentinel.read_text() != "unchanged":
            raise RuntimeError("source changed in sandbox probe")
        print("PASS: real Codex reviewer profile denies source writes and permits verification scratch")
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"dummy-stand")

            def log_message(self, *_args):
                pass

        server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            for role, parent in (("acceptance", ":workspace"), ("security-hunter", ":workspace"),
                                 ("security-refuter", ":read-only")):
                profile = "aikit-" + role
                call("codex", "--no-daemon", "sandbox", "--permission-profile", profile,
                     "-c", f'permissions.{profile}.extends="{parent}"',
                     "-c", f"permissions.{profile}.network.enabled=true",
                     "-C", str(project), "--", sys.executable, "-c",
                     "import urllib.request,sys; assert urllib.request.urlopen(sys.argv[1],timeout=5).read()==b'dummy-stand'",
                     url, cwd=project)
                print(f"PASS: real {role} profile reaches disposable localhost stand")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        print("No model calls were made; full inference-driven pipeline remains a separate check.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"[codex-smoke] {exc}", file=sys.stderr)
        raise SystemExit(1)
