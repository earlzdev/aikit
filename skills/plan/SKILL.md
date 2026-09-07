---
name: plan
description: Turn a request into a plan of numbered milestones in docs/PLAN.md — each with its own steps, its "done when" checklist, and an explicit yes or no on whether it needs acceptance. Use before building anything larger than one step, and to keep the plan honest as work lands.
---

# plan — break the work into milestones a machine can finish and a person can check

<!--
WHAT: authors and maintains the plan file every other aikit skill reads.
WHY:  autopilot needs a unit of work with an end. "Build the feature" has no
      end; a milestone with a written "done when" does. The checklist is not
      bureaucracy — it is the acceptance agent's only specification, and the
      only thing that makes "done" a fact rather than an opinion.
HOW:  §1 shape, §2 how to split, §3 the two gates, §4 keeping it honest.
-->

Read `aikit.yml` first: `plan.path`, `plan.markers`, `language`. The plan is
written in `language` — it is a document for the owner, not for a model.

## 1. The shape

Two levels, and the distinction is load-bearing:

- **Milestone** (`##`) — a numbered chunk of user-visible change with its own
  "done when" block. It is the unit that goes through acceptance and the unit
  that merges.
- **Step** (`###`) — a piece of a milestone that one pass of work can finish.
  It is the unit that goes through review-loop.

```markdown
## → E57 — A new client's file carries its card data · planned 2026-09-07

<What changes, in prose, with the reasoning. "Why" matters more than "what"
here: it is what the acceptance agent uses to tell a deliberate omission from
an unfinished one. Without it, a capability left out on purpose gets filed as
a bug.>

### E57.1 — The parser accepts the card block
### E57.2 — The web form writes it back

**E2E:** <the tests that must be green, by name, or "none">

**Done when** <the criterion, in prose a person can check — not "the code is
written", but what becomes true for whoever uses it>

acceptance: yes
<The owner's scenario, in words: how a person actually uses this. Required
whenever acceptance is yes.>
```

Use the words from `plan.markers` rather than the English above — a project
whose plan is Russian writes `**Готово, когда**` and `приёмка: да`, and the
markers config is what tells every skill where to look.

Mark state in the heading: `→` planned, `✅` done with the date. Finished
milestones stay in the file. The plan is the project's history as much as its
future, and a milestone deleted after landing takes its reasoning with it.

## 2. How to split

**A milestone ends in something a person can see.** If you cannot write its
"done when" as a sentence about what becomes true for a user, it is not a
milestone — it is a step, and it belongs inside one.

**A step is one pass of work.** If a step needs its own plan, it is a
milestone. If two steps cannot be reviewed apart from each other, they are one
step.

Anchors, not rules: three to seven steps in a milestone is comfortable. One
step means the milestone was really a step. A dozen means it should have been
two milestones, and the second one will be re-planned by the time you reach it
anyway.

**Order milestones so each one could ship alone.** Autopilot stops on a
blocker, and what has landed by then should be worth having.

## 3. Two gates, and only two

**The plan gate.** Nothing is built until the owner approves the plan. This is
the cheapest gate in the system and the one that prevents a fleet spending a
night building the wrong product. Present the milestones, wait, and do not
start on "obviously fine" ones in the meantime.

**The acceptance line.** Every milestone gets an explicit yes or no, written by
the owner. Do not decide it yourself and do not leave it out:

- **yes** — there is an interface a person walks through. Requires a scenario
  in words, right there in the milestone.
- **no** — nothing to click (a migration, a refactor, an internal contract).
  A deliberate answer, not a forgotten line.

When a milestone has no such line, say so and ask. A missing line is not a
default of "no".

## 4. Keeping the plan honest

- When a milestone lands, mark it `✅` with the date **in the same commit** as
  the work. A plan updated later is a plan nobody trusts.
- When reality diverges from the plan, edit the plan and say what changed and
  why — do not quietly build something else. If the project keeps a decisions
  log, the reasoning goes there and the plan links to it.
- Findings that arrive after a milestone is done become a NEW milestone, not an
  edit to the finished one. A closed milestone's text is what the acceptance
  agent was judged against; rewriting it destroys the record.
- A "general rules" section at the top of the file, for constraints that apply
  to every milestone below, saves repeating them in each one.

## Producing a plan

1. Read the existing `plan.path` if there is one — the numbering, the wording
   and the conventions in it beat anything suggested here.
2. Ask whatever you genuinely cannot infer. Scope, ordering and the acceptance
   line are the owner's; structure is yours.
3. Write the milestones. For each: the prose with reasoning, the steps, the
   "done when", the acceptance line, and a scenario when acceptance is yes.
4. Present them for approval. Do not start building.
