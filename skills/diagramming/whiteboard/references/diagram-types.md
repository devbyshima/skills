# Diagram Type Conventions

When the user names a specific diagram type, apply the matching conventions below: which `Scene` methods to call, which **role** (→ palette colour) and **shape** each box wants, which arrowhead / stroke style each edge uses, and which **layout direction** to lay it out in. Everything here is expressed in builder terms — you wire it up by calling `scripts/excalidraw.py`'s `Scene`, never by hand-writing JSON. A style preset (see `references/style-presets.md`), if active, layers its palette / font / roughness / edge defaults on top via `Scene.from_preset(...)`.

Read this file when:
- The user names one of these types (ERD, UML class, sequence, architecture, ML/DL model, flowchart, mind map).
- You're choosing shape vocabulary, role colours, or layout direction for a new diagram.

## What Excalidraw does *not* have (and how the builder works around it)

Excalidraw's vocabulary is deliberately small — three filled shapes (`rect`, `ellipse`, `diamond`), `text`, `line`, `arrow`, `frame`, `image`. There are **no table, swimlane, lifeline, cylinder, or parallelogram shapes**, and arrowheads are limited to `"arrow"`, `"triangle"`, `"dot"`, `"bar"`, `"diamond"`, or `None` (there is no hollow-vs-filled flag). So the structural shapes other tools give you are modeled as compositions:

| Want | Build it as |
|---|---|
| ERD table | one `rect` whose `text=` is the field list, `\n`-separated (title on line 1) |
| UML class (3 sections) | one `rect` (title + members in `text=`) **or** a tall `rect` + a `line()` separator + a `text()` block |
| Sequence lifeline | a header `rect` at top + a dashed vertical `line()` dropping down from it |
| Database cylinder | `ellipse` with `role="database"` (green) |
| I/O parallelogram | `rect` (note "I/O" in the label or use the accent/orange role) |
| Layer / tier swimlane | a big transparent dashed `frame()` or `rect(background="transparent", stroke_style="dashed")` enclosing the tier |
| Inheritance "hollow triangle" | `end_arrowhead="triangle"` |
| Composition / aggregation diamond | `end_arrowhead="diamond"` (filled — Excalidraw has no hollow diamond) |

**Roles → colours** (the seven palette slots; `role=` resolves automatically, or pass explicit `stroke=`/`background=`):

| role | slot | colour |
|---|---|---|
| `service` / `client` | primary | blue |
| `database` / `store` | success | green |
| `queue` / `bus` · decisions | warning | yellow |
| `gateway` / `api` | accent | orange |
| `error` | danger | red |
| `external` | neutral | grey |
| `security` / `auth` | secondary | purple |

`s.diamond(...)` already defaults to `role="warning"` (yellow); `s.ellipse(...)` defaults to `rounded=False`.

---

## ERD (Entity-Relationship Diagram)

Excalidraw has no table shape, so **each entity is one `rect` whose label is the column list** — title on the first line, columns on the lines below, `\n`-separated. Mark the primary key with a `PK ` prefix and foreign keys with `FK `.

| Element | Builder call | Notes |
|---|---|---|
| Entity / table | `s.rect(x, y, w, h, text="User\nPK id\nemail\nname", role="service")` | Title line + `\n`-separated columns. Use `role="database"` (green) if you prefer a data tint. Width ~180-220; height ≈ `26 * (rows+1)` |
| PK / FK marker | text convention inside the label | `PK id`, `FK author_id` — prefix in the string |
| Relationship | `s.arrow(a, b, label="1 : N")` | Put cardinality in the label (`1:1`, `1:N`, `N:M`) |
| Optional / nullable FK | `s.arrow(a, b, stroke_style="dashed", label="0..N")` | Dashed = optional participation |
| Identifying edge | `s.arrow(a, b, end_arrowhead="bar")` | `"bar"` reads as the "one" crow's-foot end |

