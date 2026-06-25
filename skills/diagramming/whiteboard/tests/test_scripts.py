#!/usr/bin/env python3
"""Smoke tests for whiteboard scripts (no Node/browser needed).

Run: python3 tests/test_scripts.py
Exercises the Scene builder, the structural linter, the style presets, and —
when Graphviz `dot` is available — the autolayout pipeline. Image export
(render.mjs) needs Node + a browser and is out of scope here.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(SKILL_DIR, "scripts")
STYLES = os.path.join(SKILL_DIR, "styles", "built-in")
sys.path.insert(0, SCRIPTS)

from excalidraw import Scene, _validate_dict  # noqa: E402


def run_validate(path, strict=False):
    cmd = [sys.executable, os.path.join(SCRIPTS, "validate.py"), path]
    if strict:
        cmd.append("--strict")
    return subprocess.run(cmd, capture_output=True, text=True)


class TestBuilder(unittest.TestCase):
    def test_demo_selftest_clean(self):
        out = subprocess.run([sys.executable, os.path.join(SCRIPTS, "excalidraw.py"),
                              "--selftest"], capture_output=True, text=True)
        self.assertEqual(out.returncode, 0, out.stdout + out.stderr)

    def test_shapes_arrows_bind_both_sides(self):
        s = Scene()
        a = s.rect(0, 0, 100, 50, text="A", role="service")
        b = s.ellipse(0, 200, 100, 50, text="B", role="database")
        arr = s.arrow(a, b, label="x")
        d = s.to_dict()
        self.assertEqual(_validate_dict(d), [])
        by_id = {e["id"]: e for e in d["elements"]}
        # arrow listed in both shapes' boundElements
        for shape in (a, b):
            ids = [be["id"] for be in by_id[shape]["boundElements"]]
            self.assertIn(arr, ids)
        # arrow binds both shapes
        self.assertEqual(by_id[arr]["startBinding"]["elementId"], a)
        self.assertEqual(by_id[arr]["endBinding"]["elementId"], b)

    def test_bound_label_round_trips(self):
        s = Scene()
        r = s.rect(0, 0, 120, 60, text="Hello")
        d = s.to_dict()
        by_id = {e["id"]: e for e in d["elements"]}
        labels = [e for e in d["elements"] if e["type"] == "text" and e.get("containerId") == r]
        self.assertEqual(len(labels), 1)
        self.assertIn(labels[0]["id"], [be["id"] for be in by_id[r]["boundElements"]])

    def test_image_goes_in_files_map(self):
        s = Scene()
        s.image(0, 0, 40, 40, "data:image/svg+xml;base64,PHN2Zz48L3N2Zz4=")
        d = s.to_dict()
        self.assertEqual(len(d["files"]), 1)
        img = [e for e in d["elements"] if e["type"] == "image"][0]
        self.assertIn(img["fileId"], d["files"])

    def test_deterministic(self):
        self.assertEqual(Scene().dumps(), Scene().dumps())


class TestPresets(unittest.TestCase):
    def test_each_builtin_loads_and_builds(self):
        for name in ("default", "sketch", "clean"):
            with open(os.path.join(STYLES, f"{name}.json")) as fh:
                preset = json.load(fh)
            s = Scene.from_preset(preset)
            s.rect(0, 0, 120, 60, text="x", role="service")
            self.assertEqual(_validate_dict(s.to_dict()), [], f"{name} produced invalid scene")


class TestValidate(unittest.TestCase):
    def test_clean_file_passes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".excalidraw", delete=False) as f:
            Scene().rect(0, 0, 100, 50, text="ok")
            path = f.name
        Scene().dump(path)
        res = run_validate(path, strict=True)
        self.assertEqual(res.returncode, 0, res.stdout)
        os.unlink(path)

    def test_dangling_binding_is_error(self):
        s = Scene()
        a = s.rect(0, 0, 100, 50)
        b = s.rect(0, 200, 100, 50)
        s.arrow(a, b)
        d = s.to_dict()
        # break one binding target
        for e in d["elements"]:
            if e["type"] == "arrow":
                e["endBinding"]["elementId"] = "ghost"
        with tempfile.NamedTemporaryFile("w", suffix=".excalidraw", delete=False) as f:
            json.dump(d, f)
            path = f.name
        res = run_validate(path)
        self.assertEqual(res.returncode, 1)
        self.assertIn("missing", res.stdout)
        os.unlink(path)


@unittest.skipUnless(shutil.which("dot"), "Graphviz `dot` not installed")
class TestAutolayout(unittest.TestCase):
    def test_graph_to_excalidraw(self):
        graph = {
            "direction": "TB",
            "nodes": [
                {"id": "a", "label": "A", "role": "service", "group": "g1"},
                {"id": "b", "label": "B", "role": "database", "shape": "ellipse", "group": "g1"},
                {"id": "c", "label": "C", "role": "gateway"},
            ],
            "edges": [{"source": "a", "target": "b", "label": "e"},
                      {"source": "c", "target": "a"}],
        }
        with tempfile.TemporaryDirectory() as d:
            gpath = os.path.join(d, "graph.json")
            opath = os.path.join(d, "out.excalidraw")
            with open(gpath, "w") as fh:
                json.dump(graph, fh)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "autolayout.py"),
                                gpath, "-o", opath], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            with open(opath) as fh:
                doc = json.load(fh)
            self.assertEqual(doc["type"], "excalidraw")
            self.assertEqual(_validate_dict(doc), [])
            self.assertGreaterEqual(len([e for e in doc["elements"] if e["type"] == "arrow"]), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
