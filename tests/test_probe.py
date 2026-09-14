"""Tests for the security-audit hands and the fence.

WHAT: the parts of `bin/probe` that decide whether a request may be sent at all
      (the scope allowlist, loopback detection), whether it may still be sent
      (the budget), and whether a proof of concept round-trips (transcript
      serialise/parse). The socket itself is not exercised — the rules above it
      are what make a run trustworthy.
WHY:  the fence is the whole safety story. "Only attack the stand" in a prompt
      is a wish; a request outside scope that never opens a socket is a fact.
      An untested fence is a fence that quietly lets everything through.
HOW:  `python3 -m unittest discover -s tests`. No browser, no network.
"""

import importlib.machinery
import importlib.util
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
_loader = importlib.machinery.SourceFileLoader("aikit_probe", str(ROOT / "bin" / "probe"))
_spec = importlib.util.spec_from_loader("aikit_probe", _loader)
p = importlib.util.module_from_spec(_spec)
sys.modules["aikit_probe"] = p
_loader.exec_module(p)


def run(**over):
    base = dict(run="audit", started=1_000_000.0, max_requests=3, minutes=10,
                targets=["http://localhost:3000"], authorized=False)
    base.update(over)
    return p.Run(**base)


class TestTargetParsing(unittest.TestCase):
    def test_full_url(self):
        t = p.parse_target("http://localhost:3000/api")
        self.assertEqual((t.host, t.port, t.path, t.scheme), ("localhost", 3000, "/api", "http"))

    def test_bare_host_port_has_no_scheme(self):
        t = p.parse_target("10.0.0.5:8080")
        self.assertEqual((t.host, t.port, t.scheme), ("10.0.0.5", 8080, ""))

    def test_empty_target_is_rejected(self):
        with self.assertRaises(p.OutOfScope):
            p.parse_target("   ")

    def test_split_url_fills_default_port(self):
        self.assertEqual(p.split_url("http://localhost/x"), ("http", "localhost", 80, "/x"))
        self.assertEqual(p.split_url("https://localhost/x")[2], 443)

    def test_split_url_requires_absolute(self):
        with self.assertRaises(p.OutOfScope):
            p.split_url("/api/orders/1")


class TestLoopback(unittest.TestCase):
    def test_localhost_and_127_are_loopback(self):
        self.assertTrue(p.is_loopback("localhost"))
        self.assertTrue(p.is_loopback("127.0.0.1"))
        self.assertTrue(p.is_loopback("127.9.9.9"))
        self.assertTrue(p.is_loopback("::1"))

    def test_lan_and_public_are_not_loopback(self):
        self.assertFalse(p.is_loopback("192.168.1.10"))
        self.assertFalse(p.is_loopback("10.0.0.5"))
        self.assertFalse(p.is_loopback("example.com"))


class TestFence(unittest.TestCase):
    def targets(self, *specs):
        return tuple(p.parse_target(s) for s in specs)

    def test_in_scope_passes(self):
        p.check_scope("http://localhost:3000/api/x", self.targets("http://localhost:3000"), False)

    def test_wrong_port_is_out_of_scope(self):
        with self.assertRaises(p.OutOfScope):
            p.check_scope("http://localhost:9999/x", self.targets("http://localhost:3000"), False)

    def test_wrong_host_is_out_of_scope(self):
        with self.assertRaises(p.OutOfScope) as caught:
            p.check_scope("http://evil.example.com/x",
                          self.targets("http://localhost:3000"), True)
        self.assertIn("not in scope", str(caught.exception))

    def test_path_prefix_narrows_scope(self):
        tg = self.targets("http://localhost:3000/api")
        p.check_scope("http://localhost:3000/api/orders", tg, False)
        with self.assertRaises(p.OutOfScope):
            p.check_scope("http://localhost:3000/admin", tg, False)

    def test_bare_host_port_matches_either_scheme(self):
        tg = self.targets("localhost:3000")
        p.check_scope("http://localhost:3000/x", tg, False)
        p.check_scope("https://localhost:3000/x", tg, False)

    def test_non_loopback_needs_authorization(self):
        """Decision 1: a LAN or public target is refused unless the owner attested."""
        tg = self.targets("http://192.168.1.10:8080")
        with self.assertRaises(p.OutOfScope) as caught:
            p.check_scope("http://192.168.1.10:8080/x", tg, False)
        self.assertIn("not authorized", str(caught.exception))
        # …and passes once authorized.
        p.check_scope("http://192.168.1.10:8080/x", tg, True)


class TestBudget(unittest.TestCase):
    def test_charge_counts_requests(self):
        r = run()
        r.charge(now=r.started)
        r.charge(now=r.started)
        self.assertEqual((r.requests, r.seq), (2, 2))

    def test_request_cap_raises_before_sending(self):
        r = run(max_requests=1)
        r.charge(now=r.started)
        with self.assertRaises(p.Exhausted):
            r.charge(now=r.started)
        self.assertEqual(r.requests, 1)

    def test_time_cap_raises(self):
        r = run(minutes=5)
        with self.assertRaises(p.Exhausted) as caught:
            r.charge(now=r.started + 5 * 60)
        self.assertIn("time budget", str(caught.exception))

    def test_exhausted_says_could_not_not_clean(self):
        r = run(max_requests=0)
        with self.assertRaises(p.Exhausted) as caught:
            r.charge(now=r.started)
        self.assertIn("could not", str(caught.exception))


