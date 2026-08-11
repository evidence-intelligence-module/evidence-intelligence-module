# Setup

What to configure after cloning this repo. Read [`CLAUDE.md`](CLAUDE.md) first — it's the actual orientation doc; this file only covers machine/tooling setup.

## Already in the repo — nothing to install for basic use

`.claude/skills/`, `.specify/`, and `skills-lock.json` are committed, not generated. A fresh clone already has Spec Kit's templates, scripts, and the `/speckit-*` slash commands, plus the vendored `brainstorming` skill. You do **not** need to run `specify init` again.

## Prerequisites

| Tool | Needed for |
|---|---|
| [Claude Code](https://claude.com/claude-code) | The `/speckit-*` and other skills in `.claude/skills/` only run inside it |
| Git | Cloning, obviously |
| PowerShell 7+ (`pwsh`) | This repo was initialized with `--script ps`, so `.specify/scripts/powershell/*.ps1` are the active automation scripts the `/speckit-*` skills call |

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

## Verify the environment

```
uvx --from git+https://github.com/github/spec-kit.git@v0.16.2 specify check
```
Confirms required tools (git, the selected AI integration, script runtime) are present and matches what the repo expects.

## First read, in order

1. [`CLAUDE.md`](CLAUDE.md) — hard boundaries and directory map
2. [`documents/initiatives/evidence-intelligence-module/README.md`](documents/initiatives/evidence-intelligence-module/README.md)
3. `Constitution.md` → `HLD.md` → `Modeling-Approach.md` → `Evidence-Flow-Spec.md` in that same folder
4. [`documents/initiatives/evidence-intelligence-module/notes/brainstorm-auth.md`](documents/initiatives/evidence-intelligence-module/notes/brainstorm-auth.md) — why things were deliberately removed, before assuming something is missing

## Notes

- This is a documentation-only repo today (`crop-insurance/code/` is empty) — there's no build, test, install, or run step beyond the above.
- `.specify/memory/constitution.md` is a Spec-Kit-facing distillation of the canonical `Constitution.md` above; if that canonical doc is amended, re-sync this file too (see its own header comment).
