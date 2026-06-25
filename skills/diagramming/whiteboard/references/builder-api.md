# Builder API — `scripts/excalidraw.py`

The `Scene` class is the **single source of truth** for the `.excalidraw` file format. The skill generates every diagram by importing `Scene` and calling its methods — it **never** hand-writes JSON. `autolayout.py` builds on this same class.

Why a builder and not raw JSON: every element needs a unique `id`, a `seed`, a `versionNonce`, and the right `roundness`/`roughness`/`fillStyle` vocabulary. Arrows must carry relative `points` **plus** `startBinding`/`endBinding`, and **each shape an arrow touches must list that arrow back in its own `boundElements`**. Bound text labels are the same on both sides (the text points at its container via `containerId`; the container lists the text in `boundElements`). Miss either side and the file opens but renders wrong — floating arrows, unlabeled boxes. `Scene` handles all of that for you.

```python
import sys; sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene

s = Scene()
a = s.rect(100, 100, 160, 60, text="Client", role="service")
b = s.rect(100, 300, 160, 60, text="API",    role="gateway")
s.arrow(a, b, label="HTTP")          # geometry + both-sided binding handled
s.dump("diagram.excalidraw")
```

Element-creating methods (`rect`, `ellipse`, `diamond`, `text`, `arrow`, `routed_arrow`, `line`, `frame`, `image`) all **return the new element's `id` (a `str`)** so you can wire arrows and labels to it.

---

## Constructing a Scene

```python
Scene(
    background="#ffffff",   # appState.viewBackgroundColor
    seed=12345,             # base for the deterministic seed/versionNonce stream
    roughness=1,            # 0 architect · 1 artist (default) · 2 cartoonist
    font_family=1,          # 1 hand-drawn · 2 normal · 3 code   (FONT_HAND/NORMAL/CODE)
    fill_style="solid",     # solid · hachure · cross-hatch
    stroke_width=2,         # 1 thin · 2 bold · 4 extra-bold
    font_size=20,           # default for shape labels and free text
    palette=None,           # dict: slot -> {"stroke": hex, "background": hex} (merged over PALETTE)
    roles=None,             # dict: role name -> palette slot (merged over ROLE_SLOT)
)
```

Every option becomes the scene's **default** for elements that don't override it. `background` sets the page color; the rest (`roughness`, `font_family`, `fill_style`, `stroke_width`, `font_size`) are applied to each shape unless you pass the matching per-call keyword. `palette` and `roles` let a style preset override colors and role mapping (see `Scene.from_preset`).

Construction also sets `self.edge_defaults` (`stroke_style="solid"`, `start_arrowhead=None`, `end_arrowhead="arrow"`) — the defaults `arrow()`/`routed_arrow()` fall back to when their own args are `None`.

### `Scene.from_preset(preset, **overrides)`

Builds a Scene configured from a style-preset dict (`styles/built-in/<name>.json` or `~/.whiteboard/styles/<name>.json`). It maps the Excalidraw-vocabulary preset onto the constructor:

| Preset key | Maps to |
|---|---|
| `palette[slot]` = `{strokeColor, backgroundColor}` | `palette[slot]` = `{stroke, background}` |
| `roles` | `roles` (role → slot) |
| `extras.roughness` / `.fillStyle` / `.strokeWidth` | `roughness` / `fill_style` / `stroke_width` |
| `font.family` (`"hand"`/`"normal"`/`"code"`) / `font.size` | `font_family` / `font_size` |
| `edges.strokeStyle` / `.startArrowhead` / `.endArrowhead` | `self.edge_defaults` |

`**overrides` are keyword args that win over the preset (e.g. `Scene.from_preset(p, background="#1e1e1e")`).

```python
import json
preset = json.load(open("<this-skill-dir>/styles/built-in/sketch.json"))
s = Scene.from_preset(preset)            # cartoonist roughness + hachure fills
```

---

## Role → color palette

Roles auto-pick a stroke + fill from `PALETTE`. Pass `role=` on any shape; the role resolves through `ROLE_SLOT` to a palette slot. The seven slots:

| Slot | Stroke | Background | Roles that map here | Typical use |
|---|---|---|---|---|
| `primary` | `#1971c2` | `#a5d8ff` | `service`, `client` | services, clients |
| `success` | `#2f9e44` | `#b2f2bb` | `database`, `store` | databases, success states |
| `warning` | `#f08c00` | `#ffec99` | `queue`, `bus`, `decision`, *(diamond default)* | queues, decisions |
| `accent` | `#e8590c` | `#ffd8a8` | `gateway`, `api` | gateways, APIs |
| `danger` | `#e03131` | `#ffc9c9` | `error` | errors, alerts |
| `neutral` | `#495057` | `#e9ecef` | `external` | external / neutral systems |
| `secondary` | `#9c36b5` | `#eebefa` | `security`, `auth` | security, auth |

