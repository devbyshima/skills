#!/usr/bin/env node
/**
 * Render a .excalidraw file to SVG and/or PNG using Excalidraw's own renderer
 * in a headless browser — the only way to get the genuine hand-drawn look
 * (rough.js strokes, Excalifont) that a from-scratch SVG writer can't reproduce.
 *
 * Excalidraw has no official CLI, so this:
 *   1. Bundles @excalidraw/excalidraw's export functions to a browser IIFE with
 *      esbuild (once, cached in scripts/.cache/ — fonts inlined as data URIs so
 *      rendering works offline, no remote code).
 *   2. Drives a local Chrome/Chromium/Edge via puppeteer-core (no bundled
 *      browser download) over a file:// harness.
 *   3. Calls exportToSvg / exportToBlob and writes the result.
 *
 * Dependencies (install once in the skill dir): `npm install`.
 * Browser: any installed Chrome/Chromium/Edge; override with CHROME_PATH=...
 * If anything is missing it exits non-zero with guidance — the skill then falls
 * back to delivering the .excalidraw JSON (always valid) and opening it in a
 * viewer. Image export is best-effort by design.
 *
 * Usage:
 *   node render.mjs input.excalidraw [-o out] [-f svg|png|both] [--scale 2]
 *                   [--theme light|dark] [--no-background]
 */
import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const require = createRequire(import.meta.url);

function die(msg, code = 1) { console.error(msg); process.exit(code); }

// --- args --------------------------------------------------------------------
const argv = process.argv.slice(2);
function opt(names, def) {
  for (const n of names) {
    const i = argv.indexOf(n);
    if (i >= 0) return argv[i + 1];
  }
  return def;
}
const input = argv.find(a => !a.startsWith("-") &&
  (argv.indexOf(a) === 0 || !["-o", "-f", "--scale", "--theme"].includes(argv[argv.indexOf(a) - 1])));
if (!input) die("usage: node render.mjs input.excalidraw [-o out] [-f svg|png|both] [--scale 2] [--theme light|dark] [--no-background]");
if (!fs.existsSync(input)) die(`error: input not found: ${input}`);
const fmt = opt(["-f", "--format"], "png");
const scale = parseFloat(opt(["--scale", "-s"], "2"));
const theme = opt(["--theme"], "light");
const withBg = !argv.includes("--no-background");
const outBase = opt(["-o", "--output"], input.replace(/\.excalidraw$/, ""));

// --- resolve deps -------------------------------------------------------------
let esbuild, puppeteer;
try { esbuild = require("esbuild"); puppeteer = require("puppeteer-core"); require.resolve("@excalidraw/excalidraw"); }
catch (e) {
  die(`error: render dependencies missing (${e.message.split("\n")[0]}).\n` +
      `Run \`npm install\` in ${path.resolve(__dirname, "..")} first, then retry.\n` +
      `(The .excalidraw file itself is already written and valid — open it at ` +
      `https://excalidraw.com, in the VS Code "Excalidraw" extension, or Obsidian.)`, 3);
}

// --- find a browser -----------------------------------------------------------
const CANDIDATES = [
  process.env.CHROME_PATH,
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  "/Applications/Chromium.app/Contents/MacOS/Chromium",
  "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
  "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
  "/usr/bin/microsoft-edge",
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
].filter(Boolean);
const chrome = CANDIDATES.find(p => { try { return fs.existsSync(p); } catch { return false; } });
if (!chrome) die("error: no Chrome/Chromium/Edge found. Set CHROME_PATH=/path/to/chrome and retry.\n" +
                 "(The .excalidraw JSON is already written — open it in any Excalidraw viewer.)", 4);

// --- ensure the browser bundle (cached) --------------------------------------
const cacheDir = path.join(__dirname, ".cache");
fs.mkdirSync(cacheDir, { recursive: true });
const bundlePath = path.join(cacheDir, "excalibundle.js");
// The package's `exports` map blocks `require(".../package.json")`, so walk up
// from the resolved entry to read its version (for cache invalidation).
function pkgVersion(entry) {
  let dir = path.dirname(require.resolve(entry));
  for (let i = 0; i < 8 && dir !== path.dirname(dir); i++, dir = path.dirname(dir)) {
    const pj = path.join(dir, "package.json");
    if (fs.existsSync(pj)) { try { return JSON.parse(fs.readFileSync(pj, "utf8")).version; } catch {} }
  }
  return "unknown";
}
const exVersion = pkgVersion("@excalidraw/excalidraw");
const stamp = path.join(cacheDir, "version.txt");
const stale = !fs.existsSync(bundlePath) ||
  !fs.existsSync(stamp) || fs.readFileSync(stamp, "utf8") !== exVersion;
if (stale) {
  const entry = path.join(cacheDir, "entry.js");
  fs.writeFileSync(entry, `export { exportToSvg, exportToBlob } from "@excalidraw/excalidraw";\n`);
  await esbuild.build({
    entryPoints: [entry], bundle: true, format: "iife", globalName: "ExcalidrawLib",
    outfile: bundlePath, logLevel: "error", target: "es2020",
    define: { "process.env.NODE_ENV": '"production"' },
    loader: { ".json": "json", ".woff2": "dataurl", ".woff": "dataurl",
              ".ttf": "dataurl", ".css": "text", ".png": "dataurl", ".svg": "dataurl" },
  });
  fs.writeFileSync(stamp, exVersion);
}
const harness = path.join(cacheDir, "harness.html");
fs.writeFileSync(harness,
  `<!DOCTYPE html><html><head><meta charset="utf8"></head><body><script src="excalibundle.js"></script></body></html>`);

// --- render -------------------------------------------------------------------
const scene = JSON.parse(fs.readFileSync(input, "utf8"));
const browser = await puppeteer.launch({ executablePath: chrome, headless: "new" });
try {
  const page = await browser.newPage();
  page.on("pageerror", e => console.error("render warning:", String(e).slice(0, 160)));
  await page.goto("file://" + harness, { waitUntil: "load", timeout: 60000 });
  await page.waitForFunction("window.ExcalidrawLib && window.ExcalidrawLib.exportToSvg", { timeout: 60000 });

  const wantSvg = fmt === "svg" || fmt === "both";
  const wantPng = fmt === "png" || fmt === "both";
  const out = await page.evaluate(async (scene, opts) => {
    const { exportToSvg, exportToBlob } = window.ExcalidrawLib;
    const base = {
      elements: scene.elements,
      appState: { ...scene.appState, exportBackground: opts.withBg, exportWithDarkMode: opts.theme === "dark" },
      files: scene.files || {},
    };
    const res = {};
    if (opts.wantSvg) res.svg = new XMLSerializer().serializeToString(await exportToSvg(base));
    if (opts.wantPng) {
      const blob = await exportToBlob({ ...base, mimeType: "image/png",
        getDimensions: (w, h) => ({ width: w * opts.scale, height: h * opts.scale, scale: opts.scale }) });
      res.png = await new Promise(r => { const fr = new FileReader(); fr.onload = () => r(fr.result); fr.readAsDataURL(blob); });
    }
    return res;
  }, scene, { wantSvg, wantPng, scale, theme, withBg });

  const written = [];
  if (out.svg) { const p = outBase + ".svg"; fs.writeFileSync(p, out.svg); written.push(p); }
  if (out.png) { const p = outBase + ".png"; fs.writeFileSync(p, Buffer.from(out.png.split(",")[1], "base64")); written.push(p); }
  console.log("wrote " + written.join(", "));
} finally {
  await browser.close();
}
