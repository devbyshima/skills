---
name: copycat
description: Port or rewrite an existing tool with the original as the oracle, then make it faster. Use when the user wants to rewrite something in another language, build a drop-in replacement, or match a tool's output exactly.
---

# Copycat

The original program is the **oracle**: whatever it outputs for an input is correct by definition. A port is done when it matches the oracle across a real-world corpus, which turns "rewrite X" into thousands of small checks an agent can grind through alone.

## Phase 1: Pin the oracle

- Pin the exact version (lockfile, container image or checksum) and the exact invocation (flags, env, working directory) in `oracle/run <case>`.
- Run it twice on one input and diff. Whatever differs (timestamps, absolute paths, hash ordering, temp names) becomes a rule in `normalize`. Noise found later masquerades as port bugs.

Done when two oracle runs on the same input match after `normalize`.

## Phase 2: Build the corpus

- Use real-world inputs: popular open-source projects in the domain, plus the user's own code if they want it covered. Real code reaches features toy examples skip.
- Split it into three tiers: **smoke** (seconds), **standard** (minutes), **full** (everything).
- Lay it out as `corpus/<tier>/<category>/<case>`, with a manifest recording each case's source, commit and size. The corpus is read-only to the porting agent.

Done when each tier exists and its oracle runtime is measured.

## Phase 3: Record goldens

Run the oracle over the corpus and capture everything observable: stdout, stderr, exit code, written files, diagnostics with positions and codes. Store the normalized results as **goldens**, with the oracle version in their manifest. Goldens change only with a deliberate oracle upgrade.

## Phase 4: Add mutations

Clean code rarely reaches error paths. `mutate --seed N` makes realistic edits to corpus inputs (delete a token, swap a type, drop an import, truncate a file), and the oracle's response to each becomes a golden in a **mutations** tier. Fixed seeds keep every case reproducible.

## Phase 5: Build the harness

Copy [scripts/verify.template.py](scripts/verify.template.py) to `./verify` and fill in its config block. It:

- records goldens from the oracle (`--record`)
- runs the port on each case, normalizes, and diffs against the goldens
- prints the pass rate overall and per category
- **clusters** failures by their first differing line and prints the biggest first, so the agent always knows what to fix next
- shards a tier across machines (`--shard 2/8`) and exits 0 only at 100%

### Completion criterion

- [ ] `./verify --tier smoke` has run against the port (show the output).
- [ ] Pointing `PORT_CMD` at the oracle itself scores 100%.
- [ ] A deliberately broken port scores below 100% and its cluster names the break.

## Phase 6: Climb

- Work the biggest cluster first; one fix usually clears many cases.
- The full-tier pass rate is a **ratchet**: a change that lowers it is reverted.
- Commit each gain with the pass rate in the message, and append each run to `PROGRESS.md`.
- Every input takes the same code path, and goldens stay as recorded. When the oracle itself looks wrong, record the case in `KNOWN_DIVERGENCES.md` for the user to rule on.
- When builds of the port take minutes, the build becomes the bottleneck. Give parallel agents a build queue or lock, and a snapshot of a warm build environment to start from.

Done when the full tier, mutations included, passes at 100%, or every remaining failure is recorded in `KNOWN_DIVERGENCES.md`.

## Phase 7: Speed

Once Phase 6 is done, read [SPEED.md](SPEED.md).

For an unattended multi-day run, call the Skill tool with "climb" for the goal prompt, gaming review and budget. This harness is its verifier.
