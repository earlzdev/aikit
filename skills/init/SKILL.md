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
  Files that belong to no zone are normal and expected — a `Makefile`,
  `CLAUDE.md`, CI config. Leave them out of every zone: a change touching only
  them matches no zone command, and the rule is then `verify_all`. Do not
  invent a zone to hold them, and do not list one file in several zones to
  force that — say it once in the config's comments if it needs saying.
- **Verify commands.** `Makefile` targets, `package.json` scripts, CI workflow
  steps, `pyproject.toml`, `pytest.ini`. The CI workflow is the best source:
  it is what the project already believes "green" means.
- **Rulebooks.** `.claude/projects/*.md`, or whatever the project calls them.
  If there are none, **omit `zones[].rulebook` entirely** — a key pointing at a
  file that does not exist is worse than an absent key, because a reviewer told
  to read it will report the missing file instead of reviewing the diff. The
  project's `CLAUDE.md`, if it has one, carries the conventions instead.
- **A plan.** `docs/PLAN.md`, `PLAN.md`, `ROADMAP.md`. If one exists, read its
  wording and take `plan.markers` from what it actually says. Never impose the
  defaults on a plan that already has its own words.
- **An acceptance harness.** Does anything already bring up a disposable
  stand — `scripts/e2e/`, a compose file with a test profile, a `stand.sh`?
- **Language.** What language is the existing plan, changelog and docs written
  in? That is `language`.

## 2. Then ask, only what is left

Anything the owner already said when invoking this counts as an answer given —
do not ask it again. Batch what remains. Typically:

- Anything you could not infer about zones or verify commands.
- Round caps, if the owner wants something other than 3 for development and 2
  for fixes.
- **Do not ask which model each agent should run on.** `review.model` and
  `acceptance.model` exist, but they are a tuning decision for a project that
  has watched its own runs, not an opening question — leave them out and let
  every agent inherit.
- Whether acceptance is wanted at all right now. It is the expensive half, and
  a project with no interface does not need it yet — `acceptance` can be left
  out of the config entirely and added later.
- For acceptance: how a disposable stand comes up, whether a read-only database
  role exists or must be made, and the addresses a person would use.

## 3. Write `aikit.yml`

At the repo root. The reference is `$AIKIT/docs/config.md` — **resolve
`$AIKIT` now, using §5 step 3's recipe, rather than when you get to §5.** The
recipe's first source is `plugin_root:` in `aikit.yml`, a file that does not
exist yet at this point, so it will fall through to the cache glob; that is
expected, and it is why the version check there matters. If you end up writing
`plugin_root:` into the config, write it in this pass rather than coming back
to edit a file you were told to write once —
read it before writing, and write only the keys this project actually needs.
Omitting the whole `acceptance` block is a valid, common configuration.

Add `evidence` (default `.acceptance`) to `.gitignore`. Screenshots and tree
dumps must never enter the repository — they swell it and leave nothing
readable in the history. The tracker directory, holding verdict text, IS
committed.

## 4. The two things aikit cannot write for you

**Skip this whole section if you left the `acceptance` block out in §3** — with
no block, nothing references these and a stub nobody calls is just litter.

Otherwise: everything else is shipped or configured, and these two are
irreducibly the project's, because they touch its own stack:

**`acceptance.stand.up` / `.down`** — bring up a disposable stand and tear it
down with its volumes. Build it on top of whatever e2e stand the project
already has rather than beside it: a second stack with the same services
diverges from the first within a milestone, and acceptance would then be
checking yesterday's configuration. It must never point at production.

**`acceptance.truth`** — one read-only `SELECT` against the stand's database.
Read-only as a property of the database role, not as an instruction: an
acceptance agent able to write a row will one day help itself to one instead of
reporting that the button failed to create it.

`$AIKIT/docs/harness.md` has the full contract and a worked
example. Scaffold both as stubs that exit non-zero with a clear message, so an
unconfigured harness fails loudly instead of silently passing.

Hands are optional for a web product: leave `acceptance.hands` unset to use
aikit's own `bin/drive` (it attaches to a Chromium over CDP at
`acceptance.browser.cdp`), or name the project's own driver when the browser is
only reachable from inside a container.

