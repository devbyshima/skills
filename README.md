# devbyshima/skills

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A collection of [**Agent Skills**](https://agentskills.io) I've built — reusable capabilities for AI coding agents (Claude Code, Cursor, Copilot, Codex, and any Agent-Skills-compatible CLI). Each skill is a self-contained folder with a `SKILL.md` (instructions + metadata) and any scripts/references/assets it needs. Agents load a skill's name + description first, and only read the rest when it's relevant (progressive disclosure).

## 📦 Install

Skills are installed with [`npx skills`](https://github.com/vercel-labs/skills) — think "npm, but for agent skills, with GitHub as the registry."

```bash
# install every skill in this collection
npx skills add devbyshima/skills

# install one skill by name
npx skills add devbyshima/skills --skill whiteboard

# install one skill by its direct path
npx skills add https://github.com/devbyshima/skills/tree/main/skills/diagramming/whiteboard
```

The CLI copies the skill into your agent's skills directory (`.claude/skills/` or `.agents/skills/`) — no manual setup. Re-run `add` to update.

## 🗂️ Catalog

| Category | Skill | What it does |
|---|---|---|
| **diagramming** | [`whiteboard`](skills/diagramming/whiteboard) | Turns natural language into hand-drawn `.excalidraw` diagrams (sketches, flowcharts, architecture, ER/UML/sequence, mind maps) via a Python builder; exports PNG/SVG locally; can auto-layout a codebase's import/class graph. |

## 🧱 Repository layout

Skills are organized into **category** folders under `skills/` — the [catalog layout](https://github.com/vercel-labs/skills) the `skills` CLI discovers automatically:

```
skills/
  <category>/
    <skill-name>/
      SKILL.md          # required — name + description frontmatter, then instructions
      scripts/          # optional — executable helpers
      references/       # optional — docs loaded on demand
      styles/ · data/   # optional — assets
```

Adding more skills (and more categories) just means adding folders here — the install commands above keep working.

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a new skill or category and the conventions each skill follows.

## 📄 License

[MIT](LICENSE) © devbyshima. Individual skills may note their own origin/attribution in their folder (e.g. `whiteboard` is adapted from the MIT-licensed `drawio-skill`).