- **Layout:** `TB`, entities ~300px apart vertically; group related tables in a column. Keep labels left-readable (multi-line text in a rect renders centered — that's fine for ERDs).
- For >~10 tables, hand-placing gets painful — feed an autolayout graph (`role`, multi-line `label`) and let Graphviz place them: `python3 <this-skill-dir>/scripts/autolayout.py erd.json -o erd.excalidraw`.

```python
import sys; sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene
s = Scene()
user = s.rect(120, 80, 200, 130,
              text="User\nPK id\nemail\nname\ncreated_at", role="service")
post = s.rect(120, 320, 200, 130,
              text="Post\nPK id\nFK author_id\ntitle\nbody", role="success")
s.arrow(user, post, label="1 : N")          # one user, many posts
s.dump("erd.excalidraw")
```

## UML Class Diagram

A UML class is a three-section box (name / attributes / methods). Two ways to build it:

- **Simple (one rect):** put everything in the label — `"ClassName\n+ id: int\n+ name: str\n--\n+ save()\n+ delete()"`. The `--` line reads as the section divider. Fastest; good for sketches.
- **Crisp separators:** a tall `rect`, then a `s.line([(x, y), (x+w, y)])` drawn across at the section boundary, with `s.text(...)` blocks for each section (left-aligned, `align="left"`). Use this when you want visible rules between name / attributes / methods.

| Element | Builder call | Notes |
|---|---|---|
| Class box | `s.rect(x, y, w, h, text="Animal\n+ name\n--\n+ speak()", role="service")` | Interfaces: use `role="secondary"` (purple) to set them apart |
| Section separator | `s.line([(x, y), (x+w, y)], stroke_width=1)` | Horizontal rule between sections (crisp variant) |
| Inheritance (extends) | `s.arrow(child, parent, end_arrowhead="triangle")` | Triangle head points at the **parent** |
| Implementation (implements) | `s.arrow(impl, iface, end_arrowhead="triangle", stroke_style="dashed")` | Dashed + triangle |
| Composition | `s.arrow(part, whole, end_arrowhead="diamond")` | Filled diamond at the **whole** end |
| Aggregation | `s.arrow(part, whole, end_arrowhead="diamond", stroke_style="dotted")` | Excalidraw has no hollow diamond — dotted stroke distinguishes it |
| Association | `s.arrow(a, b)` (plain) | Optionally label multiplicity |

- **Layout:** `TB`, classes ~250px apart, **interfaces / superclasses above** their implementors so inheritance triangles point upward.

```python
s = Scene()
animal = s.rect(200, 80, 180, 90,  text="Animal\n+ name\n--\n+ speak()", role="service")
dog    = s.rect(80, 300, 180, 90,  text="Dog\n--\n+ speak()", role="service")
cat    = s.rect(320, 300, 180, 90, text="Cat\n--\n+ speak()", role="service")
s.arrow(dog, animal, end_arrowhead="triangle")   # Dog extends Animal
s.arrow(cat, animal, end_arrowhead="triangle")
s.dump("classes.excalidraw")
```

## Sequence Diagram

No lifeline shape — build each participant as a **header `rect` at the top** plus a **dashed vertical `line()`** dropping from its centre. Messages are horizontal arrows between the lifelines, placed at increasing `y` so **time flows top→bottom**.

| Element | Builder call | Notes |
|---|---|---|
| Participant header | `s.rect(x, 40, 140, 50, text="API", role="service")` | One per actor, evenly spaced across the top |
| Lifeline | `s.line([(cx, 90), (cx, bottom)], stroke_style="dashed", stroke=...)` | `cx` = header centre x; dashed, light grey/role stroke |
| Sync (call) message | `s.arrow((x1,y),(x2,y), label="getUser()")` | Solid, filled `"arrow"` head. Use **raw point pairs** at the chosen `y` (not bound to the header) |
| Async message | `s.arrow((x1,y),(x2,y), end_arrowhead="triangle", stroke_style="dashed")` | Dashed, open-ish head |
| Return / reply | `s.arrow((x2,y),(x1,y), stroke_style="dashed", stroke="#868e96")` | Grey dashed, pointing back |
| Activation bar | a thin `s.rect(cx-6, y0, 12, y1-y0, role=...)` over the lifeline | Optional; narrow box on the lifeline span |

- Messages use **raw `(x, y)` endpoints**, not element ids — you want them at a specific vertical position on the lifeline, not auto-attached to the header box.
- **Layout:** lifelines spaced ~200px apart horizontally; step each message down ~50-70px. The diagram reads left-to-right for participants, top-to-bottom for time.

```python
s = Scene()
cx_user, cx_api, cx_db = 100, 360, 620
u  = s.rect(40,  40, 120, 50, text="User",    role="external")
a  = s.rect(300, 40, 120, 50, text="API",     role="gateway")
d  = s.rect(560, 40, 120, 50, text="Database", role="database")
for cx in (cx_user, cx_api, cx_db):
    s.line([(cx, 90), (cx, 480)], stroke_style="dashed", stroke="#868e96")
s.arrow((cx_user,140),(cx_api,140), label="login()")
s.arrow((cx_api,210),(cx_db,210),  label="SELECT")
s.arrow((cx_db,280),(cx_api,280), stroke_style="dashed", stroke="#868e96")   # return
s.arrow((cx_api,350),(cx_user,350), stroke_style="dashed", stroke="#868e96")
s.dump("sequence.excalidraw")
```

## Architecture / System Diagram

The skill's home turf — roles map directly onto tiers. Group tiers with a transparent dashed `frame()` (or a big dashed `rect`) labelled by tier.

| Element | Builder call | Notes |
|---|---|---|
| Client / service | `s.rect(..., role="service")` | Blue. The default building block |
| API / gateway / LB | `s.rect(..., role="gateway")` | Orange |
| Database / store | `s.ellipse(..., role="database")` | Green (ellipse stands in for the cylinder) |
| Queue / bus | `s.rect(..., role="queue")` | Yellow — place centrally for a hub/fan-out pattern |
| Cache / auth / security | `s.rect(..., role="security")` | Purple |
| External system | `s.rect(..., role="external", stroke_style="dashed")` | Grey, dashed border = outside the boundary |
| Error / dead-letter path | `s.rect(..., role="error")` | Red |
| Tier / layer grouping | `s.frame(x, y, w, h, "API tier")` | Draw the frame first so nodes sit on top |
| AI/LLM or data-store logo | `s.image(x, y, w, h, dataURL)` | Resolve with `python3 <this-skill-dir>/scripts/aiicons.py "openai" --json` |

- Edges: plain `s.arrow(a, b, label="HTTPS")` for synchronous calls; `stroke_style="dashed"` for async / events / pub-sub.
- **Layout:** `LR` for ≤3 tiers (request flows left→right), `TB` for ≥4 tiers; keep hub nodes (queue/bus) centred. For >~15 nodes or a real code import graph, **don't hand-place** — use `autolayout.py` (it draws the dashed group containers and routes edges around boxes) via the `pyimports.py` / `jsimports.py` / `goimports.py` / `rustimports.py` importers.

```python
s = Scene()
web = s.rect(80, 120, 160, 60, text="Web App",  role="service")
gw  = s.rect(320, 120, 160, 60, text="Gateway",  role="gateway")
q   = s.rect(320, 260, 160, 60, text="Queue",    role="queue")
svc = s.rect(560, 120, 160, 60, text="Orders",   role="service")
db  = s.ellipse(560, 260, 160, 70, text="Orders DB", role="database")
s.arrow(web, gw, label="HTTPS")
s.arrow(gw, svc, label="REST")
s.arrow(svc, q, stroke_style="dashed", label="event")   # async
s.arrow(svc, db, label="SQL")
s.dump("architecture.excalidraw")
```

## ML / Deep Learning Model Diagram

Each layer is a `rect`; colour it by layer **type** with the explicit palette colours (these are the same hexes the role slots use, but here you map them to layer kinds rather than service roles). Annotate each block with its tensor shape on a **second label line** (`\n`-separated), e.g. `"Conv2D\n(B, 64, 32, 32)"`.

| Layer type | Builder call | Colour |
|---|---|---|
| Input / Output | `s.rect(..., role="database")` | green |
| Conv / Pooling | `s.rect(..., role="service")` | blue |
| Attention / Transformer | `s.rect(..., role="security")` | purple |
| RNN / LSTM / GRU | `s.rect(..., role="queue")` | yellow |
| FC / Linear / Dense | `s.rect(..., role="gateway")` | orange |
| Loss / Activation | `s.rect(..., role="error")` | red |
| Skip / residual connection | `s.arrow(a, b, stroke_style="dashed")` | dashed, routes alongside the main path |
| Forward edge | `s.arrow(a, b)` | plain solid arrow |

- **Tensor-shape convention:** put dimensions in `(B, C, H, W)` or `(B, T, D)` form on the second line of each block's label — `text="Conv2D\n(B, 64, 32, 32)"`.
- **Layout:** `TB`, data flows top→bottom, layers ~150px apart. Group an encoder / decoder (or a repeated block ×N) inside a `frame()` and label it.

```python
s = Scene()
x    = s.rect(200, 60,  200, 60, text="Input\n(B, 3, 224, 224)",  role="database")
conv = s.rect(200, 200, 200, 60, text="Conv2D\n(B, 64, 112, 112)", role="service")
attn = s.rect(200, 340, 200, 60, text="Self-Attention\n(B, 196, 768)", role="security")
fc   = s.rect(200, 480, 200, 60, text="Linear\n(B, 1000)",          role="gateway")
loss = s.rect(200, 620, 200, 60, text="CrossEntropy",               role="error")
s.arrow(x, conv); s.arrow(conv, attn); s.arrow(attn, fc); s.arrow(fc, loss)
s.arrow(conv, fc, stroke_style="dashed")          # residual / skip
s.dump("model.excalidraw")
```

## Flowchart

| Element | Builder call | Notes |
|---|---|---|
| Start / End | `s.ellipse(x, y, w, h, text="Start", role="database")` | Green oval (terminator) |
| Process step | `s.rect(x, y, w, h, text="Validate", role="service")` | Blue rounded rectangle |
| Decision | `s.diamond(x, y, w, h, text="Authed?")` | Diamond, already yellow by default |
| I/O | `s.rect(..., role="gateway")` | Orange (no parallelogram shape — note "I/O" in the label if needed) |
| Subprocess | `s.rect(..., role="security")` | Purple |
| Error / fail path | `s.rect(..., role="error")` | Red |
| Branch labels | `s.arrow(dec, a, label="yes")` / `label="no"` | **Always label both decision branches** |

- **Layout:** `TB`, ~200px vertical gap. Decisions branch sideways (one target `LR`-offset) and merge back toward the centre column. Decision boxes are a touch wider/taller than process boxes (e.g. 180×90) so the label fits the diamond.

```python
s = Scene()
start = s.ellipse(160, 40,  140, 60, text="Start", role="database")
auth  = s.diamond(130, 160, 200, 100, text="Authed?")
ok    = s.rect(360, 175,  160, 60, text="Load dashboard", role="service")
deny  = s.rect(120, 320,  160, 60, text="Show 401",       role="error")
end   = s.ellipse(390, 320, 140, 60, text="End", role="database")
s.arrow(start, auth)
s.arrow(auth, ok,   label="yes")
s.arrow(auth, deny, label="no")
s.arrow(ok, end)
s.dump("flowchart.excalidraw")
```

## Mind Map

A radial layout: one central topic with coloured branches fanning out. Place the **central node** in the middle of the canvas and arrange first-level branches around it (clockwise from the top), giving each branch its own colour so sub-topics inherit the branch's identity.

| Element | Builder call | Notes |
|---|---|---|
| Central topic | `s.ellipse(cx, cy, 200, 90, text="Topic", role="service")` | Big, centred; ellipse reads as the hub |
| Branch node | `s.rect(...)` with an explicit branch colour | One distinct palette role per branch — cycle `service` (blue), `success` (green), `accent` (orange), `secondary` (purple), `queue` (yellow), `error` (red) |
| Leaf / sub-topic | `s.rect(..., role=<same as its branch>)` | Inherit the parent branch's colour so clusters read as a family |
| Connector | `s.arrow(center, branch, end_arrowhead=None)` | Mind-map links are usually **lines, not arrows** — pass `end_arrowhead=None`. Bind to ids so they attach to borders |

- Branches radiate from the centre — compute positions on a circle (`x = cx + R*cos θ`, `y = cy + R*sin θ`), spacing the first level evenly (`θ = 2π·i/n`). Sub-topics sit further out along the same direction.
- **Layout:** radial / free (no single TB/LR direction). Use `end_arrowhead=None` so connectors look like the soft branches of a mind map rather than directed edges. Roughness 1-2 (artist/cartoonist) suits the brainstorm feel.

```python
import math, sys; sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene
s = Scene(roughness=2)                       # cartoonist = brainstormy
cx, cy, R = 500, 360, 240
hub = s.rect(cx-100, cy-45, 200, 90, text="Product Launch", role="service")
branches = [("Marketing", "accent"), ("Engineering", "service"),
            ("Design", "secondary"), ("Sales", "success")]
for i, (label, role) in enumerate(branches):
    th = 2*math.pi*i/len(branches) - math.pi/2     # start at the top
    bx, by = cx + R*math.cos(th) - 80, cy + R*math.sin(th) - 30
    node = s.rect(bx, by, 160, 60, text=label, role=role)
    s.arrow(hub, node, end_arrowhead=None)         # soft branch, no arrowhead
s.dump("mindmap.excalidraw")
```

---

After building any of these, lint before previewing:

```bash
python3 <this-skill-dir>/scripts/validate.py diagram.excalidraw
```

Builder output should pass clean (no dangling bindings, no <2-point arrows, no stacked filled shapes). Then export a PNG/SVG if a browser is available (`node <this-skill-dir>/scripts/render.mjs diagram.excalidraw -f png -o diagram`), or deliver the `.excalidraw` file directly — it always opens in excalidraw.com, the VS Code Excalidraw extension, and Obsidian.
