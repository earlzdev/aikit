---
name: step-loop
description: Build one step of a plan, then loop an independent reviewer over the result until no critical or high issues remain. Delegates the building to a held implementer agent so the caller's context stays small. Use after any non-trivial change; every aikit phase with a review gate invokes this instead of describing a loop of its own.
---

# step-loop — build the step, then verify it independently until it holds

<!--
WHAT: the one build-and-review implementation aikit ships. Anything with a
      review gate invokes THIS rather than restating round caps, the verdict
      line and ping-pong detection in its own words.
WHY:  that used to be prose duplicated per command. A wrong instruction in one
      copy silently diverged from the others and nobody could tell which copies
      still had the bug.
WHY delegated by default. This skill loads into the CALLER's context — it is
      instructions, not a container. The context boundary comes from the agents
      it spawns. When the caller is `autopilot`, having it build twenty steps
      itself means one conversation holding twenty diffs, every verify run and
      every review report at once; the same work split across twenty
      short-lived implementers costs several times less for the same turns,
      because what each turn re-sends is bounded by one step instead of the
      whole plan. Nothing big may cross back over: the caller sees a summary
      and a verdict line, never a diff.
HOW:  the invoker states the task, the round cap, who does the building, and
      whether the work is already done. Everything project-specific comes from
      `aikit.yml`.
-->

## Inputs, stated by whoever invokes this skill

- **Task** — the original request, verbatim. If nothing was stated, STOP and
  ask. Never review nothing.
- **Round cap** — a number. Take it from `review.rounds` in `aikit.yml`
  (`develop` for an implementation step, `fix` for a fix or refactor) unless
  the invoker states one.
- **Who builds** — **delegated** (spawn an implementer agent and hold it across
  the loop) or **inline** (the caller does the work in its own context).
  **"already done" implies inline**: there is no implementer to hold when the
  work predates this skill, so the fixing falls to the caller.
  `autopilot` and any other unattended caller always passes **delegated**. A
  person invoking this skill by hand gets **inline** unless they ask otherwise:
  when someone is watching and wants to interject, the work belongs in the
  conversation they are watching.
- **Starting point** — either **fresh** (the work does not exist yet, start at
  Phase 0) or **already done** (the invoker did the work and hands you a
  baseline ref — skip to Phase 2 using it as `<baseline>`).
- **Step notes** — the path to this milestone's
  `<tracker>/<milestone>/step-notes.md`. Earlier steps of the same milestone
  leave their conventions there for the fresh implementer that has not seen
  them. **Pass it from the first step onward**: the path is well defined before
  the file exists, and withholding it until something has been written is how
  the chain never starts — step one writes nothing, so step two is handed
  nothing, so nothing is ever written. Absent only when the caller is not
  working through a milestone at all.

Read `aikit.yml` at the repo root first. You need `zones` (each zone's `paths`,
`rulebook` and `verify`), `verify_all`, `tracker` (only when you were given a
step-notes path to write back to), and `review` — including the optional
`review.model.implementer` and `review.model.reviewer`. When either is set,
pass it as the spawn's model; when it is absent, spawn without a model override
and let the agent inherit. Never substitute a model of your own choosing:
which model gates this project's work is the owner's call, written in their
config, and `docs/config.md` explains what it costs them.

Roles are strictly separated: **the reviewer only reports; building and fixing
are the builder's alone.** A reviewer never edits files.

## Who builds, and who reviews

**The implementer** — spawn the `implementer` agent (Agent tool) when the mode
is delegated. Spawn it ONCE per step and **keep it** for the whole loop: send
each round's findings back to that same agent with `SendMessage` rather than
spawning a fresh one. The agent that wrote the code is the only one that knows
why it chose what it chose; making a new agent re-derive that from a diff is
both more expensive and worse.

**The reviewer** — the persona named by `review.reviewer` in `aikit.yml`,
spawned **fresh every round**. The default, `reviewer-strict`, ships with aikit
and has no `Write` or `Edit` in its tool list at all: it is *structurally*
unable to touch code, not merely asked not to.

Do not substitute "a fresh instance of the builder persona, told to review".
Such an instance still carries the full tool list it has everywhere else, and
is one bad turn from silently patching what it was supposed to report. Nothing
in the harness stops it — only an instruction.

**Fresh per round is not an oversight, and holding the reviewer to save its
cold start is a false economy.** Its cold start — persona, `aikit.yml`,
`CLAUDE.md`, the rulebook — is byte-identical on every spawn and therefore
cached; what carrying it over would add instead is a whole round's transcript,
which is neither. And a reviewer that blessed something in round 1 is anchored
to bless it again in round 2. The previous round's report, handed in as
Phase 2's item 4, already does that job better.

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

## Phase 1 — build the step

