# Changelog

Newest first. What changed, and why.

## 0.4.0 — 2026-09-08

Autopilot stops building. Then the whole plugin was run on a throwaway project
— every skill, both binaries, all three agents — and that run found 39 defects
in aikit itself, most of them in instructions no test can reach.

Autopilot stops building. It dispatches instead, and the cost of a long run
stops growing with the length of the plan.

- **`review-loop` is now `step-loop`, and it delegates.** It used to load into
  the caller's context and have the caller write the code, so `autopilot` was
  the author of every step, the holder of every diff and every verify run, and
  the thing that closed the milestone — all in one conversation. A conversation
  re-sends everything it holds on every turn, so the last milestone of a plan
  paid for the whole plan. `step-loop` now spawns an **implementer** per step
  and hands the caller back a summary and a verdict line. Same work, cost
  bounded by a step rather than by the run: on a four-milestone, twenty-step
  plan the modelled saving is roughly 5–6×. The `review.rounds` and
  `review.reviewer` config keys are unchanged — the skill was renamed, the
  config surface was not.
- **New `agents/implementer.md`.** Builds one step, gates it on the project's
  own `verify`, reports what it changed. It has no `Agent` tool, marks nothing
  done, and never touches the plan or the tracker. It is **held** across that
  step's review rounds and released at the end: the agent that wrote the code
  is the one that fixes the findings, because it knows why it chose what it
  chose and a fresh agent re-deriving that from a diff is both worse and more
  expensive.
- **The reviewer stays fresh every round, deliberately.** Holding it across
  rounds looks like a saving and is not: its cold start — persona, `aikit.yml`,
  the rulebook — is byte-identical on every spawn and therefore cached, while
  its transcript is neither. Carrying it is *modelled* at about 1.5× more per
  round, and — the part that needs no model — anchors a reviewer to re-bless
  what it already approved. `step-loop` now says so where someone would
  otherwise try it.
- **`step-notes.md` per milestone.** Each step's implementer is fresh and has
  not seen the earlier steps, so what they established goes in a file the next
  one reads — not into a held agent. Re-readable, free between steps, and it
  survives a stopped run.
- **`review.model` and `acceptance.model`, both optional, both unset by
  default.** Agents inherit the run's model unless the owner says otherwise.
  `docs/config.md` argues against the obvious move of cheapening the reviewer:
  it is the gate, and a gate that misses things costs a round and returns the
  project to where it started.
- **Verify output no longer goes into a context whole.** Every self-gate now
  says to send it to a file and read the tail or the failures. A red suite is
  thousands of lines and none of them are worth what they cost to hold.
- **`autopilot` §2 is explicit that it does not build**, §3 routes acceptance
  findings back through a fresh `step-loop` rather than fixing them by hand,
  and §5 no longer demands a recital of every carry-over from every round —
  those live in the tracker and the report cites them.
- **The gate's evidence check was defeated seven times and rewritten seven
  times.** Each fix was itself defeated by the next review round, always by the
  same shape — a string that satisfies the evidence requirement with no capture
  behind it:
  1. only the `screen:` prefix was checked, so any invented filename paid;
  2. the fix skipped an *empty* name rather than refusing it, so a bare
     `screen:` paid — cheaper than what it had just closed;
  3. the fix then passed the name to `evidence_dir / name`, and `pathlib`
     discards the left operand when the right is absolute, so
     `screen:/etc/hosts` resolved outside the evidence directory and any file
     on the machine paid;
  4. and underneath all three, the prefix itself was optional: the
     `screen:`/`db:` requirements are report-wide, while an individual item was
     satisfied by any non-empty string. One real capture paid for the entire
     checklist, and `checked, works` — the literal string this module's
     docstring promises is refused — went through untouched, as did `Screen:`
     with a capital S;
  5. and once names were checked against the evidence directory, that
     directory was the one the gate had just read the report from — so
     `screen:verdict.json` named a file guaranteed present in every project on
     every run, and paid for a whole checklist from an otherwise empty
     directory, with no filesystem access at all;
  6. and the `screen:` requirement was report-*wide*, so `db:checked, works`
     paid for every checklist item while the one screenshot the report needed
     hung off a non-blocking `clumsy` finding. `agents/acceptance.md` had said
     since 0.1.0 that a point counts as passed ONLY with a screenshot; the gate
     had never enforced it per item;
  7. and the evidence directory was never cleared between rounds, so a round
     that took no actions at all could pay for itself with the previous
     round's screenshots — which lands on rounds 2 and 3 exactly, since those
     only happen because round 1 blocked. `acceptance-loop` now archives each
     round's captures into `round-<N>/` before the next one starts.

  Now: every evidence string on a passed item must carry a known prefix,
  matched case-insensitively; `db:` must have something after it; a `screen:`
  name must be one plain filename, not a path, and not the report's own; and
  it is matched against the real files in the evidence directory — `os.scandir`
  rather than `is_file()`, which followed symlinks, counted directories and
  ignored case on macOS — comparing under NFC too, so a Cyrillic capture name
  is not rejected over a normalisation difference.

  Worth recording how they were found: the first by running the binary against
  a throwaway project, the other six by reviewers attacking the previous fix
  with constructed strings. Reading the code found none of them, and neither
  did the test suite — it was green over every one.

  **Known limits, recorded rather than fixed.** One real capture cited on
  several checklist lines still pays for all of them: the same screenshot can
  legitimately show two "done when" lines, so distinctness is not required,
  and the comment in `defects()` no longer claims otherwise. And an agent with
  a shell can always `touch` a file and quote its name — this check is hygiene
  against a lazy run, never a boundary against an adversarial one.

  **What would actually fix it**, when someone has the appetite: the check
  asks whether a string looks like a file that exists, when the question it
  wants is whether the driver did the work. `bin/drive` already knows — have
  it append a manifest (`captures.json`: name, timestamp, target, digest) that
  the reporting agent did not author, and the gate can require every cited
  capture to appear in it and cross-check `spend.actions` against the driver's
  own count. Seven rounds of narrowing the vocabulary of the lie is what
  happens without that.
