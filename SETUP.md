# Setup

What to configure after cloning this repo. Read [`CLAUDE.md`](CLAUDE.md) first — it's the actual orientation doc; this file only covers machine/tooling setup for Spec Kit itself. For configuring and running the actual application (env vars, tests, the service, model training), see [`GUIDE.md`](GUIDE.md).

## Already in the repo — nothing to install for basic use

`.claude/skills/`, `.specify/`, and `skills-lock.json` are committed, not generated. A fresh clone already has Spec Kit's templates, scripts, and the `/speckit-*` slash commands, plus the vendored `brainstorming` skill. You do **not** need to run `specify init` again.

## Prerequisites

Spec Kit's own tooling prerequisites (Claude Code, Git, PowerShell) and the "verify the environment" check now live in [`GUIDE.md`](GUIDE.md#configure), alongside the application's own configuration steps.

Optional, only if you need to touch the Spec Kit installation itself (upgrade it, re-check tool integrations, add an extension) — not required to just read docs or use the existing `/speckit-*` commands:

- [`uv`/`uvx`](https://docs.astral.sh/uv/) — runs the `specify` CLI without a separate install:
  ```
  uvx --from git+https://github.com/github/spec-kit.git@v0.16.2 specify check
  ```
  Pin the `@v0.16.2` tag to match what's in `.specify/init-options.json` (`speckit_version`) unless you're deliberately upgrading — see `specify self upgrade --dry-run` first if you want a newer version.

Optional, only for the `brainstorming` skill's visual companion (mockups/diagrams in a browser tab during design discussions — the skill itself works text-only without it):

- **Node.js** — runs `.claude/skills/brainstorming/scripts/server.cjs`
- A POSIX shell to run `start-server.sh`/`stop-server.sh` — Git Bash on Windows works (the same `Bash` tool this environment already uses); the scripts auto-detect Windows/MSYS and adjust process handling accordingly

## Where the skills came from

`.claude/skills/brainstorming/` is vendored from the [`obra/superpowers`](https://github.com/obra/superpowers) GitHub repo, not written here. `skills-lock.json` at the repo root pins its source path and content hash — if you ever need to update it, re-fetch from that source and update the hash, don't hand-edit the skill in place. The `speckit-*` skills came from the Spec Kit install above and are tracked the same way as any other committed file (no separate lock).

## First read, in order

1. [`CLAUDE.md`](CLAUDE.md) — hard boundaries and directory map
2. [`documents/README.md`](documents/README.md) — goal, problem, boundaries, reading order
3. `Constitution.md` → `HLD.md` → `Modeling-Approach.md` → `Evidence-Flow-Spec.md` in `documents/initiatives/evidence-intelligence-module/`
4. [`documents/initiatives/evidence-intelligence-module/notes/decision-log.md`](documents/initiatives/evidence-intelligence-module/notes/decision-log.md) — why things were deliberately removed, before assuming something is missing

## Notes

- `src/` holds the actual implementation (see `CLAUDE.md`'s directory map). It has its own `pyproject.toml` — see [`GUIDE.md`](GUIDE.md#configure) for the environment-setup and test-run commands. `documents/` and `specs/` remain documentation-only with no build step of their own.
- `.specify/memory/constitution.md` is a Spec-Kit-facing distillation of the canonical `Constitution.md` above; if that canonical doc is amended, re-sync this file too (see its own header comment).
