# `aikit.yml` — the project's answers

<!--
WHAT: The one file aikit reads. Every skill, both agents and both binaries
      take their project-specific values from here.
WHY:  the predecessor of this plugin substituted
      values into copied template files at scaffold time. That works exactly
      once. Two projects rendered from it sat five kit versions behind with
      no upgrade path, because a rendered copy can only be re-rendered over
      the owner's local edits. Reading values at RUNTIME means the method can
      ship a new version and change nothing in the project.
HOW:  drop this file at the repo root. `/aikit:init` writes a first draft by
      interview; after that it is hand-edited like any other config.
-->

One file at the repo root. Nothing else in the project is aikit's to own.

```yaml
version: 1

# Language the owner is addressed in. Model-facing instructions are always
# English (a model reads English instructions fine whatever the conversation
# language); this key controls only what is written FOR THE HUMAN — verdict
# text, reports, tracker entries.
language: ru            # ru | en

plan:
  path: docs/PLAN.md
  # The plan is prose a human reads, so its section markers are words, and
  # words differ per project. aikit never hardcodes them.
  markers:
    milestone: "^##+\\s"        # regex: what starts a milestone heading
    done_when: "Готово, когда"  # the checklist block's opening words
    acceptance: "приёмка"       # the line that decides whether acceptance runs
    yes: "да"
    no: "нет"

tracker: docs/tracker   # per-milestone artefacts, committed
evidence: .acceptance   # screenshots and dumps, NOT committed (gitignore it)

# How this project proves itself. One entry per zone; a zone is a path set
# with its own verify command and rulebook.
zones:
  - key: backend
    label: Backend
    paths: ["modules/**", "core/**"]
    rulebook: .claude/projects/01-backend-rulebook.md
    verify: "uv run pytest -q"
  - key: web
    label: Web
    paths: ["admin/**"]
    rulebook: .claude/projects/04-web-rulebook.md
    verify: "npm --prefix admin test"

# Run when a change touches more than one zone.
verify_all: "uv run ruff check . && uv run mypy && uv run pytest -q"

review:
  # Which persona reviews. `reviewer-strict` is the one aikit ships; name a
  # project persona instead if the project has zone reviewers of its own.
  reviewer: reviewer-strict
  rounds:
    develop: 3          # cap for a normal implementation step
    fix: 2              # cap for a fix or refactor

acceptance:
  rounds: 3
  budget:
    actions: 120
    minutes: 45
  # The two commands aikit cannot write for you — see docs/harness.md.
  stand:
    up: "scripts/acceptance/stand.sh up"
    down: "scripts/acceptance/stand.sh down"
  query: "scripts/acceptance/query.py"
  # Hands. Omit `drive` to use aikit's own `bin/drive`; set it to a project
  # command when the browser is only reachable from inside a container.
  drive: "scripts/acceptance/drive.py"
  browser:
    mode: cdp                       # cdp | local | project
    cdp: "http://127.0.0.1:9222"
  # What the acceptance agent is told it can reach. Names and addresses ONLY
  # — never a file path, never a module name (see docs/harness.md, "the brief
  # is the lock").
  entrypoints:
    - name: "Landing"
      url: "http://localhost/"
    - name: "Owner admin"
      url: "http://admin.example.test/"
      note: "sign in with the stand token in the stand's output"
  seed: "an empty client with a small token cap"

git:
  main: main
  branch_prefix: "task/"
  pr: true
```

## Keys that carry weight

**`plan.markers`** — the plan is written for a human, so aikit matches its
words rather than imposing a schema. The defaults above are the Russian
wording of the project this pipeline grew in; a project writing its plan in
English sets `done_when: "Done when"`,
`acceptance: "acceptance"`, `yes: "yes"`, `no: "no"`.

**`zones[].verify`** — the single most-used key. The review loop's self-gate
runs the changed zone's command; a reviewer is told to run it itself rather
than trust a claim. A zone whose verify command is missing or wrong turns
every review round into a reading exercise.

**`acceptance.stand`** — must bring up a DISPOSABLE stand and must never
point at production. The acceptance agent clicks everything, types a
thousand characters into fields, and abandons flows halfway on purpose. That
belongs somewhere that gets torn down afterwards.

**`acceptance.query`** — read-only, one `SELECT`, no write privileges *in the
database role*, not merely by instruction. This is what separates "works"
from "works, but lies", and an acceptance agent that could write a row would
one day help itself to one instead of reporting that the button didn't
create it.

**`acceptance.entrypoints`** — addresses and human-facing notes only. If a
reader could learn from this block WHICH FILES changed, it is over-specified
and the acceptance phase is worth less.

## What aikit does NOT read

No key points at source files, module names, or a diff. The acceptance
agent's blindness to implementation is a property of the config's shape, not
a rule it is asked to follow.