Resolution rules (`_resolve`):
- A `role` looks up `ROLE_SLOT[role]`, then `PALETTE[slot]`. If the role name **is itself a slot** (e.g. `role="primary"`), that works too.
- An explicit `stroke=`/`background=` always wins over the role's value.
- With no role and no explicit color: stroke falls back to `DEFAULT_STROKE` (`#1e1e1e`) and background to `"transparent"`.

Module-level names you can import: `PALETTE`, `ROLE_SLOT`, `DEFAULT_STROKE`, `FONT_HAND` (1), `FONT_NORMAL` (2), `FONT_CODE` (3).

---

## Vocabulary

| Attribute | Values |
|---|---|
| **roughness** | `0` architect (clean, no wobble) · `1` artist (default) · `2` cartoonist (most sketchy) |
| **fill_style** | `"solid"` · `"hachure"` (sketchy diagonal) · `"cross-hatch"` |
| **font_family** | `1` hand-drawn (Excalifont) · `2` normal (Nunito) · `3` code (Comic Shanns Mono) |
| **stroke_width** | `1` thin · `2` bold · `4` extra-bold |
| **stroke_style** | `"solid"` · `"dashed"` · `"dotted"` |

---

## Shapes

All three shape methods share the same keyword set (passed through `_shape`):

`text=None, role=None, stroke=None, background=None, fill_style=None, stroke_width=None, stroke_style="solid", roughness=None, rounded=…, opacity=100, group_ids=None, angle=0.0, font_size=None, font_family=None, text_color=None`

- `text=` adds a **bound, centered** label (wired both ways — see below). `text_color=` defaults to the shape's stroke.
- `font_size`/`font_family` apply to that bound label.
- Any of `fill_style`/`stroke_width`/`roughness`/`font_size` left `None` inherit the scene default.
- `group_ids` is a list of group id strings; `angle` is rotation in radians.

### `s.rect(x, y, w, h, **kw) -> id`

Rounded rectangle (services, modules, processes). `rounded` defaults **on** — sets `roundness={"type": 3}`.

```python
api = s.rect(120, 260, 160, 60, text="API Gateway", role="gateway")
```

### `s.ellipse(x, y, w, h, **kw) -> id`

Ellipse / circle (databases-as-circles, start/end). `rounded` defaults **off**.

```python
db = s.ellipse(360, 560, 160, 70, text="User DB", role="database")
```

### `s.diamond(x, y, w, h, **kw) -> id`

Diamond (decisions). `rounded` defaults **off**; `role` defaults to `"warning"` (yellow) when you don't pass one.

```python
dec = s.diamond(110, 410, 180, 90, text="Authed?")
```

---

## Text

### `s.text(x, y, text, *, font_size=None, font_family=None, color=None, align="left", valign="top", group_ids=None, angle=0.0, opacity=100) -> id`

Free-standing text — titles, annotations. `(x, y)` is the top-left. `color` defaults to `DEFAULT_STROKE`; `font_family`/`font_size` fall back to the scene defaults. `align` is `"left"`/`"center"`/`"right"`; `valign` is `"top"`/`"middle"`/`"bottom"`. Box size is estimated by `_measure`; Excalidraw recomputes exact metrics on load.

```python
title = s.text(120, 40, "Request flow", font_size=28)
```

---

## Arrows & lines

### How binding works

`arrow()` accepts **either** two element ids **or** two raw `(x, y)` point pairs:

- **Element ids** (`s.arrow(a, b)`) — the recommended path. The builder computes each end's **on-border attachment point** along the ray to the other shape's center (pushed out by `gap`, default `6`), sets relative `points`, wires `startBinding`/`endBinding` with `focus: 0, gap`, and **registers the arrow in both shapes' `boundElements`**. The arrow stays attached and re-routes when you move shapes in Excalidraw.
- **Raw points** (`s.arrow((100,100), (300,300))`) — no shapes to bind to, so `startBinding`/`endBinding` are `None`. Use only when there's nothing to attach to; prefer ids so arrows track their shapes.

### Bound text labels

Passing `label=` to an arrow (or `text=` to a shape) creates a text element centered on the arrow/shape, with `containerId` pointing back at it and the container listing the label in `boundElements` — the both-sided wiring Excalidraw needs. Label font size defaults to `16` (`label_font_size=`); the label color defaults to the arrow's stroke.

