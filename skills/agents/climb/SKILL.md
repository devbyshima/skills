---
name: climb
description: Make a big goal climbable, with one verifier command and a goal prompt an agent can run on for days. Use when the user wants a long or overnight run, a hill climb, or says "don't stop until".
---

# Climb

A goal is **climbable** when one command scores it. Agents are trained on tasks a program can check, so a climbable goal keeps an agent working for days: change, run the **verifier**, read the score, change again. A goal without one ends the moment the work _looks_ done.

This skill builds the setup. Starting the run is the user's call.

## Phase 1: Pin the target

Settle with the user, in one round:

- **Destination**: what exists at the end, and the **reference** it must match (an existing tool, a spec, footage of a game).
- **Scope**: what the run leaves alone.
- **Budget**: wall-clock and spend limits, and what happens when one is hit.

Tedium is welcome. A 100,000-file port is miserable for a human and ideal for an agent; ambiguity is what stalls one.

Done when destination, reference, scope and budget are each one sentence the user has confirmed.

## Phase 2: Build the verifier

**This is the skill.** With a verifier the agent can run alone, the rest is waiting. Without one, the run drifts.

If the project already has one, test it against the completion criterion below and move on. Otherwise reach for the strongest kind that fits, in this order:

1. **Oracle**: an existing tool already produces the right answer. Record its outputs over a corpus and require a match. For ports and drop-in replacements, read `../copycat/SKILL.md` (relative to this skill's directory), follow its Phases 1 to 5, then return here.
2. **Mutations**: inject errors into oracle inputs so failure paths get scored too.
3. **Threshold**: a measured target, such as "2x faster than baseline, median of 5 runs".
4. **Properties**: invariants and fuzzing when no oracle exists (round-trips, idempotence, no crashes on generated input).
5. **Judge panel**: for looks and feel. Read [JUDGE-PANEL.md](JUDGE-PANEL.md) before building one.
6. **Human**: last resort, since the loop then moves at the human's pace. Drive them with a script that prompts each check and captures the answer, so the loop stays structured.

Wrap it as `./verify`: it prints a score and exits 0 only at the destination. When a full run takes more than about ten minutes, add `./verify --fast` for the inner loop and keep the full run as the gate.

### Completion criterion

- [ ] `./verify` has run against the current state (show the output).
- [ ] The reference scores as passing, and a deliberately broken build scores as failing.
- [ ] Goldens, corpus and rubrics sit outside the agent's write scope.
- [ ] Full and fast runtimes are measured and written down.

## Phase 3: Find the gaming paths

The agent climbs exactly what the verifier rewards. List every way the score could rise while the destination stays as far away: hard-coded outputs, special-cased inputs, edited goldens, a judge that rewards brightness. Close each one, or write it into the goal prompt as a rule.

Then check the reference is the one the user means. A run pointed at the wrong reference climbs the wrong hill for days (one game clone kept brightening its scenes until its reference switched from Skate 3 to Skate 1).

Done when every gaming path on the list is closed or named in a rule.

## Phase 4: Equip the agent

List what the work needs: GPU, display, headless browser, Blender, build machines, RAM, credentials. Provide each one now. When parallel agents share machines, add a build queue or lock so they cannot exhaust memory.

Done when every item is provided, or recorded in the hand-off as a known **blocker**.

## Phase 5: Write the goal prompt

Write `GOAL.md`:

```markdown
# Goal
<What to build, and the reference it must match.>

## Done when
`./verify` exits 0.

## Rules
- Goldens, corpus and rubrics are read-only. Every input takes the same code path.
- After each `./verify` run, append to PROGRESS.md: time, score, what changed.
- Commit each gain with the score in the message. The full-run score is a ratchet: a change that lowers it is reverted.
- After 3 failed approaches to one failure, record it in BLOCKERS.md (what was tried, what is needed) and move to the next.

## Scope
<What the run leaves alone.>

## Budget
At <limit>, stop and summarise in PROGRESS.md.
```

Stage the ambition. Reach the destination first, then raise it ("now 2x faster, `./verify` still green"), keeping each earlier verifier as a guardrail.

## Hand-off

Give the user: the verifier kind and why, the Phase 2 checklist output, each gaming path and how it is closed, known blockers, and the exact command or prompt that starts the run.
