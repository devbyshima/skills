#!/usr/bin/env python3
"""Deterministic structural linter for .excalidraw files.

Catches the class of mistakes a vision self-check is slow and unreliable at —
the ones unique to Excalidraw's JSON model:

  errors (exit non-zero):
    - not a valid Excalidraw document / unparseable JSON
    - duplicate element ids
    - arrow/line with fewer than 2 points (won't render)
    - startBinding / endBinding pointing at a missing element
    - text containerId pointing at a missing element
    - boundElements entry pointing at a missing element

  warnings (exit non-zero only with --strict):
    - one-sided binding: an arrow binds a shape but the shape doesn't list the
      arrow in boundElements (or vice-versa) — the link won't move when edited
    - a bound text label whose container doesn't list it back
    - two filled shapes overlapping (stacked nodes)
    - element with non-finite / negative-size geometry

Runs without a browser, so it's a fast pre-check before the (slower, vision-
based) self-check. Generated output from scripts/excalidraw.py and autolayout.py
should always pass clean; a failure means a hand-edit or an external file is
malformed.

Usage: python3 validate.py diagram.excalidraw [--strict]
"""
import argparse
import json
import math
import sys

SHAPES = {"rectangle", "ellipse", "diamond"}


def finite_rect(el):
    try:
        x, y, w, h = (float(el["x"]), float(el["y"]),
                      float(el["width"]), float(el["height"]))
    except (KeyError, TypeError, ValueError):
        return None
    if any(math.isnan(v) or math.isinf(v) for v in (x, y, w, h)):
        return None
    return (x, y, w, h)


def overlap(a, b):
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


def check(doc):
    errors, warns = [], []
    if not isinstance(doc, dict) or doc.get("type") != "excalidraw":
        return ["not an Excalidraw document (top-level type != 'excalidraw')"], []
    elements = [e for e in doc.get("elements", []) if not e.get("isDeleted")]

    by_id = {}
    for el in elements:
        eid = el.get("id")
        if eid in by_id:
            errors.append(f"duplicate id {eid!r}")
        by_id[eid] = el

    # bound-elements back-reference index: element id -> set of ids that list it
    listed = {}
    for el in elements:
        for be in el.get("boundElements") or []:
            bid = be.get("id")
            if bid not in by_id:
                errors.append(f"{el.get('id')!r} boundElements -> missing {bid!r}")
            else:
                listed.setdefault(bid, set()).add(el["id"])

    for el in elements:
        eid, etype = el.get("id"), el.get("type")

        if etype in ("arrow", "line"):
            pts = el.get("points") or []
            if len(pts) < 2:
                errors.append(f"{etype} {eid!r} has <2 points (won't render)")
            for end in ("startBinding", "endBinding"):
                b = el.get(end)
                if b:
                    tgt = b.get("elementId")
                    if tgt not in by_id:
                        errors.append(f"{eid!r} {end} -> missing {tgt!r}")
                    elif tgt not in listed.get(el["id"], ()):  # noqa: E713
                        warns.append(f"arrow {eid!r} binds {tgt!r} but it isn't "
                                     f"in that shape's boundElements")

        if etype == "text":
            cid = el.get("containerId")
            if cid is not None:
                if cid not in by_id:
                    errors.append(f"text {eid!r} containerId -> missing {cid!r}")
                elif cid not in listed.get(el["id"], ()):  # noqa: E713
                    warns.append(f"text {eid!r} is in container {cid!r} but that "
                                 f"container doesn't list it in boundElements")

        if etype in SHAPES or etype in ("text", "image", "frame"):
            r = finite_rect(el)
            if r is None:
                errors.append(f"{etype} {eid!r} has missing/invalid geometry")
            else:
                _, _, w, h = r
                if w < 0 or h < 0:
                    warns.append(f"{etype} {eid!r} negative size {w:g}x{h:g}")

    # overlap among filled shapes only (transparent boxes are containers/groups)
    filled = [(el.get("id"), finite_rect(el)) for el in elements
              if el.get("type") in SHAPES
              and el.get("backgroundColor", "transparent") != "transparent"]
    filled = [(i, r) for i, r in filled if r]
    for i in range(len(filled)):
        for j in range(i + 1, len(filled)):
            (ia, ra), (ib, rb) = filled[i], filled[j]
            if overlap(ra, rb):
                warns.append(f"filled shapes {ia!r} and {ib!r} overlap")
    return errors, warns


def main():
    ap = argparse.ArgumentParser(description="Lint an .excalidraw file for structural errors.")
    ap.add_argument("file")
    ap.add_argument("--strict", action="store_true", help="treat warnings as failure too")
    args = ap.parse_args()
    try:
        with open(args.file, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        sys.exit(f"error: cannot read {args.file}: {exc}")
    errors, warns = check(doc)
    for w in warns:
        print(f"warning: {w}")
    for e in errors:
        print(f"error: {e}")
    print(f"{len(errors)} error(s), {len(warns)} warning(s)")
    if errors or (args.strict and warns):
        sys.exit(1)


if __name__ == "__main__":
    main()
