#!/usr/bin/env python3
"""Tasteful icons: soft glass squircles, a colored superellipse tile holding a frosted white glass glyph.

Usage:
  tasteful_icons.py list
  tasteful_icons.py build OUT_DIR [--only a,b] [--sizes 1024,512,128] [--no-sheet]
  tasteful_icons.py build OUT_DIR --spec icons.json [--sizes ...] [--no-sheet]

Writes OUT_DIR/svg/<name>.svg, OUT_DIR/png@<size>/<name>.png and OUT_DIR/preview.png.
PNG export needs `rsvg-convert` (Homebrew: librsvg). The preview sheet needs Pillow.
Can also be imported: see SKILL.md for the Python API.
"""
import argparse
import colorsys
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass

S = 512  # canvas; every coordinate below is in this 512 x 512 space


# Color ------------------------------------------------------------------------

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    """Blend color a toward color b by t (0..1)."""
    A, B = _rgb(a), _rgb(b)
    return _hex([A[i] + (B[i] - A[i]) * t for i in range(3)])


def shade(c, dl):
    """Shift HLS lightness by dl (-1..1), keeping hue and saturation."""
    h, l, s = colorsys.rgb_to_hls(*[v / 255 for v in _rgb(c)])
    return _hex([v * 255 for v in colorsys.hls_to_rgb(h, max(0, min(1, l + dl)), s)])


@dataclass
class Palette:
    top: str     # tile gradient, top
    bottom: str  # tile gradient, bottom
    mark: str    # solid marks set into the glass (pin dot, calendar bar, arcs)
    pool: str    # colored light pooling in the lower half of the glass
    shadow: str  # glyph drop shadow on the tile


def palette(base, **overrides):
    """Derive a full palette from one saturated tile color."""
    p = Palette(top=shade(base, 0.025), bottom=shade(base, -0.03), mark=shade(base, -0.06),
                pool=mix(base, "#FFFFFF", 0.35), shadow=mix(base, "#000000", 0.4))
    for k, v in overrides.items():
        setattr(p, k, v)
    return p


# Geometry ---------------------------------------------------------------------

def squircle_path(n=2.5, size=S, steps=48):
    """Superellipse |x|^n + |y|^n = 1 (n = 2.5 matches the reference tile), as smooth cubics."""
    a = size / 2
    pts = []
    total = steps * 4
    for i in range(total):
        t = 2 * math.pi * i / total
        ct, st = math.cos(t), math.sin(t)
        pts.append((a + a * math.copysign(abs(ct) ** (2 / n), ct),
                    a + a * math.copysign(abs(st) ** (2 / n), st)))
    d = [f"M{pts[0][0]:.2f} {pts[0][1]:.2f}"]
    m = len(pts)
    for i in range(m):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % m], pts[(i + 2) % m]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{c1[0]:.2f} {c1[1]:.2f} {c2[0]:.2f} {c2[1]:.2f} {p2[0]:.2f} {p2[1]:.2f}")
    return "".join(d) + "Z"


SQUIRCLE = squircle_path()


def rrect(x, y, w, h, r):
    """Rounded rectangle path."""
    return (f"M{x + r} {y}H{x + w - r}A{r} {r} 0 0 1 {x + w} {y + r}V{y + h - r}"
            f"A{r} {r} 0 0 1 {x + w - r} {y + h}H{x + r}A{r} {r} 0 0 1 {x} {y + h - r}"
            f"V{y + r}A{r} {r} 0 0 1 {x + r} {y}Z")


def circle(cx, cy, r):
    """Circle path (two arcs, so it can sit inside a compound path)."""
    return f"M{cx - r} {cy}A{r} {r} 0 1 1 {cx + r} {cy}A{r} {r} 0 1 1 {cx - r} {cy}Z"


# Document ---------------------------------------------------------------------