**Delegated** — spawn the `implementer` agent. Its brief is:

1. the task, verbatim — never a paraphrase;
2. the milestone or surrounding context it belongs to, so it knows what the
   step is *for* without being told how to write it;
3. the zone(s) the step touches, with each zone's `rulebook` path and `verify`
   command from `aikit.yml`, and `verify_all`;
4. `<baseline>`; the step-notes file when you were given one; and the
   milestone's `carry-over.md` when it exists, said to be **read-only
   background** — a Low left open on an earlier step often constrains this
   one's design, and an implementer that has to discover the overlap between
   the two files works it out mid-step or not at all;
5. the instruction to run its own self-gate **and commit** before returning.
   Its persona says to commit a checkpoint when green; say so here too, so the
   two agree. You want the work committed at hand-off: Phase 2 hands the
   reviewer a diff range, and an uncommitted tree has none.

Keep its agent id. You will need it every round.

It returns a short summary and the list of files it changed. **That summary,
and nothing larger, is what enters your context** — do not ask it for the diff,
and do not read the diff yourself. The reviewer reads the diff; you do not need
to.

**Inline** — do the work yourself, following the project's `CLAUDE.md` and the
rulebook of each zone you touch (`zones[].rulebook`).

**The self-gate.** Cheap checks first — never burn a review round on a missing
import. **Delegated:** the implementer runs it and commits the checkpoint
itself; take the result from its report and do not re-run it, because re-running
puts the verify output back in the context this mode exists to keep empty. If
its report does not say the gate passed, that is the report being incomplete —
ask it, do not go and look. **Inline**, do it yourself:

1. Run the changed zone's `verify` command, or `verify_all` when the change
   touched more than one zone. **Send its output to a file and read the tail,
   or the failures only** — a red suite is thousands of lines and pasting it
   whole into a context buys nothing a `tail -40` does not.
2. Fix every failure.
3. Only once green: commit a checkpoint (`step-loop: phase 1 complete`), note
   the changed files, and go to Phase 2.

## Phase 2 — review round N of the cap

Announce it: "Review round N of max `<cap>`." Spawn a FRESH reviewer. Its
prompt MUST contain:

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

**Fixing belongs to whoever built.** Delegated: `SendMessage` the findings to
the held implementer — the whole report, verbatim, with the instruction to fix
every Critical and High with a minimal diff, re-run the self-gate, commit
(`step-loop: round N fixes`) and report back what it changed and anything it
disagrees with. Inline: do that yourself.

No unrelated refactoring. A finding you disagree with leaves the code as it is,
is recorded, and is raised in Phase 4. Never drop a finding silently.

**Loop decision:**

- `VERDICT: CLEAN` (or `0 critical, 0 high`) → Phase 4. Converged.
- Otherwise → a NEW round with a FRESH reviewer instance and the SAME
  implementer.
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

## Phase 4 — report, and let the implementer go

Let the implementer go — stop sending to it; the step is over and its context
has done its work.

**Write the step notes before you do**, whenever you were given a path. The
implementer's report ends with whatever the next step should reuse or match;
append those lines to that file, creating it if this was the first step.

**Give each file a header that states its own shelf life**, because the next
implementer may receive it without any of this prose around it — and a file
headed only `# M1` tells a reader working on M3 nothing about whether it still
binds:

```markdown
# <milestone> — step notes
Conventions established here. They bind later steps, and later milestones in
this codebase, until something supersedes them. Follow them; do not relitigate.

# <milestone> — carry-over
Non-blocking findings left open, with the reason each was left. Read them as
BACKGROUND: they tell you what is known-wrong so you do not mistake it for the
intended design. Do not fix them as part of another step.
```

That distinction is the whole value of handing over both. Where they disagree —
the notes say reuse a neighbour's shape, the carry-over says that shape is
subtly wrong — is exactly the decision the next step most needs to get right,
and it can only see the tension if it has both.
That report is your only source for them — you never read the diff — so a step
whose report omits them leaves the next implementer to rediscover the same
conventions. A file, not a held agent: re-readable, free between steps, and it
survives a stopped run. Inline, or with no milestone in play, there is nothing
to write and no file to create.

**And drop the round detail.** The reviewer reports you forwarded this step are
finished business the moment the step is. Keep the outcome and the carry-over
list; let the rest go. This skill runs in your context, so nothing evicts them
for you.

To the owner, or to whatever invoked this skill: what changed and the
checkpoint refs (`git diff <baseline>..HEAD`); one line per round (found /
fixed); the accumulated Medium and Low list; any finding the builder disagreed
with, both positions stated; and the outcome — **converged clean**, **stopped
at the round cap** (with what is still open), or **stopped on reviewer
disagreement** (with both sides).

Keep it to that. A caller running twenty of these in a row cannot afford a
transcript from each.