- **What running the whole thing on a test project changed.** A two-milestone
  plan on a real CLI product, carried from preconditions to two `✅`s, plus
  `init` and `plan` run cold by agents holding only the skill text. Nothing
  below was visible from reading:
  - **`/aikit:init` silently configured a project against a stale release.**
    Its `$AIKIT` recipe fell through to the cache glob, resolved an older
    cached version, ran `verdict --help` against it, printed `ok` and exited 0
    — while the prose two lines below worried about exactly that. The check
    proved *a* verdict existed, never the right one. It now prints the resolved
    **version**, and says to compare it with what you installed.
  - **`acceptance-loop` told owners to set `bin:`**, a key renamed to
    `plugin_root:` in 0.2.2 and read by nothing since. `plugin_root:` was also
    undocumented in the file `init` calls "the reference"; both fixed.
  - **`plan` forbade what it required.** "The acceptance line is written by the
    owner. Do not decide it yourself and do not leave it out" against its own
    "write the acceptance line". On a first plan the owner has not seen the
    milestone yet. It now says to *propose* the line and list every proposal at
    the gate, where the owner decides.
  - **`plan` never pointed at `docs/plan-format.md`**, where the `M<n>`
    numbering lives — so a cold planner had no way to learn the convention. It
    is now in the skill itself.
  - **`yes:` and `no:` marker keys were unquoted in every example.** YAML 1.1
    parses those as booleans, so both keys vanish and the marker lookup finds
    nothing.
  - **`zones[].paths` read as a write boundary.** An implementer flagged that
    writing a test outside its zone's paths looked like a scope violation;
    `docs/config.md` now states that `paths` selects the rulebook and verify
    command and is not a fence — a reviewer treating it as one files an
    inflated High, which costs a whole round.
  - **The acceptance persona was written for a browser in places it should not
    have been**: a hard-coded `.png` on evidence names, five probes named as
    browser gestures with no way to answer "no meaning here", "one read-only
    `SELECT`" pushing a JSON-dump stand toward quoting SQL it never ran, and a
    tripwire warning that read as though the agent's own captures voided its
    run. All fixed against a real CLI stand.
  - **The step hand-off carried decisions but not scaffolding.** Fixed by
    asking for how to test what you built, for user-visible wording, and for
    any knowing divergence from neighbouring code *with its blast radius* —
    the last after a reviewer observed that "the rulebook wins" and "a
    neighbour's bug is out of scope" only produce the right outcome together,
    and nothing recorded that the result was deliberate.
- **The old pipeline GIF is retired.** The new animation draws the pipeline as
  a graph itself, so keeping both meant two renderings of the same thing and
  1.9 MB of duplicate raster in the repository. `docs/pipeline.html` stays —
  it is the source of the interactive version the README links, which is a
  different medium and still worth having.
- **Milestones are numbered `M<n>` in every example and docstring**, where
  they used to be `E<n>` (and `Э<n>` in the Russian diagram). `M` for
  milestone reads as what it is in either language, where `E` was a leftover
  from «этап» that meant nothing in English. Nothing parses the prefix —
  `plan.markers.milestone` keys on the status glyph — so this changes examples
  and nothing else; existing plans keep whatever they use.
- **The gate no longer truncates the owner's ledger.** `--write` wrote to
  `<tracker>/<milestone>/acceptance.md`, which `acceptance-loop` designates as
  the owner's hand-written record of what acceptance missed. Every later round
  replaced it wholesale. The verdict now goes to `acceptance-verdict.md` and
  the ledger is left alone.
- **A failed checklist item now blocks.** `blocked` consulted only findings and
  defects, so a report could mark every "done when" line `passed: false`, file
  nothing, and be told it may merge — the written shape of "could not", which
  `agents/acceptance.md` says is never "good". A failed item still needs no
  evidence, which was the deliberate rule and remains one: only a pass needs
  proof. It just no longer passes for done.
- **`acceptance-loop`'s Phase 3 now dispatches too.** It was the one phase still
  telling the orchestrator to fix by hand, which contradicted the new §2 of
  `autopilot` in the same run. Acceptance findings go into a fresh `step-loop`
  at `review.rounds.fix` — a fix arriving after acceptance deserves a review
  round of its own.
- **A tool-trimming change for the acceptance agent was written, reviewed
  three times, and withdrawn.** The agent inherits every installed tool, and on
  a project carrying several MCP servers that is tens of thousands of tokens of
  schema in each of a hundred turns — a real cost. The instruction to "spawn it
  with the tools its brief names" was, however, one no orchestrator can follow:
  `tools:` in agent frontmatter is static while `hands` and `truth` are
  per-project, and the spawn takes no tool list. It survived two review rounds
  as a self-consistent contradiction before the third checked whether anything
  implemented it. `acceptance-loop` now carries a note saying why the obvious
  fix does not work, so the next person spends their time elsewhere.

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
