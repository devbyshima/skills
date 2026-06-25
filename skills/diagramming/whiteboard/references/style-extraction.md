# Style Extraction — agent reference

Loaded on demand by `SKILL.md` when the user asks to learn a style ("learn my style from `<path>` as `<name>`") or when the agent needs to render a sample after extraction.

A learned style ends up as a **preset JSON** matching `styles/schema.json`: a `palette` (the seven slots `primary` / `success` / `warning` / `accent` / `danger` / `neutral` / `secondary`, each a `{strokeColor, backgroundColor}` pair or `null`), a `roles` map (role → slot name), a `shapes` map (role/`decision`/`container` → `rectangle` | `ellipse` | `diamond`), a `font` (`family`: `hand`/`normal`/`code`, `size`, optional `titleSize`), `edges` (`strokeStyle`, `endArrowhead`, `startArrowhead`, `dashedFor`), and `extras` (`roughness` 0/1/2, `fillStyle` `solid`/`hachure`/`cross-hatch`, `strokeWidth` 1/2/4). `Scene.from_preset(preset_dict)` maps all of that onto the builder, so a learned preset drives generation exactly like a built-in.

There are two extraction paths:

| Source | Path | Method | Best confidence |
|---|---|---|---|
| `.excalidraw` (JSON) | parse the JSON, tally element props | deterministic, no LLM | `high` |
| `.png` / `.jpg` / `.svg` (image) | read it with vision | inference | `medium` |

## Sample diagram (for approval render)

After extracting a candidate preset, render a small representative diagram with the candidate's palette/shapes/fonts/edges so the user can eyeball it before saving. Build it with the **builder**, never hand-written JSON — `Scene.from_preset(candidate)` applies every field of the candidate so the sample reflects exactly what generation will produce.

The skeleton below exercises five roles (two services, a gateway, a database, an error sink), a `decision` diamond, and a labeled edge — plus one optional dashed edge that only appears if the candidate carries a `dashedFor` convention. Write the candidate dict to a temp path, point the script at it, run it, then render the result.

```python
import json, sys
sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene

candidate = json.load(open("/tmp/excalidraw-preset-<name>.json"))
s = Scene.from_preset(candidate)        # palette, roles, shapes, font, edges, extras all applied

s.text(120, 40, "Preset sample", font_size=candidate.get("font", {}).get("titleSize", 28))

# helper: honor the candidate's per-role shape choice (rectangle | ellipse | diamond)
shape_of = candidate.get("shapes", {})
def node(role, x, y, w, h, text):
    kind = shape_of.get(role, "rectangle")
    fn = {"rectangle": s.rect, "ellipse": s.ellipse, "diamond": s.diamond}[kind]
    return fn(x, y, w, h, text=text, role=role)

client = node("service",  120, 130, 160, 60, "Web Client")
gw     = node("gateway",  120, 280, 160, 60, "API Gateway")
dec    = s.diamond(110, 430, 180, 90, text="Authed?")     # decision: always a diamond
svc    = node("service",  360, 430, 160, 60, "User Service")
db     = node("database", 360, 580, 160, 70, "User DB")
err    = node("error",    110, 580, 160, 60, "401")

s.arrow(client, gw, label="HTTPS")
s.arrow(gw, dec)
s.arrow(dec, svc, label="yes")
s.arrow(dec, err, label="no")
s.arrow(svc, db, label="SQL")

# Optional dashed edge — only if the preset declares a dashed convention.
# from_preset already set edge defaults (strokeStyle/arrowheads); override
# stroke_style here so the sample shows the dashed look without faking one.
dashed_for = (candidate.get("edges") or {}).get("dashedFor") or []
if dashed_for:
    s.arrow(gw, svc, label=dashed_for[0], stroke_style="dashed")

s.dump("/tmp/excalidraw-preset-<name>.excalidraw")
print("wrote /tmp/excalidraw-preset-<name>.excalidraw")
```

