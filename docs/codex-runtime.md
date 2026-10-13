# Codex runtime contract

Read this before running any aikit workflow in Codex. It adapts the shared
skills and agent procedures; those remain the source of the pipeline rules.

## Installation and binaries

Build with `python3 bin/codex-kit build --output out/codex`. The generated
`out/codex/aikit` is a self-contained plugin with all six skills, all five role
procedures, the three existing tools, and the Codex runner. Never maintain a
second copy of a workflow in the generated package.

In a packaged skill, resolve the package root from the skill file's location
(two parents above its directory). `plugin_root` in `aikit.yml` may override
that location; verify it contains `bin/codex-kit` and `bin/verdict`. Do not use
`CLAUDE_PLUGIN_ROOT`, Claude's cache glob, or Claude's manifest in Codex. Read
the version from the package's root `plugin.json`. When working from this
checkout, the root holding this document and `bin/` is the package root.

Invoke sibling workflows by reading `skills/<name>/SKILL.md` in that package
and executing their procedure in the caller's context. Do not assume Claude's
`/aikit:*` commands or its Skill tool exist. Read `AGENTS.md` and applicable
nested rules alongside any existing `CLAUDE.md` and configured zone rulebooks.

## Roles, context and permissions

For orchestrated runs, use the local `aikit_roles.run_role` MCP tool. It binds
one workspace and ignored evidence directory at server startup, accepts only
the five known roles, and always uses local mode. It exposes no arbitrary
command, executable, workspace change or unrestricted profile. An initial call
starts a fresh session; its returned `run_id` resumes only a held implementer
or hunter. Read its report and status, then apply the existing gates. The MCP
tool executes the runner outside the orchestrator's shell sandbox; this avoids
nesting OS sandboxes, which blocked command execution in the live test.

The package includes the local broker in `mcp.json`. If configuring it directly
for a project, run `python3 <root>/bin/codex-mcp --project <project>
--evidence-root <ignored-evidence>` as a stdio MCP server. Bind the intended
workspace at startup; do not give the model an arbitrary workspace argument.
For unattended use, approve **only** its `run_role` tool for authorized local
work, using the client setting
`mcp_servers.aikit_roles.tools.run_role.approval_mode = "approve"` (or the
equivalent plugin-scoped tool setting). A server-level `approval_mode` key
does not configure this permission. Keep the normal approval mode unless
the owner has authorized unattended role execution. The tool's declared
side effects remain writes to the bound project; it is not read-only.
Set the broker's client `tool_timeout_sec` to 600 so a role's normal run is not
cut off by the client's shorter default MCP timeout.

For standalone terminal runs, use `bin/codex-kit run`. Each initial call starts a separate
`codex exec` session with only the role procedure and supplied brief. It does
not fork or inherit the orchestrator's conversation. In particular, never
paste a diff, changed paths, step notes, or an implementation summary into an
acceptance brief. Acceptance has automatic project instruction loading
disabled to avoid leaking implementation details through `AGENTS.md`.

Write the brief to a file, then run:

```sh
python3 <root>/bin/codex-kit run --role implementer --project <project> \
  --brief <brief.txt> --output <ignored-evidence>/agents/M1.1-build \
  --model <current-codex-model>
```

The output directory must be new and outside the project or gitignored, with
no tracked files underneath. Read
`report.txt` and `state.json`; keep `events.jsonl` and `stderr.txt` out of the
orchestrator's context. A nonzero runner exit means the agent did not complete
successfully; it never means the review or acceptance passed. Parse the
reviewer's verdict and run the existing acceptance/security gates separately.

For an implementer's next fix round, use a new output directory and
`--resume <previous-output-directory>`. The runner resumes the exact saved
session, and rejects cross-role, cross-project or cross-runtime resumes.
Reviewers, acceptance agents and refuters must always start fresh. A hunter
may be resumed to complete a defective report, as the security skill specifies.

Calls are synchronous and run without the shared Codex daemon. Wait for the runner to finish before reading results
or opening the next round. The runner has a wall-clock timeout and terminates
its child process group on completion, timeout or interruption. `TaskStop` maps to stopping
the running runner process (including its child group), not deleting a saved
session. A completed call has no worker still building in the background.

The caller must provide an authenticated, writable `CODEX_HOME`. When roles
are launched from another Codex session's shell, that **outer** sandbox must
also permit network access to the model service. A child's permission profile
cannot undo network restrictions imposed by its parent process. If normal
session storage is read-only, configure a writable session home under ignored
evidence before starting the orchestrator; retain it across implementer fix
rounds. The runner inherits that environment and never creates credentials.
Denied storage or model-network access is a capability failure, not a clean
review. Do not retry with an unrestricted filesystem profile. A network-enabled
outer shell still does not guarantee nested OS sandboxes work. Use the host MCP
broker in that case; if it is unavailable, report the dispatch capability gap
instead of retrying shell nesting or building/reviewing inline.

