---
name: whiteboard
version: 1.0.0
description: Use when the user wants a hand-drawn / whiteboard-style diagram, sketch, flowchart, architecture or system diagram, ER/UML/sequence diagram, mind map, ML/DL model figure, or any visualization with a loose, sketchy, "drawn on a whiteboard" aesthetic. Also use proactively when explaining a system with 3+ components or a data flow that reads better as a casual sketch than a precise CAD-like figure. Generates `.excalidraw` JSON (opens in excalidraw.com, the VS Code Excalidraw extension, and Obsidian) via a Python builder, and exports PNG/SVG locally when a browser is available.
license: MIT
homepage: https://github.com/devbyshima/skills
compatibility: Core generation needs only python3. Image export (PNG/SVG) needs Node.js + an installed Chrome/Chromium/Edge and a one-time `npm install` in the skill dir; without them the skill delivers the `.excalidraw` file (always valid) to open in a viewer. Optional auto-layout (scripts/autolayout.py) needs Graphviz (`dot`). Self-check needs a vision-enabled model; gracefully skipped if unavailable.
platforms: [macos, linux, windows]
metadata: {"openclaw":{"requires":{"anyBins":["python3"]},"emoji":"✏️","os":["darwin","linux","win32"],"install":[{"id":"npm-install","kind":"npm","label":"Install render deps (PNG/SVG export) — run `npm install` in the skill dir","optional":true},{"id":"brew-graphviz","kind":"brew","formula":"graphviz","bins":["dot"],"label":"Install Graphviz for optional autolayout.py","os":["darwin"],"optional":true}]},"hermes":{"tags":["excalidraw","diagram","sketch","whiteboard","flowchart","architecture","hand-drawn","visualization"],"category":"design","related_skills":["drawio-skill","mermaid","tldraw"]},"author":"devbyshima","version":"1.0.0"}
---

# Excalidraw Diagrams

## Overview

Generate `.excalidraw` files — the hand-drawn / whiteboard look (rough strokes, the Excalifont handwriting, sketchy fills) — and export them to PNG/SVG locally.

`.excalidraw` is a **JSON** format. Hand-writing it is error-prone (every element needs a unique id, a `seed`, a `versionNonce`; arrows must carry relative `points` **plus** `startBinding`/`endBinding`, and each shape they touch must list the arrow back in its own `boundElements`; bound text labels are the same on both sides). So this skill **never writes raw JSON by hand** — it generates diagrams by calling the `scripts/excalidraw.py` builder (a `Scene` class that owns the schema), then optionally renders to an image.

