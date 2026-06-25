# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-25

Initial release. Adapted from `drawio-skill` to produce `.excalidraw` (JSON, hand-drawn / whiteboard look) instead of `.drawio` (XML). The skill never hand-writes the JSON — it generates diagrams by calling the `Scene` builder, then optionally renders an image.

### Added

- **Scene builder** (`scripts/excalidraw.py`) — a `Scene` class that owns the Excalidraw JSON schema (unique ids, `seed`, `versionNonce`, `roundness`/`roughness`/`fillStyle`). Element-creating methods return the new element's id so arrows and labels can wire to it: `rect`, `ellipse`, `diamond`, `text`, `arrow` (computes border attach points + both-sided `startBinding`/`endBinding` and registers itself in each shape's `boundElements`), `routed_arrow`, `line`, `frame`, `image`, and `to_dict` / `dumps` / `dump`. Seven semantic roles (service, database, queue, gateway, error, external, security) map to a built-in palette; `Scene.from_preset(...)` applies a style preset. `roughness` 0/1/2 (architect / artist / cartoonist), `fill_style` solid / hachure / cross-hatch, `font_family` 1/2/3 (hand-drawn Excalifont / normal Nunito / code). CLI: `--selftest` and `--demo OUT`.
- **Graphviz auto-layout** (`scripts/autolayout.py`) — takes a graph JSON (`direction`, `nodes`, `edges`) and runs `dot` to place nodes and route edges orthogonally, replaying dot's bend points as multi-point arrows so edges go *around* boxes. Emits a `.excalidraw` via the shared `Scene` builder. Supports node roles/shapes, hierarchical `group` clusters, `--mono`, and `--roughness 0|1|2`.

  ```bash
  python3 scripts/autolayout.py graph.json -o out.excalidraw [--mono] [--roughness 0|1|2]
  ```

- **Structural linter** (`scripts/validate.py`) — a fast, browser-free deterministic lint for `.excalidraw` files. Errors on duplicate ids, arrows/lines with fewer than 2 points, and `startBinding` / `endBinding` / `containerId` / `boundElements` pointing at a missing element; `--strict` also fails on one-sided bindings, unlisted bound labels, overlapping filled shapes, and bad geometry.

  ```bash
  python3 scripts/validate.py file.excalidraw [--strict]
  ```

- **AI / LLM brand logos** (`scripts/aiicons.py`) — resolves a brand name (OpenAI, Claude, Gemini, Mistral, Llama, HuggingFace, LangChain, …) to a lobe-icons SVG and inlines it as a data URI ready for `s.image(...)`, with a simple-icons supplement for common data stores (Qdrant, Redis, Postgres, …). Excalidraw embeds image bytes in the file's `files` map, so the resulting `.excalidraw` is fully self-contained and offline-renderable. Supports `--json`, `--variant color|mono|text`, `--size N`, and `--list`.

  ```bash
  python3 scripts/aiicons.py "openai" [--json] [--variant color|mono|text] [--size N] [--list]
  ```

- **Code importers** — extract a project's structure as autolayout graph JSON (same contract as `autolayout.py`): `pyimports.py`, `jsimports.py`, `goimports.py`, `rustimports.py` for module-import graphs, and `pyclasses.py` for a Python class hierarchy.

  ```bash
  python3 scripts/pyimports.py <dir> -o graph.json [--direction TB|LR] [--group] [--no-reduce]
  ```

- **Offline PNG/SVG export** (`scripts/render.mjs`) — renders via Excalidraw's own renderer in a headless system Chrome/Chromium/Edge (the only way to get the genuine rough.js strokes + Excalifont). Bundles `@excalidraw/excalidraw` with esbuild (cached in `scripts/.cache/`, fonts inlined for offline use) and drives the browser with puppeteer-core. `CHROME_PATH` overrides the browser. If deps or a browser are missing it exits non-zero, and the skill falls back to delivering the always-valid `.excalidraw` file.

  ```bash
  node scripts/render.mjs input.excalidraw [-o out] [-f svg|png|both] [--scale 2] [--theme light|dark] [--no-background]
  ```

- **Built-in style presets** (`styles/built-in/`) — three presets validated against `styles/schema.json`, applied via `Scene.from_preset(...)`:
  - `default` — artist roughness, solid fills, handwriting.
  - `sketch` — full hand-drawn: cartoonist roughness + hachure fills.
  - `clean` — architect roughness 0 + normal font (Excalidraw structure without the wobble).

  User presets in `~/.whiteboard/styles/<name>.json` shadow built-ins and may set `"default": true`.

- **Reference documentation** (`references/`) — eight on-demand docs: `builder-api.md`, `diagram-types.md`, `elements.md`, `export.md`, `style-presets.md`, `style-extraction.md`, `troubleshooting.md`, and `autolayout.md`.

[1.0.0]: https://github.com/devbyshima/skills/releases/tag/v1.0.0