Notes:
- `Scene.from_preset` reads `extras.roughness` → the sketchy-stroke level, `extras.fillStyle` → solid/hachure/cross-hatch, `extras.strokeWidth`, `font.family`/`font.size`, the palette, and `roles`. You do **not** re-pass those per shape — passing `role=` is enough; the role resolves through the candidate's `roles` map into the candidate's palette slot.
- The `decision` diamond carries no `roles[...]` slot of its own (it isn't a colored role); `s.diamond(...)` defaults to the warning palette, which is the intended "decision yellow" look.

### Rendering the sample

```bash
node <this-skill-dir>/scripts/render.mjs /tmp/excalidraw-preset-<name>.excalidraw \
     -f png -o ./preset-<name>-sample
```

That writes `./preset-<name>-sample.png` in the user's working directory (the `-o` base gets `.png` appended). Then:

1. Show the user a **preset summary table** (palette slots + their hex pairs, per-role shape, font family/size, roughness, fillStyle, strokeWidth, edge style).
2. Give the **PNG path** (`./preset-<name>-sample.png`).
3. Add a one-line **provenance + confidence** note (e.g. *"Learned from `diagram.excalidraw` (JSON parse) — confidence high."*).

### Approval loop

| User says | Action |
|---|---|
| "save" / "looks good" | write the candidate to `~/.whiteboard/styles/<name>.json`; delete the temp `.json`/`.excalidraw` and the sample PNG |
| "change `<field>` to `<value>`" | edit the in-memory candidate, re-run the builder script, re-render, re-ask |
| "cancel" | delete the temp files and the sample PNG; no save |

### If sample render fails (no Node / no browser / deps missing)

`render.mjs` exits non-zero with guidance when `npm install` hasn't run or no Chrome/Chromium/Edge is found. Don't block — still show the summary table and the provenance line, and note: *"Could not render sample PNG (render deps/browser unavailable). The preset is still valid; save anyway on your OK, or open the sample `.excalidraw` in a viewer."* The `.excalidraw` sample is always valid.

## `.excalidraw` (JSON) extraction path

Input: a `.excalidraw` file path. Output: candidate preset JSON. Deterministic — no LLM inference.

`.excalidraw` is JSON: a top-level object with an `elements` array. Each element has a `type` (`rectangle` / `ellipse` / `diamond` / `arrow` / `line` / `text` / `image` / `frame`), and shape elements carry `strokeColor`, `backgroundColor`, `fillStyle`, `strokeWidth`, `roughness`, plus bound text via `boundElements` / `containerId`. Parse with `json.load`; you never touch raw text.

### Steps

1. **Parse the file.** `data = json.load(open(path))`; `els = data["elements"]`. Drop anything with `isDeleted: true`. Split into **shape elements** (`type` in `rectangle` / `ellipse` / `diamond`), **arrows** (`type == "arrow"`), and **text** elements (`type == "text"`).

2. **Resolve labels.** A shape's label is the `text` of the text element whose `containerId` equals the shape's `id` (or, equivalently, the text listed in the shape's `boundElements` with `type: "text"`). Build a `shape_id → label` map for role inference.

3. **Extract palette.** For every shape element, take the `(strokeColor, backgroundColor)` pair. Skip pairs where `backgroundColor == "transparent"` and the stroke is the default `#1e1e1e` (uncolored). Count frequency; keep the top ≤7 distinct pairs.

4. **Extract shape vocabulary + role mapping.** A shape element's **shape class** is just its `type` (`rectangle` / `ellipse` / `diamond`) — Excalidraw has no cylinder/swimlane primitive. Infer the semantic role from shape class + label. **Evaluate in order; first match wins:**
   - `type == "diamond"` → `decision`
   - `type == "ellipse"` → `database` (the skill's convention; circles read as stores)
   - `strokeStyle == "dashed"` + **grey-family fill** (the hex's R, G, B channels all within ±16 of each other, i.e. near-achromatic) → `external`
   - label matches `/queue|bus|kafka|rabbit/i` → `queue`
   - label matches `/gateway|api|lb|load|ingress/i` → `gateway`
   - label matches `/auth|login|jwt|oauth|sso/i` → `security`
   - label matches `/error|fail|alert|dead.?letter/i` → `error`
   - everything else → `service`

   For each **role that has a canonical palette slot** — `service`, `database`, `queue`, `gateway`, `error`, `external`, `security` — the most frequent `(role, color-pair)` mapping wins. That pair goes into the role's slot:

   | Role | Slot |
   |---|---|
   | `service` | `primary` |
   | `database` | `success` |
   | `queue` | `warning` |
   | `gateway` | `accent` |
   | `error` | `danger` |
   | `external` | `neutral` |
   | `security` | `secondary` |

   Set `roles[role]` to that slot name.

   **`decision` and `container` do not get a `roles[...]` entry** — they are recorded only in `shapes.decision` / `shapes.container`. Color pairs seen on `decision` vertices still participate in the palette (they can fill leftover slots) but aren't tied to a colored role.

   Leftover color pairs (not claimed by any role-slot mapping) fill remaining empty palette slots in descending-frequency order.

   Record the shape class per role in `shapes[role]` (one of `rectangle` / `ellipse` / `diamond`). The six named `shapes` keys are `service`, `database`, `queue`, `decision`, `external`, `container`; the `gateway`, `error`, and `security` roles inherit `shapes.service` and get no own entry. Example: `shapes.database = "ellipse"`.

5. **Extract fonts.** Read `fontFamily` off the text elements (`1` hand-drawn / `2` normal / `3` code) and map back to the preset's `font.family` vocabulary: `1 → "hand"`, `2 → "normal"`, `3 → "code"`. Take the modal value across **bound labels** (ignore free-standing titles for the body font). Take the modal `fontSize` of bound labels as `font.size`. If a distinguishable subset of **free-standing** text elements (no `containerId`) uses a clearly larger `fontSize`, treat those as titles and set `font.titleSize` to their modal size; otherwise omit `titleSize`.

6. **Extract edge defaults.** Across `arrow` elements: take the modal `strokeStyle` (`solid` / `dashed` / `dotted`) as `edges.strokeStyle`. Take the modal `endArrowhead` (`arrow` / `triangle` / `dot` / `bar` / `diamond` / `null`) as `edges.endArrowhead`, and the modal `startArrowhead` (usually `null`) as `edges.startArrowhead`. If any arrows have `strokeStyle == "dashed"`, collect their bound-label `text`; if ≥2 share a common token (e.g. all "async" or "optional"), add that token to `edges.dashedFor`. Else `edges.dashedFor = []`.

7. **Extract extras.** Modal `roughness` across shape elements (`0` / `1` / `2`) → `extras.roughness`. Modal `fillStyle` (`solid` / `hachure` / `cross-hatch`) → `extras.fillStyle`. Modal `strokeWidth` (snap to the nearest of `1` / `2` / `4`) → `extras.strokeWidth`.

8. **Set provenance.**
   ```json
   {
     "source": { "type": "excalidraw", "path": "<input absolute path>", "extracted_at": "YYYY-MM-DD" },
     "confidence": "high"
   }
   ```

### JSON edge cases

| Situation | Behavior |
|---|---|
| Source has <3 distinct color pairs | Leave unfilled slots as `null`. Downgrade `confidence` to `"medium"`. Summary warns the user. |
| Source has >7 color pairs | Keep the top 7 by frequency. Summary warns that some colors were dropped. |
| Non-English labels | The English-keyword regexes in step 4 mostly miss; most shapes collapse to `service`. Palette / shapes / font / edges are still captured correctly (they don't depend on label text), so `confidence` stays `"high"`. Summary notes: *"Role labels not in English — `service` / `database` / `decision` inferred from shape class; other roles not mapped."* |
| Embedded `image` elements (logos via `aiicons.py`) | Images carry no palette/role info — ignore them for extraction. Note in the summary if the source leaned on logos: *"Embedded logos not part of the preset (color, shape, font, edges captured)."* |
| File has no shape elements at all (only text / arrows / images) | Stop. Refuse to save. Message: *"Nothing to learn from — source file has no shapes."* |

## Image extraction path

Input: path to a `.png` / `.jpg` (or any vision-readable image, including a rendered `.svg`). Output: candidate preset JSON. Inference-based; `confidence: "medium"` at best.

**Prerequisite:** the agent's vision capability must be available (the same mechanism the main workflow's self-check uses). If vision is not available, stop and tell the user:
*"Image-based learning needs a vision-enabled model (Claude Sonnet or Opus). Re-run on such a model, or provide the `.excalidraw` source file instead."*

### Steps

1. **Read the image.** Use the agent's vision input — the same path the main workflow's self-check uses to read exported PNGs.

2. **Extract palette by visual inspection.** Identify distinct fill-color regions on shape bodies. Excalidraw's own swatches are saturated-outline + light-fill pairs (e.g. blue `#1971c2` outline over `#a5d8ff` fill), so read both the body fill and its border.

   For each distinct fill:
   - `backgroundColor` — quantize each RGB channel to the nearest multiple of 16. Excalidraw's standard fills sit at high lightness (HSL L ≈ 0.80–0.95); if your read lands darker than L ≈ 0.75, raise L to ≈ 0.85 (keep hue and saturation; HSL→RGB round-trip). Emit `#RRGGBB`. If a shape is unfilled, emit `"transparent"`.
   - `strokeColor` — read the matching border. If unreadable, derive from the fill by darkening ~30% (same hue/saturation, drop L by ~0.30) toward Excalidraw's saturated outline.

   Map each `(strokeColor, backgroundColor)` pair to a named slot using this order:

   1. **Grey check first.** If the fill's R, G, B channels are all within ±16 of each other (same near-achromatic rule as the JSON path), **or** HSL saturation < 0.20 → `neutral`. Wins regardless of hue.
   2. **Hue band otherwise** (HSL hue angle of the fill):
      - 180°–260° → `primary` (blue)
      - 80°–170° → `success` (green)
      - 45°–65° → `warning` (yellow)
      - 20°–44° → `accent` (orange)
      - 0°–19° or 320°–360° → `danger` (red/pink)
      - 260°–320° → `secondary` (purple)
   3. **No band matched** (gaps at 65°–80° or 170°–180°) → spill to the nearest band by angular distance.

   **Collision rule.** If ≥2 distinct fills land in the same slot, sort by total pixel area covered (descending). The largest keeps the canonical slot; the rest spill to the **nearest empty slot** by hue-band angular distance (adjacent bands first, then farther). If every slot is filled, drop the extras and warn in the summary.

3. **Extract shape vocabulary.** Excalidraw has three drawable primitives — classify every visible shape into one of them:
   - rounded **rectangle** (Excalidraw rectangles are rounded by default) → `rectangle`
   - circle / oval → `ellipse`
   - diamond → `diamond`
   - a cylinder-looking store has no Excalidraw primitive → record it as `ellipse` (the skill's database convention)

   Role assignment uses the **same label-text + shape rules as the JSON path step 4** (diamond → `decision`, ellipse → `database`, dashed grey rectangle → `external`, then the label regexes, else `service`). Read visible labels via vision.

4. **Extract fonts.** Best-effort, mapped to the preset's three families:
   - clearly hand-drawn / wobbly handwriting (Excalifont/Virgil) → `family: "hand"`
   - clearly monospaced → `family: "code"`
   - otherwise a clean upright sans → `family: "normal"`

   Size by relative appearance: small → `size: 16`, medium → `size: 20`, large → `size: 28`. If titles are distinctly larger → set `titleSize` to that larger value.

5. **Extract edge defaults.**
   - Mostly solid connectors → `edges.strokeStyle = "solid"`; visibly dashed → `"dashed"`; dotted → `"dotted"`.
   - Standard arrowheads → `edges.endArrowhead = "arrow"`; open none → `null`; triangle/dot/bar/diamond heads map to those values.
   - `edges.startArrowhead` is normally `null` unless arrows are clearly double-headed.
   - Dashed arrows near labels like "optional", "async", "fallback", "secondary" → add those tokens to `edges.dashedFor`. Else `[]`.

6. **Extract extras.** This is the "roughness / fill feel" read:
   - **roughness** — crisp straight strokes → `0`; the usual slightly-wobbly hand-drawn look → `1`; very loose, doubled, cartoonish strokes → `2`. (`extras.roughness`.)
   - **fillStyle** — flat opaque fills → `"solid"`; sketchy diagonal hatching → `"hachure"`; crossed hatching → `"cross-hatch"`. (`extras.fillStyle`.)
   - **strokeWidth** — thin → `1`; normal bold → `2`; clearly heavy (>1.5× normal) → `4`. (`extras.strokeWidth`.)

7. **Set provenance and confidence.**
   ```json
   {
     "source": { "type": "image", "path": "<input absolute path>", "extracted_at": "YYYY-MM-DD" },
     "confidence": "medium"
   }
   ```
   Adjustments:
   - <3 distinct shapes identifiable → `confidence: "low"`.
   - Image path stays at `"medium"` by default. The only route to `"high"` is a strictly-verifiable signal: the image is recognizably an Excalidraw export (the hand-drawn rough.js stroke texture and Excalifont are unmistakable) **and** all seven palette slots are filled **and** all seven roles are labeled. This preserves the semantic gap between inference-based (image) and parse-based (JSON) provenance.

### Image edge cases

| Situation | Behavior |
|---|---|
| Vision unavailable | Stop as described above — do not fall back to guessing. |
| Image has <3 identifiable shapes | Continue; mark `confidence: "low"`; summary explicitly warns the preset is a loose approximation. |
| Image has no visible labels | Role assignment collapses to shape-class only: ellipses → `database`, diamonds → `decision`, dashed grey rectangles → `external`, everything else → `service`. Palette / font / edges still captured. Summary notes: *"No labels readable — semantic roles beyond shape-class not inferred."* |
| Two palette fills land in the same hue family | Keep the larger-area one in its canonical slot; spill the other to the adjacent empty slot (step 2 collision rule). |
| Image has more than 7 distinct fills | Keep the 7 most area-covering fills per the step 2 collision rule. Summary warns that some colors were dropped. |

## Confidence levels

| Level | When | What it signals |
|---|---|---|
| `high` | `.excalidraw` parse with ≥3 color pairs (or a verified-Excalidraw image with full palette + labels) | Every field came from real data; safe to set as default. |
| `medium` | image extraction (default), or a JSON parse with <3 color pairs | Palette / roughness inferred or partial; eyeball the sample before trusting it. |
| `low` | image with <3 identifiable shapes | Loose approximation; the sample render is essential before saving. |

`confidence` is written into the preset JSON (the schema allows `low` / `medium` / `high`) and surfaced in the provenance line shown to the user.
