---
name: review-loop
description: Do a step of work, then loop an independent reviewer over the result until no critical or high issues remain. Use after any non-trivial change; every aikit phase with a review gate invokes this instead of describing a loop of its own.
---

# review-loop — do the work, then verify it independently until it holds

<!--
WHAT: the one review implementation aikit ships. Anything with a review phase
      invokes THIS rather than restating round caps, the verdict line and
      ping-pong detection in its own words.
WHY:  that used to be prose duplicated per command. A wrong instruction in one
      copy silently diverged from the others and nobody could tell which copies
      still had the bug.
HOW:  the invoker states the task, the round cap, and whether the work is
      already done. Everything project-specific comes from `aikit.yml`.
-->

## Inputs, stated by whoever invokes this skill

- **Task** — the original request, verbatim. If nothing was stated, STOP and
  ask. Never review nothing.
- **Round cap** — a number. Take it from `review.rounds` in `aikit.yml`
  (`develop` for an implementation step, `fix` for a fix or refactor) unless
  the invoker states one.
- **Starting point** — either **fresh** (the work does not exist yet, start at
  Phase 0) or **already done** (the invoker did the work and hands you a
  baseline ref — skip to Phase 2 using it as `<baseline>`).

Read `aikit.yml` at the repo root first. You need `zones` (each zone's `paths`,
`rulebook` and `verify`), `verify_all`, and `review`.

Roles are strictly separated: **the reviewer only reports, you only fix.** A
reviewer never edits files.

## Who reviews

Spawn the persona named by `review.reviewer` in `aikit.yml` with the Agent
tool. The default, `reviewer-strict`, ships with aikit and has no `Write` or
`Edit` in its tool list at all: it is *structurally* unable to touch code, not
merely asked not to.

Do not substitute "a fresh instance of the builder persona, told to review".
Such an instance still carries the full tool list it has everywhere else, and
is one bad turn from silently patching what it was supposed to report. Nothing
in the harness stops it — only an instruction.

Either way the reviewer has never seen this conversation, only the diff. That
independence is the point.

## Severity ladder

The single definition. Every aikit persona cites it rather than restating it —
a second copy is how "missing acceptance criterion" ends up Critical in one
file and Medium in another for no reason.

- **Critical** — wrong behaviour that breaks the feature, a missing acceptance
  criterion, or a security hole.
- **High** — real and blocking, short of critical: a scope violation, a rule
  violation, a failed verification run.
- **Medium** — real but non-blocking.
- **Low** — taste. Keep these few; a review that is mostly Low gets ignored,
  including its Criticals.

Only Critical and High are counted in the `VERDICT:` line and block the loop.
Medium and Low accumulate in the report body — see the carry-over rule.

## Phase 0 — baseline

Record the current git state so every later change is a reviewable diff:
`git add -A && git stash create`, or note the current `HEAD` when the tree is
clean. Remember it as `<baseline>`. If the repo has unrelated uncommitted
changes, say so before proceeding.

## Phase 1 — do the work

Complete the task, following the project's `CLAUDE.md` and the rulebook of each
zone you touch (`zones[].rulebook`).

**Self-gate before any review round** — cheap checks first, never burn a review
round on a missing import:

1. Run the changed zone's `verify` command, or `verify_all` when the change
   touched more than one zone.
2. Fix every failure yourself.
3. Only once green: commit a checkpoint (`review-loop: phase 1 complete`), note
   the changed files, and go to Phase 2.

## Phase 2 — review round N of the cap

Announce it: "Review round N of max `<cap>`." Spawn the reviewer. Its prompt
MUST contain:

1. The original task, verbatim — never a paraphrase.
2. The diff range: `git diff <baseline>..HEAD`. The reviewer reads files
   itself; do not paste file contents into the prompt.
3. The instruction to **run the project's verification itself** — the changed
   zone's `verify`, or `verify_all` for a multi-zone change — rather than trust
   any claim that it passed. A failure is automatically High, or Critical when
   it breaks the build project-wide.
4. For round ≥ 2: the previous round's full report, labelled "previously found
   and supposedly fixed — verify each fix independently before your own
   review."
5. The requirement that the report ends with exactly one line: `VERDICT: CLEAN`
   or `VERDICT: <n> critical, <m> high`.

## Phase 3 — fix, then decide

**Fixing is yours alone.** Fix every Critical and High with a minimal diff — no
unrelated refactoring. If you disagree with a finding, leave the code as it is,
record the disagreement, and raise it in Phase 4. Never drop a finding
silently. Re-run the Phase 1 self-gate after fixing, then commit
(`review-loop: round N fixes`).

**Loop decision:**

- `VERDICT: CLEAN` (or `0 critical, 0 high`) → Phase 4. Converged.
- Otherwise → a NEW round with a FRESH reviewer instance.
- **Ping-pong detection.** Keep a ledger of `file + one-line description`
  fingerprints across rounds. If round N re-reports something already fixed, or
  flags code that was itself written to satisfy an earlier finding, that is
  reviewer disagreement rather than progress — STOP, keep the current state,
  and escalate both positions in Phase 4.
- **Round cap reached** with Criticals or Highs still open → stop, keep every
  fix made so far, and list what is unresolved. Do not quietly continue.

**Carry-over.** Append every Medium and Low from each round to one deduplicated
list. A fresh reviewer will not re-find them all, and nothing may be lost
between rounds.

## Phase 4 — report

To the owner, or to whatever invoked this skill: what changed and the
checkpoint refs (`git diff <baseline>..HEAD`); one line per round (found /
fixed); the accumulated Medium and Low list; any finding you disagreed with,
both positions stated; and the outcome — **converged clean**, **stopped at the
round cap** (with what is still open), or **stopped on reviewer disagreement**
(with both sides).
