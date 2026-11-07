#!/usr/bin/env python3
"""Differential verifier. Copy to ./verify (repo root) and fill in CONFIG.

The oracle is always right. This runs the port over the corpus, diffs its
normalized output against the oracle's goldens, and prints the pass rate plus
the biggest failure clusters, so the next fix is always obvious.

Layout
  corpus/<tier>/<category>/<case>            one file or directory per case
  goldens/<tier>/<category>/<case>.out       written by --record
  goldens/<tier>.sha256                      seal over the tier, written by --record

Usage
  ./verify --record --tier smoke     run the ORACLE, write goldens and the seal
  ./verify --tier smoke              run the PORT, diff against goldens
  ./verify --tier full --shard 2/8   run one eighth of the full tier

The seal holds a hash of every corpus file and golden in the tier. Scoring
refuses to run (exit 2) when either no longer matches it, and every score line
ends with the seal's digest, so a re-record shows up in PROGRESS.md.
"""
import argparse
import hashlib
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

CANNOT_RUN = "== cannot run"
IGNORED = {".DS_Store"}


def run(cmd, case):
    try:
        p = subprocess.run(cmd + [str(case)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=TIMEOUT_S)
        raw = f"== exit {p.returncode} ==\n== stdout ==\n{p.stdout}\n== stderr ==\n{p.stderr}"
    except subprocess.TimeoutExpired:
        raw = f"== timeout after {TIMEOUT_S}s =="
    except OSError as e:  # not built yet, not executable: a failing case, not a crash
        raw = f"{CANNOT_RUN} {cmd[0]}: {e.strerror} =="
    return normalize(raw, case)


def list_cases(tier):
    base = Path("corpus") / tier
    if not base.is_dir():
        sys.exit(f"no corpus at {base}")
    return sorted(c for cat in base.iterdir() if cat.is_dir()
                  for c in cat.iterdir() if c.name not in IGNORED)


def take_shard(cases, shard):
    i, n = shard
    return [c for k, c in enumerate(cases) if k % n == i - 1]


def golden_path(case):
    return Path("goldens", *case.parts[1:-1], case.name + ".out")


def seal_path(tier):
    return Path("goldens", f"{tier}.sha256")


def case_files(case):
    """A case's corpus files, then its golden."""
    if case.is_file():
        files = [case]
    else:
        files = sorted(p for p in case.rglob("*") if p.is_file() and p.name not in IGNORED)
    return files + [golden_path(case)]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_seal(tier, cases):
    lines = [f"{sha256(p)}  {p.as_posix()}" for c in cases for p in case_files(c) if p.exists()]
    seal_path(tier).parent.mkdir(parents=True, exist_ok=True)
    seal_path(tier).write_text("\n".join(lines) + "\n", encoding="utf-8")


def check_seal(tier, all_cases, cases):
    """List what changed since the seal was written (empty when nothing did)."""
    path = seal_path(tier)
    if not path.exists():
        return [f"no seal at {path}: run --record"]
    sealed = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, _, name = line.partition("  ")
        sealed[name] = digest
    present = {p.as_posix() for c in all_cases for p in case_files(c)}
    problems = [f"removed: {name}" for name in sorted(sealed.keys() - present)]
    for case in cases:
        for p in case_files(case):
            name = p.as_posix()
            if name not in sealed:
                if p.exists():  # a golden that was never recorded is scored as missing
                    problems.append(f"not sealed: {name}")
            elif not p.exists():
                problems.append(f"removed: {name}")
            elif sha256(p) != sealed[name]:
                problems.append(f"changed: {name}")
    return problems


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
    ap.add_argument("--record", action="store_true", help="run the oracle, write goldens and the seal")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--clusters", type=int, default=10, help="how many clusters to print")
    args = ap.parse_args()

    os.chdir(Path(__file__).resolve().parent)
    shard = tuple(int(x) for x in args.shard.split("/"))
    all_cases = list_cases(args.tier)
    cases = take_shard(all_cases, shard)
    if not cases:
        sys.exit(f"no cases in tier {args.tier} shard {args.shard}")

    if not args.record:
        problems = check_seal(args.tier, all_cases, cases)
        if problems:
            print(f"refusing to score tier {args.tier}: corpus or goldens differ from the seal")
            for p in problems[:20]:
                print(f"  {p}")
            if len(problems) > 20:
                print(f"  ... and {len(problems) - 20} more")
            print("Restore them from version control. Re-recording (--record) is the user's call.")
            return 2

    cmd = ORACLE_CMD if args.record else PORT_CMD
    with ThreadPoolExecutor(args.jobs) as pool:
        outputs = list(pool.map(lambda c: run(cmd, c), cases))

    if args.record:
        failed = [out for out in outputs if out.startswith(CANNOT_RUN)]
        if failed:
            sys.exit(f"the oracle did not start, nothing recorded: {failed[0]}")
        for case, out in zip(cases, outputs):
            g = golden_path(case)
            g.parent.mkdir(parents=True, exist_ok=True)
            g.write_text(out, encoding="utf-8")
        write_seal(args.tier, all_cases)
        print(f"recorded {len(cases)} goldens for tier {args.tier}, "
              f"seal {sha256(seal_path(args.tier))[:12]}")
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
          f"({100 * passed / len(cases):.1f}%), seal {sha256(seal_path(args.tier))[:12]}")
    for cat, (p, t) in sorted(per_cat.items()):
        print(f"  {cat:<28} {p}/{t}")
    if clusters:
        print("\nbiggest failure clusters (fix from the top):")
        for key, n in clusters.most_common(args.clusters):
            print(f"  {n:>5}x  {key}\n         e.g. {example[key]}")
    return 0 if passed == len(cases) else 1


if __name__ == "__main__":
    sys.exit(main())