For any other stack, `hands` and `truth` take `kind: mcp` or `kind: skill` and
name tools the agent already carries — it holds every tool this project has, and
these keys only say which ones reach the product, so a key left vague costs it
budget hunting for them.
Interview for those the same way: what reaches this product the way a person
does, and what can read its data without being able to change it.

## 5. Prove it, don't declare it

Run each of these and show the output. An init that ends in a summary rather
than in evidence is how a project discovers its config is wrong three
milestones later.

1. `verify_all` — must pass on untouched code.
2. Each zone's `verify` — must pass.
3. **Resolve aikit's binaries and prove it.** They live in the installed
   plugin, not in this project, and `$CLAUDE_PLUGIN_ROOT` is *not* set in a
   Bash tool call — so it can never be the only source:

   ```bash
   # In this order. `$CLAUDE_PLUGIN_ROOT` is NOT set inside a Bash tool call,
   # so it can never be the only source.
   AIKIT="$(plugin_root_from_aikit_yml)"          # `plugin_root:` in aikit.yml, if set
   AIKIT="${AIKIT:-$CLAUDE_PLUGIN_ROOT}"
   AIKIT="${AIKIT:-$(ls -d ~/.claude/plugins/cache/aikit/*/*/ 2>/dev/null | sort -V | tail -1)}"
   AIKIT="${AIKIT%/}"
   # PRINT THE VERSION, not just "ok". `verdict --help` succeeds against ANY
   # installed copy, so a check that only runs it proves the wrong thing: on a
   # machine with an older release still cached, the glob picks that one and
   # the probe says fine. Read the version and confirm it is the one you mean.
   echo "$AIKIT"
   python3 -c "import json,sys;print('version', json.load(open(sys.argv[1]))['version'])" \
     "$AIKIT/.claude-plugin/plugin.json"
   "$AIKIT/bin/verdict" --help >/dev/null && echo "binaries run"
   ```

   (`plugin_root_from_aikit_yml` is shorthand — read that optional key yourself.)

   **Check the version it printed against the one you meant to install.** An
   older release left in the cache is the normal case, not an exotic one, and
   the glob takes the highest version number it finds — which is not
   necessarily the newest thing you installed.

   If that finds nothing, or finds a version other than the one you mean,
   locate the plugin yourself and **write its absolute path into `aikit.yml` as
   a top-level `plugin_root:`** — the skills that need a binary
   (`init` and `acceptance-loop`) read that key first. It is the
   plugin's ROOT, the directory holding `bin/`, not `bin/` itself. Do not leave this to be discovered later: a project whose skills
   cannot find `verdict` fails at the acceptance gate, which is the worst
   moment to learn about it.
4. The gate, end to end, in a scratch directory. The gate reads
   `<evidence-root>/<milestone>/verdict.json`, so the milestone's own directory
   has to exist — and since the gate checks that every `screen:` it is shown is
   really on disk, the skeleton's placeholder capture has to exist too. An
   empty file is enough; the gate asks whether the capture happened, not
   whether it is a valid PNG:
   ```
   mkdir -p /tmp/aikit-probe/probe
   : > /tmp/aikit-probe/probe/007-saved.png       # the skeleton's placeholder capture
   "$AIKIT/bin/verdict" template probe > /tmp/aikit-probe/probe/verdict.json
   "$AIKIT/bin/verdict" gate probe --evidence-root /tmp/aikit-probe   # exit 0
   ```
   Then delete the `not_checked` field from that file and run the gate again:
   it must exit 1 and name the missing line. A gate that cannot fail is not a
   gate, and this is the only step here that proves it can — which is why the
   run above has to reach exit 0 first. If it does not, the two runs agree and
   the step proves nothing.
5. If acceptance is configured: `acceptance.stand.up`, then the query command,
   then `acceptance.stand.down`. Confirm the stand actually came up and the
   query actually returned rows.

Then tell the owner what was written, what they still need to fill in, and the
one command that starts real work: `/aikit:plan` for a new plan, or
`/aikit:autopilot` when a plan is already approved.
