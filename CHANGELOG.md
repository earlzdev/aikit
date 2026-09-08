# Changelog

Newest first. What changed, and why.

## 0.3.0 — 2026-09-08

A minor rather than a patch: two config keys change meaning, and the acceptance
report gains a field. Everything below was found by RUNNING the plugin for the
first time — twelve components exercised, eight of them broken.

- **Every skill's path to aikit's own binaries was broken, in every version
  since 0.1.0.** They said `"$CLAUDE_PLUGIN_ROOT/bin/verdict"`, and that
  variable is NOT set inside a Bash tool call — it resolved to `/bin/verdict`,
  so the acceptance gate could never have run for anyone who installed the
  plugin. The skills now resolve it in three steps (an optional top-level
  `bin:` in `aikit.yml`, then the variable where it does exist, then the plugin
  cache, newest version) and `/aikit:init` proves the result runs instead of
  echoing the variable and hoping.
- **The default `plan.markers.milestone` could not tell a milestone from a
  step.** It shipped as `^##+\s`, which matches `##`, `###` and a plain
  `## General rules` alike — 14 matches in a plan with 2 milestones. Milestones
  are the unit that merges and goes through acceptance; steps are the unit that
  goes through review; a marker matching both silently collapses the
  distinction the plan format rests on. It is `^## [→✅]` now, keyed on the
  status glyph, with a separate `step: "^### "`. Fixed in every example config.
- **`/aikit:init`'s own proof step could never pass as printed.** It wrote the
  probe report to `<root>/verdict.json` while the gate reads
  `<root>/<milestone>/verdict.json`, and omitted the `mkdir -p`, so the
  redirect failed outright. An operator following §5 literally would conclude
  the gate was broken.
- **`bin:` is now `plugin_root:`.** It holds the plugin's root directory — the
  one containing `bin/` — and the old name invited pointing it at `bin/`
  itself, which fails silently.
- **`init` now covers what it previously left to invention:** rulebooks when a
  project has none (omit the key rather than write a dangling path), files that
  belong to no zone, and §4's harness stubs being skipped when no `acceptance`
  block was configured.
- **`plan` now says** that the plan is committed when written, that a
  "general rules" section is deliberately not a milestone, and how to write
  `**E2E:**` in a project that has no e2e suite at all.
- **`docs/harness.md` now requires `stand.up` to tear down a previous stand
  first.** Found by running it: an orphaned server kept the port, the new stand
  failed to bind, and `up` still exited 0 because the health check was answered
  by the OLD build. The acceptance run that followed would have walked stale
  code and reported on it. A health check a previous stand can satisfy is not a
  health check.
- **The acceptance report gained `verified_fixed`.** On round 2 an agent had
  nowhere to record "the previous round's finding is now fixed", so it filed
  the confirmation as a `clumsy` finding — misreporting the class and burying
  the one line that shows the loop converging. It is its own field and its own
  section in the verdict now, and never blocks.
- No behaviour change in the binaries beyond the path and report changes: the acceptance loop,
  `autopilot` and `reviewer-strict` were all run end to end for the first time
  in this version and needed none.

## 0.2.2 — 2026-09-08

- **`bin/drive` was broken and is now fixed.** Playwright removed
  `page.accessibility` in 1.62, so every action after `begin` died on
  `AttributeError`. It uses `page.aria_snapshot()` now — which already returns
  an indented role/name outline — and falls back to the old API so a project
  pinning an older Playwright is not forced to upgrade. Found by running it
  against a real Chromium for the first time, which is the only way this class
  of bug is ever found.
- **The 0.2.1 tripwire had a false positive that would have voided every real
  run.** It fingerprinted `git status`, and *using* a product mutates a
  repository — the first live run tripped on a `.pyc` the test suite wrote. The
  fingerprint now takes `--tree-ignore` (a bare name matches any path
  component, so `__pycache__` catches it at any depth) and the defect names the
  paths that moved, so a block says which file and is actionable instead of
  mysterious. Config key: `acceptance.tripwire_ignore`.
- **The changelog was out of order**, with shipped work filed under
  "Unreleased". Rewritten newest-first.

