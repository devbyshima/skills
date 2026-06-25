# Auto-layout (Graphviz)

Read this when a diagram is **large or layout-heavy** — dependency/call graphs, code/module structure, or roughly **more than ~15 nodes** — where hand-placing `x`/`y` coordinates in the builder is slow, error-prone, and overlap-prone.

Instead of computing coordinates by hand in the **Generate** step, describe the graph as JSON and let `scripts/autolayout.py` place the nodes and route the edges with Graphviz. The script feeds everything through the same `excalidraw.Scene` builder the rest of the skill uses, so the output is a normal `.excalidraw` file — continue the usual workflow (Export draft → Self-check → Review loop → Final delivery) from there.

For small or carefully-styled diagrams, keep hand-placing — auto-layout trades fine control for scale.

## Dependency

Requires Graphviz `dot` on PATH:

```bash
# macOS
brew install graphviz
# Debian/Ubuntu
sudo apt install graphviz
```

The script exits with a clear message (``error: Graphviz `dot` not found on PATH (brew install graphviz)``) if `dot` is missing — fall back to hand-placed coordinates in that case.

## Usage

```bash
python3 <this-skill-dir>/scripts/autolayout.py graph.json -o diagram.excalidraw
```

It prints `wrote diagram.excalidraw (N nodes, M edges)` to stderr and writes a normal `.excalidraw` file (with `-o` omitted it streams the JSON to stdout). From there, continue at the **Export draft** step of the main workflow:

```bash
node <this-skill-dir>/scripts/render.mjs diagram.excalidraw -f png -o diagram
```

Two flags shape the look: `--mono` (no group colours) and `--roughness 0|1|2`.

| Flag | Default | Effect |
|---|---|---|
| `-o`, `--output` | stdout | Output `.excalidraw` path |
| `--mono` | off (colour) | Don't colour groups by palette — dashed grey containers, uncoloured (black-outline) nodes |
| `--roughness` | `1` | Stroke style for the whole scene: `0` architect (clean) · `1` artist (default) · `2` cartoonist |

## Input format

```json
{
  "direction": "TB",
  "nodes": [
    {"id": "client", "label": "Web Client", "role": "service"},
    {"id": "gw", "label": "API Gateway", "role": "gateway", "group": "edge", "groupLabel": "Edge tier"},
    {"id": "db", "label": "User DB", "shape": "ellipse", "role": "database", "width": 160, "height": 70, "group": "data"}
  ],
  "edges": [
    {"source": "client", "target": "gw", "label": "HTTPS"},
    {"source": "gw", "target": "db"}
  ]
}
```

**Fields**

| Field | Required | Default | Notes |
|---|---|---|---|
| `direction` | no | `TB` | `TB` (top→bottom) or `LR` (left→right) — the layout rank direction |
| `nodes[].id` | **yes** | — | Unique; matched by edges |
| `nodes[].label` | no | the `id` | Display text shown inside the shape |
| `nodes[].role` | no | none (else group colour, else uncoloured) | One of `service` / `database` / `queue` / `gateway` / `decision` / `error` / `external` / `security` — picks colours from the shared palette (service→blue, database→green, queue/decision→yellow, gateway→orange, error→red, external→grey, security→purple) |
| `nodes[].shape` | no | `rectangle` | `rectangle` (rounded box), `ellipse`, or `diamond` |
| `nodes[].width` / `height` | no | `160` / `60` | Pixels; dot lays out at this real size |
| `nodes[].fillColor` / `strokeColor` | no | none | Explicit hex colours; **override** `role` and group tint |
| `nodes[].group` | no | none | Group key, or a `/`-delimited path (`"core/db"`) for **nested** containers — nodes sharing a path are boxed together (see **Containers / grouping**) |
| `nodes[].groupLabel` | no | last path segment | Title shown on the node's deepest container (first node carrying it wins) |
| `edges[].source` / `target` | **yes** | — | Must match node ids |
| `edges[].label` | no | empty | Edge text, attached to the arrow |

