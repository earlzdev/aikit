---
name: acceptance-loop
description: After review-loop, put a finished milestone through acceptance — a separate agent walks the feature by hand on a disposable stand, without the diff, and says whether it is fit for a person. Runs only on a milestone whose plan line says acceptance is required.
---

# acceptance-loop — the second check beside review: is this fit to use?

<!--
WHAT: the phase between review-loop and merge. Review answers "is the code
      right?". Acceptance answers a different question: "can this be used?"
WHY:  a test suite checks what the author foresaw, which is why the findings
      that matter keep arriving through the owner's own eyes while the suite
      is green. What was missing was never more tests — it was A LAYER OF
      JUDGEMENT.
HOW:  bring up a disposable stand, assemble a BRIEF (no diff!), run the
      `acceptance` agent, put its report through a mechanical gate, and decide
      whether the milestone may merge. Rounds work like review-loop's.
-->

Read `aikit.yml` first: `acceptance` (rounds, budget, stand, hands, truth,
browser, entrypoints, seed), `plan.markers`, `tracker`, `evidence`, `language`.

## When this phase exists, and when it does not

**Only when the milestone's plan entry says so** — the line matched by
`plan.markers.acceptance` inside its "done when" block, and nothing else.

- acceptance **yes** → the phase is MANDATORY. It cannot be skipped. A stand
  that did not come up, a spent budget, an agent that did not get there — all
  of those are "could not", not "good", and the merge waits.
- acceptance **no** → there is no phase, and that is the owner's deliberate
  answer rather than a forgotten line: a milestone with no interface has
  nothing to click, and a stand plus a live model costs money.
- **the line is missing entirely** → do not assign the phase yourself and do
  not decide on the owner's behalf. Say the line is missing and ask.

Beside that line the owner writes a **scenario in words**. Without one the
acceptance agent wanders: the checklist says what should exist, the scenario
says how the thing is used. No scenario — ask, do not invent one.

## Inputs, stated by whoever invokes this skill

- **Milestone** — its number and its FULL TEXT, reasoning included.
- **Checklist** — that milestone's "done when" block, verbatim.
- **The owner's scenario** — in words, from the milestone.
- **Round cap** — `acceptance.rounds`, default 3.

## What the acceptance agent does NOT get — the skill's central rule

No diff. No list of changed files. No account of how it was built. No module,
endpoint or component names.

The author knows where to click and steps over the rakes without noticing. An
agent holding the diff reproduces exactly that blindness: it checks what the
code says rather than what a person needs — becoming a second code review,
which the project already has.

**The brief is exactly four things**, and nothing beyond them (the agent is
stateless; the whole context is handed over on every run):

1. the milestone's text with its reasoning — "why" is what separates an
   unfinished thing from a deliberate decision; without it, a capability that
   is absent *on purpose* gets filed as a bug;
2. the "done when" checklist;
3. the owner's scenario, in words;
4. the hands and the truth source — from `acceptance.hands` and
   `acceptance.truth`, whether those are commands, MCP tools or a skill —
   plus `acceptance.entrypoints`, `acceptance.seed` and the output language,
   with **no project file names**.

The agent holds every tool the project has; item 4 tells it which of them reach
THIS product, so it does not spend a budget discovering that. Its blindness to
the implementation is not its tool list — a shell alone would defeat that — it
is this brief plus a gate that accepts only evidence the product produced.

While assembling the brief, reread it as a stranger would. If it lets anyone
work out WHAT WAS CHANGED IN THE CODE, cut that out.

## Phase 0 — the stand

Run `acceptance.stand.up` — a command, or the tool sequence it names. It must bring up a **disposable** stand and seed
whatever `acceptance.seed` describes — empty, deliberately: acceptance walks
the path from zero, like an owner with a new account, not through yesterday's
data where everything is already set up.

**Production, never.** If the stand does not come up, that is "could not":
report it and stop. Do not proceed to merge.

## Phase 1 — round N of the cap

**Fingerprint the working tree before you spawn anything:**

```
"$CLAUDE_PLUGIN_ROOT/bin/verdict" tree      # record this digest
```

