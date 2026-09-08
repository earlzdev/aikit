# aikit

A delivery pipeline for [Claude Code](https://claude.com/claude-code) that can
run without someone watching it.

Plan the work into numbered milestones. Take each step through a reviewer that
**cannot edit code**. Take each finished milestone through an acceptance agent
that **never sees the diff**. Nothing passes on the author's own word.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/pipeline-dark.gif">
  <img alt="One task moving through the aikit pipeline: plan, owner gate, then each step through the review loop and the milestone through the acceptance loop before it closes. Round one fails in both loops." src="docs/pipeline-light.gif" width="900">
</picture>

Round one fails in both loops above, on purpose — the loop is the product, and a
clean straight-through run would show you the opposite of what this does.
[**Watch it interactively →**](https://claude.ai/code/artifact/00501ab2-7b5e-470b-b5bf-8a71054e279c)
· regenerate the GIF with `node docs/capture.mjs dark out/frames` (see
[`docs/capture.mjs`](docs/capture.mjs)).

## Why it exists

A test suite checks what the author foresaw. That is a real limit, not a
staffing problem — which is why the findings that matter keep arriving through
the owner's own eyes while the suite is green. Adding more tests does not fix
it. What is missing is a **layer of judgement**: someone who uses the thing and
says whether a person could.

aikit adds two such layers, and both work the same way — by taking something
away rather than by asking nicely:

| | how it is independent |
|---|---|
| `reviewer-strict` | has no `Write` or `Edit` tool at all — it *cannot* patch what it reviews |
| `acceptance` | its brief contains no file names — looking for the code destroys the only check it exists for |
| the gate (`bin/verdict`) | a program, not a paragraph: an incomplete report exits non-zero exactly like a breakage |

A rule enforced by an instruction holds until the first long run. A rule
enforced by a missing tool holds always.

## Install

```
/plugin marketplace add earlzdev/aikit
/plugin install aikit
```

Then, in a project:

```
/aikit:init
```

It reads the repo, asks only what it cannot infer, writes one `aikit.yml`, and
**proves the pieces run** rather than declaring success.

## Use

```
/aikit:plan  <what to build>     # milestones, each with its own "done when"
/aikit:autopilot                 # run the pipeline until done or genuinely blocked
```

or a single piece on its own — each skill is invocable by name:

```
/aikit:review-loop <task>        # do it, then loop an independent reviewer
/aikit:acceptance-loop <n>       # walk a finished milestone by hand
```

## One config, not copied templates

Everything project-specific lives in one `aikit.yml` at the repo root, read at
**runtime**:

```yaml
zones:
  - key: backend
    paths: ["src/**"]
    verify: "pytest -q"
verify_all: "ruff check . && pytest -q"
review:
  rounds: { develop: 3, fix: 2 }
```

This is the design decision the whole plugin turns on. aikit's predecessor
substituted values into copied template files at scaffold time — which works
exactly once. Two projects built that way ended up five versions behind with no
upgrade path, because a rendered copy can only ever be re-rendered over the
owner's own edits. Reading the values at runtime means upgrading aikit changes
nothing in the project.

Full reference: [`docs/config.md`](docs/config.md). Worked examples:
[`docs/examples/`](docs/examples/).

## What ships

```
skills/     init · plan · review-loop · acceptance-loop · autopilot
agents/     reviewer-strict · acceptance
bin/        verdict (the gate) · drive (browser hands)
```

`bin/verdict` is dependency-free Python and unit-tested — it is the piece that
decides whether a milestone may merge, so it is the piece that has to be right:

```
python3 -m unittest discover -s tests
```

## What your project supplies

Two commands, and only if you want the acceptance phase at all. Leave the
`acceptance` block out of `aikit.yml` and the phase does not exist — the right
configuration for anything with no interface to walk.

- **a disposable stand** (`up` / `down`) — never production, torn down with its
  volumes;
- **a read-only query** — one `SELECT`, under a database role with no write
  privilege. Read-only as a property of the role, not as an instruction: an
  agent that *can* fix the stand to match its expectation eventually will.

Contract and worked example: [`docs/harness.md`](docs/harness.md).

Hands are optional — `bin/drive` attaches to a Chromium over CDP and gives the
agent an accessibility tree plus a screenshot after each action, enforcing the
action and time budgets itself. Point `acceptance.hands` at your own driver when
the browser is only reachable from inside a container — or at MCP tools, for a
stack that is not a browser at all. The agent holds every tool the project has;
`hands` and `truth` only tell it which ones reach this product.

## Status

`0.3.0`. What has actually been run, and what has not — the distinction matters,
because the two bugs found so far were both in code that had never executed.

**Exercised end to end**

- **`bin/verdict`** — 68 unit tests, plus a full pass in a scratch git repo:
  every gate path (blocking findings, each report defect, the owner override,
  `--no-db`, `--write`, a missing report) and both tripwire directions —
  a test suite writing bytecode does *not* trip it, a source edit does.
- **`bin/drive`** — every verb against a live headless Chromium: open, click,
  fill, type, press, wait, upload, reload, back, snap, and the action budget
  refusing once spent.
- **`reviewer-strict`** — run on a real diff. It ran the project's verify
  command itself, found the planted defect and both rulebook violations, rated
  an edge case Low rather than inflating it, returned a parseable `VERDICT:`
  line, and left the working tree byte-identical.
- **The acceptance loop, whole, twice** — against a toy app carrying one planted
  defect: the screen prints "Saved: <name>" and the row is never written. The
  agent brought up the stand, walked the owner's scenario, **queried the
  database rather than believing the screen**, and classed it `lies` — the
  class that exists for exactly this. It ran all five probes, attached 22
  screenshots and 10 database rows, wrote a 990-character "what I could not
  check" line, and found five defects nobody planted. The gate returned exit 1.
  The tripwire confirmed it edited nothing, though it holds every tool. A
  second round against the *repaired* app blocked again, correctly: it found a
  POST-then-reload that duplicated the contact on every refresh, and a name
  rendered into the page unescaped — screen and stored value disagreeing, which
  is also an injection hole. It verified the previous round's findings were
  fixed and corrected one of its own earlier conclusions with better reasoning.

- **`autopilot`** — a full milestone plus the handover into acceptance:
  preconditions (it caught that the run
  was starting on `main` and branched), step → review-loop → converged on round
  one, acceptance correctly skipped on a milestone marked `acceptance: no`,
  then `✅` written into the plan in the same commit as the work. Its stop
  conditions were checked too: a pre-red suite halts it before any work, and a
  blocking acceptance verdict keeps a milestone open.
- **`init` and `plan`** — run cold by agents that had only the skill text, in
  fresh projects. Both produced usable output and between them found six and
  four defects in their own instructions, all fixed in 0.2.3.

**Not yet run by anyone**
- The **Android path** in `docs/examples/android.aikit.yml`.

Two guarantees are hard — the reviewer has no editing tool in its process, and
the gate's exit code is a number. Everything else is procedure a model follows.

## Licence

MIT.
