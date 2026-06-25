#!/usr/bin/env python3
"""Build valid .excalidraw scenes programmatically.

Hand-authoring Excalidraw JSON is error-prone: every element needs a unique id,
a `seed`, a `versionNonce`, the right `roundness`/`roughness`/`fillStyle`
vocabulary, and — the part that breaks most by hand — arrows must carry relative
`points` plus `startBinding`/`endBinding`, AND each shape they touch must list
the arrow back in its own `boundElements`. Bound text labels are the same: the
text element points at its container via `containerId`, and the container lists
the text in `boundElements`. Miss either side and the file opens but renders
wrong (floating arrows, unlabeled boxes).

This module is the single source of truth for that schema. The skill generates
diagrams by importing `Scene` and calling its methods, never by pasting raw
JSON. `autolayout.py` builds on it too.

    from excalidraw import Scene
    s = Scene()
    a = s.rect(100, 100, 160, 60, text="Client", role="service")
    b = s.rect(100, 300, 160, 60, text="API",    role="gateway")
    s.arrow(a, b, label="HTTP")          # geometry + both-sided binding handled
    s.dump("diagram.excalidraw")

File format: https://docs.excalidraw.com/docs/codebase/json-schema
Opens in excalidraw.com, the VS Code "Excalidraw" extension, and Obsidian.

CLI:
    python3 excalidraw.py --selftest          # build a sample and validate it
    python3 excalidraw.py --demo out.excalidraw
"""
from __future__ import annotations

import argparse
import json
import math
import sys

# --- palette -----------------------------------------------------------------
# Excalidraw's own stroke/background presets (the swatches in its UI), mapped to
# the seven semantic roles the skill uses everywhere. backgroundColor is the
# light fill; strokeColor is the saturated outline that pairs with it.
PALETTE = {
    "primary":   {"stroke": "#1971c2", "background": "#a5d8ff"},  # blue   — services, clients
    "success":   {"stroke": "#2f9e44", "background": "#b2f2bb"},  # green  — databases, success
    "warning":   {"stroke": "#f08c00", "background": "#ffec99"},  # yellow — queues, decisions
    "accent":    {"stroke": "#e8590c", "background": "#ffd8a8"},  # orange — gateways, APIs
    "danger":    {"stroke": "#e03131", "background": "#ffc9c9"},  # red    — errors, alerts
    "neutral":   {"stroke": "#495057", "background": "#e9ecef"},  # grey   — external, neutral
    "secondary": {"stroke": "#9c36b5", "background": "#eebefa"},  # purple — security, auth
}
ROLE_SLOT = {
    "service": "primary", "client": "primary",
    "database": "success", "store": "success",
    "queue": "warning", "bus": "warning", "decision": "warning",
    "gateway": "accent", "api": "accent",
    "error": "danger",
    "external": "neutral",
    "security": "secondary", "auth": "secondary",
}
DEFAULT_STROKE = "#1e1e1e"

# sentinel so arrow arrowheads can distinguish "not passed" (inherit edge_defaults)
# from an explicit None (no arrowhead).
_INHERIT = object()

# Excalidraw font ids. 1 = hand-drawn (Excalifont/Virgil), 2 = normal (Nunito),
# 3 = code (Comic Shanns Mono). Excalidraw maps these on load.
FONT_HAND, FONT_NORMAL, FONT_CODE = 1, 2, 3

_FIXED_TS = 1700000000000   # stable `updated` stamp -> reproducible files