The acceptance agent holds every tool this project has, editing tools included.
"You only report, the author fixes" is an instruction it could talk itself out
of on a long run, so Phase 2 hands this digest back to the gate, which blocks
if the tree moved while the run was happening. A run that edited the code it
was judging is void, not passed.

Announce it: "Acceptance, round N of `<cap>`." Spawn the `acceptance` agent
(Agent tool) with the four-part brief, the round number, and the budget from
`acceptance.budget` (`--max-actions`, `--minutes`).

There are three spend limits and they are not a suggestion: whatever cap the
stand's seed applies, the action count, and the run timeout (both enforced
inside the driver). Hitting one produces "got this far, and why" in the report
instead of a run that silently trails off.

For round ≥ 2 add ONE line to the brief: "the previous round found these,
check them again" — with the findings, and **no account of how they were
fixed**.

## Phase 2 — the gate

```
"$CLAUDE_PLUGIN_ROOT/bin/verdict" gate <milestone> \
  --tracker <tracker> --evidence-root <evidence> --lang <language> \
  --expect-tree <the digest from Phase 1>
```

The gate is mechanical and returns non-zero in three cases:

- there is a finding of class **broken** or **lies**;
- **the report is defective**: no "what I could not check" line, one of the
  five probes unanswered, a checklist item marked passed with no evidence, not
  one screenshot or not one database row;
- **the working tree moved during the run** — or could not be fingerprinted at
  all, which fails closed for the same reason a stand that did not come up is
  "could not" and never "good".

None of the three can be lifted by an owner override except a finding: an
incomplete run and a void run are not opinions to disagree with.

A defective report blocks exactly like a breakage, deliberately: an acceptance
run that never looked at the data has not earned the right to say "good". When
the gate objects to the report, that is **not** a reason to edit the report by
hand. Hand the agent its own output back and ask it to complete it.

Class **clumsy** does not hold the merge — it goes to the owner as a line.

## Phase 3 — fixing, and the round decision

**The AUTHOR fixes** — you, the orchestrator. The acceptance agent only
reports. Same separation of roles as review-loop. After each fix:

1. re-run the affected zone's `verify` command from `aikit.yml`;
2. **run acceptance again, WHOLE** — not "just recheck that point". A fix
   breaks its neighbour, and an acceptance that only revisits what was fixed
   cannot see that by construction;
3. a new round means a FRESH instance of the agent.

Decision:

- gate returned 0 → Phase 4, acceptance passed;
- otherwise → a new round, until the cap is spent;
- **cap spent** → stop, keep every fix, report to the owner with what remains
  open. Do not merge.

If you disagree with a finding, do not edit the code and do not drop the
finding silently. Leave it, and put both positions to the owner. **Only the
owner lifts a block**, and lifting is written as a line in
`<tracker>/<milestone>/acceptance-override.md`:

```
- lifted by owner: <the finding's text, verbatim> — <reason>
```

The gate reads that file itself. The record is required not as ceremony: it is
the only way to see how often the acceptance agent is wrong.

## Phase 4 — close out

```
"$CLAUDE_PLUGIN_ROOT/bin/verdict" gate <milestone> --write ...   # verdict into the tracker
<acceptance.stand.down>                                          # the stand is disposable
```

Only the verdict and the findings, as text, are committed to the milestone's
tracker. Screenshots and tree dumps stay in `<evidence>/<milestone>/` on the
machine and out of git — otherwise the repository swells with pictures and the
history holds nothing readable.

To the owner, in `language`: the verdict, findings by class, the "what I could
not check" line, the run's spend, and the number of rounds.

## Keeping score afterwards

Deliberately seeding breakages as regular calibration is **rejected**: "said
ok, then said not-ok once something was broken" proves only that the agent is
not blind, while what actually harms us is leniency. Measure differently:
**every finding the owner makes after a green acceptance is written as a line
in `<tracker>/<milestone>/acceptance.md`** — "acceptance missed this". Three or
four such lines in a row is the signal to fix this instruction, or to raise the
agent's model, which is the cheapest lever available. Seeded breakage stays a
one-off tool for a specific occasion — when the score has gone bad and it is
unclear whether the agent got dull or the instruction is poor.
