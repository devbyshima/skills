#!/usr/bin/env python3
"""Smoke tests for copycat's verify template (standard library only).

Run: python3 tests/test_scripts.py
Copies scripts/verify.template.py into a temp project with a tiny corpus and
toy oracle and port commands, then checks recording, a passing port, a broken
port, missing goldens, sharding, the seal, and commands that cannot start.
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

    def write_verify(self, port_script=None, oracle_script="oracle.py"):
        """None keeps the template's command, which points at a binary that does not exist."""
        with open(TEMPLATE) as f:
            src = f.read()
        for old, script in (
            ('ORACLE_CMD = ["oracle/run"]', oracle_script),
            ('PORT_CMD = ["./target/release/port"]', port_script),
        ):
            self.assertIn(old, src, "template config block changed; update this test")
            if script:
                src = src.replace(old, f'{old.split(" =")[0]} = [sys.executable, "{script}"]')
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
        self.verify("--record", "--tier", "smoke", "--shard", "1/2")
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 1, run.stdout)
        self.assertIn("1x  missing golden", run.stdout)

    def test_shards_split_the_tier(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        first = self.verify("--tier", "smoke", "--shard", "1/2")
        second = self.verify("--tier", "smoke", "--shard", "2/2")
        self.assertIn("2/2 passed", first.stdout)
        self.assertIn("1/1 passed", second.stdout)

    def path(self, *parts):
        return os.path.join(self.root, *parts)

    def assert_refuses(self, *expected):
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 2, run.stdout + run.stderr)
        self.assertIn("refusing to score", run.stdout)
        self.assertNotIn("passed", run.stdout)
        for text in expected:
            self.assertIn(text, run.stdout)

    def test_unrecorded_tier_refuses_to_score(self):
        self.write_verify("oracle.py")
        self.assert_refuses("no seal at goldens/smoke.sha256")

    def test_score_line_shows_seal_digest(self):
        self.write_verify("oracle.py")
        rec = self.verify("--record", "--tier", "smoke")
        digest = rec.stdout.strip().rsplit("seal ", 1)[1]
        self.assertRegex(digest, r"^[0-9a-f]{12}$")
        self.assertIn(f"(100.0%), seal {digest}", self.verify("--tier", "smoke").stdout)

    def test_edited_golden_refuses_to_score(self):
        # The gaming move: make a failing case's golden match the broken port.
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        self.write_verify("broken.py")
        golden = self.path("goldens", "smoke", "alpha", "two.txt.out")
        with open(golden) as f:
            text = f.read()
        with open(golden, "w") as f:
            f.write(text.replace("BANANA", "banana"))
        self.assert_refuses("changed: goldens/smoke/alpha/two.txt.out")

    def test_edited_corpus_refuses_to_score(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        with open(self.path("corpus", "smoke", "beta", "three.txt"), "w") as f:
            f.write("easy")
        self.assert_refuses("changed: corpus/smoke/beta/three.txt")

    def test_added_case_refuses_to_score(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        with open(self.path("corpus", "smoke", "beta", "four.txt"), "w") as f:
            f.write("date")
        self.assert_refuses("not sealed: corpus/smoke/beta/four.txt")

    def test_removed_case_refuses_to_score(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        os.remove(self.path("corpus", "smoke", "alpha", "two.txt"))
        self.assert_refuses("removed: corpus/smoke/alpha/two.txt",
                            "removed: goldens/smoke/alpha/two.txt.out")

    def test_finder_metadata_is_ignored(self):
        self.write_verify("oracle.py")
        self.verify("--record", "--tier", "smoke")
        open(self.path("corpus", "smoke", "alpha", ".DS_Store"), "w").close()
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertIn("3/3 passed", run.stdout)

    def test_unbuilt_port_scores_zero(self):
        self.write_verify(None)
        self.verify("--record", "--tier", "smoke")
        run = self.verify("--tier", "smoke")
        self.assertEqual(run.returncode, 1, run.stdout + run.stderr)
        self.assertNotIn("Traceback", run.stderr)
        self.assertIn("0/3 passed", run.stdout)
        self.assertIn("3x  expected '== exit # ==', got '== cannot run ./target/release/port:", run.stdout)

    def test_missing_oracle_records_nothing(self):
        self.write_verify("oracle.py", oracle_script=None)
        rec = self.verify("--record", "--tier", "smoke")
        self.assertNotEqual(rec.returncode, 0)
        self.assertIn("the oracle did not start", rec.stderr)
        self.assertFalse(os.path.exists(self.path("goldens")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