### `s.arrow(source, target, *, label=None, stroke=None, stroke_width=2, stroke_style=None, roughness=None, start_arrowhead=None, end_arrowhead="arrow", gap=6, label_font_size=16, group_ids=None, opacity=100) -> id`

`stroke_style` and the arrowheads, left unset, inherit `edge_defaults` (so a style preset's `edges` apply) — the effective defaults are solid stroke, no start head, `"arrow"` end head. Arrowheads are `"arrow"`, `"triangle"`, `"dot"`, `"bar"`, `"diamond"`, or `None`.

```python
s.arrow(client, api, label="HTTPS")             # bound, both sides
s.arrow(dec, err, label="no", stroke_style="dashed")
s.arrow((100, 100), (300, 300))                 # raw points, unbound
```

### `s.routed_arrow(points, *, source=None, target=None, label=None, stroke=None, stroke_width=2, stroke_style=None, roughness=None, end_arrowhead="arrow", start_arrowhead=None, label_font_size=16, gap=4, group_ids=None, opacity=100) -> id`

Arrow following an **explicit absolute polyline** (≥2 points) — used by `autolayout.py` to replay Graphviz's orthogonal route so the line bends around nodes. Optional `source`/`target` element ids add editable bindings (and register the arrow in those shapes' `boundElements`) without overriding the hand-routed geometry.

```python
s.routed_arrow([(120, 170), (120, 230), (300, 230), (300, 410)],
               source=api, target=db, label="query")
```

### `s.line(points, *, stroke=None, stroke_width=2, stroke_style="solid", roughness=None, group_ids=None, opacity=100) -> id`

Multi-point line from absolute `[(x, y), …]` (separators, freeform). No arrowheads, no binding.

```python
s.line([(40, 200), (640, 200)], stroke_style="dashed")   # divider
```

---

## Containers & images

### `s.frame(x, y, w, h, name="Frame") -> id`

A named frame — a visual grouping region (light grey border).

```python
s.frame(80, 80, 600, 700, name="Auth tier")
```

### `s.image(x, y, w, h, data_url, mime="image/svg+xml") -> id`

Embed an image. `data_url` is a `data:` URI; the bytes are stored in the scene's `files` map and referenced by `fileId`. AI/LLM brand logos come from `aiicons.py` (which returns an embeddable data URL).

```python
import json, subprocess
logo = json.loads(subprocess.check_output(
    ["python3", "<this-skill-dir>/scripts/aiicons.py", "openai", "--json"]))
s.image(120, 110, 48, 48, logo["dataURL"])
```

---

## Output

| Method | Returns / effect |
|---|---|
| `s.to_dict()` | the full scene as a Python dict (`type`/`version`/`source`/`elements`/`appState`/`files`) |
| `s.dumps(indent=2)` | the scene as a JSON string |
| `s.dump(path, indent=2)` | writes the file and returns `path` |

---

## Deterministic seeds

Each element's `seed` and `versionNonce` come from a deterministic LCG (Numerical Recipes constants) advanced from the constructor's `seed` arg, and every `updated` stamp is a fixed timestamp (`1700000000000`). roughjs only needs a stable integer, so **the same script always produces byte-identical output** — diffable in git, reproducible across runs. Pass a different `seed=` to vary the hand-drawn jitter while keeping it deterministic.

---

## Worked example

```python
import sys; sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene

s = Scene()                                                  # artist roughness, handwriting
s.text(120, 40, "Request flow", font_size=28)
client = s.rect(120, 110, 160, 60, text="Web Client", role="service")
gw     = s.rect(120, 260, 160, 60, text="API Gateway", role="gateway")
dec    = s.diamond(110, 410, 180, 90, text="Authed?")        # yellow by default
svc    = s.rect(360, 410, 160, 60, text="User Service", role="service")
db     = s.ellipse(360, 560, 160, 70, text="User DB", role="database")
err    = s.rect(110, 560, 160, 60, text="401", role="error")
s.arrow(client, gw, label="HTTPS")
s.arrow(gw, dec)
s.arrow(dec, svc, label="yes")
s.arrow(dec, err, label="no", stroke_style="dashed")
s.arrow(svc, db, label="SQL")
s.dump("request-flow.excalidraw")
```

Then lint: `python3 <this-skill-dir>/scripts/validate.py request-flow.excalidraw`. The builder also ships a self-test that builds this exact scene and validates its structure:

```bash
python3 <this-skill-dir>/scripts/excalidraw.py --selftest          # prints element/file/error counts
python3 <this-skill-dir>/scripts/excalidraw.py --demo out.excalidraw
```