This is the **same contract as the drawio-skill** graph JSON (with `role`/`shape` in place of a raw style string), so the bundled importers feed both skills.

## How it places things

- Node positions come from `dot` (`-Tplain`, the hierarchical layered layout), converted from dot's bottom-left-origin points to Excalidraw's top-left pixels and snapped to the grid (multiples of 10).
- The dot graph is built with `splines=ortho`, so dot computes an **orthogonal route** for each edge. That route's bend points are replayed verbatim as a multi-point `s.routed_arrow([...])` — Excalidraw arrows are otherwise straight and **do not auto-avoid obstacles**, so replaying dot's route is what makes edges go *around* nodes instead of through them. (If an edge has no route — e.g. a self/parallel case — it falls back to a bound straight `s.arrow(src_id, dst_id)`.)
- Each node becomes `s.rect` / `s.ellipse` / `s.diamond` per its `shape`, coloured by `role` (or `fillColor`/`strokeColor`, or its group tint). Arrows bind to the node element ids on both sides, so the file passes the structural lint and stays editable in any viewer.

## Containers / grouping

Give nodes a `group` key and the script wraps each group in a labeled container — a **dashed rounded box** drawn first (so nodes sit on top) with the group title in its top padding — and tells `dot` to keep that group's nodes together via a Graphviz cluster (`subgraph cluster_N { margin=… }`). Ungrouped nodes stay at the top level. This turns a flat hairball into a "boxes of related modules" architecture view.

**Nesting.** A `group` value with `/` separators builds nested containers: `"core/db"` puts the node inside a `db` box that itself sits inside a `core` box. Every path prefix becomes a container, so an arbitrarily deep package tree maps to nested boxes. A node can also sit *directly* in a parent box (`group: "core"`) alongside a sibling sub-box (`group: "core/db"`).

- **Colour by group.** Each top-level group is assigned a colour from the skill's palette, cycled in role order: blue → green → orange → purple → yellow → red → grey (`primary` → `success` → `accent` → `secondary` → `warning` → `danger` → `neutral`). A node with no `role`/`fillColor` of its own is tinted with its group's colour, and the container's dashed border + title match — so related modules read as a coloured cluster instead of monochrome boxes. A node that carries its own `role` or `fillColor`/`strokeColor` is left untouched. Pass `--mono` to turn colouring off (dashed grey boxes, uncoloured black-outline nodes). Ungrouped graphs are unaffected.
- Each container box is the bounding box of its members and child boxes plus a uniform padding (`GROUP_PAD = 28`, with extra room at the top for the title). The dot cluster `margin` is set to that same padding, so each box matches dot's cluster box — which dot keeps non-overlapping at **any nesting depth**.
- The title text sits in the box's top padding, coloured to match the border; the box title is the path's last segment, or a member's `groupLabel`.
- Containers are **visual only** (no arrows of their own). Edges still connect node→node and route across containers normally.
- If a container's top padding would cross the canvas origin, the whole scene is shifted so nothing lands at a negative coordinate.

## Validate before previewing

`scripts/validate.py` is a deterministic structural linter — run it on the produced `.excalidraw` before the (slower, vision-based) self-check:

```bash
python3 <this-skill-dir>/scripts/validate.py diagram.excalidraw
```

It catches dangling arrow bindings, duplicate ids, and sub-2-point arrows (errors), plus one-sided bindings, negative-size geometry, and overlapping filled shapes (warnings) — without launching a browser. Exit status is non-zero on any error (or any warning with `--strict`), so it can gate the workflow. Auto-layout output should always pass clean; a failure means a malformed input graph (e.g. an edge referencing a missing node id).

## Importers — visualize code structure

Bundled importers turn a codebase into a graph JSON ready for autolayout, so "visualize this project" is a two-step pipeline:

| Language | Script | Node = | Edge = |
|---|---|---|---|
| Python | `scripts/pyimports.py <dir>` | module / package (`ast`) | intra-project `import` / `from` |
| JS / TS | `scripts/jsimports.py <dir>` | source file (`.ts/.tsx/.js/.jsx/.mjs/.cjs`) | resolved relative `import` / `export from` / `require()` / `import()` |
| Go | `scripts/goimports.py <dir>` | package (directory, via `go.mod`) | intra-module package import |
| Rust | `scripts/rustimports.py <dir>` | module (`.rs` file / `mod`) | intra-crate `use crate::` / `super::` / `self::` |
| Python (classes) | `scripts/pyclasses.py <dir>` | class (`ast`) | subclass → base (inheritance) |

```bash
python3 <this-skill-dir>/scripts/pyimports.py myproject -o graph.json
python3 <this-skill-dir>/scripts/autolayout.py graph.json -o diagram.excalidraw
```

Each keeps only **intra-project** edges (third-party/stdlib imports are ignored), shortens node labels (drops the shared package/module/directory prefix; ids stay fully qualified), and shares the same flags: `--direction TB|LR` (default `TB`), `--group`, `--no-reduce`.

- **Python** (`pyimports.py`): if the directory is itself a package (`__init__.py` present), module names are package-qualified so the project's own absolute imports resolve; nested subpackages (`pkg.sub.mod`) are handled.
- **JS/TS** (`jsimports.py`): resolution is path-based (tries the source extensions and directory `index` files); `node_modules` and bare specifiers are skipped. Scanning is regex-based, not a full parser.
- **Go** (`goimports.py`): reads the `module` path from `go.mod`; each directory of `.go` files is one package; `*_test.go` and `vendor/` are skipped.
- **Rust** (`rustimports.py`): each `.rs` file is a module (`mod.rs`/`main.rs`/`lib.rs` name the enclosing module); edges come from `use` paths rooted at `crate::`/`super::`/`self::` (brace groups expanded). `std`/external crates and `target/` are skipped. Regex-based — inline `mod { … }` blocks aren't split out, and 2015-edition bare intra-crate paths aren't resolved.
- **Python classes** (`pyclasses.py`): a finer granularity — one node per class, edges from each subclass to the project base classes it extends, so the result is an auto-generated class hierarchy. Bases are matched by name (preferring the same module); external bases (`object`, third-party) are ignored. With `--group`, classes are boxed by their module, so a deep package tree nests naturally. Inheritance only — function-level call graphs are out of scope (static call resolution in Python is unreliable).

**Density reduction is on by default** — this is the key to a readable result. Real import graphs are dense (asyncio: 33 modules / ~149 edges); without reduction they render as a hairball. Every importer applies **transitive reduction** (Graphviz `tred` — drops edges already implied by a longer path), which on asyncio cuts ~149 edges to ~46 and turns the hairball into a clean, traceable diagram. Pass `--no-reduce` to keep every edge.

**`--group`** assigns each node a container by its sub-package / directory path, so autolayout boxes related modules together — nested when the path has depth (see **Containers / grouping**). The fastest way to turn a large code graph into a tiered architecture view.

For any other language, produce the same graph JSON from any analyzer (e.g. `dependency-cruiser` for richer JS/TS resolution, `go-callvis` for Go call graphs) and feed it to autolayout the same way.

## Limitations

- **Placement is topological, not semantic** — dot minimises edge crossings, which may put a node in a different column than you'd choose by hand. Re-export with the other `direction`, or open the produced `.excalidraw` and nudge shapes by hand (it's a normal file).
- **Import edges are static** — `pyimports`/`jsimports`/`goimports` read static import statements (not dynamic `importlib`, runtime `require`, or reflection); `pyclasses` resolves inheritance only, not method-level calls.
- **Parallel edges** between the same `(source, target)` pair share one route.
- **Containers don't add edges** — `group`/nesting only boxes nodes for layout; edges remain node→node. For hand-built architecture containers with their own connections, build the scene directly with the `Scene` builder (see `references/builder-api.md`).