def svg(title, pal, defs, body, shadow=(0.4, 14, 12)):
    """Wrap a glyph in the tile. shadow = (opacity, blur, dy) of the glyph drop shadow."""
    op, blur, dy = shadow
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{S}" height="{S}" viewBox="0 0 {S} {S}">
  <title>{title}</title>
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{pal.top}"/>
      <stop offset="1" stop-color="{pal.bottom}"/>
    </linearGradient>
    <clipPath id="tile"><path d="{SQUIRCLE}"/></clipPath>
    <filter id="shadow" x="-30%" y="-30%" width="160%" height="170%" color-interpolation-filters="sRGB">
      <feGaussianBlur in="SourceAlpha" stdDeviation="{blur}"/>
      <feOffset dy="{dy}" result="b"/>
      <feFlood flood-color="{pal.shadow}" flood-opacity="{op}"/>
      <feComposite in2="b" operator="in" result="s"/>
      <feComposite in="s" in2="SourceAlpha" operator="out"/>
    </filter>
    <filter id="edgeblur" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="7"/></filter>
    <filter id="haloblur" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="6"/></filter>
{defs}
  </defs>
  <path d="{SQUIRCLE}" fill="url(#bg)"/>
  <g clip-path="url(#tile)">
{body}
  </g>
</svg>
"""


# Glass ------------------------------------------------------------------------

def glass(uid, d, pool, *, milk=(0.86, 0.5), pool_opacity=0.7, pool_at=(0.5, 0.75),
          pool_r=0.52, sheen=0.5, inner=0.8, inner_w=20, edge=0.75, edge_w=2.6,
          shadow=True, marks="", halos=""):
    """Frosted glass glyph. Returns (defs, body).

    Layers, back to front: knocked-out drop shadow on the tile, milky white body
    (opacity milk[0] at top to milk[1] at bottom), colored light pooling near the
    bottom, a soft sheen up top, a blurred white glow along the inside of the edge,
    a thin bright edge, then blurred white halos and the solid marks inside it.
    """
    defs = f"""    <clipPath id="{uid}-clip"><path d="{d}"/></clipPath>
    <linearGradient id="{uid}-milk" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="{milk[0]}"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="{milk[1]}"/>
    </linearGradient>
    <radialGradient id="{uid}-pool" cx="{pool_at[0]}" cy="{pool_at[1]}" r="{pool_r}">
      <stop offset="0" stop-color="{pool}" stop-opacity="{pool_opacity}"/>
      <stop offset="0.5" stop-color="{pool}" stop-opacity="{pool_opacity * 0.5:.3f}"/>
      <stop offset="1" stop-color="{pool}" stop-opacity="0"/>
    </radialGradient>
    <radialGradient id="{uid}-sheen" cx="0.42" cy="0.24" r="0.6">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="{sheen}"/>
      <stop offset="1" stop-color="#FFFFFF" stop-opacity="0"/>
    </radialGradient>"""
    shadow_layer = f'\n    <path d="{d}" fill="#000000" filter="url(#shadow)"/>' if shadow else ""
    halo_layer = f'\n      <g filter="url(#haloblur)">{halos}</g>' if halos else ""
    body = f"""{shadow_layer}
    <g clip-path="url(#{uid}-clip)">
      <path d="{d}" fill="url(#{uid}-milk)"/>
      <path d="{d}" fill="url(#{uid}-pool)"/>
      <path d="{d}" fill="url(#{uid}-sheen)"/>
      <path d="{d}" fill="none" stroke="#FFFFFF" stroke-opacity="{inner}" stroke-width="{inner_w * 2}" filter="url(#edgeblur)"/>
      <path d="{d}" fill="none" stroke="#FFFFFF" stroke-opacity="{edge}" stroke-width="{edge_w * 2}"/>{halo_layer}
    </g>{marks}"""
    return defs, body


def _marks(marks, color):
    """marks: [{"d": path, "stroke": width} | {"d": path, "fill": true}], optional "color", "halo"."""
    halos, solids = [], []
    for m in marks:
        c = m.get("color", color)
        halo = m.get("halo", 20)
        if "stroke" in m:
            w = m["stroke"]
            halos.append(f'<path d="{m["d"]}" fill="none" stroke="#FFFFFF" stroke-opacity="0.7" '
                         f'stroke-linecap="round" stroke-linejoin="round" stroke-width="{w + halo}"/>')
            solids.append(f'\n    <path d="{m["d"]}" fill="none" stroke="{c}" stroke-linecap="round" '
                          f'stroke-linejoin="round" stroke-width="{w}"/>')
        else:
            halos.append(f'<path d="{m["d"]}" fill="#FFFFFF" stroke="#FFFFFF" stroke-width="{halo}" '
                         f'stroke-linejoin="round" opacity="{m.get("halo_opacity", 0.7)}"/>')
            solids.append(f'\n    <path d="{m["d"]}" fill="{c}"/>')
    return "".join(halos), "".join(solids)


def glass_icon(title, pal, glyph, marks=(), parts=(), transform=None, shadow=(0.4, 14, 12), **glass_kw):
    """Generic icon: one glass glyph path, solid marks inside it, and optional extra glass parts.

    parts: [(path, {glass kwargs})] drawn behind the main glyph (calendar tabs, apple leaf).
    """
    defs, body = [], []
    for i, (d, kw) in enumerate(parts):
        pd, pb = glass(f"p{i}", d, kw.pop("pool", pal.pool), **kw)
        defs.append(pd)
        body.append(pb)
    halos, solids = _marks(marks, pal.mark)
    gd, gb = glass("g", glyph, pal.pool, halos=halos, marks=solids, **glass_kw)
    defs.append(gd)
    body.append(gb)
    inner = "".join(body)
    if transform:
        inner = f'\n    <g transform="{transform}">{inner}\n    </g>'
    return svg(title, pal, "\n".join(defs), inner, shadow)


# Presets ----------------------------------------------------------------------

PIN = ("M129 222A127 127 0 0 1 383 222"
       "C383 288 332 343 276 393"
       "Q256 412 236 393"
       "C180 343 129 288 129 222Z")


def pin_icon(title, pal):
    return glass_icon(title, pal, PIN, marks=[{"d": circle(256, 222, 42), "fill": True, "halo": 24, "halo_opacity": 0.75}],
                      shadow=(0.45, 14, 12), milk=(0.9, 0.62), pool_opacity=0.5, pool_at=(0.5, 0.74), pool_r=0.55)


def calendar_icon(title, pal):
    tabs = rrect(172, 98, 28, 64, 14) + rrect(312, 98, 28, 64, 14)
    tab_kw = dict(pool="#FFFFFF", milk=(0.98, 0.9), pool_opacity=0, sheen=0, inner=0.6, inner_w=6, edge=1, edge_w=2)
    return glass_icon(title, pal, rrect(102, 132, 308, 288, 76),
                      marks=[{"d": rrect(170, 199, 172, 26, 13), "fill": True}],
                      parts=[(tabs, tab_kw)], shadow=(0.4, 14, 12),
                      milk=(0.86, 0.5), pool_opacity=0.7, pool_at=(0.5, 0.72), pool_r=0.5)


ARCS = [("M152 220Q262 166 366 224", 34), ("M164 276Q256 234 350 280", 28), ("M176 328Q252 296 332 332", 22)]


def playlist_icon(title, pal):
    return glass_icon(title, pal, circle(256, 258, 170), marks=[{"d": d, "stroke": w} for d, w in ARCS],
                      shadow=(0.35, 14, 12), milk=(0.86, 0.48), pool_opacity=0.7, pool_at=(0.5, 0.8), pool_r=0.5)


APPLE_BODY = ("M256 176C241 166 221 158 196 158C152 158 118 194 118 252C118 302 138 346 165 373"
              "C178 386 192 391 206 390C224 389 234 380 256 380C278 380 288 389 306 390"
              "C321 391 335 382 348 367C360 353 368 338 376 320C346 306 328 282 328 252"
              "C328 225 343 205 366 193C351 172 327 160 302 160C284 160 270 167 256 176Z")
APPLE_LEAF = "M256 148C254 118 276 92 306 86C308 116 288 143 256 148Z"


def apple_icon(title, pal):
    # White glass: the shadow under the apple reads through the lower body as a gray haze (the pool).
    leaf_kw = dict(milk=(0.98, 0.9), pool_opacity=0, sheen=0.4, inner=0.8, inner_w=6, edge=1, edge_w=2)
    return glass_icon(title, pal, APPLE_BODY, parts=[(APPLE_LEAF, leaf_kw)],
                      transform="translate(247 238) scale(1.08) translate(-247 -238)", shadow=(0.5, 16, 14),
                      milk=(0.98, 0.9), pool_opacity=0.38, pool_at=(0.5, 0.68), pool_r=0.45,
                      sheen=0.6, inner=0.9, inner_w=16, edge=0.9, edge_w=2.6)


def radar_icon(title, pal):
    """Rings cut by a V notch holding a white glass wedge. Meant for a dark tile."""
    cx, cy = 256.0, 258.0
    r_out, r_out_in, r_mid, r_mid_in = 156, 93, 59, 31
    alpha = math.radians(31)   # wedge half angle
    apex_y = cy - 34           # wedge apex
    gap, far, k = 27, 420, 9   # notch width, ray length, apex rounding
    sa, ca = math.sin(alpha), math.cos(alpha)
    gap_apex = apex_y + gap / sa
    gl, gr = (cx - far * sa, gap_apex - far * ca), (cx + far * sa, gap_apex - far * ca)
    wl, wr = (cx - far * sa, apex_y - far * ca), (cx + far * sa, apex_y - far * ca)
    al, ar = (cx - k * sa, apex_y - k * ca), (cx + k * sa, apex_y - k * ca)
    wedge = (f"M{al[0]:.2f} {al[1]:.2f}Q{cx} {apex_y} {ar[0]:.2f} {ar[1]:.2f}"
             f"L{wr[0]:.2f} {wr[1]:.2f}L{wl[0]:.2f} {wl[1]:.2f}Z")
    ring_in, ring_out = mix(pal.bottom, "#FFFFFF", 0.22), mix(pal.bottom, "#FFFFFF", 0.3)
    mid = mix(pal.bottom, "#FFFFFF", 0.25)
    defs = f"""    <radialGradient id="ringfill" cx="{cx}" cy="{cy}" r="{r_out}" gradientUnits="userSpaceOnUse">
      <stop offset="0.6" stop-color="{ring_in}"/>
      <stop offset="1" stop-color="{ring_out}"/>
    </radialGradient>
    <linearGradient id="ringshade" x1="0" y1="{cy - r_out}" x2="0" y2="{cy + r_out}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.06"/>
      <stop offset="1" stop-color="#000000" stop-opacity="0.12"/>
    </linearGradient>
    <linearGradient id="wedgefill" x1="0" y1="{cy - r_out}" x2="0" y2="{apex_y}" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FAFAFA"/>
      <stop offset="1" stop-color="#D4D4D4"/>
    </linearGradient>
    <mask id="vcut" maskUnits="userSpaceOnUse" x="0" y="0" width="{S}" height="{S}">
      <rect width="{S}" height="{S}" fill="#FFFFFF"/>
      <path d="M{cx} {gap_apex:.2f}L{gl[0]:.2f} {gl[1]:.2f}L{gr[0]:.2f} {gr[1]:.2f}Z" fill="#000000"/>
    </mask>
    <clipPath id="outer"><circle cx="{cx}" cy="{cy}" r="{r_out}"/></clipPath>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur in="SourceGraphic" stdDeviation="9" result="g"/>
      <feComponentTransfer in="g" result="g2"><feFuncA type="linear" slope="0.3"/></feComponentTransfer>
      <feMerge><feMergeNode in="g2"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>"""
    ring_r, ring_w = (r_out + r_out_in) / 2, r_out - r_out_in
    mid_r, mid_w = (r_mid + r_mid_in) / 2, r_mid - r_mid_in
    body = f"""    <g mask="url(#vcut)" fill="none">
      <circle cx="{cx}" cy="{cy}" r="{ring_r}" stroke="url(#ringfill)" stroke-width="{ring_w}"/>
      <circle cx="{cx}" cy="{cy}" r="{ring_r}" stroke="url(#ringshade)" stroke-width="{ring_w}"/>
      <circle cx="{cx}" cy="{cy}" r="{mid_r}" stroke="{mid}" stroke-width="{mid_w}"/>
      <circle cx="{cx}" cy="{cy}" r="{mid_r}" stroke="url(#ringshade)" stroke-width="{mid_w}"/>
    </g>
    <g filter="url(#glow)">
      <path d="{wedge}" fill="url(#wedgefill)" clip-path="url(#outer)"/>
    </g>"""
    return svg(title, pal, defs, body)


# (angle clockwise from 12 o'clock in degrees, length from center in px)
RAYS = [(11, 152), (46, 158), (86, 160), (108, 156), (134, 168), (152, 160),
        (182, 166), (209, 162), (233, 158), (266, 164), (301, 160), (332, 170)]


def _ray(cx, cy, ang, length, w0=9, w1=14):
    t = math.radians(ang)
    ux, uy = math.sin(t), -math.cos(t)
    px, py = -uy, ux
    r0, r1 = 2, length - w1
    a = (cx + ux * r0 + px * w0, cy + uy * r0 + py * w0)
    b = (cx + ux * r1 + px * w1, cy + uy * r1 + py * w1)
    c = (cx + ux * r1 - px * w1, cy + uy * r1 - py * w1)
    d = (cx + ux * r0 - px * w0, cy + uy * r0 - py * w0)
    return (f"M{a[0]:.2f} {a[1]:.2f}L{b[0]:.2f} {b[1]:.2f}A{w1} {w1} 0 0 0 {c[0]:.2f} {c[1]:.2f}"
            f"L{d[0]:.2f} {d[1]:.2f}A{w0} {w0} 0 0 0 {a[0]:.2f} {a[1]:.2f}Z")


def starburst_icon(title, pal):
    """Tapered rays with a glowing white core."""
    cx, cy = 260, 254
    rays = "".join(_ray(cx, cy, a, l) for a, l in RAYS)
    defs = f"""    <radialGradient id="rayfill" cx="{cx}" cy="{cy}" r="170" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FFFFFF"/>
      <stop offset="0.3" stop-color="{mix(pal.top, '#FFFFFF', 0.9)}"/>
      <stop offset="1" stop-color="{mix(pal.top, '#FFFFFF', 0.78)}"/>
    </radialGradient>
    <radialGradient id="core" cx="{cx}" cy="{cy}" r="64" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="#FFFFFF" stop-opacity="0.95"/>
      <stop offset="0.55" stop-color="{mix(pal.top, '#FFFFFF', 0.92)}" stop-opacity="0.7"/>
      <stop offset="1" stop-color="{mix(pal.top, '#FFFFFF', 0.85)}" stop-opacity="0"/>
    </radialGradient>"""
    body = f"""    <path d="{rays}" fill="#000000" filter="url(#shadow)"/>
    <path d="{rays}" fill="url(#rayfill)"/>
    <circle cx="{cx}" cy="{cy}" r="64" fill="url(#core)"/>"""
    return svg(title, pal, defs, body, shadow=(0.3, 10, 8))


PRESETS = {"pin": pin_icon, "calendar": calendar_icon, "playlist": playlist_icon,
           "apple": apple_icon, "radar": radar_icon, "starburst": starburst_icon}

# The original set, with hand-tuned palettes (closest match to the reference shots).
DEFAULT_SET = {
    "search-nearby": ("pin", "Search nearby", Palette("#FFD305", "#FFC100", "#F6BB00", "#FFD447", "#D58F00")),
    "traffic": ("pin", "Traffic", Palette("#FFA41A", "#FF8A00", "#F98700", "#FFB257", "#C95A00")),
    "my-schedule-cyan": ("calendar", "My schedule", Palette("#00E0F3", "#00D4E8", "#00CFE3", "#45EEF8", "#0096B4")),
    "my-schedule-blue": ("calendar", "My schedule", Palette("#0444FF", "#003AEA", "#003AD8", "#6A93FF", "#001F96")),
    "daily-playlist": ("playlist", "Daily playlist", Palette("#00DE0C", "#00CE00", "#00C90A", "#5EEC7C", "#008F00")),
    "call-uber": ("radar", "Call Uber", Palette("#2E2E2E", "#2A2A2A", "#606060", "#FFFFFF", "#000000")),
    "computer": ("apple", "Computer", Palette("#C6C6C6", "#B9B9B9", "#B9B9B9", "#8C8C8C", "#5E5E5E")),
    "claude-code": ("starburst", "Claude Code", Palette("#F87A4C", "#F5744A", "#FFDCCF", "#FFF1EB", "#B8401A")),
}


# Build ------------------------------------------------------------------------

def from_spec(entry):
    """Build one icon from a JSON spec entry (see SKILL.md for the format)."""
    pal = palette(entry["color"], **entry.get("palette", {}))
    title = entry.get("title", entry["name"])
    preset = entry.get("preset", "glass")
    if preset == "glass":
        parts = [(p["d"], dict(p.get("glass", {}))) for p in entry.get("parts", [])]
        shadow = tuple(entry.get("shadow", (0.4, 14, 12)))
        return glass_icon(title, pal, entry["glyph"], marks=entry.get("marks", []), parts=parts,
                          transform=entry.get("transform"), shadow=shadow, **entry.get("glass", {}))
    return PRESETS[preset](title, pal)


def scope_ids(data, prefix):
    """Prefix every id and #ref so several icons can be inlined in one HTML page without clashes."""
    ids = set(re.findall(r'id="([^"]+)"', data))
    for i in sorted(ids, key=len, reverse=True):
        data = data.replace(f'id="{i}"', f'id="{prefix}-{i}"').replace(f"url(#{i})", f"url(#{prefix}-{i})")
    return data


