---
name: init
description: Set aikit up in a project — work out its zones and verify commands, interview the owner about what cannot be detected, write aikit.yml, and prove the pieces actually run. Use once per project, and again when the project's shape changes.
---

# init — teach aikit this project

<!--
WHAT: writes `aikit.yml` and proves it works.
WHY:  aikit ships a method, not templates. Everything project-specific is read
      from one config at runtime, which is why an aikit upgrade changes nothing
      in a project. That only holds if the config is right — so this skill ends
      by running the things it configured, not by declaring success.
HOW:  §1 look, §2 ask, §3 write, §4 the harness, §5 prove it.
-->

## 1. Look before asking

Read the repo and answer as much as you can yourself. Asking about something
sitting in `Makefile` wastes the owner's attention on the wrong questions.

- **Zones.** How does this project already divide? Look for a zone table in
  `CLAUDE.md`, existing rulebooks in `.claude/projects/`, top-level source
  directories, separate test suites, distinct language stacks. Two to four
  zones is usual. One is fine for a small project.
- **Verify commands.** `Makefile` targets, `package.json` scripts, CI workflow
  steps, `pyproject.toml`, `pytest.ini`. The CI workflow is the best source:
  it is what the project already believes "green" means.
- **A plan.** `docs/PLAN.md`, `PLAN.md`, `ROADMAP.md`. If one exists, read its
  wording and take `plan.markers` from what it actually says. Never impose the
  defaults on a plan that already has its own words.
- **An acceptance harness.** Does anything already bring up a disposable
  stand — `scripts/e2e/`, a compose file with a test profile, a `stand.sh`?
- **Language.** What language is the existing plan, changelog and docs written
  in? That is `language`.

## 2. Then ask, only what is left

Batch the questions. Typically:

- Anything you could not infer about zones or verify commands.
- Round caps, if the owner wants something other than 3 for development and 2
  for fixes.
- Whether acceptance is wanted at all right now. It is the expensive half, and
  a project with no interface does not need it yet — `acceptance` can be left
  out of the config entirely and added later.
- For acceptance: how a disposable stand comes up, whether a read-only database
  role exists or must be made, and the addresses a person would use.

## 3. Write `aikit.yml`

At the repo root. The reference is `${CLAUDE_PLUGIN_ROOT}/docs/config.md` —
read it before writing, and write only the keys this project actually needs.
Omitting the whole `acceptance` block is a valid, common configuration.

Add `evidence` (default `.acceptance`) to `.gitignore`. Screenshots and tree
dumps must never enter the repository — they swell it and leave nothing
readable in the history. The tracker directory, holding verdict text, IS
committed.

## 4. The two things aikit cannot write for you

Everything else is shipped or configured. These two are irreducibly the
project's, because they touch its own stack:

**`acceptance.stand.up` / `.down`** — bring up a disposable stand and tear it
down with its volumes. Build it on top of whatever e2e stand the project
already has rather than beside it: a second stack with the same services
diverges from the first within a milestone, and acceptance would then be
checking yesterday's configuration. It must never point at production.

**`acceptance.query`** — one read-only `SELECT` against the stand's database.
Read-only as a property of the database role, not as an instruction: an
acceptance agent able to write a row will one day help itself to one instead of
reporting that the button failed to create it.

`${CLAUDE_PLUGIN_ROOT}/docs/harness.md` has the full contract and a worked
example. Scaffold both as stubs that exit non-zero with a clear message, so an
unconfigured harness fails loudly instead of silently passing.

Hands are optional: leave `acceptance.drive` unset to use aikit's own
`bin/drive` (it attaches to a Chromium over CDP at `acceptance.browser.cdp`),
or point it at the project's own driver when the browser is only reachable from
inside a container.

## 5. Prove it, don't declare it

Run each of these and show the output. An init that ends in a summary rather
than in evidence is how a project discovers its config is wrong three
milestones later.

1. `verify_all` — must pass on untouched code.
2. Each zone's `verify` — must pass.
3. `echo "$CLAUDE_PLUGIN_ROOT"` — must resolve. If it does not, find the
   plugin's installed path and record it in `aikit.yml` as `bin:` so the skills
   can find `verdict` and `drive`.
4. The gate, end to end, in a scratch directory:
   ```
   "$CLAUDE_PLUGIN_ROOT/bin/verdict" template probe > /tmp/aikit-probe/verdict.json
   "$CLAUDE_PLUGIN_ROOT/bin/verdict" gate probe --evidence-root /tmp/aikit-probe
   ```
   It must exit 0 on the skeleton. Then delete a required field and confirm it
   exits 1 — a gate that cannot fail is not a gate.
5. If acceptance is configured: `acceptance.stand.up`, then the query command,
   then `acceptance.stand.down`. Confirm the stand actually came up and the
   query actually returned rows.

Then tell the owner what was written, what they still need to fill in, and the
one command that starts real work: `/aikit:plan` for a new plan, or
`/aikit:autopilot` when a plan is already approved.
