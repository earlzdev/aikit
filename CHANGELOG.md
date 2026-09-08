# Changelog

Newest first. What changed, and why.

## 0.1.1 — 2026-09-08

- **Dropped `commands/`.** A command and a skill sharing a name both register
  under `/aikit:`, so the picker showed `/aikit:autopilot` twice (and `init`
  and `plan` likewise). The commands only forwarded `$ARGUMENTS`, which skills
  already take, so the skills are now the single entry point. The two nudges
  that lived only in a command file moved into the skill they belonged to:
  what to do when `plan` is invoked with nothing to plan, and that anything
  the owner said when invoking `init` is an answer already given.

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

## Unreleased

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
