#!/usr/bin/env python3
"""Auto-layout a logical graph into an .excalidraw scene using Graphviz.

Takes a graph (nodes + edges as JSON), runs `dot` to position the nodes and
route the edges orthogonally, and emits a .excalidraw file via the shared
`excalidraw.Scene` builder. dot's bend points are replayed as multi-point arrows
so edges go *around* nodes (Excalidraw arrows are otherwise straight and won't
avoid obstacles). This removes the hand-coordinate ceiling for medium/large
diagrams.

Input JSON (same contract as the draw.io skill, so the bundled importers feed
both):
  {
    "direction": "TB",          # TB (top-bottom, default) or LR (left-right)
    "nodes": [
      {"id": "a", "label": "Service A", "role": "service",
       "shape": "rectangle", "width": 160, "height": 60}
    ],
    "edges": [
      {"source": "a", "target": "b", "label": "calls"}
    ]
  }
Only "id" is required per node. `role` (service/database/queue/gateway/error/
external/security/decision) picks colours from the shared palette; `shape`
(rectangle/ellipse/diamond) picks the form; explicit `fillColor`/`strokeColor`
override. A styleless grouped node is tinted by its group's colour.

Usage: python3 autolayout.py graph.json [-o diagram.excalidraw] [--mono] [--roughness 0|1|2]
Requires Graphviz `dot` on PATH (brew install graphviz).
"""
import argparse
import json
import os
import shlex
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from excalidraw import Scene, PALETTE  # noqa: E402

DEFAULT_W, DEFAULT_H = 160, 60
GROUP_PAD = 28
# Palette role order, so each top-level group reads as a distinct coloured cluster.
_PALETTE_ORDER = ["primary", "success", "accent", "secondary", "warning", "danger", "neutral"]


def dot_quote(value):
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'


def snap(value, grid=10):
    return int(round(value / grid) * grid)


def group_tree(nodes):
    """Parse hierarchical `group` paths ("a/b") into a container tree.
    Returns (gpath, direct, children, ordered) — see autolayout.md."""
    gpath, direct, paths = {}, {}, set()
    for node in nodes:
        g = node.get("group")
        if g is None or str(g).strip("/") == "":
            continue
        t = tuple(str(g).strip("/").split("/"))
        gpath[node["id"]] = t
        direct.setdefault(t, []).append(node["id"])
        for k in range(1, len(t) + 1):
            paths.add(t[:k])
    children = {}
    for p in sorted(paths):
        if len(p) > 1:
            children.setdefault(p[:-1], []).append(p)
    ordered = sorted(paths, key=lambda p: (len(p), p))
    return gpath, direct, children, ordered


def build_dot(graph):
    rankdir = "LR" if str(graph.get("direction", "TB")).upper() == "LR" else "TB"
    lines = [f"digraph G {{ rankdir={rankdir}; splines=ortho; node [shape=box fixedsize=true];"]
    _, direct, children, ordered = group_tree(graph["nodes"])
    cidx = {p: i for i, p in enumerate(ordered)}

    def emit_cluster(p, pad):
        lines.append(f'{pad}subgraph cluster_{cidx[p]} {{ margin={GROUP_PAD};')
        for c in children.get(p, []):
            emit_cluster(c, pad + "  ")
        lines.extend(f'{pad}  {dot_quote(m)};' for m in direct.get(p, []))
        lines.append(pad + "}")

    for root in [p for p in ordered if len(p) == 1]:
        emit_cluster(root, "")
    for node in graph["nodes"]:
        w = node.get("width", DEFAULT_W) / 72.0
        h = node.get("height", DEFAULT_H) / 72.0
        lines.append(f'{dot_quote(node["id"])} [width={w:.4f} height={h:.4f}];')
    for edge in graph.get("edges", []):
        lines.append(f'{dot_quote(edge["source"])} -> {dot_quote(edge["target"])};')
    lines.append("}")
    return "\n".join(lines)


def layout(dot_src):
    """Run `dot -Tplain`; return (height_in, {id:(xc,yc)}, {(src,dst):[(x,y),...]})."""
    try:
        proc = subprocess.run(["dot", "-Tplain"], input=dot_src,
                              capture_output=True, text=True, check=True)
    except FileNotFoundError:
        sys.exit("error: Graphviz `dot` not found on PATH (brew install graphviz)")
    except subprocess.CalledProcessError as exc:
        sys.exit(f"error: dot failed: {exc.stderr.strip()}")
    height, pos, edges = 0.0, {}, {}
    for line in proc.stdout.splitlines():
        tok = shlex.split(line)
        if not tok:
            continue
        if tok[0] == "graph":
            height = float(tok[3])
        elif tok[0] == "node":
            pos[tok[1]] = (float(tok[2]), float(tok[3]))
        elif tok[0] == "edge":
            n = int(tok[3])
            edges[(tok[1], tok[2])] = [
                (float(tok[4 + 2 * i]), float(tok[5 + 2 * i])) for i in range(n)
            ]
    return height, pos, edges


