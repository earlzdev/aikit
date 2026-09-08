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
    # A milestone heading carries its STATUS. That glyph is what separates a
    # milestone from a step and from a plain `##` section like "General rules"
    # — `^##+\s` matched all three, which cost the distinction the whole plan
    # format rests on.
    milestone: "^## [→✅]"
    step: "^### "
    done_when: "Готово, когда"
    acceptance: "приёмка"
    # Quoted KEYS on purpose: under YAML 1.1 — which PyYAML still speaks —
    # bare `yes:` and `no:` parse as the booleans true and false, so the two
    # keys vanish and the marker lookup silently finds nothing.
    "yes": "да"
    "no": "нет"

# Optional. Where the INSTALLED PLUGIN lives — the directory holding `bin/`,
# not `bin/` itself. Set it when the plugin is somewhere the cache glob does
# not reach, or when several versions are cached and the glob picks the wrong
# one. `/aikit:init` prints the version it resolved so you can tell.
# plugin_root: /Users/you/.claude/plugins/cache/aikit/aikit/0.4.0

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
  # Optional. Omit either key — or the whole block — to inherit the model the
  # run is already using. This is a QUALITY dial that happens to be a cost
  # dial; see "Keys that carry weight". Shown commented out because absent and
  # empty are NOT the same: `reviewer:` with nothing after it is a null, not an
  # omission.
  # model:
  #   implementer: opus
  #   reviewer: sonnet
  rounds:
    develop: 3          # cap for a normal implementation step
    fix: 2              # cap for a fix or refactor

acceptance:
  rounds: 3
  # model: sonnet       # optional, as above — omit the key to inherit
  budget:
    actions: 120
    minutes: 45
  # The two commands aikit cannot write for you — see docs/harness.md.
  stand:
    up: "scripts/acceptance/stand.sh up"
    down: "scripts/acceptance/stand.sh down"
  # Hands and truth source. `kind` says how the agent reaches them:
  #   command — a shell command it runs
  #   mcp     — tools from an MCP server it already has
  #   skill   — a skill it invokes
  # The agent has EVERY tool the project has; these keys tell it which ones are
  # the hands for this product, so it does not spend budget guessing.
  hands:
    kind: command
    use: "scripts/acceptance/drive.py"   # omit to use aikit's own bin/drive
  truth:
    kind: command
    use: "scripts/acceptance/query.py"   # one read-only SELECT
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
  # Generated files this project TRACKS, which running it will touch. Anything
  # already gitignored never counts. Leave empty unless a run trips the gate on
  # a file nobody edited — `verdict tree --show` names what is dirty.
  tripwire_ignore: ["__pycache__", "*.pyc"]

git:
  main: main
  branch_prefix: "task/"
  pr: true
```

## Keys that carry weight

**`plan.markers`** — the plan is written for a human, so aikit matches its
words rather than imposing a schema. `milestone` must NOT match a step or a
plain section heading: milestones are the unit that merges and goes through
acceptance, steps are the unit that goes through review, and a marker that
matches both silently turns every step into a milestone. Keying on the status
glyph is what keeps them apart. The defaults above are the Russian
wording of the project this pipeline grew in; a project writing its plan in
English sets `done_when: "Done when"`,
`acceptance: "acceptance"`, `yes: "yes"`, `no: "no"`.

**`zones[].paths`** — a **routing key, not a permission fence.** It answers
"which `verify` and which `rulebook` apply to this change", and nothing more.
Files belonging to no zone are normal — a `Makefile`, CI config — and a change
touching only those runs `verify_all`. In particular an agent is not confined
to the paths of the zone it was given: a zone whose `verify` is
`unittest discover -s tests` is *pointing at* `tests/`, so a step that writes a
test there is in scope even when `paths` lists only the source tree. A reviewer
reading `paths` as a write boundary files an inflated scope violation, which is
the most expensive false positive there is — it burns a whole round.

**`zones[].verify`** — the single most-used key. The step loop's self-gate
runs the changed zone's command; a reviewer is told to run it itself rather
than trust a claim. A zone whose verify command is missing or wrong turns
every review round into a reading exercise.

**`review.model` / `acceptance.model`** — aikit ships **no default here on
purpose**. Every agent inherits the model the run is already using unless you
say otherwise, and the temptation is to set the reviewer to something cheap:
it reads a diff against a rulebook, which sounds like undemanding work. It is
not. The reviewer is the gate, and the whole claim of this pipeline is that
nothing passes on the author's own word — a gate that misses things returns the
project to exactly the state it was in before, while still costing a round.
Move the implementer or the acceptance agent first if you are trimming spend,
and treat lowering the reviewer as a decision to revisit the moment
`<tracker>/<milestone>/acceptance.md` starts collecting "acceptance missed
this" lines.

**`acceptance.stand`** — must bring up a DISPOSABLE stand and must never
point at production. The acceptance agent clicks everything, types a
thousand characters into fields, and abandons flows halfway on purpose. That
belongs somewhere that gets torn down afterwards.

**`acceptance.truth`** — read-only, one `SELECT`, no write privileges *in the
database role*, not merely by instruction. This is what separates "works"
from "works, but lies", and an acceptance agent that could write a row would
one day help itself to one instead of reporting that the button didn't
create it.

**`acceptance.tripwire_ignore`** — the acceptance agent holds editing tools, so
the gate checks the repository did not move during its run. Using a product
mutates a repository, though: this is the list of generated paths that do not
count. Keep it short. Every entry here is a place the tripwire stops watching.

**`acceptance.entrypoints`** — addresses and human-facing notes only. If a
reader could learn from this block WHICH FILES changed, it is over-specified
and the acceptance phase is worth less.

## What aikit does NOT read

No key points at source files, module names, or a diff. The acceptance agent
could read the source — a shell alone is enough — but nothing here tells it
where to look, and the gate accepts only evidence the PRODUCT produced.
Reading the implementation earns it nothing and costs the check.