## 0.2.1 — 2026-09-08

- **The gate now checks that the acceptance run did not touch the code it was
  judging.** `verdict tree` fingerprints the repository, the acceptance-loop
  records it before spawning, and `verdict gate --expect-tree <digest>` blocks
  if it moved. 0.2.0 gave the agent every tool, editing tools included, and
  left "you only report" as prose; this puts the guarantee back on the one exit
  code that already stops a merge. Fails closed — a tree that cannot be
  fingerprinted is a defect, not a pass — and an owner override cannot lift it,
  because a void run is not a finding to disagree with.

## 0.2.0 — 2026-09-08

- **The acceptance agent now holds every tool the project has** — MCP servers,
  skills, browser control — instead of `Bash, Write`. The narrow list never
  bought the blindness it looked like it bought: a shell alone reads any file.
  What actually holds is the brief, which carries no file name, and the gate,
  which accepts only evidence the PRODUCT produced — a checklist item cannot be
  paid for with a line of source. So the restriction cost capability and
  protected nothing. `reviewer-strict` keeps its narrow list, where "cannot
  edit" IS the lock.
- **`acceptance.drive`/`query` became `hands`/`truth`, each with a `kind`** —
  `command`, `mcp` or `skill`. A stack whose hands are MCP tools rather than a
  shell command is now expressible, which is what Android needs.
- **`docs/examples/android.aikit.yml`** — the emulator as the acceptance stand,
  with the two guarantees that get weaker there written down rather than
  discovered: resource ids leak developer names, and `adb shell` can write.

## 0.1.1 — 2026-09-08

- **Dropped `commands/`.** A command and a skill sharing a name both register
  under `/aikit:`, so the picker showed `/aikit:autopilot` twice (and `init`
  and `plan` likewise). The commands only forwarded `$ARGUMENTS`, which skills
  already take, so the skills are now the single entry point. The two nudges
  that lived only in a command file moved into the skill they belonged to:
  what to do when `plan` is invoked with nothing to plan, and that anything
  the owner said when invoking `init` is an answer already given.
- **`docs/pipeline.html`** — an animated trace of one task through the pipeline.
  Round one fails on purpose, in both loops: an animation of a clean
  straight-through run would misrepresent the thing, because the loop is the
  product.
- **`docs/pipeline-{dark,light}.gif`** for the README, built from
  `docs/pipeline-capture.html` by `docs/capture.mjs` — headless Chrome over CDP
  with no npm install, drawing frame `n` and screenshotting it rather than
  screen-recording a clock. Milestones are numbered `E57` there rather than
  `Э57`: at that size the Cyrillic `Э` reads as a `3`.

## 0.1.0 — 2026-09-07

First release. The pipeline extracted from a project that had grown it in
place, generalised so it can be installed rather than copied.

- **Runtime config instead of rendered templates** (`aikit.yml`). The
  predecessor substituted values into copied files at scaffold time; two
  projects then sat five versions behind with no upgrade path, because a
  rendered copy can only be re-rendered over the owner's edits.
- **`review-loop`** — round caps, the severity ladder in one place, ping-pong
  detection, medium/low carry-over across rounds.
- **`acceptance-loop`** — the phase between review and merge, run only on a
  milestone whose plan line asks for it. The brief is four things and contains
  no file names.
- **`plan`** — milestones (`##`, the acceptance and merge unit) and steps
  (`###`, the review unit), with markers read from config so a plan keeps its
  own language.
- **`autopilot`** — the pipeline unattended, with a written boundary between
  what it decides alone and what stops it.
- **`init`** — ends by running what it configured, not by summarising it.
- **`reviewer-strict`** and **`acceptance`** agents; independence enforced by a
  missing tool and a brief with no file names respectively.
- **`bin/verdict`** — the mechanical gate. A defective report blocks exactly
  like a breakage: an acceptance run that never looked at the data has not
  earned the right to say "good". Only the owner lifts a block, and lifting is
  a written line.
- **`bin/drive`** — browser hands with the action and time budgets enforced in
  code. The Playwright layer is not yet exercised against a live browser.
