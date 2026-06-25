# Troubleshooting — Common Mistakes

Read this when something looks wrong in the output (rendering, export, layout, arrows) or when a CLI invocation fails. Most rows have a one-line fix.

The deterministic linter catches the structural class of bugs before a human (or vision) ever sees the diagram — run it after every generation:

```bash
python3 <this-skill-dir>/scripts/validate.py name.excalidraw          # errors fail; warnings print
python3 <this-skill-dir>/scripts/validate.py name.excalidraw --strict  # warnings fail too
```

Builder output (`scripts/excalidraw.py`, `scripts/autolayout.py`) should always pass clean. A failure means a hand-edit or an external file is malformed.

| Mistake | Fix |
|---------|-----|
| `render.mjs` exits `error: render dependencies missing` | Run the one-time `npm install` in the skill dir: `cd <this-skill-dir> && npm install`. Until then, deliver the `.excalidraw` file — it's already written and valid. |
| `render.mjs` exits `error: no Chrome/Chromium/Edge found` | Point it at an installed browser: `CHROME_PATH=/path/to/chrome node <this-skill-dir>/scripts/render.mjs name.excalidraw -f png -o name`. The exit code is `4`. No browser at all → deliver the `.excalidraw` JSON to open in a viewer. |
| esbuild bundle fails / stale cache after an `@excalidraw/excalidraw` upgrade | The bundle is cached in `scripts/.cache/` keyed on the package version. If it wedges, delete the cache and re-render: `rm -rf <this-skill-dir>/scripts/.cache && node <this-skill-dir>/scripts/render.mjs name.excalidraw -f png -o name`. |
| Vision can't read / rejects the preview PNG | Re-export smaller (the PNG scales with `--scale`): `node <this-skill-dir>/scripts/render.mjs name.excalidraw -f png -o name --scale 1`. SVG is unaffected; the vision self-check is optional and can be skipped. |
| Arrows don't connect (a gap, or they float away when edited) | Bind by **element id**, not raw points: `s.arrow(src_id, dst_id, label=…)` — the ids are the return values of `s.rect(...)` / `s.ellipse(...)` / `s.diamond(...)`. `s.arrow` computes the border attach points and sets binding on **both** sides. |
| `validate.py` warns `arrow … binds … but it isn't in that shape's boundElements` | One-sided binding — the link won't move with the shape. Comes from hand-edited JSON or a raw-point arrow. Regenerate the arrow via `s.arrow(src_id, dst_id)` so the builder writes the back-reference into the shape's `boundElements`. |
| `validate.py` errors `startBinding -> missing` / `endBinding -> missing` / `boundElements -> missing` | An arrow (or label) points at an id that no longer exists — usually a deleted/renamed shape. Re-run the builder script so every binding references a live element. |
| `validate.py` errors `arrow … has <2 points (won't render)` | Every arrow/line needs ≥2 points. Use `s.arrow(a, b)` or `s.routed_arrow([(x,y),(x,y),…])`; never write a single-point arrow. |
| Lines crossing through unrelated shapes | Don't hand-place a crowded graph. Describe it as graph JSON and let Graphviz route edges around boxes: `python3 <this-skill-dir>/scripts/autolayout.py graph.json -o name.excalidraw`. Or move the shapes apart. |
| Labels clipped (text wider than its shape) | Widen the shape (`s.rect(x, y, w, h, …)` with a bigger `w`) or shorten the label. Bound text wraps to the container, so the box must be wide enough for the longest line. |
| Overlapping / stacked shapes (`validate.py` warns `filled shapes … overlap`) | Increase the gaps in the builder script. Scale with complexity: ≤5 nodes ~150px, 6-10 ~200px, >10 ~260px. Snap coordinates to multiples of 10. For layout-heavy diagrams, switch to `autolayout.py`. |
| File won't open in excalidraw.com / VS Code / Obsidian | Lint it first: `python3 <this-skill-dir>/scripts/validate.py name.excalidraw`. It must be valid JSON with top-level `type: "excalidraw"` (the linter's first check). If it parses but `type` is wrong, it wasn't produced by the builder — regenerate via `s.dump("name.excalidraw")`, never hand-write the JSON. |
| `autolayout.py` exits `error: Graphviz \`dot\` not found on PATH` | Install Graphviz: `brew install graphviz` (macOS) / `apt install graphviz` (Debian/Ubuntu). Without it, hand-place coordinates with the builder instead. |
| `autolayout.py` exits `error: dot failed: …` | Graphviz is installed but the graph JSON is malformed (bad edge `source`/`target`, missing `id`). Every edge `source`/`target` must match a node `id`; fix the JSON and re-run. |
| Embedded logo not showing | `aiicons.py` fetches the SVG over the network at generation time and inlines it as a data URL (network required *then*; the resulting file is self-contained after). If the icon is blank, re-run when online: `python3 <this-skill-dir>/scripts/aiicons.py "openai" --json`, and confirm the `dataURL` made it into the file's `files` map (`s.image(x, y, w, h, dataURL)` registers it). A `warning: could not fetch …` on stderr means the fetch failed. |
| `aiicons.py` exits `no logo for …` | No matching brand. List what's available with `python3 <this-skill-dir>/scripts/aiicons.py --list`, or for a data store just draw an ellipse/cylinder instead of an embedded logo. |
| Iteration loop never ends | After 5 review rounds, stop and suggest the user open `name.excalidraw` at https://excalidraw.com (or the VS Code Excalidraw extension / Obsidian) for fine-tuning. The `.excalidraw` source is always the deliverable. |

## When export simply can't run

Image export is **best-effort** — the `.excalidraw` JSON is the guaranteed output and opens in every Excalidraw viewer. If `render.mjs` exits non-zero for any reason (deps missing → code `3`, no browser → code `4`), don't block: lint the file, deliver it, and tell the user where it opens.

```bash
python3 <this-skill-dir>/scripts/validate.py name.excalidraw   # confirm it's structurally sound
open name.excalidraw          # macOS   (xdg-open on Linux, start on Windows)
```

Then offer https://excalidraw.com as the no-install path.