Reviewer and refuter shell execution uses a profile extending Codex's
**read-only sandbox**, with approval escalation disabled. Only the runner's
`scratch/` directory is writable by default. Unlike merely removing Write/Edit,
this also restricts shell writes. If a verify command needs source-tree writes, report
that verification is blocked; never weaken the sandbox to obtain CLEAN.
Configure verification to put caches/build output in the supplied scratch directory,
or have the orchestrator run that check separately and retain the limitation
in the review report. The runner does not claim the reviewer independently
ran a command it could not run. For security refutation, also pass
`--evidence-root <evidence>` so `probe replay` can write transcripts and spend
budget. That existing directory must be outside the project or gitignored.
The refuter profile permits network access for the disposable stand; `probe`
still enforces request scope and budgets.

Other roles use workspace-write and the existing tree tripwire. Acceptance
and hunter profiles enable networking so command hands can reach HTTP/CDP
stands; the hunter must still use scope-fenced `probe` for every request. Acceptance
and security roles can write evidence and reach a disposable stand; this is
not a guarantee that they cannot read source. Their blindness is the fresh
brief and product-only evidence rule. The runner disables nested multi-agent
dispatch, hooks, plugins, connectors, memory and automatic user configuration.
It rejects project/ancestor `.codex/config.toml` layers rather than risk loading
extra tools or runtime overrides. MCP/skill hands needing user
configuration are not supported by this CLI adapter yet: use command hands,
or report a capability gap rather than silently substituting a tool.

## Models

The caller reads YAML; the runner intentionally does not. Resolve each role's
model from `runtime.codex.models.<role>` first. Otherwise use an explicitly
configured existing role model only if it is a Codex model. Claude aliases
(`opus`, `sonnet`, `haiku`) are invalid in Codex and must not be silently
translated. If no override exists, pass the orchestrator's current model to
`--model` only when its exact supported identifier is observable from CLI
session configuration or metadata. A separate CLI cannot inherit its parent's
model. Never infer a model identifier from a persona, system identity, or
product name. If the current identifier is unavailable and the owner has
configured no model, omit the flag and disclose use of the account's CLI
default. An explicit owner model that the account rejects is a blocker;
never silently substitute another model.

## Local work and Git operations

**Local mode is the runner default.** A user's no-commit/no-push instruction
always wins over checkpoint/PR instructions in shared procedures. Pass the
same mode to every role. In local mode do not stage, stash, commit, change
branches, push, merge or open a PR. Existing unrelated edits belong to the
owner: inventory them, preserve them, and stop if the requested step overlaps
in a way that cannot be reviewed independently.

For each step, record a baseline without modifying Git's index:

```sh
python3 <root>/bin/codex-kit snapshot --project <project> \
  --output <ignored-evidence>/M1.1-before.json
```

After implementation, the reviewer reads a content diff using:

```sh
python3 <root>/bin/codex-kit diff --project <project> \
  --baseline <ignored-evidence>/M1.1-before.json
```

This includes tracked and nonignored untracked files, deletion, binary and
symlink changes, and executable modes. Snapshot review currently rejects
submodules rather than omitting them. A new snapshot starts the next step,
so earlier local steps are not attributed to it. It replaces
`git diff <baseline>..HEAD`, checkpoint refs and stash-based baselines in the
shared workflow. Save verification results and notes locally; mark a milestone
done only after its gates pass, and report that it is locally complete and
uncommitted. A successful agent call alone is not a gate.

`--git-mode checkpoint` restores the shared checkpoint procedure when the
owner explicitly authorizes it. It does not authorize publishing: pushes,
merges and PRs still require the owner's instruction. Never select checkpoint
mode in a session where the owner requested local work.

## Runtime compatibility

This adapter targets Codex CLI (development baseline: 0.162.1). Desktop plugin
discovery can load the generated skills, but role execution still needs the
local CLI. Cloud/ChatGPT Work and MCP-backed hands are not claimed supported.
Fail closed on an unsupported CLI flag, denied sandbox operation, timeout,
missing report, or unsuccessful session. Never retry with full access.

References: [plugin packaging](https://developers.openai.com/plugins/build/plugins),
[subagents and inherited permissions](https://learn.chatgpt.com/docs/agent-configuration/subagents),
[MCP tool approval configuration](https://learn.chatgpt.com/docs/config-file/config-reference).

## Live validation

On 2026-10-13, real Codex sessions exercised two disposable, uncommitted Python
projects: setup and planning; local autopilot with a broker-dispatched builder
and fresh reviewer; a deliberately broken title-normalization feature caught
by review and repaired by the held implementer; blind CLI acceptance with real
terminal captures; and an intentionally vulnerable localhost service audited
by a hunter and confirmed by a fresh refuter against reseeded data.

Acceptance gates rejected missing coverage, missing captures and a mutation to
already-dirty source. The security fence rejected off-scope HTTP requests. The
read-only SQLite truth connection rejected writes. The live tests exposed the
network, unsupported-model and nested-sandbox dispatch problems addressed above.

These fixtures validate the local command-based CLI path, not browser/CDP,
external product MCP hands, gitleaks/OSV integrations, cloud or desktop model
execution. Plugin installation and the packaged broker handshake were checked
separately; the live orchestrator used an explicitly configured project-bound
broker. Plugin auto-discovery across desktop surfaces is not claimed tested.
