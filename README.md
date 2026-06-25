<div align="center">

# devbyshima/skills

*Agent skills I build and actually use — one command to add them to any AI coding agent.*

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[![tests](https://github.com/devbyshima/skills/actions/workflows/test.yml/badge.svg)](https://github.com/devbyshima/skills/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Quickstart](#quickstart) · [Skills](#skills) · [How it works](#how-it-works) · [Local development](#local-development) · [Contributing](CONTRIBUTING.md)

</div>

A growing collection of [**Agent Skills**](https://agentskills.io) — reusable capabilities that teach an AI coding agent (Claude Code, Cursor, Copilot, Codex, …) to do a specific job well. Each skill is a self-contained folder with a `SKILL.md`; the agent reads its name and description first and only loads the rest when the task calls for it, so skills stay cheap until they're needed.

## Quickstart

```bash
npx skills@latest add devbyshima/skills
```

That copies the skills into your agent's directory (`.claude/skills/` or `.agents/skills/`) — no manual setup. Then just describe what you want and the agent reaches for the right skill.

> [!TIP]
> Want only one? `npx skills@latest add devbyshima/skills --skill <name>`. Re-run `add` any time to update.

## Skills

| Skill | Category | Invocation | What it does |
| --- | --- | --- | --- |
| [`whiteboard`](skills/diagramming/whiteboard) | [diagramming](skills/diagramming) | model-invoked | Turns natural language into hand-drawn `.excalidraw` diagrams — sketches, flowcharts, architecture, ER/UML/sequence, mind maps — via a Python builder. Exports PNG/SVG locally, embeds AI/LLM brand logos, and can auto-layout a codebase's import or class graph. |

*More skills and categories land here over time; the `add` command above keeps working as they're added.*

## Installation

Skills are managed with [`npx skills`](https://github.com/vercel-labs/skills) — think "npm for agent skills, with GitHub as the registry."

```bash
# the whole collection
npx skills@latest add devbyshima/skills

# a single skill, by name…
npx skills@latest add devbyshima/skills --skill whiteboard

# …or by its direct path
npx skills@latest add https://github.com/devbyshima/skills/tree/main/skills/diagramming/whiteboard
```

This repo also ships a [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json), so it doubles as a **Claude Code plugin** and is discoverable by any tool that reads the plugin manifest.

> [!NOTE]
> Skills run with your agent's full permissions. Skim a skill's `SKILL.md` before using it — same habit as reviewing any dependency.

## How it works

Every skill follows the [Agent Skills](https://agentskills.io) format and lives in its own folder:

```
skills/
  <category>/
    <skill-name>/
      SKILL.md          # required — name + description frontmatter, then instructions
      scripts/ · references/ · styles/ · data/ · tests/   # optional bundled resources
    README.md           # category index (user- vs model-invoked)
```

- **Progressive disclosure** — the agent matches on the `description`, then reads `SKILL.md`, and only opens `references/` or runs `scripts/` when the work needs them.
- **Self-contained** — a skill carries its own scripts and docs and resolves paths relative to itself, so it behaves the same wherever it's installed.
- **Verified** — skills that ship scripts include a `tests/` suite; CI runs every `skills/**/tests/` on each push.

## Local development

Working on a skill in a clone of this repo:

```bash
bash scripts/list-skills.sh    # list every skill: name — description
bash scripts/link-skills.sh    # symlink all skills into ~/.claude/skills and ~/.agents/skills
```

`link-skills.sh` symlinks rather than copies, so a `git pull` keeps your installed skills current. See [CONTRIBUTING.md](CONTRIBUTING.md) and [CLAUDE.md](CLAUDE.md) for how to add a skill or category.

---

<div align="center">

MIT licensed · Built by [devbyshima](https://github.com/devbyshima)

</div>
