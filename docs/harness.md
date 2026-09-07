# The acceptance harness — the two commands aikit cannot write for you

<!--
WHAT: the contract for `acceptance.stand` and `acceptance.query`.
WHY:  everything else in the acceptance phase is a method, and a method ships.
      Bringing up a stand and reading a database are irreducibly this
      project's: its compose file, its schema, its credentials. Rather than
      guess at them, aikit states what it needs and checks that it got it.
HOW:  §1 and §2 are the two contracts. §3 is why read-only is a database
      property. §4 is hands.
-->

Skip this whole file if the project has no interface to walk. Leave the
`acceptance` block out of `aikit.yml` and the phase simply does not exist.

## 1. `acceptance.stand.up` / `acceptance.stand.down`

```yaml
acceptance:
  stand:
    up:   "scripts/acceptance/stand.sh up"
    down: "scripts/acceptance/stand.sh down"
```

`up` must:

- bring the product up **disposably** — every run starts from nothing;
- seed whatever `acceptance.seed` describes, and seed it **empty**. Acceptance
  walks the path from zero, like an owner with a new account. A stand carrying
  yesterday's data has all the awkward first-time steps already done, which is
  exactly where the findings are;
- make the addresses in `acceptance.entrypoints` reachable;
- exit non-zero if any of that failed. A stand that half came up produces an
  acceptance run that half happened, reported as a pass.

`down` must tear it down **with its volumes**. A disposable stand that survived
its run is a stand the next acceptance walks through stale data on.

**Never production.** The acceptance agent clicks everything, types a thousand
characters into fields, double-clicks buttons and abandons flows halfway — on
purpose. That belongs somewhere that gets destroyed afterwards.

Build it on top of the project's existing e2e stand rather than beside it. A
second stack with the same services diverges from the first within one
milestone, and acceptance then checks a configuration nobody ships.

## 2. `acceptance.query`

```yaml
acceptance:
  query: "scripts/acceptance/query.py"
```

Called as `<query> "SELECT …"`, and `<query> --tables` to list what is visible.
It must:

- run exactly one `SELECT` — reject a second statement, any DDL, or a semicolon
  in the middle, **before** the text reaches the database;
- connect as a role with no write privilege at all;
- print rows in a form that can be pasted into a report as evidence. The
  acceptance agent writes them into its `evidence` field prefixed `db:`.

Without this, the finding class **works, but lies** cannot be distinguished
from **works**. The screen said "Saved" and the row never changed; the form
thanked you for the enquiry and nothing arrived. An acceptance agent with no
database access can only believe the screen — that is, check the one thing that
did not need checking.

## 3. Why read-only is a property of the role, not an instruction

`Bash` would let the acceptance agent run anything. The lock is not the
sentence "please do not write" — it is a database role that has no `INSERT`
privilege to use. An agent that *can* fix the stand to match its expectation
eventually will, and will report a pass. Grant a role, whitelist the tables it
may read, and hand it to `query` alone.

The same shape appears twice more in aikit, and it is the design rule worth
taking away: `reviewer-strict` has no `Write` tool, so it cannot patch what it
reviews; the acceptance brief has no file names, so its blindness to the
implementation costs nothing to maintain.

## 4. Hands

Optional and pre-built. Leave `acceptance.drive` unset and aikit's own
`bin/drive` attaches to a Chromium over CDP at `acceptance.browser.cdp`, which
the stand is expected to expose. It gives back an accessibility tree after each
action, writes a numbered screenshot beside it, and enforces the action and
time budgets itself.

Set `acceptance.drive` to the project's own driver when the browser is only
reachable from inside a container — that is the common case for a stand whose
network namespace is the only place `localhost` and a valid `Origin` mean the
right thing. The driver must accept the verbs listed in `agents/acceptance.md`
and must enforce the budgets: an unenforced budget is how a run trails off with
no "got this far, and why" line.

## Worked example

The project this pipeline grew in has three files under `scripts/acceptance/`:
a `stand.sh` layered over the existing e2e stand rather than beside it, a
`query.py` guarded by a single-`SELECT` parser and a role with a table
whitelist, and a `drive.py` that runs its host half and its in-container half
out of one file. That last shape is worth copying when your browser lives
inside the stand: the host half re-invokes itself through the container and
collects the artefacts back, so no separate acceptance server is needed.
