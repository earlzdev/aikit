---
name: autopilot
description: Run the whole delivery pipeline unattended — plan into milestones, then for each milestone work its steps through step-loop, put the finished milestone through acceptance-loop, close it out and take the next one. Stops on a real blocker rather than guessing. Use when the owner wants work to continue without being asked about every step.
---

# autopilot — the pipeline, running without someone watching it

<!--
WHAT: the driver that strings plan → step-loop → acceptance-loop → close
      into one unattended run over a plan's milestones.
WHY:  each phase already exists and each is independently sound. What was
      missing was the thing that runs them in order without a person
      re-deciding at every seam, and — more importantly — a written boundary
      for what it may decide alone. An unattended loop with no boundary
      eventually merges something nobody agreed to.
WHY it dispatches rather than builds. Autopilot used to write every line of
      every step itself, which meant one conversation holding twenty diffs,
      every verify run and every review report by the end of a plan. What each
      turn re-sends grows with the whole run, so the last milestone of a plan
      costs several times the first for the same work. Now the building happens
      in a held implementer per step and the reviewing in a fresh reviewer per
      round; autopilot sees summaries and verdict lines. Same work, bounded
      context — and the thing that decides a step is done is no longer the
      thing that wrote it.
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
   code — output to a file, read the tail or the failures, never the whole
   green suite. A suite that was already red makes every later review round
   meaningless — report it and stop.

State the milestone you are starting on, and the stop conditions from §4, in
one message before you begin. That message is what the owner reads when they
come back to a stopped run.

## 2. The loop

**You dispatch; you do not build.** Every line of code in an autopilot run is
written by an implementer agent inside `step-loop`, and judged by a reviewer
that cannot edit. You read the plan, hold the ledger, run the gates, commit and
report. Doing a step yourself "because it is small" is the failure this
structure exists to prevent: it puts the author and the closer back in one
head, and it is how the run's context grows until the last milestone costs
several times the first.

Keep out of your own context, deliberately: diffs, file contents, full verify
output, and agent transcripts. If you find yourself reading a diff, the thing
that needed it was the reviewer.

For each milestone in plan order, oldest unfinished first:

**A. Open it.** Read the milestone whole — text, reasoning, steps, "done when",
the acceptance line and the scenario. If the acceptance line is missing, stop
and ask (see the `acceptance-loop` skill: a missing line is not a "no").

**B. Each step, through step-loop.** For every `###` step in order, invoke the
`step-loop` skill with:

- the step as the task, verbatim;
- `review.rounds.develop` as the cap;
- **who builds: delegated** — always, without exception. Unattended is exactly
  the case the delegated mode exists for.

`step-loop` runs **in your own context** — it is a procedure, not a subagent —
so nothing evicts a step's working detail for you. What you keep past a closed
step is the outcome and the carry-over list, and that is all. The reviewer
reports you forwarded during its rounds, the implementer's file lists, the
verify results: let all of it go. A step that ends "stopped at the round cap" or
"stopped on reviewer disagreement" ends the milestone too — go to §4.

**Step notes.** Each step's implementer is a fresh agent that has not seen the
earlier steps of this milestone, so what they established — a helper to reuse, a
convention to match, a decision not to relitigate — travels in a file rather
than in a held agent: re-readable, free between steps, and it survives a stopped
run. Pass `<tracker>/<milestone>/step-notes.md` to **every** step-loop of this
milestone, the first one included; `step-loop` Phase 4 does the writing, and the
path is well defined before the file exists.

**Carry-over, in the same breath.** As each step closes, append that
step-loop's Medium and Low list to `<tracker>/<milestone>/carry-over.md`. Do it
then, not at the end: §5's report cites this file rather than reciting it, and
by the end you will no longer be holding what it needed to say.

**C. The milestone, through acceptance.** Once every step is clean:

- acceptance **yes** → invoke the `acceptance-loop` skill with the milestone's
  number, full text, checklist, scenario and `acceptance.rounds`. Its verdict
  decides whether this milestone may close.
- acceptance **no** → skip to D, and say in the report that this milestone
  closed without acceptance because the plan said so.

**D. Close it out.** Run `verify_all` — again to a file, tail only. Mark the
milestone `✅` with today's date in the plan **in the same commit as the
work**. Commit, and open a PR when `git.pr` is true. Write one paragraph into
the milestone's tracker directory: what landed, how many review rounds, the
acceptance verdict.

By now that directory should already hold the two files the run wrote as it
went, rather than a recital assembled from memory at the end:
`<tracker>/<milestone>/step-notes.md`, appended as each step closed, and
`<tracker>/<milestone>/carry-over.md`, where each step-loop's Medium and Low
list went. §5 cites these; nothing else has to remember them.

**E. Take the next one** — and re-read the plan file before you do. A milestone
three ahead was written before anything was built; if what you just learned
changes it, say so and adjust it before starting rather than halfway through.

Announce each milestone as you open and close it. An unattended run that
reports only at the end is indistinguishable from a hung one.

## 3. What you decide alone

Everything the plan already settled, and everything below it:

- how a step gets implemented, which files it touches, how the code is
  structured — decided by the implementer inside `step-loop`, on your
  authority, without coming back to you;
- getting anything a reviewer or the acceptance agent finds fixed — by the
  implementer still holding that step, or by a fresh `step-loop` when the
  milestone's code is already finished;
- adding tests, fixtures, migrations and scaffolding a step needs;
- ordinary refactoring *inside* a step's own scope;
- retrying a flaky run once, and saying in the report that you did.

An acceptance finding is the one thing you send to a *fresh* `step-loop` rather
than to the implementer that built the step. The milestone's code is finished
by then, so there is no implementer left holding it, and a fix arriving after
acceptance deserves a review round of its own.

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
- everything still open — **by reference, not by recital**: each step-loop's
  Medium and Low list is appended to `<tracker>/<milestone>/carry-over.md` as
  the step closes, and each acceptance's "works, but awkward" findings beside
  it. The report cites those files with a count and the few that actually
  matter. Holding every Medium from every round of a whole plan in your head to
  list it at the end is what made the last milestone of a run the most
  expensive one;
- what you decided that the plan did not cover, so it can be disagreed with;
- the exact next action you would take if told to continue.

That last line is what makes a stopped run cheap to resume. Write it even when
the run finished cleanly.
