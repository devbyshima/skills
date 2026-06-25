# Style Presets — Learn, Apply, Manage

A **style preset** is a named JSON file capturing a user's visual preferences — palette, role→slot mapping, shape vocabulary, font, edge style, and the hand-drawn extras (roughness / fill / stroke width). When a preset is active, it fully replaces the built-in palette/roughness/font conventions in SKILL.md. The file is validated against `<this-skill-dir>/styles/schema.json` and applied with `Scene.from_preset(...)`.

Read this file when:
- The user asks to "learn", "save", "remember", or "extract" a style from a `.excalidraw` file or an image.
- The user wants to manage presets (list, show, set default, delete, rename).
- You've resolved an active preset in Step 0 and need the application rules.
- You need to validate a preset file before loading it.

## Anatomy of a preset

Mirrors `styles/schema.json`. Required top-level keys: `name`, `version`, `palette`, `roles`, `shapes`, `font`, `edges`. Optional: `default`, `confidence`, `source`, `extras`.

| Key | Shape | Notes |
|---|---|---|
| `name` | string `^[a-z0-9][a-z0-9_-]*$` | Always lowercase. Matches the filename stem. |
| `version` | integer, must be `1` | Schema version. |
| `default` | boolean | Only **user** presets may set `true`. |
| `palette` | 7 slots, each `{strokeColor, backgroundColor}` or `null` | Slots: `primary, success, warning, accent, danger, neutral, secondary`. `strokeColor` is `#RRGGBB`; `backgroundColor` is `#RRGGBB` or `"transparent"`. |
| `roles` | `{role: slotName}` | Maps the seven semantic roles to palette slots. Roles: `service, database, queue, gateway, error, external, security`. |
| `shapes` | `{role: "rectangle"\|"ellipse"\|"diamond"}` | Vertex geometry per concept. Keys: `service, database, queue, decision, external, container`. |
| `font` | `{family: "hand"\|"normal"\|"code", size, titleSize?}` | `hand`=Excalifont(1), `normal`=Nunito(2), `code`=Comic Shanns Mono(3). |
| `edges` | `{strokeStyle, startArrowhead, endArrowhead, dashedFor?}` | `strokeStyle` ∈ `solid\|dashed\|dotted`; arrowheads ∈ `null\|arrow\|triangle\|dot\|bar\|diamond`; `dashedFor` is a list of trigger words. |
| `extras` | `{roughness: 0\|1\|2, fillStyle: solid\|hachure\|cross-hatch, strokeWidth: 1\|2\|4}` | The sketchiness controls. |
| `source` | `{type, path?, extracted_at?}` | `type` ∈ `excalidraw\|image\|built-in\|hand-authored`. |
| `confidence` | `low\|medium\|high` | Set by the Learn flow. |

The built-in `default` preset is the canonical example — open `<this-skill-dir>/styles/built-in/default.json`.

## Locations and lookup order

1. `~/.whiteboard/styles/<name>.json` — user presets (survive updates / `git pull`).
2. `<this-skill-dir>/styles/built-in/<name>.json` — built-ins shipped with the skill: **`default`** (artist roughness 1, solid fills, handwriting), **`sketch`** (cartoonist roughness 2 + hachure fills, dashes `optional` edges), **`clean`** (architect roughness 0 + normal font, stroke width 1).

A user preset **shadows** a built-in of the same name. Resolve by name in that order; first hit wins.

Only user presets can carry `"default": true`. When the user says *"make `<built-in-name>` my default"*, first copy the built-in JSON to `~/.whiteboard/styles/<name>.json`, then set `default: true` on the copy — never mutate the shipped built-in.

**Name normalisation:** always lowercase the user-provided name before writing or looking up files. The schema's `name` pattern rejects uppercase, so an unnormalised name fails validation.

## Applying a preset

When SKILL.md's Step 0 resolves a preset, load its JSON and build the scene from it — one line:

```python
import json, os, sys
sys.path.insert(0, "<this-skill-dir>/scripts")
from excalidraw import Scene

preset = json.load(open(os.path.expanduser("~/.whiteboard/styles/<name>.json")))
s = Scene.from_preset(preset)
# now build as usual — roles auto-pick the preset's colors:
client = s.rect(120, 110, 160, 60, text="Web Client", role="service")
db     = s.ellipse(120, 300, 160, 70, text="User DB",  role="database")
s.arrow(client, db, label="SQL")
s.dump("diagram.excalidraw")
```

### What `Scene.from_preset(preset_dict, **overrides)` maps

`from_preset` translates the Excalidraw-vocabulary preset onto the `Scene` constructor. Keyword `**overrides` win over the preset (e.g. `Scene.from_preset(p, background="#1e1e1e")`).

