# Element schema & vocabulary

Read this when you need the **raw Excalidraw element schema**, the
color/font/roughness vocabulary, or to understand how community
`.excalidrawlib` libraries map in. This is the reference for *understanding and
debugging* a `.excalidraw` file — **not** an authoring guide.

Excalidraw has **no 10,000-shape stock library**. There are nine element types
and a small set of styling fields; everything (a database, a queue, a service)
is one of those nine with a chosen color, fill, and label. So unlike a
stencil-based tool, the "vocabulary" here is *fields*, not shape names.

> **Always generate with the `Scene` builder** (`references/builder-api.md`),
> never by hand-writing this JSON. Every element needs a unique `id`, a `seed`,
> and a `versionNonce`; arrows must carry relative `points` **plus**
> `startBinding`/`endBinding`, and each shape they touch must list the arrow
> back in its own `boundElements`; bound text labels are wired the same on both
> sides. `Scene` owns all of that. Hand-edits are what `scripts/validate.py`
> exists to catch — see the end of this file.

## The file shape

A `.excalidraw` file is a single JSON object. `Scene.to_dict()` produces exactly
this:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://github.com/devbyshima/skills",
  "elements": [ /* the drawing — ordered back-to-front */ ],
  "appState": { "gridSize": null, "viewBackgroundColor": "#ffffff" },
  "files": { /* fileId -> embedded image data, see Images below */ }
}
```

| Field | Meaning |
|---|---|
| `type` | always `"excalidraw"` — viewers reject anything else |
| `version` | schema version (the builder emits `2`) |
| `source` | provenance string; cosmetic |
| `elements` | the array of element objects, **painted in array order** (later = on top) |
| `appState` | canvas-level state; the builder only sets `gridSize` (null) and `viewBackgroundColor` |
| `files` | map of `fileId` → `{mimeType,id,dataURL,...}` for embedded images; `{}` when there are none |

`.excalidrawlib` (libraries, below) is a *different* top-level shape
(`"type": "excalidrawlib"`) — don't confuse the two.

## Element types

Nine `type` values. The builder method that produces each is in the last column.

| `type` | What it is | Builder method |
|---|---|---|
| `rectangle` | box — services, modules, processes (rounded by default) | `s.rect(...)` |
| `ellipse` | circle/ellipse — databases-as-circles, start/end | `s.ellipse(...)` |
| `diamond` | decision / branch (defaults to yellow) | `s.diamond(...)` |
| `arrow` | a directed connector, optionally bound to two shapes | `s.arrow(...)` / `s.routed_arrow(...)` |
| `line` | an undirected multi-point polyline / separator | `s.line(...)` |
| `text` | free-standing label, or a label bound inside a container | `s.text(...)`, or `text=` on a shape |
| `image` | an embedded raster/SVG (logos via `aiicons.py`) | `s.image(...)` |
| `frame` | a named grouping region drawn around elements | `s.frame(...)` |
| `freedraw` | a raw pen stroke (sketched by hand in the app) | — not emitted by the builder |

`freedraw` exists in files you *open* (someone drew with the pencil tool); the
builder never creates one. Treat it as read-only.

## Common fields (every element)

These appear on all element types. The builder's `_base(...)` sets every one of
them, so you never assign them yourself.

| Field | Type | Notes |
|---|---|---|
| `id` | string | unique per element; the builder returns it from each `s.rect/ellipse/...` call so you can wire arrows |
| `type` | string | one of the nine above |
| `x`, `y` | number | top-left corner; **origin top-left, y grows downward** |
| `width`, `height` | number | bounding box |
| `angle` | number | rotation in **radians** (0 = upright) |
| `strokeColor` | hex string | outline color |
| `backgroundColor` | hex or `"transparent"` | fill color (containers/arrows/text are `"transparent"`) |
| `fillStyle` | string | `solid` · `hachure` · `cross-hatch` (only matters when `backgroundColor` ≠ transparent) |
| `strokeWidth` | number | `1` thin · `2` bold · `4` extra-bold |
| `strokeStyle` | string | `solid` · `dashed` · `dotted` |
| `roughness` | int | `0` architect · `1` artist · `2` cartoonist — the hand-drawn wobble |
| `roundness` | object or null | `{"type": 3}` = rounded corners (rectangles only); `null` = sharp |
| `opacity` | int | 0–100 |
| `seed` | int | feeds roughjs's wobble RNG; **must be present** or the shape mis-renders |
| `version`, `versionNonce` | int | edit-tracking / collab; the builder sets `version: 1` and a deterministic nonce |
| `isDeleted` | bool | tombstone — viewers skip `true`; `validate.py` ignores them |
| `boundElements` | array | back-references: `[{"id","type":"arrow"|"text"}]` — the arrows/labels attached to *this* element |
| `groupIds` | array of string | shared group membership (selecting one selects the group); empty by default |
| `frameId` | string or null | the `frame` this element belongs to, if any |
| `updated` | int | last-edit timestamp (ms); builder uses a fixed value for reproducible output |
| `link`, `locked` | string?/bool | hyperlink and lock state; defaults `null`/`false` |

`seed` + `versionNonce` are the two fields most commonly missed when JSON is
hand-written — and they're exactly what make the wobble deterministic, so the
builder derives both from a seeded LCG.

## Text fields (`type: "text"`)

A text element adds these on top of the common fields. It comes in two flavors:
**free-standing** (`containerId: null`, from `s.text(...)`) or a **bound label**
(`containerId` set, created automatically when you pass `text=` to a shape or
`label=` to an arrow).

| Field | Notes |
|---|---|
| `text` | the rendered string (`\n` for line breaks) |
| `originalText` | pre-wrap source text; equals `text` for the builder's output |
| `fontSize` | px |
| `fontFamily` | font id — `1` hand-drawn, `2` normal, `3` code (table below) |
| `textAlign` | `left` · `center` · `right` |
| `verticalAlign` | `top` · `middle` · `bottom` |
| `containerId` | id of the shape/arrow this label lives inside, or `null` for free text |
| `lineHeight` | multiplier (builder uses `1.25`) |
| `autoResize` | `true` for free text, `false` for bound labels (the container fixes the box) |

A bound label is wired **both ways**: the text's `containerId` points at the
container, and the container's `boundElements` lists `{"id": <text id>, "type":
"text"}`. Break either side and the box renders unlabeled.

## Arrow fields (`type: "arrow"`)

| Field | Notes |
|---|---|
| `points` | `[[x,y],...]` **relative to the element's `x`/`y`** — at least two points, first usually `[0,0]` |
| `startBinding` / `endBinding` | `{"elementId","focus","gap"}` binding to a shape, or `null` for an unbound (raw-point) arrow |
| `startArrowhead` / `endArrowhead` | `null` · `arrow` · `triangle` · `dot` · `bar` · `diamond` (default: start `null`, end `arrow`) |
| `lastCommittedPoint` | editor scratch field; builder sets `null` |

The hard part — and why you use the builder — is that a bound arrow is a
**three-way** contract: the arrow names both shapes in `startBinding`/
`endBinding`, **and** both shapes name the arrow back in their `boundElements`.
`s.arrow(src_id, dst_id)` computes the on-border attach points, sets the
relative `points`, and writes all three references. `s.routed_arrow(points,
source=, target=)` does the same along an explicit polyline (this is how
`autolayout.py` replays Graphviz's orthogonal routes so lines bend around
boxes). `line` elements share `points` but have no bindings or arrowheads.

## Image fields (`type: "image"`) + the `files` map

| Field | Notes |
|---|---|
| `fileId` | key into the top-level `files` map |
| `status` | `"saved"` once the bytes are present |
| `scale` | `[sx, sy]` flip/scale, normally `[1, 1]` |

The pixels/SVG live in `files`, keyed by `fileId`:

```json
"files": {
  "file-1": {
    "id": "file-1",
    "mimeType": "image/svg+xml",
    "dataURL": "data:image/svg+xml;base64,PHN2Zy4uLg==",
    "created": 1700000000000,
    "lastRetrieved": 1700000000000
  }
}
```

Excalidraw **embeds image bytes as a data URL** — there is no "reference by URL"
mode. `s.image(x, y, w, h, dataURL, mime="image/svg+xml")` allocates the
`fileId`, adds the element, and stores the entry. This is what makes a logo
diagram fully self-contained and offline-renderable. See **AI / brand logos**
below.

## Frames and groups

- **`frame`** is a first-class element: a named, bordered region. `s.frame(x,
  y, w, h, name)` creates one; member elements carry its id in their `frameId`.
- **`groupIds`** is lighter: any number of elements sharing an id in their
  `groupIds` array move and select together, with no visible border. The builder
  accepts `group_ids=[...]` on shape/arrow/line methods.

Use a `frame` when you want a visible labeled boundary (a tier/zone); use
`groupIds` for "these move as one" with no chrome.

## Color palette

The builder maps seven **semantic roles** to Excalidraw's own stroke/background
swatch pairs. Pass `role=` and the colors are chosen for you; pass explicit
`stroke=`/`background=` to override. (`backgroundColor` is the light fill;
`strokeColor` is the saturated outline that pairs with it.)

| Slot | Roles → it | `strokeColor` | `backgroundColor` | Reads as |
|---|---|---|---|---|
| `primary` | service, client | `#1971c2` | `#a5d8ff` | blue |
| `success` | database, store | `#2f9e44` | `#b2f2bb` | green |
| `warning` | queue, bus, decision | `#f08c00` | `#ffec99` | yellow |
| `accent` | gateway, api | `#e8590c` | `#ffd8a8` | orange |
| `danger` | error | `#e03131` | `#ffc9c9` | red |
| `neutral` | external | `#495057` | `#e9ecef` | grey |
| `secondary` | security, auth | `#9c36b5` | `#eebefa` | purple |

