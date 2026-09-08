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
  It is the unit that goes through step-loop.

Milestones are numbered **`M<n>`** — M for milestone — and a step carries its
milestone's number with a suffix: `M57.1`, `M57.2`. On a project with no plan
yet, start at `M1`. Nothing parses the prefix, so a project that already
numbers differently keeps its own scheme; §"Producing a plan" step 1 says the
existing file wins. `docs/plan-format.md` in this plugin is the same format
written out at length, with a worked example — read it if anything below is
ambiguous.

```markdown
## → M57 — A new client's file carries its card data · planned 2026-09-07

<What changes, in prose, with the reasoning. "Why" matters more than "what"
here: it is what the acceptance agent uses to tell a deliberate omission from
an unfinished one. Without it, a capability left out on purpose gets filed as
a bug.>

### M57.1 — The parser accepts the card block
### M57.2 — The web form writes it back

**E2E:** <the tests that must be green, by name, or "none">

**Done when** <the criteria a person can check — not "the code is written",
but what becomes true for whoever uses it. One line each, as many as the
milestone needs; this block is the acceptance agent's whole specification, and
it walks it point by point.>

acceptance: yes
<The owner's scenario, in words: how a person actually uses this. Required
whenever acceptance is yes.>
```

Use the words from `plan.markers` rather than the English above — a project
whose plan is Russian writes `**Готово, когда**` and `приёмка: да`, and the
markers config is what tells every skill where to look. `**E2E:**` is the one
exception: it has no marker because nothing looks for it mechanically, so keep
it in that literal form whatever language the plan is in.

**Mark state in the heading — `→` planned, `✅` done, each with its date — and
that glyph is not decoration.** It is what `plan.markers.milestone` keys on, so it
is what separates a milestone from a step and from an ordinary `##` section
like "General rules". A heading-level match alone (`^##+`) catches all three
and silently turns every step into a milestone, which costs exactly the
distinction §1 calls load-bearing. `→` and `✅` are what the shipped default
matches; a project that configures `plan.markers.milestone` differently uses
whatever its own regex keys on, and this skill follows the config rather than
the two glyphs named here. Finished
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

**The acceptance line.** Every milestone carries an explicit yes or no, and
the answer is the owner's:

- **yes** — there is an interface a person walks through. Requires a scenario
  in words, right there in the milestone.
- **no** — nothing to click (a migration, a refactor, an internal contract).
  A deliberate answer, not a forgotten line.

**On a plan you are writing, propose it.** The owner has not seen the milestone
yet — that is what the gate in §4 is for — so there is no answer of theirs to
transcribe. Write the line you think is right, write the scenario if you wrote
`yes`, and list every acceptance line you proposed when you present the plan,
so the gate is where they are actually decided. Proposing is not deciding; the
plan is not approved until the owner says so.

**On a plan that already exists, do not touch it.** A milestone whose line is
missing gets a question, not a default: say it is missing and ask. A missing
line is never a default of "no".

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
  to every milestone below, saves repeating them in each one. It is a `##`
  heading with **no status glyph**, so it is not a milestone and needs no "done
  when" and no acceptance line — that is the case the status-glyph marker
  exists to exclude.
- **Commit the plan when you write it**, before the approval gate. A plan that
  exists only in a conversation is lost with the conversation. The commit is
  not the approval: approval is the owner saying yes, and `autopilot` asks when
  it cannot tell that it has one.
- **`**E2E:**` may say `none`** — but say which `none` it is. "This project has
  no end-to-end suite" and "this milestone needs no e2e" read identically and
  mean different things, so name the gate that does apply instead of leaving a
  reader to wonder whether a suite was forgotten.

## Producing a plan

1. Read the existing `plan.path` if there is one — the numbering, the wording
   and the conventions in it beat anything suggested here. If you were given
   nothing to plan, read that file and ask the owner what comes next. Never
   invent a plan for a project that did not ask for one.
2. Ask whatever you genuinely cannot infer. Scope, ordering and the acceptance
   line are the owner's; structure is yours.
3. Write the milestones. For each: the prose with reasoning, the steps, the
   "done when", the acceptance line, and a scenario when acceptance is yes.
4. Present them for approval — including every acceptance line you proposed.
   Do not start building.

Two things people ask that the shape above does not answer. **Numbering** on a
fresh plan starts at `M1`. **The plan commit** goes on the branch you are
already on: a plan is not a task and does not take `git.branch_prefix`, and
putting it on a branch of its own hides `plan.path` from anything reading the
working tree on `main` — autopilot included.