| Preset field | Becomes on the Scene | Effect |
|---|---|---|
| `palette[slot] = {strokeColor, backgroundColor}` | `palette[slot] = {stroke, background}` | Each non-null slot is remapped (key rename). `null` slots are dropped from the palette. |
| `roles` | `roles=` (merged over the built-in `ROLE_SLOT`) | `role="service"` → slot → `(stroke, background)`. |
| `extras.roughness` (default `1`) | `roughness=` | `0` clean · `1` artist · `2` cartoonist. |
| `extras.fillStyle` (default `solid`) | `fill_style=` | `solid` · `hachure` · `cross-hatch`. |
| `extras.strokeWidth` (default `2`) | `stroke_width=` | line weight on every shape. |
| `font.family` (default `hand`) | `font_family=` | `hand`→1, `normal`→2, `code`→3. |
| `font.size` (default `20`) | `font_size=` | default label size. |
| `edges.{strokeStyle, startArrowhead, endArrowhead}` | `s.edge_defaults` | every `s.arrow(...)`/`s.routed_arrow(...)` inherits these unless you pass `stroke_style=`/`start_arrowhead=`/`end_arrowhead=` explicitly. |

**Role → color** is then automatic: passing `role=` to `s.rect/ellipse/diamond` resolves `roles[role]` → slot → the preset's `(stroke, background)`. If a role's slot is missing or `null`, the builder falls back to the raw default stroke (`#1e1e1e`) on a transparent fill — so populate every slot you intend to use, or pass explicit `stroke=`/`background=`.

### Things the builder does NOT auto-apply (the agent applies them)

- **`shapes`** — `from_preset` does not pick geometry for you. Honor `preset.shapes[role]` yourself when choosing the method: `"rectangle"`→`s.rect`, `"ellipse"`→`s.ellipse`, `"diamond"`→`s.diamond`. The six keys are `service, database, queue, decision, external, container`. Roles without a shape key (`gateway, error, security`) reuse `shapes.service` unless the preset names them.
- **Decision shapes** — `s.diamond(...)` defaults to the `warning` (yellow) slot; that already matches the canonical convention. Pass `role=` only to recolor.
- **`font.titleSize`** — apply to titles/headers by hand: `s.text(x, y, "Title", font_size=preset["font"].get("titleSize", 28))`.
- **`edges.dashedFor`** — a list of trigger words (e.g. `"optional"`, `"async"`, `"fallback"`). When an edge's meaning matches a token (the user's prompt used the word, or one end plays a role whose typical relation is optional), draw that arrow dashed: `s.arrow(a, b, stroke_style="dashed")`. Otherwise edges use `edge_defaults["stroke_style"]`.

### Interaction with diagram-type conventions

Diagram-type sections in `references/diagram-types.md` set **structural** choices (ERD attribute rows, UML compartments, sequence lifelines). Keep the structure; layer the preset's color / font / edge / extras on top. Where a diagram type would hardcode a color that conflicts with the preset, the **preset wins**. A genuinely transparent fill (`background="transparent"`) is structural — don't overwrite it with a palette color.

## Learn flow

**Triggers:** "learn my style from `<path>` as `<name>`", "save this as `<name>` style", "remember this style as `<name>`".

**Dispatch by file extension** of the source:
- `.excalidraw` (and `.excalidraw.json`) → **scene path** (parse the JSON, read element colors/fonts/roughness directly).
- `.png`, `.jpg`, `.jpeg`, `.svg` → **image path** (vision extraction).

**Steps:**

1. **Load the extraction reference.** Read `references/style-extraction.md` into context — it holds both the scene-parse and image-vision procedures plus the sample-diagram skeleton.
2. **Extract** following the scene path or image path procedure there.
3. **Normalize and build candidate.** Lowercase the user-provided name; use that for ALL paths in this flow. Build the candidate preset JSON and write it to `/tmp/excalidraw-preset-<name>.json`. Do **not** save to `~/.whiteboard/styles/<name>.json` yet. Set `source` (`type`, `path`, `extracted_at` as `YYYY-MM-DD`) and `confidence`.
4. **Validate** the candidate against `styles/schema.json` (see below). If it fails, fix the offending field before rendering.
5. **Render a sample.** Build the sample-diagram skeleton from `style-extraction.md` with `Scene.from_preset(candidate)`, dump it, and export a preview:
   ```bash
   python3 /tmp/build-preset-sample.py                                   # writes /tmp/excalidraw-preset-<name>.excalidraw
   node <this-skill-dir>/scripts/render.mjs /tmp/excalidraw-preset-<name>.excalidraw -f png -o /tmp/excalidraw-preset-<name>
   ```
   If render deps/browser are missing, skip the PNG and show the `.excalidraw` path instead — never block on it.
6. **Show the user:**
   - Preset summary table (palette hex per slot, shape per role, font family+size, edge style, extras).
   - The sample PNG path (embed the image if the environment supports it), or the `.excalidraw` path.
   - Provenance line: `source.type`, `source.path`, `extracted_at`, `confidence`.