**Output:** `.excalidraw` (always — opens in [excalidraw.com](https://excalidraw.com), the VS Code "Excalidraw" extension, and Obsidian's Excalidraw plugin), plus **PNG/SVG** when a browser is available.

## When to use / when NOT to use

**Use this skill for:** anything that benefits from a casual, hand-drawn, low-fidelity feel — whiteboard sketches, brainstorms, architecture/flow sketches, mind maps, explainer diagrams, "napkin" system diagrams, talk/blog figures.

**Do NOT use it — route elsewhere — for:**
- Polished, precise diagrams with strict shape vocabulary, swimlanes, 10,000+ stock/branded shapes, exact geometry → **drawio-skill**.
- Diagrams-as-code that live in git / render in Markdown → **mermaid** (general) or **plantuml** (UML).
- Freeform infinite-canvas collaboration with many cursors → **tldraw**.

## Bundled resources

Read these on demand — none need to be in context up front.

| File | Read it when |
|---|---|
| `references/builder-api.md` | You're generating a diagram and want the full `Scene` method reference (every shape, arrow, label, image, frame option) |
| `references/diagram-types.md` | The user names a specific diagram type (ERD, UML class, sequence, architecture, ML/DL, flowchart, mind map) |
| `references/elements.md` | You need the raw Excalidraw element schema, the color/font/roughness vocabulary, or how community `.excalidrawlib` libraries map in |
| `scripts/aiicons.py` | The diagram involves an **AI/LLM brand** (OpenAI, Claude, Gemini, Mistral, Llama, HuggingFace, LangChain, …) or a common data store — resolves the brand to an embeddable logo image |
| `references/style-presets.md` | The user asks to learn / save / list / set-default / delete a style preset, or you've resolved an active preset and need the application rules |
| `references/style-extraction.md` | You're inside the Learn flow and need the extraction procedure |
| `references/export.md` | You need export details, the render setup, or an export failed |
| `references/troubleshooting.md` | A render fails, vision rejects a PNG, or a diagram looks wrong |
| `references/autolayout.md` | The diagram is large or layout-heavy (dependency/call graph, code structure, >~15 nodes) and you want Graphviz to place nodes + route edges |
| `scripts/pyimports.py` · `jsimports.py` · `goimports.py` · `rustimports.py` | Visualize a **Python / JS-TS / Go / Rust project** structure — extracts the import graph for autolayout |
| `scripts/pyclasses.py` | Visualize a **Python class hierarchy** — extracts classes + inheritance for autolayout |
| `scripts/validate.py` | After generating any `.excalidraw`, run a fast deterministic structural lint before the vision self-check |

## Prerequisites

- **Generation:** `python3` only (the builder is pure stdlib). Always available.
- **Image export (PNG/SVG):** Node.js + an installed Chrome/Chromium/Edge, and a one-time dependency install. The skill works without it — see the fallback chain.

```bash
# one-time, in the skill directory (enables PNG/SVG export)
cd <this-skill-dir> && npm install
# Graphviz for optional autolayout.py
brew install graphviz            # macOS  (apt install graphviz on Debian/Ubuntu)
```

If `npm install` or a browser isn't available, **skip export** and deliver the `.excalidraw` file — it is always valid and opens in any Excalidraw viewer.

## Workflow

Before starting, assess whether the request is specific enough. If key details are missing, ask 1-3 focused questions (diagram type? rough-sketch vs cleaner look? output location? scope/labels?). Skip clarification for clearly simple requests ("sketch a flowchart of X").

**Step 0 — Resolve active preset.** Determine which (if any) user style preset applies.
- Scan the user's message for a phrase clearly naming a preset: "use my `<name>` style", "in `<name>` mode", "in the style of `<name>`". A bare "with `<name>`" does **not** count (names a component, not a style).
- Else check `~/.whiteboard/styles/` for a file with `"default": true`.
- Else no preset; use the built-in palette/roughness conventions.

Built-in presets live in `<this-skill-dir>/styles/built-in/`: **`default`** (artist roughness, solid fills, handwriting), **`sketch`** (full hand-drawn: cartoonist roughness + hachure fills), **`clean`** (architect roughness 0 + normal font — Excalidraw structure without the wobble). User presets in `~/.whiteboard/styles/<name>.json` shadow built-ins. If a named preset exists in neither location, tell the user, list available presets, and stop. When a preset loads, say so in the first line: *"Using preset `<name>`."* Apply it with `Scene.from_preset(preset_dict)` (see below). Details: `references/style-presets.md`.

1. **Plan** — identify the shapes, their roles (service / database / queue / gateway / decision / error / external / security), relationships, and layout direction (LR or TB). Group by tier/layer. For >~15 nodes or a code graph, plan to use autolayout instead of hand-placing.

2. **Generate via the builder.** Write a short Python script that imports the `Scene` builder and calls its methods, then run it. **Never emit raw `.excalidraw` JSON by hand.**

   ```python
   import sys; sys.path.insert(0, "<this-skill-dir>/scripts")
   from excalidraw import Scene

   s = Scene()                              # or Scene.from_preset(preset_dict)
   title  = s.text(120, 40, "Login flow", font_size=28)
   client = s.rect(120, 110, 160, 60, text="Web Client", role="service")
   api    = s.rect(120, 260, 160, 60, text="API",        role="gateway")
   db     = s.ellipse(120, 410, 160, 70, text="User DB",  role="database")
   s.arrow(client, api, label="HTTPS")      # geometry + both-sided binding handled
   s.arrow(api, db, label="SQL")
   s.dump("login-flow.excalidraw")
   ```

   - **Coordinates:** top-left origin, y grows downward. Snap to multiples of 10. Scale gaps with complexity (≤5 nodes → ~150px; 6-10 → ~200px; >10 → ~260px).
   - **Roles** auto-pick colors from the palette; pass `role=` (or explicit `stroke=`/`background=`). See `references/builder-api.md` for every option.
   - **Large / layout-heavy diagrams:** don't hand-place. Describe the graph as JSON and run `python3 <this-skill-dir>/scripts/autolayout.py graph.json -o name.excalidraw` (Graphviz places nodes + routes edges around boxes). For a code project, the matching importer (`pyimports.py` / `jsimports.py` / `goimports.py` / `rustimports.py` / `pyclasses.py`) produces the graph JSON. See `references/autolayout.md`.
   - **AI/LLM brand logos:** `python3 <this-skill-dir>/scripts/aiicons.py "openai" --json` returns an embeddable logo; drop it in with `s.image(x, y, w, h, dataURL)`.
   - Default output dir is the user's working dir; honor any explicit path (`mkdir -p` it first).

   Then **lint**: `python3 <this-skill-dir>/scripts/validate.py name.excalidraw` (catches dangling bindings, duplicate ids, <2-point arrows, one-sided bindings, overlaps). Builder output should pass clean.

3. **Export draft (best-effort).** If render deps are available, produce a preview PNG for the self-check:
   ```bash
   node <this-skill-dir>/scripts/render.mjs name.excalidraw -f png -o name
   ```
   If `render.mjs` reports missing deps or no browser, **skip to step 6 with the `.excalidraw` file** (JSON-only path) — tell the user it opens in excalidraw.com / VS Code / Obsidian, and optionally `open name.excalidraw`.

4. **Self-check (if a PNG was produced).** Use the agent's vision to read `name.png` and catch issues before showing the user (requires a vision-enabled model; skip if unavailable). Re-run the builder script with fixes and re-export. Max **2 self-check rounds**.

   | Check | Look for | Fix |
   |---|---|---|
   | Overlapping shapes | shapes stacked | increase coordinates / gaps in the builder script |
   | Clipped labels | text wider than its shape | widen the shape (`w=`) or shorten the label |
   | Arrows not connecting | a gap between arrow and shape | bind via element ids (`s.arrow(a, b)`), not raw points |
   | Lines through shapes | an edge crosses an unrelated box | use `autolayout.py` (routes around), or move shapes apart |
   | Crowding | everything cramped | scale all gaps up |

5. **Review loop.** Show the image (or the `.excalidraw` path) and collect feedback. Apply targeted edits by **editing the builder script and re-running it** — keep the script as the source of truth (don't hand-edit the JSON). Re-export. Loop until approved. After 5 rounds, suggest the user open the file in Excalidraw for fine-tuning.

6. **Final delivery.** Re-run the builder for the approved version. Export requested formats (`-f both` for PNG+SVG). Report the path to the `.excalidraw` source **and** any images. Offer to open it: `open name.excalidraw` (macOS) / `xdg-open` (Linux) / `start` (Windows), or at https://excalidraw.com.

## The builder (`scripts/excalidraw.py`)

`Scene` is the single source of truth for the file format. Element-creating methods return the new element's **id** (a string) so you can wire arrows and labels to it.

| Method | Creates |
|---|---|
| `s.rect(x, y, w, h, text=?, role=?)` | rounded rectangle — services, modules, processes |
| `s.ellipse(x, y, w, h, text=?, role=?)` | ellipse/circle — databases, start/end |
| `s.diamond(x, y, w, h, text=?)` | diamond — decisions (defaults to yellow) |
| `s.text(x, y, "label", font_size=?)` | free-standing text — titles, annotations |
| `s.arrow(src_id, dst_id, label=?)` | bound arrow between two shapes — computes border attach points, sets both-sided binding, optional label |
| `s.routed_arrow([(x,y),…], source=?, target=?, label=?)` | arrow along an explicit polyline (used by autolayout) |
| `s.line([(x,y),…])` | multi-point line / separator |
| `s.image(x, y, w, h, dataURL, mime=?)` | embedded image (logos via `aiicons.py`) — stored in the `files` map |
| `s.frame(x, y, w, h, name)` | a named frame (grouping region) |
| `s.dump("file.excalidraw")` | write the file |

Construction options (also settable per preset): `Scene(background="#ffffff", roughness=1, fill_style="solid", stroke_width=2, font_family=1, font_size=20, palette=…, roles=…)`.
- **roughness** `0` architect (clean) · `1` artist (default) · `2` cartoonist (most sketchy).
- **fill_style** `"solid"` · `"hachure"` (sketchy diagonal) · `"cross-hatch"`.
- **font_family** `1` hand-drawn (Excalifont) · `2` normal (Nunito) · `3` code.
- **roles → palette slots:** service→blue, database→green, queue/decision→yellow, gateway→orange, error→red, external→grey, security→purple.

Apply a style preset in one line: `s = Scene.from_preset(json.load(open(preset_path)))`.

Full option list, colors, and the underlying element schema: `references/builder-api.md` and `references/elements.md`.

## Diagram type presets

When the user requests a specific type, read `references/diagram-types.md` for the matching shape/edge/layout conventions:

| User says | Section |
|---|---|
| "ER diagram", "schema", "data model" | ERD |
| "UML class diagram", "class diagram" | UML Class |
| "sequence diagram", "lifeline" | Sequence |
| "architecture", "system diagram" | Architecture |
| "neural network", "model architecture", "deep learning" | ML / Deep Learning |
| "flowchart", "process flow" | Flowchart |
| "mind map", "brainstorm" | Mind Map |

## Style presets

A **style preset** is a named JSON file (palette, shapes, font, roughness, fill, edges) that, when active, replaces the built-in conventions. Lookup order: `~/.whiteboard/styles/<name>.json` (user) → `<this-skill-dir>/styles/built-in/<name>.json` (built-in). Apply with `Scene.from_preset(...)`. For the Learn flow, management ops, and application rules, read `references/style-presets.md`.

## Export & fallback chain

Image export is **best-effort** — the `.excalidraw` JSON is the guaranteed deliverable. Details in `references/export.md`.

| Scenario | Behavior |
|---|---|
| Node + browser + deps present | Render PNG/SVG via `scripts/render.mjs` (system Chrome/Chromium/Edge; offline) |
| `npm install` not run / dep missing | `render.mjs` prints the install command and exits non-zero → deliver `.excalidraw`, open in a viewer |
| No browser found | Set `CHROME_PATH=…`, or deliver `.excalidraw` only |
| Vision unavailable | Skip self-check (step 4); show the PNG or the file directly |
| Graphviz `dot` missing | `autolayout.py` exits with a clear message → hand-place coordinates instead |

## Common mistakes

When something looks wrong (render fails, vision rejects a PNG, layout broken, arrows float), see `references/troubleshooting.md` for a mistake → fix table.
