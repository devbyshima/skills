#!/usr/bin/env python3
"""Differential verifier. Copy to ./verify (repo root) and fill in CONFIG.

The oracle is always right. This runs the port over the corpus, diffs its
normalized output against the oracle's goldens, and prints the pass rate plus
the biggest failure clusters, so the next fix is always obvious.

Layout
  corpus/<tier>/<category>/<case>            one file or directory per case
  goldens/<tier>/<category>/<case>.out       written by --record

Usage
  ./verify --record --tier smoke     run the ORACLE, write goldens
  ./verify --tier smoke              run the PORT, diff against goldens
  ./verify --tier full --shard 2/8   run one eighth of the full tier
"""
import argparse
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ---- CONFIG ----------------------------------------------------------------
ORACLE_CMD = ["oracle/run"]  # called as ORACLE_CMD + [case]
PORT_CMD = ["./target/release/port"]  # called as PORT_CMD + [case]
TIMEOUT_S = 120
# Each command must print everything observable (including files it writes)
# to stdout or stderr, so the diff sees it.


def normalize(text: str, case: Path) -> str:
    """Strip anything that differs between two runs of the same program."""
    text = text.replace(str(case.resolve()), "<CASE>").replace(str(case), "<CASE>")
    text = text.replace(os.getcwd(), "<CWD>")
    # Add rules found in copycat Phase 1, e.g.:
    # text = re.sub(r"\d+(\.\d+)?ms", "<MS>", text)
    return text
# -----------------------------------------------------------------------------


def run(cmd, case):
    try:
        p = subprocess.run(cmd + [str(case)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=TIMEOUT_S)
        raw = f"== exit {p.returncode} ==\n== stdout ==\n{p.stdout}\n== stderr ==\n{p.stderr}"
    except subprocess.TimeoutExpired:
        raw = f"== timeout after {TIMEOUT_S}s =="
    return normalize(raw, case)


def list_cases(tier, shard):
    base = Path("corpus") / tier
    if not base.is_dir():
        sys.exit(f"no corpus at {base}")
    found = sorted(c for cat in base.iterdir() if cat.is_dir() for c in cat.iterdir())
    i, n = shard
    return [c for k, c in enumerate(found) if k % n == i - 1]


def golden_path(case):
    return Path("goldens", *case.parts[1:-1], case.name + ".out")


def first_diff(expected, actual):
    e, a = expected.splitlines(), actual.splitlines()
    for n in range(max(len(e), len(a))):
        el = e[n] if n < len(e) else "<EOF>"
        al = a[n] if n < len(a) else "<EOF>"
        if el != al:
            return n + 1, el[:120], al[:120]
    return 0, "", ""


def main():
    ap = argparse.ArgumentParser(description="Diff the port against the oracle's goldens.")
    ap.add_argument("--tier", default="smoke")
    ap.add_argument("--shard", default="1/1", help="i/n: run every n-th case starting at i")
    ap.add_argument("--record", action="store_true", help="run the oracle and write goldens")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--clusters", type=int, default=10, help="how many clusters to print")
    args = ap.parse_args()

    os.chdir(Path(__file__).resolve().parent)
    shard = tuple(int(x) for x in args.shard.split("/"))
    cases = list_cases(args.tier, shard)
    if not cases:
        sys.exit(f"no cases in tier {args.tier} shard {args.shard}")

    cmd = ORACLE_CMD if args.record else PORT_CMD
    with ThreadPoolExecutor(args.jobs) as pool:
        outputs = list(pool.map(lambda c: run(cmd, c), cases))

    if args.record:
        for case, out in zip(cases, outputs):
            g = golden_path(case)
            g.parent.mkdir(parents=True, exist_ok=True)
            g.write_text(out, encoding="utf-8")
        print(f"recorded {len(cases)} goldens for tier {args.tier}")
        return 0

    per_cat = defaultdict(lambda: [0, 0])
    clusters, example = Counter(), {}
    for case, out in zip(cases, outputs):
        g = golden_path(case)
        expected = g.read_text(encoding="utf-8") if g.exists() else None
        ok = expected == out
        per_cat[case.parent.name][0] += ok
        per_cat[case.parent.name][1] += 1
        if ok:
            continue
        if expected is None:
            key, where = "missing golden (run --record)", ""
        else:
            line, exp, got = first_diff(expected, out)
            key = re.sub(r"\d+", "#", f"expected {exp!r}, got {got!r}")
            where = f" (line {line})"
        clusters[key] += 1
        example.setdefault(key, f"{case}{where}")

    passed = sum(p for p, _ in per_cat.values())
    print(f"tier {args.tier} shard {args.shard}: {passed}/{len(cases)} passed "
          f"({100 * passed / len(cases):.1f}%)")
    for cat, (p, t) in sorted(per_cat.items()):
        print(f"  {cat:<28} {p}/{t}")
    if clusters:
        print("\nbiggest failure clusters (fix from the top):")
        for key, n in clusters.most_common(args.clusters):
            print(f"  {n:>5}x  {key}\n         e.g. {example[key]}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