class TestRoles(unittest.TestCase):
    def test_role_is_created_and_persisted(self):
        r = run()
        role = r.role("tenantA")
        role.headers["Authorization"] = "Bearer x"
        r.put_role("tenantA", role)
        self.assertEqual(r.role("tenantA").headers["Authorization"], "Bearer x")

    def test_cookies_round_trip_through_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            r = run()
            role = r.role("t")
            role.cookies["session"] = "abc"
            r.put_role("t", role)
            p.save(root, r)
            self.assertEqual(p.load(root).role("t").cookies["session"], "abc")


class TestCookies(unittest.TestCase):
    def test_set_cookie_keeps_pair_drops_attributes(self):
        jar = {}
        p.merge_set_cookie(jar, ["session=abc; Path=/; HttpOnly", "csrf=z; Secure"])
        self.assertEqual(jar, {"session": "abc", "csrf": "z"})

    def test_cookie_header_joins(self):
        self.assertEqual(p.cookie_header({"a": "1", "b": "2"}), "a=1; b=2")


class TestTranscript(unittest.TestCase):
    def sample(self, **over):
        base = dict(method="POST", url="http://localhost:3000/login",
                    req_headers={"Content-Type": "application/json", "Cookie": "s=1"},
                    req_body='{"u":"a"}', status=200, reason="OK",
                    resp_headers={"Set-Cookie": "s=2"}, resp_body="<html>ok</html>",
                    truncated=0, role="tenantA")
        base.update(over)
        return p.Exchange(**base)

    def test_request_half_round_trips(self):
        """`replay` must reconstruct exactly the request it sends again."""
        text = p.render_transcript(self.sample())
        method, url, headers, body = p.parse_request(text)
        self.assertEqual(method, "POST")
        self.assertEqual(url, "http://localhost:3000/login")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(headers["Cookie"], "s=1")
        self.assertEqual(body, '{"u":"a"}')

    def test_empty_body_round_trips(self):
        text = p.render_transcript(self.sample(method="GET", req_body="", req_headers={}))
        method, _url, _headers, body = p.parse_request(text)
        self.assertEqual((method, body), ("GET", ""))

    def test_multiline_body_round_trips(self):
        text = p.render_transcript(self.sample(req_body="line1\nline2\nline3"))
        _, _, _, body = p.parse_request(text)
        self.assertEqual(body, "line1\nline2\nline3")

    def test_missing_request_line_is_rejected(self):
        with self.assertRaises(p.BadTranscript):
            p.parse_request("< 200 OK\n< body")

    def test_response_lines_are_ignored_by_parse(self):
        text = p.render_transcript(self.sample(resp_body="GET http://evil/ should not be parsed"))
        method, url, _, _ = p.parse_request(text)
        self.assertEqual((method, url), ("POST", "http://localhost:3000/login"))


class TestTranscriptName(unittest.TestCase):
    def test_ordered_and_slugged(self):
        self.assertEqual(p.transcript_name(run(seq=6), "idor on orders"), "006-idor-on-orders.http")

    def test_unsafe_characters_do_not_reach_the_filesystem(self):
        self.assertEqual(p.transcript_name(run(seq=1), "../../etc/passwd"), "001-etc-passwd.http")

    def test_empty_name_still_produces_a_file(self):
        self.assertEqual(p.transcript_name(run(seq=2), ""), "002-req.http")


class TestCli(unittest.TestCase):
    def test_begin_then_end_needs_no_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["--evidence-root", tmp]
            self.assertEqual(p.main(argv + ["begin", "audit", "--target",
                                            "http://localhost:3000", "--requests", "5"]), 0)
            self.assertTrue((pathlib.Path(tmp) / "audit").is_dir())
            self.assertEqual(p.main(argv + ["end"]), 0)
            self.assertFalse(p.state_path(pathlib.Path(tmp)).exists())

    def test_begin_refuses_non_loopback_without_authorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as caught:
                p.main(["--evidence-root", tmp, "begin", "audit",
                        "--target", "http://192.168.1.10:8080"])
            self.assertIn("authorized", str(caught.exception))

    def test_begin_allows_non_loopback_with_authorized(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(p.main(["--evidence-root", tmp, "begin", "audit",
                                     "--target", "http://192.168.1.10:8080", "--authorized"]), 0)

    def test_request_without_begin_exits(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                p.main(["--evidence-root", tmp, "request", "GET", "http://localhost:3000/"])

    def test_auth_pins_headers_for_a_role(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["--evidence-root", tmp]
            p.main(argv + ["begin", "audit", "--target", "http://localhost:3000"])
            self.assertEqual(p.main(argv + ["auth", "tenantA",
                                            "--header", "Authorization: Bearer xyz"]), 0)
            self.assertEqual(p.load(pathlib.Path(tmp)).role("tenantA").headers["Authorization"],
                             "Bearer xyz")


if __name__ == "__main__":
    unittest.main()