class Scene:
    """An accumulating Excalidraw scene. Element-creating methods return the new
    element's id (a string) so you can wire arrows and labels to it."""

    def __init__(self, background: str = "#ffffff", seed: int = 12345,
                 roughness: int = 1, font_family: int = FONT_HAND,
                 fill_style: str = "solid", stroke_width: int = 2,
                 font_size: int = 20, palette: dict | None = None,
                 roles: dict | None = None):
        self.elements: list[dict] = []
        self.files: dict[str, dict] = {}
        self.background = background
        self.default_roughness = roughness        # 0 architect, 1 artist, 2 cartoonist
        self.default_font = font_family
        self.default_fill = fill_style            # solid / hachure / cross-hatch
        self.default_stroke_width = stroke_width  # 1 thin, 2 bold, 4 extra-bold
        self.default_font_size = font_size
        # palette / role-map overrides (e.g. from a style preset)
        self.palette = {**PALETTE, **(palette or {})}
        self.roles = {**ROLE_SLOT, **(roles or {})}
        self.edge_defaults = {"stroke_style": "solid", "start_arrowhead": None,
                              "end_arrowhead": "arrow"}
        self._n = 0
        self._rng = seed & 0x7FFFFFFF
        self._by_id: dict[str, dict] = {}

    @classmethod
    def from_preset(cls, preset: dict, **overrides):
        """Build a Scene configured from a style-preset dict (styles/*.json).

        Maps the Excalidraw-vocabulary preset (strokeColor/backgroundColor,
        fillStyle, roughness, font family name) onto the builder's constructor.
        Pass keyword overrides (e.g. background=...) to win over the preset."""
        FONTS = {"hand": FONT_HAND, "normal": FONT_NORMAL, "code": FONT_CODE}
        pal = {slot: {"stroke": c["strokeColor"], "background": c["backgroundColor"]}
               for slot, c in (preset.get("palette") or {}).items() if c}
        extras = preset.get("extras") or {}
        font = preset.get("font") or {}
        kw = dict(
            palette=pal,
            roles=preset.get("roles") or {},
            roughness=extras.get("roughness", 1),
            fill_style=extras.get("fillStyle", "solid"),
            stroke_width=extras.get("strokeWidth", 2),
            font_family=FONTS.get(font.get("family", "hand"), FONT_HAND),
            font_size=font.get("size", 20),
        )
        kw.update(overrides)
        s = cls(**kw)
        edges = preset.get("edges") or {}
        s.edge_defaults = {
            "stroke_style": edges.get("strokeStyle", "solid"),
            "start_arrowhead": edges.get("startArrowhead"),
            "end_arrowhead": edges.get("endArrowhead", "arrow"),
        }
        return s

    # -- internals ------------------------------------------------------------
    def _next_id(self, prefix: str = "el") -> str:
        self._n += 1
        return f"{prefix}-{self._n}"

    def _seed(self) -> int:
        # Deterministic LCG (Numerical Recipes constants). roughjs only needs a
        # stable integer; deterministic seeds make exported files reproducible.
        self._rng = (self._rng * 1664525 + 1013904223) & 0x7FFFFFFF
        return self._rng

    def _base(self, etype: str, x: float, y: float, w: float, h: float,
              stroke: str, background: str, fill_style: str, stroke_width: int,
              stroke_style: str, roughness: int | None, roundness,
              opacity: int, group_ids, angle: float) -> dict:
        el = {
            "id": self._next_id(),
            "type": etype,
            "x": float(x), "y": float(y),
            "width": float(w), "height": float(h),
            "angle": float(angle),
            "strokeColor": stroke,
            "backgroundColor": background,
            "fillStyle": fill_style,
            "strokeWidth": stroke_width,
            "strokeStyle": stroke_style,
            "roughness": self.default_roughness if roughness is None else roughness,
            "opacity": opacity,
            "groupIds": list(group_ids or []),
            "frameId": None,
            "roundness": roundness,
            "seed": self._seed(),
            "version": 1,
            "versionNonce": self._seed(),
            "isDeleted": False,
            "boundElements": [],
            "updated": _FIXED_TS,
            "link": None,
            "locked": False,
        }
        self.elements.append(el)
        self._by_id[el["id"]] = el
        return el

    def _resolve(self, role: str | None, stroke: str | None, background: str | None):
        """(role|explicit) -> (strokeColor, backgroundColor)."""
        if role:
            slot = self.roles.get(role.lower(), role.lower())
            pal = self.palette.get(slot)
            if pal:
                return (stroke or pal["stroke"], background or pal["background"])
        return (stroke or DEFAULT_STROKE,
                background if background is not None else "transparent")

    # -- shapes ---------------------------------------------------------------
    def _shape(self, etype, x, y, w, h, *, text=None, role=None, stroke=None,
               background=None, fill_style=None, stroke_width=None,
               stroke_style="solid", roughness=None, rounded=True, opacity=100,
               group_ids=None, angle=0.0, font_size=None, font_family=None,
               text_color=None):
        sc, bg = self._resolve(role, stroke, background)
        fill_style = self.default_fill if fill_style is None else fill_style
        stroke_width = self.default_stroke_width if stroke_width is None else stroke_width
        font_size = self.default_font_size if font_size is None else font_size
        roundness = {"type": 3} if (rounded and etype == "rectangle") else None
        el = self._base(etype, x, y, w, h, sc, bg, fill_style, stroke_width,
                        stroke_style, roughness, roundness, opacity, group_ids, angle)
        if text:
            self._bind_label(el, text, font_size, font_family, text_color or sc)
        return el["id"]

    def rect(self, x, y, w, h, **kw):
        """Rounded rectangle (services, modules, processes)."""
        return self._shape("rectangle", x, y, w, h, **kw)

    def ellipse(self, x, y, w, h, **kw):
        """Ellipse/circle (start/end, databases-as-circles)."""
        kw.setdefault("rounded", False)
        return self._shape("ellipse", x, y, w, h, **kw)

    def diamond(self, x, y, w, h, **kw):
        """Diamond (decisions)."""
        kw.setdefault("rounded", False)
        kw.setdefault("role", "warning")
        return self._shape("diamond", x, y, w, h, **kw)

    # -- text -----------------------------------------------------------------
    def _measure(self, text: str, font_size: int) -> tuple[float, float]:
        """Rough text box size. Excalidraw recomputes on load with real metrics;
        this only needs to be close enough that initial geometry isn't absurd."""
        lines = text.split("\n")
        w = max((len(ln) for ln in lines), default=1) * font_size * 0.6
        h = len(lines) * font_size * 1.25
        return max(w, font_size), max(h, font_size * 1.25)

    def text(self, x, y, text, *, font_size=None, font_family=None, color=None,
             align="left", valign="top", group_ids=None, angle=0.0,
             opacity=100):
        """Free-standing text (titles, annotations)."""
        ff = font_family or self.default_font
        font_size = self.default_font_size if font_size is None else font_size
        w, h = self._measure(text, font_size)
        el = self._base("text", x, y, w, h, color or DEFAULT_STROKE, "transparent",
                        "solid", 2, "solid", 0, None, opacity, group_ids, angle)
        el.update({
            "text": text, "originalText": text,
            "fontSize": font_size, "fontFamily": ff,
            "textAlign": align, "verticalAlign": valign,
            "containerId": None, "lineHeight": 1.25, "autoResize": True,
        })
        return el["id"]

    def _bind_label(self, container: dict, text: str, font_size, font_family, color):
        """Add a text element centered inside `container`, wired both ways."""
        ff = font_family or self.default_font
        w, h = self._measure(text, font_size)
        tx = container["x"] + (container["width"] - w) / 2
        ty = container["y"] + (container["height"] - h) / 2
        el = self._base("text", tx, ty, w, h, color, "transparent", "solid", 2,
                        "solid", 0, None, 100, [], 0.0)
        el.update({
            "text": text, "originalText": text,
            "fontSize": font_size, "fontFamily": ff,
            "textAlign": "center", "verticalAlign": "middle",
            "containerId": container["id"], "lineHeight": 1.25, "autoResize": False,
        })
        container["boundElements"].append({"id": el["id"], "type": "text"})
        return el["id"]

    # -- arrows / lines -------------------------------------------------------
    @staticmethod
    def _center(el):
        return (el["x"] + el["width"] / 2, el["y"] + el["height"] / 2)

    @staticmethod
    def _edge_point(el, toward, gap):
        """Point on `el`'s border on the ray toward (tx,ty), pushed out by `gap`."""
        cx, cy = el["x"] + el["width"] / 2, el["y"] + el["height"] / 2
        dx, dy = toward[0] - cx, toward[1] - cy
        if dx == 0 and dy == 0:
            return cx, cy
        hw, hh = el["width"] / 2, el["height"] / 2
        # scale to the nearest box edge
        sx = hw / abs(dx) if dx else math.inf
        sy = hh / abs(dy) if dy else math.inf
        s = min(sx, sy)
        ex, ey = cx + dx * s, cy + dy * s
        d = math.hypot(dx, dy)
        return ex + dx / d * gap, ey + dy / d * gap

    def arrow(self, source, target, *, label=None, stroke=None, stroke_width=2,
              stroke_style=None, roughness=None, start_arrowhead=_INHERIT,
              end_arrowhead=_INHERIT, gap=6, label_font_size=16, group_ids=None,
              opacity=100):
        """Bound arrow between two element ids (or raw ((x,y),(x,y)) points).

        Computes the on-border attachment points, sets relative `points`, wires
        `startBinding`/`endBinding`, and registers the arrow in both shapes'
        `boundElements`. Optionally adds a bound label."""
        if stroke_style is None:
            stroke_style = self.edge_defaults["stroke_style"]
        if start_arrowhead is _INHERIT:
            start_arrowhead = self.edge_defaults["start_arrowhead"]
        if end_arrowhead is _INHERIT:
            end_arrowhead = self.edge_defaults["end_arrowhead"]
        if isinstance(source, str) and isinstance(target, str):
            se, te = self._by_id[source], self._by_id[target]
            start = self._edge_point(se, self._center(te), gap)
            end = self._edge_point(te, self._center(se), gap)
        else:                                            # raw point pair
            se = te = None
            start, end = source, target
        x1, y1 = start
        x2, y2 = end
        minx, miny = min(x1, x2), min(y1, y2)
        el = self._base("arrow", minx, miny, abs(x2 - x1), abs(y2 - y1),
                        stroke or DEFAULT_STROKE, "transparent", "solid",
                        stroke_width, stroke_style, roughness, None, opacity,
                        group_ids, 0.0)
        el["points"] = [[x1 - minx, y1 - miny], [x2 - minx, y2 - miny]]
        el["lastCommittedPoint"] = None
        el["startArrowhead"] = start_arrowhead
        el["endArrowhead"] = end_arrowhead
        if se is not None:
            el["startBinding"] = {"elementId": se["id"], "focus": 0, "gap": gap}
            el["endBinding"] = {"elementId": te["id"], "focus": 0, "gap": gap}
            se["boundElements"].append({"id": el["id"], "type": "arrow"})
            te["boundElements"].append({"id": el["id"], "type": "arrow"})
        else:
            el["startBinding"] = el["endBinding"] = None
        if label:
            self._bind_label(el, label, label_font_size, None,
                             stroke or DEFAULT_STROKE)
        return el["id"]

    def routed_arrow(self, points, *, source=None, target=None, label=None,
                     stroke=None, stroke_width=2, stroke_style=None,
                     roughness=None, end_arrowhead=_INHERIT, start_arrowhead=_INHERIT,
                     label_font_size=16, gap=4, group_ids=None, opacity=100):
        """Arrow following an explicit absolute polyline (≥2 points) — used by
        autolayout to replay Graphviz's orthogonal route so the line goes around
        nodes. `source`/`target` element ids (optional) add editable bindings."""
        if stroke_style is None:
            stroke_style = self.edge_defaults["stroke_style"]
        if start_arrowhead is _INHERIT:
            start_arrowhead = self.edge_defaults["start_arrowhead"]
        if end_arrowhead is _INHERIT:
            end_arrowhead = self.edge_defaults["end_arrowhead"]
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        minx, miny = min(xs), min(ys)
        el = self._base("arrow", minx, miny, max(xs) - minx, max(ys) - miny,
                        stroke or DEFAULT_STROKE, "transparent", "solid",
                        stroke_width, stroke_style, roughness, None, opacity,
                        group_ids, 0.0)
        el["points"] = [[p[0] - minx, p[1] - miny] for p in points]
        el["lastCommittedPoint"] = None
        el["startArrowhead"] = start_arrowhead
        el["endArrowhead"] = end_arrowhead
        el["startBinding"] = el["endBinding"] = None
        if source in self._by_id:
            el["startBinding"] = {"elementId": source, "focus": 0, "gap": gap}
            self._by_id[source]["boundElements"].append({"id": el["id"], "type": "arrow"})
        if target in self._by_id:
            el["endBinding"] = {"elementId": target, "focus": 0, "gap": gap}
            self._by_id[target]["boundElements"].append({"id": el["id"], "type": "arrow"})
        if label:
            self._bind_label(el, label, label_font_size, None,
                             stroke or DEFAULT_STROKE)
        return el["id"]

    def line(self, points, *, stroke=None, stroke_width=2, stroke_style="solid",
             roughness=None, group_ids=None, opacity=100):
        """Multi-point line from absolute [(x,y), ...] (separators, freeform)."""
        xs = [p[0] for p in points]
        ys = [p[1] for p in points]
        minx, miny = min(xs), min(ys)
        el = self._base("line", minx, miny, max(xs) - minx, max(ys) - miny,
                        stroke or DEFAULT_STROKE, "transparent", "solid",
                        stroke_width, stroke_style, roughness, None, opacity,
                        group_ids, 0.0)
        el["points"] = [[p[0] - minx, p[1] - miny] for p in points]
        el["lastCommittedPoint"] = None
        el["startArrowhead"] = None
        el["endArrowhead"] = None
        return el["id"]

    # -- containers / images --------------------------------------------------
    def frame(self, x, y, w, h, name="Frame"):
        """A named frame (visual grouping region)."""
        el = self._base("frame", x, y, w, h, "#bbb", "transparent", "solid", 2,
                        "solid", 0, None, 100, [], 0.0)
        el["name"] = name
        return el["id"]

    def image(self, x, y, w, h, data_url, mime="image/svg+xml"):
        """Embed an image. `data_url` is a data: URI; stored in the files map."""
        file_id = f"file-{len(self.files) + 1}"
        el = self._base("image", x, y, w, h, "transparent", "transparent",
                        "solid", 2, "solid", 0, None, 100, [], 0.0)
        el.update({"fileId": file_id, "status": "saved", "scale": [1, 1]})
        self.files[file_id] = {
            "mimeType": mime, "id": file_id, "dataURL": data_url,
            "created": _FIXED_TS, "lastRetrieved": _FIXED_TS,
        }
        return el["id"]

    # -- output ---------------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "type": "excalidraw",
            "version": 2,
            "source": "https://github.com/devbyshima/skills",
            "elements": self.elements,
            "appState": {"gridSize": None, "viewBackgroundColor": self.background},
            "files": self.files,
        }

    def dumps(self, indent=2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def dump(self, path: str, indent=2):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.dumps(indent))
        return path


