# The security-audit config — the `security` block aikit cannot infer

<!--
WHAT: the contract for `aikit.yml`'s `security` block, read by the
      `security-audit` skill, the hunter and refuter agents, `bin/probe`, and
      `verdict security`.
WHY:  what a service exposes, who its tenants are, and which address is a
      disposable stand you own are all irreducibly this project's. aikit states
      what it needs and refuses to guess the dangerous parts.
HOW:  §1 the fence, §2 the stand, §3 boxes, §4 roles and truth, §5 the rest,
      §6 the trust model, §7 stacks that are not HTTP.
-->

The audit is **standalone** — it is not part of autopilot and does not run on a
milestone. You point it at a running service you own; it hunts, proves, ranks,
and hands findings back for you to plan. It never fixes.

Skip this whole feature if you have nothing to point it at: leave the `security`
block out of `aikit.yml` and `/aikit:security-audit` has nothing to do.

```yaml
security:
  box: black                 # black | gray | white — how much source the hunter gets
  scan: "gitleaks detect --no-banner && osv-scanner -r ."   # deterministic pre-pass
  threat_model: docs/security/threat-model.md               # gray/white: owner-approved
  scope:
    targets: ["http://localhost:3000"]
    authorized: false        # true ONLY to attest you own a non-loopback target
  stand:
    up:   "scripts/sec/stand.sh up"
    down: "scripts/sec/stand.sh down"
  roles:
    - name: anon
    - name: tenantA
      auth: "header:Authorization=Bearer <seeded-token-A>"
    - name: tenantB
      auth: "login:scripts/sec/login.sh tenantB"
  truth:
    kind: command
    use: "scripts/sec/query.py"          # read-only — confirms a real leak
  budget: { requests: 800, minutes: 40 }
  rounds: 2
  tripwire_ignore: ["__pycache__", "*.pyc"]
  # probe: "scripts/sec/probe.py"        # optional: your own fenced client
```

## 1. `security.scope` — the fence

The single most important key. `targets` is the allowlist of origins the audit
may touch; `bin/probe` refuses any request outside it **before a socket opens**.
An entry is an origin, optionally narrowed to a path prefix:
`http://localhost:3000`, `localhost:3000` (either scheme), `10.0.0.5:8080/api`.

`authorized` is the one place the config carries real risk. A **loopback** target
(`localhost`, `127.0.0.0/8`, `::1`) needs nothing. Any **other** address — a LAN
IP, a container host, a public name — is refused unless `authorized: true`. That
flag is you attesting, in writing, that you own the thing at that address and are
permitted to attack it. aikit will never set it for you, and the skill never
passes `--authorized` to probe on its own initiative. This is the whole of "only
my services": not a promise in a prompt, a target the tool will not send to.

## 2. `security.stand` — disposable, never production

`up` brings the service up fresh and reachable at `scope.targets`; `down` tears it
down with its volumes. The rules are acceptance's, for the same reasons
(`docs/harness.md`): tear down any stand already listening first, or the audit
attacks yesterday's build; exit non-zero if it half came up; seed it disposably.

**Never point a stand at production.** The hunter double-submits, injects,
enumerates ids, and sends malformed input on purpose. Build the stand on top of
the project's existing e2e or acceptance stand rather than beside it.

## 3. `security.box` — how much the hunter sees

The box is only how much source the hunter may read while it attacks the running
stand. The loop — hunt, refute, gate — is identical in all three.

- **black** — the stand only. The hunter discovers the surface by using it.
- **gray** — the stand plus partial knowledge (an API spec, the routes, the roles).
- **white** — the stand plus the full source, read to aim the attack. The proof is
  still a live request. The working tree is fingerprinted before the hunt and the
  gate blocks if it moved, so a hunter that edited the code it was auditing voids
  the run — the same tripwire acceptance uses.

## 4. `security.roles` and `security.truth`

**Roles** are the identities the hunter keeps live at once — this is what finds
authorization bugs, which are the highest-value web findings and invisible with a
single login. Each role's `auth` is either `header:Name=Value` (a seeded token,
an API key) or `login:<command>` (a command the hunter runs to obtain a session).
`anon` needs no `auth`. `bin/probe` keeps a cookie jar and pinned headers per role
and selects one with `--role`.

**`truth`** is a read-only view of the service's own stored data, used to tell
*exploitable* from *looks exploitable*: the screen returned tenant B's order — did
that row really belong to B? As in acceptance, read-only must be a property of the
database role, not an instruction (`docs/harness.md` §3). Omit it and the audit can
only believe the response, which is often exactly the thing in question.

## 5. The rest

- **`scan`** — a deterministic command (secrets scanner, dependency/SCA scanner,
  SAST). Agents are bad at what these are good at; run them and fold the results
  in. Their output is context, not a blocker on its own.
- **`threat_model`** — for gray/white, a file the owner approves before hunting,
  the way a plan is approved. The hunter proposes changes but a finding that leans
  on an unapproved change does not get to block.
- **`budget`** — `requests` and `minutes`, enforced inside `bin/probe`. A spent
  budget makes the next request fail with "could not", never a silent trail-off.
- **`rounds`** — attempts to earn a **trustworthy** report (default 2). Rounds are
  spent on defects — missing evidence, an unconfirmed exploit — not on hunting
  more. Finding bugs is the success case, not a reason to loop.
- **`tripwire_ignore`** — generated paths a run touches that git tracks, kept out
  of the working-tree fingerprint. Keep it short; every entry is a place the
  tripwire stops watching.
- **`probe`** — point at your own fenced client if `bin/probe` cannot reach the
  stand (the browser lives inside a container, the protocol is not plain HTTP). A
  substitute MUST enforce the scope allowlist, the non-loopback refusal, and the
  budget, and MUST write replayable transcripts — an unenforced fence is no fence.

## 6. Why the fence is a tool, not a rule

The same design decision as everywhere else in aikit. "Only attack the stand,
only what you were told to" written in the hunter's prompt holds until the agent
follows a link in a response to a third-party host, or reasons its way into "just
one check against prod". The fence is a program: a request outside scope never
opens a socket, and a non-loopback target without attestation is refused. The
hunter reaches the network only through it, so the guarantee does not depend on
the hunter's good behaviour over a long run.

The refuter's independence is the other half, and also structural: it has no
Write or Edit tool and cannot file findings of its own, so it validates instead of
discovering — ideally on a different model, so one set of weights does not bless
its own mistake.

And the audit never fixes. A finding is a change the owner plans and someone else
builds, reviewed like any other — the finder is never the fixer, the rule the
reviewer and acceptance agent already embody.

## 7. Stacks that are not plain HTTP

The three contracts are shapes. For a **gRPC or WebSocket** service, point
`security.probe` at a client that speaks it and still enforces the fence and
writes transcripts. For a **CLI or a service with no network interface**, the
"requests" are invocations and the "transcripts" are captured command sessions;
the boundary crossings are argument injection, path traversal, privilege. The
constant across all of them: a finding classed exploitable carries a replayable
proof the second agent can run, or the gate does not accept it.
