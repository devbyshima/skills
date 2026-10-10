#!/usr/bin/env python3
"""Smoke tests for the tasteful-icons generator (standard library only).

Run: python3 tests/test_scripts.py
Builds the default set and the example spec as SVG, checks the documents parse,
that ids are scoped per icon, and that palettes derive valid colors. PNG export is
exercised only when `rsvg-convert` is installed.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(SKILL_DIR, "scripts", "tasteful_icons.py")
SPEC = os.path.join(SKILL_DIR, "assets", "example-spec.json")
sys.path.insert(0, os.path.dirname(SCRIPT))

import tasteful_icons as ti  # noqa: E402

HEX = re.compile(r"^#[0-9A-F]{6}$")


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


class TestPalette(unittest.TestCase):
    def test_derived_palette_is_valid_hex(self):
        for base in ("#FF3B30", "#0444FF", "#2E2E2E", "#C6C6C6", "#FFFFFF", "#000000"):
            p = ti.palette(base)
            for field in ("top", "bottom", "mark", "pool", "shadow"):
                self.assertRegex(getattr(p, field), HEX, f"{base} {field}")

    def test_overrides_win(self):
        self.assertEqual(ti.palette("#FF3B30", pool="#123456").pool, "#123456")

    def test_tile_is_lighter_on_top(self):
        p = ti.palette("#0444FF")
        self.assertGreater(sum(ti._rgb(p.top)), sum(ti._rgb(p.bottom)))


class TestBuild(unittest.TestCase):
    def setUp(self):
        self.out = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.out, ignore_errors=True)

    def _svgs(self):
        d = os.path.join(self.out, "svg")
        out = {}
        for f in sorted(os.listdir(d)):
            with open(os.path.join(d, f)) as fh:
                out[f[:-4]] = fh.read()
        return out

    def test_list(self):
        r = run("list")
        self.assertEqual(r.returncode, 0, r.stderr)
        for name in ti.DEFAULT_SET:
            self.assertIn(name, r.stdout)

    def test_default_set_svg_only(self):
        r = run("build", self.out, "--sizes", "")
        self.assertEqual(r.returncode, 0, r.stderr)
        svgs = self._svgs()
        self.assertEqual(set(svgs), set(ti.DEFAULT_SET))
        for name, data in svgs.items():
            root = ET.fromstring(data)
            self.assertEqual(root.get("viewBox"), "0 0 512 512", name)
            ids = re.findall(r'id="([^"]+)"', data)
            self.assertTrue(ids, name)
            self.assertTrue(all(i.startswith(name + "-") for i in ids), f"unscoped id in {name}")
            for ref in re.findall(r"url\(#([^)]+)\)", data):
                self.assertIn(ref, ids, f"dangling reference #{ref} in {name}")

    def test_example_spec(self):
        r = run("build", self.out, "--spec", SPEC, "--sizes", "")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(SPEC) as f:
            names = {e["name"] for e in json.load(f)["icons"]}
        self.assertEqual(set(self._svgs()), names)

    def test_only_filter(self):
        r = run("build", self.out, "--only", "traffic,computer", "--sizes", "")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(set(self._svgs()), {"traffic", "computer"})

    def test_python_api_custom_glyph(self):
        pal = ti.palette("#FF2D55")
        icons = {"health": ti.glass_icon("Health", pal, ti.circle(256, 258, 160),
                                         marks=[{"d": "M256 190V326M188 258H324", "stroke": 34}])}
        ti.write_icons(icons, self.out, sizes=())
        ET.fromstring(self._svgs()["health"])

    @unittest.skipUnless(shutil.which("rsvg-convert"), "rsvg-convert not installed")
    def test_png_export(self):
        r = run("build", self.out, "--only", "traffic", "--sizes", "128", "--no-sheet")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(self.out, "png@128", "traffic.png"), "rb") as f:
            head = f.read(24)
        self.assertEqual(head[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(int.from_bytes(head[16:20], "big"), 128)


if __name__ == "__main__":
    unittest.main(verbosity=2)
