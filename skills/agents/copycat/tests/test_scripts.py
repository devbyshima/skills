#!/usr/bin/env python3
"""Smoke tests for copycat's verify template (standard library only).

Run: python3 tests/test_scripts.py
Copies scripts/verify.template.py into a temp project with a tiny corpus and
toy oracle and port commands, then checks recording, a passing port, a broken
port, missing goldens and sharding.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(SKILL_DIR, "scripts", "verify.template.py")

ORACLE = "import sys; print(open(sys.argv[1]).read().upper(), end='')\n"
# Breaks only on cases whose text contains a "b".
BROKEN = (
    "import sys\n"
    "t = open(sys.argv[1]).read()\n"
    "print(t if 'b' in t else t.upper(), end='')\n"
)
CASES = {
    "alpha/one.txt": "apple",
    "alpha/two.txt": "banana",
    "beta/three.txt": "cherry",
}


class TestVerifyTemplate(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        for rel, text in CASES.items():
            path = os.path.join(self.root, "corpus", "smoke", rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as f:
                f.write(text)
        for name, src in (("oracle.py", ORACLE), ("broken.py", BROKEN)):
            with open(os.path.join(self.root, name), "w") as f:
                f.write(src)

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def write_verify(self, port_script):
        with open(TEMPLATE) as f:
            src = f.read()
        for old, new in (
            ('ORACLE_CMD = ["oracle/run"]', 'ORACLE_CMD = [sys.executable, "oracle.py"]'),
            ('PORT_CMD = ["./target/release/port"]', f'PORT_CMD = [sys.executable, "{port_script}"]'),
        ):
            self.assertIn(old, src, "template config block changed; update this test")
            src = src.replace(old, new)
        with open(os.path.join(self.root, "verify"), "w") as f:
            f.write(src)

    def verify(self, *args):
        # Run from elsewhere: the template must chdir to its own folder.
        return subprocess.run([sys.executable, os.path.join(self.root, "verify"), *args],
                              capture_output=True, text=True, cwd=tempfile.gettempdir())

    def test_oracle_as_port_scores_100(self):
        self.write_verify("oracle.py")
        rec = self.verify("--record", "--tier", "smoke")
        self.assertEqual(rec.returncode, 0, rec.stderr)
        self.assertIn("recorded 3 goldens", rec.stdout)
        self.assertTrue(os.path.exists(os.path.join(self.root, "goldens", "smoke", "alpha", "one.txt.out")))
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        self.assertIn("3/3 passed (100.0%)", run.stdout)

    def test_broken_port_fails_and_clusters(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        self.write_verify("broken.py")
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 1)
        self.assertIn("2/3 passed", run.stdout)
        self.assertIn("biggest failure clusters", run.stdout)
        self.assertIn("'BANANA'", run.stdout)
        self.assertIn("two.txt", run.stdout)

    def test_missing_goldens_are_reported(self):
        self.write_verify("oracle.py")
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 1)
        self.assertIn("3x  missing golden", run.stdout)

    def test_shards_split_the_tier(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        first = self.verify("--tier", "smoke", "--shard", "1/2")
        second = self.verify("--tier", "smoke", "--shard", "2/2")
        self.assertIn("2/2 passed", first.stdout)
        self.assertIn("1/1 passed", second.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