def write_icons(icons, out, sizes=(1024, 512, 128), sheet=True):
    """icons: {name: svg_string}. Writes SVGs, PNGs per size and a preview sheet."""
    os.makedirs(os.path.join(out, "svg"), exist_ok=True)
    for name, data in icons.items():
        with open(os.path.join(out, "svg", f"{name}.svg"), "w") as f:
            f.write(scope_ids(data, name))
    rsvg = shutil.which("rsvg-convert")
    if sizes and not rsvg:
        print("rsvg-convert not found: SVGs written, PNGs skipped (brew install librsvg)", file=sys.stderr)
        return
    for z in sizes:
        os.makedirs(os.path.join(out, f"png@{z}"), exist_ok=True)
        for name in icons:
            subprocess.run([rsvg, "-w", str(z), "-h", str(z), os.path.join(out, "svg", f"{name}.svg"),
                            "-o", os.path.join(out, f"png@{z}", f"{name}.png")], check=True)
    if sheet and sizes:
        try:
            from PIL import Image
        except ImportError:
            print("Pillow not installed: preview sheet skipped", file=sys.stderr)
            return
        src = max(sizes)
        names = list(icons)
        cols, t, g = min(4, len(names)), 256, 48
        rows = (len(names) + cols - 1) // cols
        im = Image.new("RGBA", (cols * t + (cols + 1) * g, rows * t + (rows + 1) * g), (245, 246, 248, 255))
        for i, name in enumerate(names):
            tile = Image.open(os.path.join(out, f"png@{src}", f"{name}.png")).convert("RGBA").resize((t, t), Image.LANCZOS)
            im.alpha_composite(tile, (g + (i % cols) * (t + g), g + (i // cols) * (t + g)))
        im.convert("RGB").save(os.path.join(out, "preview.png"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list presets and the default icon set")
    b = sub.add_parser("build", help="build icons into OUT_DIR")
    b.add_argument("out")
    b.add_argument("--spec", help="JSON spec of icons to build instead of the default set")
    b.add_argument("--only", help="comma-separated names to build")
    b.add_argument("--sizes", default="1024,512,128", help="PNG sizes, comma-separated; empty for SVG only")
    b.add_argument("--no-sheet", action="store_true", help="skip preview.png")
    args = ap.parse_args()

    if args.cmd == "list":
        print("presets:", ", ".join(["glass (custom glyph)"] + list(PRESETS)))
        for name, (preset, title, pal) in DEFAULT_SET.items():
            print(f"  {name:18s} {preset:10s} tile {pal.top} -> {pal.bottom}")
        return

    if args.spec:
        with open(args.spec) as f:
            entries = json.load(f)["icons"]
        icons = {e["name"]: from_spec(e) for e in entries}
    else:
        icons = {n: PRESETS[p](t, pal) for n, (p, t, pal) in DEFAULT_SET.items()}
    if args.only:
        keep = set(args.only.split(","))
        icons = {k: v for k, v in icons.items() if k in keep}
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    write_icons(icons, args.out, sizes, sheet=not args.no_sheet)
    print(f"wrote {len(icons)} icons to {args.out}")


if __name__ == "__main__":
    main()
