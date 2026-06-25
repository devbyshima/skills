# whiteboard — From Text to Hand-Drawn Diagrams

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Agent Skills](https://img.shields.io/badge/Agent%20Skills-compatible-2ea44f)](https://agentskills.io)
[![Part of devbyshima/skills](https://img.shields.io/badge/collection-devbyshima%2Fskills-blue)](https://github.com/devbyshima/skills)

A skill that turns natural-language descriptions into `.excalidraw` diagrams — the hand-drawn / whiteboard look (rough strokes, the Excalifont handwriting, sketchy fills) — and exports them to PNG / SVG locally when a browser is available. It can also turn an **existing codebase** (Python / JS-TS / Go / Rust) into an auto-laid-out structure diagram. Works with **Claude Code, Cursor, Copilot, OpenClaw, Codex, Hermes**, and any agent compatible with the [Agent Skills](https://agentskills.io) format.

`.excalidraw` is a **JSON** format, but hand-writing it is error-prone — every element needs a unique id, a `seed`, and a `versionNonce`; arrows must carry relative `points` **plus** `startBinding`/`endBinding`, and each shape they touch must list the arrow back in its own `boundElements`. So this skill **never writes raw JSON by hand**. It generates diagrams by calling a small Python builder (`scripts/excalidraw.py`, a `Scene` class that owns the schema), then optionally renders to an image. Because the schema lives in one place, **the output is always structurally valid** and opens in [excalidraw.com](https://excalidraw.com), the VS Code "Excalidraw" extension, and Obsidian's Excalidraw plugin.

## 🚀 Installation

This skill ships in the [`devbyshima/skills`](https://github.com/devbyshima/skills) collection. Install with any [Agent Skills](https://agentskills.io)–compatible CLI (`npx skills`):

```bash
# just this skill
npx skills add devbyshima/skills --skill whiteboard

# or by direct path
npx skills add https://github.com/devbyshima/skills/tree/main/skills/diagramming/whiteboard

# or the whole collection
npx skills add devbyshima/skills
```

```bash
# Manual install — copy the skill folder into your agent's skills dir
git clone https://github.com/devbyshima/skills.git
cp -r skills/skills/diagramming/whiteboard ~/.claude/skills/whiteboard
```

**Prerequisites:**

| What you want | What you need |
|---|---|
| Core generation (`.excalidraw` JSON) | `python3` only — the builder is pure stdlib |
| PNG / SVG export | Node.js + an installed Chrome/Chromium/Edge, plus a one-time `npm install` in the skill dir |
| Optional auto-layout | Graphviz (`dot`) |

```bash
# one-time, in the skill directory — enables PNG/SVG export
cd <skill-dir> && npm install
# Graphviz for optional autolayout.py
brew install graphviz            # macOS  (apt install graphviz on Debian/Ubuntu)
```

If `npm install` or a browser isn't available, export is skipped and the `.excalidraw` file is delivered as-is — it's always valid and opens in any Excalidraw viewer. `CHROME_PATH=…` overrides the browser.

## ⚡ Quick Start

After installation, just describe what you want — *"sketch a login flow,"* *"draw a microservices architecture on a whiteboard,"* *"visualize the module structure of this Python project."* The skill plans the layout, generates the `.excalidraw` via the builder, validates it, exports an image when it can, self-checks, and lets you iterate.

Under the hood, the skill writes and runs a short Python script against the `Scene` builder. Element-creating methods return the new element's **id** (a string), so you wire arrows and labels to it — the builder computes the on-border attach points and the both-sided binding for you:

```python
import sys; sys.path.insert(0, "<skill-dir>/scripts")
from excalidraw import Scene

s = Scene()                                          # or Scene.from_preset(preset_dict)
s.text(120, 40, "Login flow", font_size=28)
client = s.rect(120, 110, 160, 60, text="Web Client", role="service")
api    = s.rect(120, 260, 160, 60, text="API",        role="gateway")
db     = s.ellipse(120, 410, 160, 70, text="User DB", role="database")
s.arrow(client, api, label="HTTPS")                  # geometry + both-sided binding handled
s.arrow(api, db, label="SQL")
s.dump("login-flow.excalidraw")
```

Then validate (builder output should pass clean), and export an image if a browser is available:

```bash
python3 <skill-dir>/scripts/validate.py login-flow.excalidraw
node   <skill-dir>/scripts/render.mjs login-flow.excalidraw -f both -o login-flow
```

`role=` auto-picks colors from the palette: service→blue, database→green, queue/decision→yellow, gateway→orange, error→red, external→grey, security→purple. You can always override with explicit `stroke=`/`background=`. The full method reference lives in [`references/builder-api.md`](references/builder-api.md).

## 🗺️ Visualize a Codebase

Beyond hand-authored diagrams, the skill turns **existing code into structure diagrams** — no manual coordinates. Just ask *"visualize the module structure of this Python project"* or *"draw the class hierarchy of `mypackage`."*

```bash
# Import graph — Python / JS-TS / Go / Rust  (run from the skill dir, or use absolute paths)
python3 scripts/pyimports.py   myproject --group -o graph.json
python3 scripts/jsimports.py   ./src     --group -o graph.json
python3 scripts/goimports.py   ./module  --group -o graph.json
python3 scripts/rustimports.py ./crate   --group -o graph.json

# Python class-inheritance hierarchy
python3 scripts/pyclasses.py   mypackage --group -o graph.json

# any extractor → auto-layout → editable .excalidraw
python3 scripts/autolayout.py  graph.json -o diagram.excalidraw
```

The graph JSON contract is `{"direction":"TB"|"LR","nodes":[…],"edges":[…]}`. Graphviz places the nodes and routes orthogonal edges *around* them (replayed as multi-point arrows, since Excalidraw arrows are otherwise straight), removing the hand-coordinate ceiling for large graphs. `--group` boxes modules into nested containers. Layout needs Graphviz (`brew install graphviz` / `apt install graphviz`) — optional; everything else works without it. Format + flags in [`references/autolayout.md`](references/autolayout.md).

## 🧩 Supported Diagram Types

When you name a type, the skill reads the matching shape / edge / layout conventions from [`references/diagram-types.md`](references/diagram-types.md):

| User says | Type |
|---|---|
| "ER diagram", "schema", "data model" | ERD |
| "UML class diagram", "class diagram" | UML Class |
| "sequence diagram", "lifeline" | Sequence |
| "architecture", "system diagram" | Architecture |
| "neural network", "model architecture", "deep learning" | ML / Deep Learning |
| "flowchart", "process flow" | Flowchart |
| "mind map", "brainstorm" | Mind Map |

## 🤖 AI / LLM Brand Logos

Excalidraw ships **no** brand/vendor shape libraries, so an LLM-app diagram would render as unlabeled boxes. `aiicons.py` resolves a brand name to a logo SVG from [lobe-icons](https://github.com/lobehub/lobe-icons) (MIT) and inlines it as a data URI. Unlike a CDN reference, the image bytes are embedded in the file's `files` map, so the resulting `.excalidraw` is fully self-contained and offline-renderable.

```bash
python3 scripts/aiicons.py "openai" --json
python3 scripts/aiicons.py "claude" --variant mono --size 64
```

Feed the result to the builder with `s.image(x, y, w, h, "<dataURL>", mime="image/svg+xml")`. Logos are trademarks of their respective owners, used for identification only.

## 🎨 Style Presets

A **style preset** is a named JSON file (palette, shapes, font, roughness, fill, edges) that, when active, replaces the built-in conventions. Three are built in — `default`, `sketch`, `clean` — under [`styles/built-in/`](styles/built-in/); user presets in `~/.whiteboard/styles/<name>.json` shadow built-ins and can set `"default": true`. Apply one in a single line:

```python
import json
from excalidraw import Scene
s = Scene.from_preset(json.load(open("<skill-dir>/styles/built-in/sketch.json")))
```

```
Draw a microservices architecture using my "sketch" style
```

The schema is at [`styles/schema.json`](styles/schema.json); preset-management commands and the application rules are in [`references/style-presets.md`](references/style-presets.md).

## 🔄 How it works

Behind the scenes: **resolve active preset → plan layout → generate `.excalidraw` via the builder → validate → export draft PNG → self-check + auto-fix** (up to 2 rounds, when a vision-enabled model is available) → **show to user → 5-round feedback loop** until approved → **final export**. The `.excalidraw` JSON is the guaranteed deliverable; image export is best-effort.

## 🎯 When to use (and when not to)

**Good fit:** anything that benefits from a casual, hand-drawn, low-fidelity feel — whiteboard sketches, brainstorms, architecture/flow sketches, mind maps, explainer diagrams, "napkin" system diagrams, talk/blog figures.

**Reach for a different tool when you need:**
- **Polished, precise diagrams** with a strict shape vocabulary, swimlanes, exact geometry, and large stock/branded shape sets → [drawio-skill](https://github.com/Agents365-ai/drawio-skill)
- **Diagrams-as-code that live in git and render in Markdown** → mermaid or plantuml
- **Freeform infinite-canvas collaboration with many cursors** → tldraw

## 📖 Documentation

- [`SKILL.md`](SKILL.md) — the workflow the agent follows
- [`references/builder-api.md`](references/builder-api.md) — full `Scene` method reference
- [`references/diagram-types.md`](references/diagram-types.md) — per-type shape/edge/layout conventions
- [`references/elements.md`](references/elements.md) — raw element schema, color/font/roughness vocabulary
- [`references/autolayout.md`](references/autolayout.md) · [`references/style-presets.md`](references/style-presets.md) · [`references/export.md`](references/export.md) · [`references/troubleshooting.md`](references/troubleshooting.md)

## 👤 Author

**devbyshima** — https://github.com/devbyshima

Adapted from [drawio-skill](https://github.com/Agents365-ai/drawio-skill) (MIT) for the hand-drawn Excalidraw format.

## 📄 License

[MIT](LICENSE)
