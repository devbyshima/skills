# devbyshima/skills

[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Agent skills I've built and actually use — reusable capabilities for AI coding agents (Claude Code, Cursor, Copilot, Codex, and any [Agent-Skills](https://agentskills.io)-compatible harness). Each skill is a self-contained folder with a `SKILL.md` (instructions + metadata) plus any scripts/references/assets it needs. The agent reads a skill's name + description first and only loads the rest when it's relevant (progressive disclosure).

## 🚀 Quickstart (30 seconds)

```bash
# install everything in this collection
npx skills@latest add devbyshima/skills

# …or just one skill
npx skills@latest add devbyshima/skills --skill whiteboard

# …or a single skill by its direct path
npx skills@latest add https://github.com/devbyshima/skills/tree/main/skills/diagramming/whiteboard
```

[`npx skills`](https://github.com/vercel-labs/skills) is "npm, but for agent skills, with GitHub as the registry." It copies the skill into your agent's skills directory (`.claude/skills/` or `.agents/skills/`) — no manual setup. Re-run `add` to update.

This repo also ships a [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json), so it doubles as a **Claude Code plugin** and is discoverable by any tool that reads the plugin manifest.

## 🗂️ Skills

Browse by category (each category README splits **user-invoked** vs **model-invoked**):

### [Diagramming](skills/diagramming) · *model-invoked*

| Skill | What it does |
|---|---|
| [`whiteboard`](skills/diagramming/whiteboard) | Natural language → hand-drawn `.excalidraw` diagrams (sketches, flowcharts, architecture, ER/UML/sequence, mind maps) via a Python `Scene` builder; offline PNG/SVG export; can auto-layout a codebase's import/class graph. |

*More categories and skills land here over time — the install commands above keep working as they're added.*

## 🧱 Repository layout

Skills are organized into **category** folders under `skills/` — the [catalog layout](https://github.com/vercel-labs/skills) the `skills` CLI discovers automatically:

```
skills/
  <category>/
    <skill-name>/
      SKILL.md          # required — name + description frontmatter, then instructions
      scripts/ · references/ · styles/ · data/ · tests/   # optional
    README.md           # category index (user- vs model-invoked)
.claude-plugin/plugin.json   # plugin manifest (lists every skill)
scripts/                     # dev helpers (list-skills, link-skills)
```

## 🛠️ Local development

```bash
bash scripts/list-skills.sh    # list every skill: name — description
bash scripts/link-skills.sh    # symlink all skills into ~/.claude/skills & ~/.agents/skills (git pull to update)
```

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (humans) and [CLAUDE.md](CLAUDE.md) (agents) for how to add a skill or category and the conventions each follows.

## 📄 License

[MIT](LICENSE) © devbyshima. Individual skills may carry their own origin/attribution in their folder (e.g. `whiteboard` is adapted from the MIT-licensed [`drawio-skill`](https://github.com/Agents365-ai/drawio-skill)).