Default stroke for a role-less, color-less shape is `#1e1e1e` on a
`transparent` fill. A **style preset** (`styles/built-in/*.json`,
`references/style-presets.md`) can replace the whole palette — e.g. `clean` uses
deeper, lower-saturation variants. Preset palette entries use
`{strokeColor, backgroundColor}`; `Scene.from_preset(...)` maps them onto the
slots above.

## Fonts, roughness, fill, stroke

| Knob | Values | Notes |
|---|---|---|
| `fontFamily` | `1` hand-drawn (Excalifont/Virgil) · `2` normal (Nunito) · `3` code (Comic Shanns Mono) | builder constants `FONT_HAND=1`, `FONT_NORMAL=2`, `FONT_CODE=3` |
| `roughness` | `0` architect (clean) · `1` artist (default) · `2` cartoonist (most sketchy) | the signature wobble |
| `fillStyle` | `solid` · `hachure` (sketchy diagonal) · `cross-hatch` | only visible when `backgroundColor` ≠ transparent |
| `strokeWidth` | `1` thin · `2` bold · `4` extra-bold | |
| `strokeStyle` | `solid` · `dashed` · `dotted` | dashed edges read as "optional" in the `sketch` preset |
| `roundness` | `{"type": 3}` rounded · `null` sharp | rectangles round by default; ellipse/diamond never |