def to_excalidraw(graph, height, pos, edge_pts, color=True, roughness=1):
    nodes = graph["nodes"]
    scene = Scene(roughness=roughness)
    # Absolute snapped rect for every placed node (flip dot's bottom-left origin).
    rects = {}
    for node in nodes:
        nid = node["id"]
        if nid not in pos:
            continue
        w, h = node.get("width", DEFAULT_W), node.get("height", DEFAULT_H)
        xc, yc = pos[nid]
        x = snap(xc * 72 - w / 2)
        y = snap((height - yc) * 72 - h / 2)
        rects[nid] = (x, y, w, h)

    gpath, direct, children, ordered = group_tree(nodes)
    top_order = []
    for node in nodes:
        t = gpath.get(node["id"])
        if t and t[0] not in top_order:
            top_order.append(t[0])

    def gslot(seg):
        return _PALETTE_ORDER[top_order.index(seg) % len(_PALETTE_ORDER)]

    # Container bounding boxes (members + nested children + padding), deepest-first.
    gbox = {}
    for p in sorted(ordered, key=len, reverse=True):
        xs = [(rects[m][0], rects[m][1], rects[m][0] + rects[m][2], rects[m][1] + rects[m][3])
              for m in direct.get(p, []) if m in rects]
        xs += [(gbox[c][0], gbox[c][1], gbox[c][0] + gbox[c][2], gbox[c][1] + gbox[c][3])
               for c in children.get(p, []) if c in gbox]
        if not xs:
            continue
        x0 = min(b[0] for b in xs) - GROUP_PAD
        y0 = min(b[1] for b in xs) - GROUP_PAD * 1.4   # extra top room for the title
        x1 = max(b[2] for b in xs) + GROUP_PAD
        y1 = max(b[3] for b in xs) + GROUP_PAD
        gbox[p] = (x0, y0, x1 - x0, y1 - y0)

    # Shift everything to positive coordinates.
    allx = [r[0] for r in rects.values()] + [b[0] for b in gbox.values()]
    ally = [r[1] for r in rects.values()] + [b[1] for b in gbox.values()]
    dx = GROUP_PAD - min(allx) if allx and min(allx) < 0 else 0
    dy = GROUP_PAD - min(ally) if ally and min(ally) < 0 else 0

    # Draw containers first (so nodes sit on top). Shallow-first.
    label_override = {}
    for node in nodes:
        if node["id"] in gpath and "groupLabel" in node:
            label_override.setdefault(gpath[node["id"]], str(node["groupLabel"]))
    for p in ordered:
        if p not in gbox:
            continue
        gx, gy, gw, gh = gbox[p]
        slot = gslot(p[0])
        stroke = PALETTE[slot]["stroke"] if color else "#868e96"
        title = label_override.get(p, p[-1])
        cid = scene.rect(gx + dx, gy + dy, gw, gh, stroke=stroke,
                         background="transparent", stroke_style="dashed",
                         rounded=True, roughness=roughness)
        scene.text(gx + dx + 10, gy + dy + 6, title, font_size=16, color=stroke)
        del cid

    # Nodes.
    for node in nodes:
        nid = node["id"]
        if nid not in rects:
            continue
        rx, ry, w, h = rects[nid]
        shape = (node.get("shape") or "rectangle").lower()
        kw = {"text": node.get("label", nid), "roughness": roughness}
        if node.get("fillColor") or node.get("strokeColor"):
            kw["background"] = node.get("fillColor", "transparent")
            kw["stroke"] = node.get("strokeColor", "#1e1e1e")
        elif node.get("role"):
            kw["role"] = node["role"]
        elif color and nid in gpath:
            kw["role"] = gslot(gpath[nid][0])            # tint styleless node by group
        fn = {"ellipse": scene.ellipse, "diamond": scene.diamond}.get(shape, scene.rect)
        node["_eid"] = fn(rx + dx, ry + dy, w, h, **kw)

    eid = {n["id"]: n.get("_eid") for n in nodes}
    # Edges: replay dot's orthogonal route as a multi-point arrow.
    for edge in graph.get("edges", []):
        pts = edge_pts.get((edge["source"], edge["target"]), [])
        if len(pts) >= 2:
            route = [(snap(x * 72) + dx, snap((height - y) * 72) + dy) for x, y in pts]
        elif edge["source"] in eid and edge["target"] in eid:
            route = None                                 # fall back to bound straight arrow
        else:
            continue
        if route:
            scene.routed_arrow(route, source=eid.get(edge["source"]),
                               target=eid.get(edge["target"]),
                               label=edge.get("label"), roughness=roughness)
        else:
            scene.arrow(eid[edge["source"]], eid[edge["target"]],
                        label=edge.get("label"), roughness=roughness)
    return scene


def main():
    ap = argparse.ArgumentParser(description="Auto-layout a graph JSON into an .excalidraw scene.")
    ap.add_argument("input", help="graph JSON file")
    ap.add_argument("-o", "--output", help="output .excalidraw path (default: stdout)")
    ap.add_argument("--mono", action="store_true", help="don't colour groups by palette")
    ap.add_argument("--roughness", type=int, default=1, choices=[0, 1, 2],
                    help="0 architect (clean), 1 artist (default), 2 cartoonist")
    args = ap.parse_args()
    with open(args.input, encoding="utf-8") as f:
        graph = json.load(f)
    height, pos, edge_pts = layout(build_dot(graph))
    scene = to_excalidraw(graph, height, pos, edge_pts,
                          color=not args.mono, roughness=args.roughness)
    if args.output:
        scene.dump(args.output)
        print(f"wrote {args.output} ({len(graph['nodes'])} nodes, "
              f"{len(graph.get('edges', []))} edges)", file=sys.stderr)
    else:
        sys.stdout.write(scene.dumps())


if __name__ == "__main__":
    main()
