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