7. **Wait for approval:**
   - "save" / "looks good" → create `~/.whiteboard/styles/` if needed, write the candidate to `~/.whiteboard/styles/<name>.json`, delete the tempfile and sample artifacts.
   - "change `<field>` to `<value>`" → edit the in-memory candidate, re-validate, re-render, re-ask.
   - "cancel" / "no" → delete the tempfile and sample artifacts; save nothing.

**Error behavior:**

| Failure | Behavior |
|---|---|
| Source path does not exist | Stop; report path not found. |
| `.excalidraw` JSON won't parse | Stop; report the parse error; suggest re-exporting from excalidraw.com. |
| Image vision unavailable | Stop; tell the user to re-run on a vision-capable model or provide the `.excalidraw` file. |
| Extraction yields 0 elements / shapes | Stop; refuse to save. |
| Fewer than 3 distinct color pairs | Continue; mark `confidence: "low"` (image) or `"medium"` (scene); warn in the summary. |
| Name collides with an existing user preset | Ask: overwrite, or pick a new name. |
| Name collides with a built-in | Save to the user dir (shadows the built-in); warn once. |
| Sample render fails | Still show the summary; note "could not render sample — saving on your OK anyway". Do not block. |

## Management operations

All natural language — no slash commands. *Lowercase every `<name>`, `<a>`, `<b>` before any file op.*

| User says | Agent does |
|---|---|
| "list my styles", "what styles do I have" | Read `~/.whiteboard/styles/` and `<this-skill-dir>/styles/built-in/`. Print a table: `name`, `location` (user / built-in), `source.type`, `confidence`, `default` flag. Mark built-ins shadowed by a user preset of the same name. |
| "show my `<name>` style", "what's in `<name>`" | Resolve by lookup order; pretty-print the JSON + a one-line summary (source, confidence, is-default). |
| "make `<name>` the default" | If `<name>` is a user preset: set `default: true` on it, clear `default` on any other user preset that had it, save both. If `<name>` is a built-in: copy `built-in/<name>.json` → `~/.whiteboard/styles/<name>.json` first, then set `default: true` on the copy. Never mutate the shipped built-in. |
| "remove default", "unset default" | Clear `default: true` from whichever user preset has it. |
| "delete `<name>`", "remove `<name>`" | Confirm first, then `rm ~/.whiteboard/styles/<name>.json`. Refuse to delete anything under `built-in/` — offer to shadow it with a user preset of the same name instead. |
| "rename `<a>` to `<b>`" | `mv ~/.whiteboard/styles/<a>.json ~/.whiteboard/styles/<b>.json`, then update the `name` field inside. Fails if `<a>` is a built-in (offer copy-then-rename). |
| "learn my style from `<path>` as `<name>`" | Dispatch to the Learn flow above. |

## Preset file validation

Validate against `<this-skill-dir>/styles/schema.json` whenever you load a preset (for generation or management). A lightweight structural check:

- Required top-level keys present: `name, version, palette, roles, shapes, font, edges`.
- `version === 1`; `name` matches `^[a-z0-9][a-z0-9_-]*$`.
- Each **populated** palette slot has both `strokeColor` (`#RRGGBB`) and `backgroundColor` (`#RRGGBB` or `"transparent"`). `null` slots are allowed.
- `roles` values are valid slot names; `shapes` values ∈ `rectangle|ellipse|diamond`.
- `font.family` ∈ `hand|normal|code`; `edges.strokeStyle` ∈ `solid|dashed|dotted`; arrowheads ∈ `null|arrow|triangle|dot|bar|diamond`.
- `extras` (if present): `roughness` ∈ `0|1|2`, `fillStyle` ∈ `solid|hachure|cross-hatch`, `strokeWidth` ∈ `1|2|4`.
- `confidence` ∈ `low|medium|high` if present.

A quick check with stdlib + the schema:

```bash
python3 - "$HOME/.whiteboard/styles/<name>.json" <<'PY'
import json, sys
preset = json.load(open(sys.argv[1]))
schema = json.load(open("<this-skill-dir>/styles/schema.json"))
req = schema["required"]
missing = [k for k in req if k not in preset]
assert not missing, f"missing required keys: {missing}"
assert preset["version"] == 1, "version must be 1"
for slot, c in (preset["palette"] or {}).items():
    if c is not None:
        assert c.get("strokeColor") and c.get("backgroundColor"), f"slot {slot} needs both colors"
print("ok")
PY
```

On validation failure:
- **During generation:** warn the user, fall back to the built-in conventions for this one diagram (`Scene()` with no preset), and do not mutate the file.
- **During learn:** refuse to save the candidate; report exactly which field failed.

For the extraction procedure (scene-parse and image-vision) and the sample-diagram skeleton, read `references/style-extraction.md`.
