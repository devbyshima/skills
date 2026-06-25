# Image export — `scripts/render.mjs`

Two deliverables, two tiers of reliability:

| Deliverable | Reliability | How |
|---|---|---|
| `.excalidraw` JSON | **Guaranteed** — pure-Python builder, no external deps | `s.dump("name.excalidraw")` |
| PNG / SVG | **Best-effort** — needs Node + a browser + a one-time `npm install` | `node <this-skill-dir>/scripts/render.mjs name.excalidraw` |

The `.excalidraw` file is always the real output. It opens in [excalidraw.com](https://excalidraw.com), the VS Code "Excalidraw" extension, and Obsidian's Excalidraw plugin. PNG/SVG is a convenience layer on top — if it can't run, deliver the JSON and move on (see the [fallback chain](#fallback-chain)).

## Why a headless browser

Excalidraw's hand-drawn look (rough.js strokes, the Excalifont handwriting, hachure fills) is produced by Excalidraw's own renderer in the DOM. There is no official Excalidraw CLI, and a from-scratch SVG writer can't reproduce the wobble. So `render.mjs` runs Excalidraw's real `exportToSvg` / `exportToBlob` in a real browser.

## Setup (one time)

```bash
cd <this-skill-dir> && npm install
```

That installs the three render dependencies (declared in `package.json`):

| Package | Role |
|---|---|
| `@excalidraw/excalidraw` | The genuine renderer + `exportToSvg` / `exportToBlob` |
| `esbuild` | Bundles the export functions into one offline browser file |
| `puppeteer-core` | Drives a browser you already have (no Chromium download) |

`puppeteer-core` (not `puppeteer`) means **no browser is downloaded** — you supply your own. For autolayout you may also want Graphviz (`brew install graphviz` / `apt install graphviz`), but that's unrelated to image export.

## How it works

1. **Bundle (cached).** On first run, `esbuild` bundles `exportToSvg` / `exportToBlob` from `@excalidraw/excalidraw` into a single browser IIFE at `scripts/.cache/excalibundle.js` (global `ExcalidrawLib`). Fonts (`.woff2`/`.woff`/`.ttf`) and images are inlined as `dataurl`s, so rendering is fully **offline — no remote code, no font fetches**.
2. **Launch.** `puppeteer-core` launches your local Chrome/Chromium/Edge headless and loads `scripts/.cache/harness.html`, which just `<script src>`s the bundle over `file://`.
3. **Render.** The page calls `exportToSvg` (serialized to a string) and/or `exportToBlob` (PNG, scaled), the result is written next to the input.

### The cache (`scripts/.cache/`)

| File | What it is |
|---|---|
| `excalibundle.js` | The bundled renderer (~14 MB; built once) |
| `entry.js` | The esbuild entry point (`export { exportToSvg, exportToBlob } …`) |
| `harness.html` | Minimal page that loads the bundle |
| `version.txt` | The `@excalidraw/excalidraw` version the bundle was built from |

The bundle is **rebuilt automatically** when `version.txt` doesn't match the installed `@excalidraw/excalidraw` version (i.e. after you bump or reinstall the dependency), or when `excalibundle.js`/`version.txt` is missing. Otherwise the cached bundle is reused, so every run after the first is fast. The cache is safe to delete — it regenerates on the next render.

## Browser discovery

`render.mjs` searches these locations in order and uses the first that exists:

1. `$CHROME_PATH` (if set) — wins over everything
2. macOS: Google Chrome, Chromium, Microsoft Edge under `/Applications`
3. Linux: `/usr/bin/{google-chrome,chromium,chromium-browser,microsoft-edge}`
4. Windows: Chrome / Edge under `Program Files`

If none is found it exits non-zero with guidance. Point it at any Chromium-family browser explicitly:

```bash
CHROME_PATH="/Applications/Brave Browser.app/Contents/MacOS/Brave Browser" \
  node <this-skill-dir>/scripts/render.mjs name.excalidraw
```

## Flags

```bash
node <this-skill-dir>/scripts/render.mjs input.excalidraw \
  [-o out] [-f svg|png|both] [--scale 2] [--theme light|dark] [--no-background]
```

| Flag | Default | Effect |
|---|---|---|
| `-o`, `--output` | input minus `.excalidraw` | Output basename. `-o name` writes `name.png` / `name.svg` |
| `-f`, `--format` | `png` | `svg`, `png`, or `both` |
| `--scale`, `-s` | `2` | PNG pixel scale (2 = retina). SVG ignores it (vector) |
| `--theme` | `light` | `light` or `dark` (`dark` sets `exportWithDarkMode`) |
| `--no-background` | off | Transparent background (omits the page fill) |

On success it prints `wrote <paths>`. Examples:

```bash
# PNG preview for the self-check (step 3)
node <this-skill-dir>/scripts/render.mjs login-flow.excalidraw -f png -o login-flow

# Final delivery: both formats, dark theme, transparent background
node <this-skill-dir>/scripts/render.mjs login-flow.excalidraw -f both --theme dark --no-background
```

## Fallback chain

Image export is best-effort **by design**. `render.mjs` exits with a distinct non-zero code and a clear message for each failure — never crashes the workflow:

| Situation | Exit | What `render.mjs` says / do |
|---|---|---|
| Deps not installed (`npm install` not run) | `3` | Prints the `npm install` command and the skill-dir path → deliver `.excalidraw` |
| No Chrome/Chromium/Edge found | `4` | Prints "set `CHROME_PATH=…`" → set it and retry, or deliver `.excalidraw` |
| Input missing / bad args | `1` | Usage line |
| Offline | — | Fine: the bundle's fonts/images are inlined, so a built cache renders with no network |

In every failure case the `.excalidraw` file is **already written and valid**. Deliver it and tell the user it opens in:

- **[excalidraw.com](https://excalidraw.com)** — drag the file in, or File → Open
- the **VS Code "Excalidraw"** extension — open the `.excalidraw` file in the editor
- **Obsidian's Excalidraw plugin** — drop it in the vault

Optionally open it locally: `open name.excalidraw` (macOS) · `xdg-open` (Linux) · `start` (Windows).

When a render fails unexpectedly (browser launches but the output looks wrong, vision rejects a PNG, etc.), see `references/troubleshooting.md`.
