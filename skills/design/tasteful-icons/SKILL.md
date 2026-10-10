---
name: tasteful-icons
version: 1.0.0
description: Use when the user wants app, launcher, shortcut or integration icons in a soft frosted-glass squircle style (a saturated superellipse tile holding a milky white glass glyph with a bright edge, colored light pooling at the bottom and solid marks set into the glass), or asks to make, recolor, extend, reproduce or export icons in that style as SVG/PNG. Generates the icons from one Python script: recolor ready-made glyphs (pin, calendar, playlist disc, radar, apple, starburst) from a single base color, or draw new glyphs from SVG paths.
license: PolyForm-Noncommercial-1.0.0
homepage: https://github.com/devbyshima/skills
compatibility: Core generation (SVG) needs only python3. PNG export needs `rsvg-convert` (librsvg; `brew install librsvg` or `apt install librsvg2-bin`); the preview sheet needs Pillow. Without them the skill still writes the SVGs.
platforms: [macos, linux]
metadata: {"author":"devbyshima","version":"1.0.0"}
---

# Tasteful icons

Generates SVG + PNG icons in one consistent soft-glass style from a single script. Look at
[assets/style-reference.png](assets/style-reference.png) first: it is the target look.

- Script: [scripts/tasteful_icons.py](scripts/tasteful_icons.py), relative to this skill's directory.
  Python 3, standard library only.
- Output: `OUT/svg/<name>.svg`, `OUT/png@1024|512|128/<name>.png`, `OUT/preview.png`.
- Put output in the project the icons belong to. If the user names no destination, ask.

## Quick start

```bash
python3 scripts/tasteful_icons.py list                       # presets + the built-in example set
python3 scripts/tasteful_icons.py build OUT                  # build the built-in set of 8
python3 scripts/tasteful_icons.py build OUT --only traffic,computer
python3 scripts/tasteful_icons.py build OUT --spec icons.json --sizes 1024,512
```

## Making new icons

Pick the cheapest route that works.

**1. Recolor a preset.** Presets: `pin`, `calendar`, `playlist` (disc with three arcs), `radar` (dark tile),
`apple`, `starburst`. One base color derives the whole palette.

**2. Custom glyph via JSON spec** (`preset` defaults to `glass`). Copy
[assets/example-spec.json](assets/example-spec.json); it builds a teal pin, a purple calendar, a mail
envelope and a chat bubble ([preview](assets/example-spec-preview.png)).

```json
{"icons": [
  {"name": "places", "preset": "pin", "color": "#12C9A6", "title": "Places"},
  {"name": "mail", "color": "#FF3B30", "title": "Mail",
   "glyph": "M160 150H352A56 56 0 0 1 408 206V318A56 56 0 0 1 352 374H160A56 56 0 0 1 104 318V206A56 56 0 0 1 160 150Z",
   "marks": [{"d": "M160 214L256 282L352 214", "stroke": 26}]}
]}
```

Entry fields:

| Field | Meaning |
|---|---|
| `name`, `title` | file name; SVG `<title>` |
| `color` | base tile color; the palette is derived from it |
| `palette` | optional overrides: `top`, `bottom`, `mark`, `pool`, `shadow` |
| `preset` | `glass` (default) or a preset name |
| `glyph` | SVG path `d` of the glass shape (512 canvas) |
| `marks` | solid shapes inside the glass: `{"d", "stroke": width}` for strokes (round caps) or `{"d", "fill": true}`; optional `color`, `halo` (px, default 20) |
| `parts` | extra glass pieces drawn behind the glyph: `[{"d", "glass": {...}}]` (calendar tabs, apple leaf) |
| `glass` | overrides for the glass layers (see Tuning) |
| `shadow` | `[opacity, blur, dy]`, default `[0.4, 14, 12]` |
| `transform` | SVG transform applied to the whole glyph |

**3. Python API**, when a glyph needs computed geometry:

```python
import sys; sys.path.insert(0, "<skill dir>/scripts")
from tasteful_icons import palette, glass_icon, pin_icon, rrect, circle, write_icons
pal = palette("#FF2D55")
icons = {
    "health": glass_icon("Health", pal, circle(256, 258, 160),
                         marks=[{"d": "M256 190V326M188 258H324", "stroke": 34}]),
    "places-pink": pin_icon("Places", pal),
}
write_icons(icons, "OUT", sizes=(1024, 512, 128))
```

## Drawing glyphs

- Canvas 512 x 512; the tile is full bleed. Glyph box roughly 250-310 px wide and 290-320 px tall,
  optically centered on (256, 258). Keep everything inside x 96-416, y 90-420.
- The glyph is one simple, chunky silhouette. Detail lives in the marks, not in the outline.
- Marks: strokes 20-34 px with round caps, or filled shapes. Nothing thinner than ~16 px, because the
  edge glow eats about 20 px of the glass interior.
- Compose paths from `rrect()`, `circle()` and straight/quadratic segments; several subpaths in one `d`
  are fine.
- A brand silhouette (like the apple) is drawn as the glass shape itself, with no marks.

## Look and tuning

[references/recipe.md](references/recipe.md) has the exact layer stack (tile, shadow, glass, marks) and the
`glass` override keys with their defaults. Read it before tuning the glass or reimplementing the style
outside this script.

## Verify before handing over

1. Build, then view `OUT/preview.png` (and a `png@1024` file for detail) and compare it with
   `assets/style-reference.png`: same tile shape, milky glass, bright edge, colored pool, haloed marks.
2. Check the glyph is optically centered and nothing touches the tile edge.
3. Show the user `preview.png` rather than describing it.

## Gotchas

- IDs inside each written SVG are prefixed with the icon name, so many icons can be inlined in one HTML page.
  Strings returned by the Python API are not prefixed yet; call `scope_ids(svg, name)` before inlining them.
- Design tools may drop or change SVG filters (blur, knockout shadow) on import. Hand designers the PNGs,
  or rebuild the layers natively from the recipe above.
- The apple, playlist, radar and starburst glyphs are redraws that evoke real brands. Before they ship in a
  public product, tell the user to check those brands' guidelines.
