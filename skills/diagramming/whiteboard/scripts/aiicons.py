#!/usr/bin/env python3
"""Find AI / LLM brand logos (OpenAI, Claude, Gemini, ...) as embeddable images.

Excalidraw ships no brand/vendor shape libraries, so an "LLM app architecture"
would otherwise be unlabeled boxes. This resolves a brand name to a logo SVG
from the lobe-icons set (https://github.com/lobehub/lobe-icons, MIT) and inlines
it as a data URI ready to drop into an Excalidraw `image` element.

Unlike the draw.io version, there is no "reference by URL" mode: Excalidraw
embeds image bytes in the file's `files` map (a data URL), so the SVG is always
fetched and inlined here (network required at generation time; the resulting
.excalidraw is then fully self-contained and offline-renderable).

  python3 aiicons.py "openai"
  python3 aiicons.py "claude" --json
  python3 aiicons.py "langchain" --variant mono --size 64

Feed the result to the builder:
  s.image(x, y, w, h, "<dataURL>", mime="image/svg+xml")   # scripts/excalidraw.py

The logos are trademarks of their respective owners and are referenced here for
identification only — the same basis on which draw.io ships AWS/Azure icons.

Usage: python3 aiicons.py <query> [--limit N] [--variant color|mono|text]
                                  [--size PX] [--json] [--list]
"""
import argparse
import base64
import json
import os
import re
import sys
import urllib.request

MANIFEST = os.path.join(os.path.dirname(__file__), "..", "data", "lobe-icons.json")
_VARIANT = re.compile(r"-(color|text)$")

# Common RAG/LLM data stores that lobe-icons lacks, mapped to simple-icons
# slugs (https://simpleicons.org, CC0), served from the simple-icons CDN.
_SIMPLEICONS_CDN = "https://cdn.simpleicons.org/"
_SUPPLEMENT = {
    "qdrant": "qdrant", "milvus": "milvus", "supabase": "supabase",
    "redis": "redis", "postgresql": "postgresql", "mongodb": "mongodb",
    "elasticsearch": "elasticsearch", "neo4j": "neo4j", "kafka": "apachekafka",
    "clickhouse": "clickhouse", "duckdb": "duckdb", "mysql": "mysql",
    "sqlite": "sqlite", "cassandra": "apachecassandra", "snowflake": "snowflake",
    "databricks": "databricks", "mariadb": "mariadb", "couchbase": "couchbase",
}


def families(icons):
    fam = {}
    for name in icons:
        base = _VARIANT.sub("", name)
        fam.setdefault(base, set()).add(name)
    return fam


def squish(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def search(fam, query, limit):
    q = squish(query)
    tokens = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if t]
    scored = {}
    for base in fam:
        b = squish(base)
        s = 0
        if q and q == b:
            s = 100
        elif q and b.startswith(q):
            s = 60
        elif q and q in b:
            s = 40
        for t in tokens:
            if t == b:
                s = max(s, 90)
            elif len(t) >= 3 and b.startswith(t):
                s = max(s, 50)
            elif len(t) >= 3 and t in b:
                s = max(s, 30)
        if s:
            scored[base] = s
    return sorted(scored, key=lambda base: (-scored[base], base))[:limit]


def search_supplement(query):
    q = squish(query)
    if not q:
        return None
    if q in _SUPPLEMENT:
        return q
    for brand in _SUPPLEMENT:
        if q in brand or brand in q:
            return brand
    return None


def pick_variant(base, variants, prefer):
    order = {"color": ["-color", "", "-text"],
             "mono":  ["", "-color", "-text"],
             "text":  ["-text", "-color", ""]}[prefer]
    for suffix in order:
        cand = base + suffix
        if cand in variants:
            return cand
    return next(iter(sorted(variants)), None)


def fetch_data_url(url):
    """Fetch an SVG and return it as a base64 data URI, or None on failure."""
    # Some CDNs (e.g. cdn.simpleicons.org) 403 the default urllib User-Agent.
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (whiteboard)"})
    try:
        svg = urllib.request.urlopen(req, timeout=15).read()
    except Exception as exc:                              # noqa: BLE001
        sys.stderr.write(f"warning: could not fetch {url} ({exc})\n")
        return None
    # Normalise the 1em intrinsic size so the embedded SVG scales predictably.
    svg = svg.replace(b'width="1em"', b'width="24"').replace(b'height="1em"', b'height="24"')
    return "data:image/svg+xml;base64," + base64.b64encode(svg).decode()


def main():
    ap = argparse.ArgumentParser(description="Find AI/LLM brand logos as embeddable Excalidraw images (lobe-icons).")
    ap.add_argument("query", nargs="?", help='brand name, e.g. "openai" or "claude"')
    ap.add_argument("--limit", type=int, default=8)
    ap.add_argument("--variant", choices=["color", "mono", "text"], default="color")
    ap.add_argument("--size", type=int, default=48, help="element width/height in px (icons are square)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--list", action="store_true", help="list all brand names and exit")
    args = ap.parse_args()

    if not os.path.exists(MANIFEST):
        sys.exit(f"error: manifest not found at {MANIFEST}")
    manifest = json.load(open(MANIFEST, encoding="utf-8"))
    fam = families(manifest["icons"])
    cdn = manifest["cdn"]

    if args.list:
        for base in sorted(fam):
            print(base)
        return
    if not args.query:
        ap.error("a query is required (or use --list)")

    matches = search(fam, args.query, args.limit)
    results = []
    if matches:
        for base in matches:
            file = pick_variant(base, fam[base], args.variant)
            data_url = fetch_data_url(f"{cdn}{file}.svg")
            if data_url:
                results.append({"brand": base, "file": file, "w": args.size,
                                "h": args.size, "mime": "image/svg+xml", "dataURL": data_url})
    else:
        brand = search_supplement(args.query)
        if brand:
            slug = _SUPPLEMENT[brand]
            data_url = fetch_data_url(_SIMPLEICONS_CDN + slug)
            if data_url:
                results.append({"brand": brand, "file": f"simpleicons:{slug}",
                                "w": args.size, "h": args.size,
                                "mime": "image/svg+xml", "dataURL": data_url})

    if not results:
        sys.exit(f"no logo for {args.query!r} — for a data store, draw an ellipse/"
                 f"cylinder, or try aiicons.py '{args.query}' with a brand name")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        for r in results:
            head = r["dataURL"][:64] + "..."
            print(f"{r['brand']}  ({r['file']}, {r['w']}x{r['h']})\n"
                  f"  s.image(x, y, {r['w']}, {r['h']}, \"{head}\")  # full data URL with --json")


if __name__ == "__main__":
    main()
