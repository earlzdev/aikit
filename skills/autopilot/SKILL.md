---
name: autopilot
description: Run the whole delivery pipeline unattended — plan into milestones, then for each milestone work its steps through review-loop, put the finished milestone through acceptance-loop, close it out and take the next one. Stops on a real blocker rather than guessing. Use when the owner wants work to continue without being asked about every step.
---

# autopilot — the pipeline, running without someone watching it

<!--
WHAT: the driver that strings plan → review-loop → acceptance-loop → close
      into one unattended run over a plan's milestones.
WHY:  each phase already exists and each is independently sound. What was
      missing was the thing that runs them in order without a person
      re-deciding at every seam, and — more importantly — a written boundary
      for what it may decide alone. An unattended loop with no boundary
      eventually merges something nobody agreed to.
HOW:  §1 preconditions, §2 the loop, §3 what it decides alone, §4 what stops
      it, §5 how it leaves the repo.
-->

Read `aikit.yml` first. If it is not there, stop and run `/aikit:init` — do not
improvise the values.

## 1. Before the first line of work

Check all of these, and stop on any that fails. They are cheap, and each one
has produced a wasted night somewhere:

1. **The plan exists and is approved.** `plan.path` has milestones, and the
   owner has said yes to them. No approval → invoke the `plan` skill and stop
   at its gate. Autopilot never approves its own plan.
2. **The working tree is clean**, or its changes are yours from an earlier run.
   Unrelated uncommitted work is the owner's; do not build on top of it and do
   not stash it away.
3. **You are on a work branch**, not `git.main`. Create
   `<git.branch_prefix><milestone>` if you are not.
4. **The zone verify commands run.** Run `verify_all` once, now, on untouched
   code. A suite that was already red makes every later review round
   meaningless — report it and stop.

State the milestone you are starting on, and the stop conditions from §4, in
one message before you begin. That message is what the owner reads when they
come back to a stopped run.

## 2. The loop

For each milestone in plan order, oldest unfinished first:

**A. Open it.** Read the milestone whole — text, reasoning, steps, "done when",
the acceptance line and the scenario. If the acceptance line is missing, stop
and ask (see the `acceptance-loop` skill: a missing line is not a "no").

**B. Each step, through review-loop.** For every `###` step in order, invoke the
`review-loop` skill with the step as the task and `review.rounds.develop` as
the cap. A step that ends "stopped at the round cap" or "stopped on reviewer
disagreement" ends the milestone too — go to §4.

**C. The milestone, through acceptance.** Once every step is clean:

- acceptance **yes** → invoke the `acceptance-loop` skill with the milestone's
  number, full text, checklist, scenario and `acceptance.rounds`. Its verdict
  decides whether this milestone may close.
- acceptance **no** → skip to D, and say in the report that this milestone
  closed without acceptance because the plan said so.

**D. Close it out.** Run `verify_all`. Mark the milestone `✅` with today's date
in the plan **in the same commit as the work**. Commit, and open a PR when
`git.pr` is true. Write one paragraph into the milestone's tracker directory:
what landed, how many review rounds, the acceptance verdict.

**E. Take the next one** — and re-read the plan file before you do. A milestone
three ahead was written before anything was built; if what you just learned
changes it, say so and adjust it before starting rather than halfway through.

Announce each milestone as you open and close it. An unattended run that
reports only at the end is indistinguishable from a hung one.

## 3. What you decide alone

Everything the plan already settled, and everything below it:

- how to implement a step, which files to touch, how to structure the code;
- fixing anything a reviewer or the acceptance agent finds;
- adding tests, fixtures, migrations and scaffolding a step needs;
- ordinary refactoring *inside* a step's own scope;
- retrying a flaky run once, and saying in the report that you did.

You do not need permission for any of that, and asking about it defeats the
point of running unattended.

## 4. What stops you

Stop, keep everything done so far, and report. Never work around any of these:

- **The round cap is spent** — in review or in acceptance — with blocking
  issues open. The unresolved list goes in the report.
- **Ping-pong** — a reviewer reversing an earlier round's finding. Both
  positions to the owner; do not pick a side by editing.
- **A blocking acceptance finding you disagree with.** Leave the code, state
  both positions. Only the owner lifts a block, and lifting is a written line
  (`acceptance-loop`, Phase 3).
- **The stand will not come up**, or a budget runs out mid-acceptance. That is
  "could not", never "good".
- **The plan is wrong** — the milestone as written cannot be built, or turns
  out to mean something else. Say so. Do not build your own interpretation of
  it.
- **The scope grows.** A milestone that turns out to need work the plan does
  not mention is a new milestone for the owner to approve, not a bigger one for
  you to finish.
- **Anything irreversible or outward-facing** that the plan did not name:
  touching production, deleting data, force-pushing, rewriting published
  history, rotating a credential, sending anything to a third party.
- **A secret would have to be read or written** to continue.

When you stop: the repo must be in a state the owner can look at. Commit what
is green, say what is uncommitted and why, and never leave a half-applied fix
behind an unexplained failure.

## 5. The report

At every stop — a finished plan, or a blocker — write the owner, in
`language`:

- which milestones closed, each with its review-round count and acceptance
  verdict;
- which milestone stopped the run, and on which of §4's conditions;
- everything still open: the carried-over Medium and Low findings from every
  review round, and the "works, but awkward" findings from every acceptance;
- what you decided that the plan did not cover, so it can be disagreed with;
- the exact next action you would take if told to continue.

That last line is what makes a stopped run cheap to resume. Write it even when
the run finished cleanly.