# --- self-test ---------------------------------------------------------------
def _demo() -> Scene:
    s = Scene()
    s.text(120, 40, "Request flow", font_size=28)
    client = s.rect(120, 110, 160, 60, text="Web Client", role="service")
    gw = s.rect(120, 260, 160, 60, text="API Gateway", role="gateway")
    dec = s.diamond(110, 410, 180, 90, text="Authed?")
    svc = s.rect(360, 410, 160, 60, text="User Service", role="service")
    db = s.ellipse(360, 560, 160, 70, text="User DB", role="database")
    err = s.rect(110, 560, 160, 60, text="401", role="error")
    s.arrow(client, gw, label="HTTPS")
    s.arrow(gw, dec)
    s.arrow(dec, svc, label="yes")
    s.arrow(dec, err, label="no", stroke_style="dashed")
    s.arrow(svc, db, label="SQL")
    return s


def _validate_dict(d: dict) -> list[str]:
    """Light structural check — same spirit as scripts/validate.py, inlined so
    --selftest needs no second file."""
    errs = []
    if d.get("type") != "excalidraw":
        errs.append("top-level type != 'excalidraw'")
    ids = {}
    for el in d["elements"]:
        if el["id"] in ids:
            errs.append(f"duplicate id {el['id']!r}")
        ids[el["id"]] = el
    for el in d["elements"]:
        if el["type"] in ("arrow", "line") and len(el.get("points", [])) < 2:
            errs.append(f"{el['type']} {el['id']!r} has <2 points")
        for end in ("startBinding", "endBinding"):
            b = el.get(end)
            if b and b["elementId"] not in ids:
                errs.append(f"{el['id']!r} {end} -> missing {b['elementId']!r}")
        if el.get("containerId") and el["containerId"] not in ids:
            errs.append(f"text {el['id']!r} containerId -> missing")
        for be in el.get("boundElements") or []:
            if be["id"] not in ids:
                errs.append(f"{el['id']!r} boundElements -> missing {be['id']!r}")
    return errs


def main():
    ap = argparse.ArgumentParser(description="Build/validate Excalidraw scenes.")
    ap.add_argument("--demo", metavar="OUT", help="write a sample .excalidraw")
    ap.add_argument("--selftest", action="store_true",
                    help="build the sample, validate structure, print result")
    args = ap.parse_args()
    if args.selftest:
        d = _demo().to_dict()
        errs = _validate_dict(d)
        print(f"elements={len(d['elements'])} files={len(d['files'])} "
              f"errors={len(errs)}")
        for e in errs:
            print("  error:", e)
        sys.exit(1 if errs else 0)
    if args.demo:
        _demo().dump(args.demo)
        print(f"wrote {args.demo}")
        return
    ap.print_help()


if __name__ == "__main__":
    main()