These are the dials the built-in presets turn: `default` = roughness 1 / solid /
hand; `sketch` = roughness 2 / hachure / hand; `clean` = roughness 0 / solid /
normal. Set them per-`Scene` (`Scene(roughness=0, fill_style="hachure", ...)`)
or per-element (`s.rect(..., roughness=2, fill_style="hachure")`).

## AI / brand logos (instead of a stencil library)

Excalidraw ships no AWS/Azure/GCP/vendor stencils, so an "LLM app architecture"
would otherwise be unlabeled boxes. `scripts/aiicons.py` resolves a brand name
to a logo SVG (from [lobe-icons](https://github.com/lobehub/lobe-icons), MIT —
OpenAI, Claude, Gemini, Mistral, Llama, HuggingFace, Ollama, LangChain, …) and
inlines it as a data URI ready for `s.image(...)`:

```bash
python3 <this-skill-dir>/scripts/aiicons.py "openai" --json        # embeddable image record
python3 <this-skill-dir>/scripts/aiicons.py "claude" --variant mono --size 64
python3 <this-skill-dir>/scripts/aiicons.py --list                 # all brand names
```

- Returns a **square** record `{brand,file,w,h,mime,dataURL}`; use the reported
  `w`/`h` for both dimensions. Picks the `-color` variant when it exists, else
  the mono logo.
- There is **no URL-reference mode** (Excalidraw embeds bytes), so the SVG is
  fetched and inlined at generation time — network is needed *then*, but the
  resulting `.excalidraw` is self-contained and renders offline.
- Common RAG/LLM data stores lobe lacks (Qdrant, Redis, Postgres, Mongo,
  Elasticsearch, Milvus, Supabase, Neo4j, ClickHouse, Kafka, Snowflake,
  Databricks, …) fall back to [simple-icons](https://simpleicons.org) (CC0) —
  same command, same output shape. A brand in neither set has no logo: draw an
  ellipse/"cylinder" instead.
- Logos are trademarks of their owners, referenced for identification only.

Drop the result into the builder:

```python
import json, subprocess, sys; sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene
icon = json.loads(subprocess.check_output(
    [sys.executable, "<this-skill-dir>/scripts/aiicons.py", "openai", "--json"]))[0]
s = Scene()
s.image(120, 120, icon["w"], icon["h"], icon["dataURL"], mime=icon["mime"])
```

## Community `.excalidrawlib` libraries

[libraries.excalidraw.com](https://libraries.excalidraw.com) hosts community
**element libraries** — reusable sticker-like groups (UI kits, AWS/network
glyphs, icon packs). They are a fundamentally different model from a draw.io
stencil set:

- A library is **not** a vocabulary of shape *names*. An `.excalidrawlib` file
  (`"type": "excalidrawlib"`, a `libraryItems` array) is just **pre-drawn groups
  of the same nine element types** described above — each item is rectangles,
  lines, and text already arranged and grouped. There is no `style=` string to
  search, no stencil engine; pasting one drops those raw elements onto the
  canvas.
- They're designed for the interactive app (browse, add to your library, drag
  onto the canvas), not for programmatic generation. There's no builder method
  to import one.

For this skill's purposes the builder + `aiicons.py` cover the practical need a
library would serve: the nine element types compose any node shape, and
`aiicons.py` supplies the **branded-logo** case (the one thing you can't draw
from primitives). If a user specifically wants a community library asset, point
them to the app: add it from libraries.excalidraw.com, then paste it into a
generated file in Excalidraw.

## Debugging a file

When a hand-edited or externally-produced `.excalidraw` renders wrong, lint it
deterministically before eyeballing pixels:

```bash
python3 <this-skill-dir>/scripts/validate.py file.excalidraw [--strict]
```

It flags exactly the schema traps this file documents — duplicate ids, arrows/
lines with `<2 points`, `startBinding`/`endBinding`/`containerId`/`boundElements`
pointing at a missing element (errors), plus one-sided bindings, a label whose
container doesn't list it back, and overlapping filled shapes (warnings, fatal
only with `--strict`). Builder output passes clean; a failure means the JSON was
touched by hand — fix it by editing the **builder script** and re-running, not
the JSON.
