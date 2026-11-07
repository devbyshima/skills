---
name: unblock
description: Audit a long-running agent project and find the constraint slowing it down.
disable-model-invocation: true
argument-hint: "The project or run to audit (defaults to this repo)"
---

You are auditing a long-running agent project. In long runs the human's job is a manager's, not a reviewer's: remove what blocks the agents. Every system has one **constraint**, the step everything else queues behind. Find it and widen it, and the next one surfaces.

This audit is read-only. Recommend; the user decides, above all on anything that costs money or touches shared machines.

## Steps

1. Read the primary sources that exist:
   - git history: commits per day and per package, reverts, gaps
   - `PROGRESS.md` or equivalent: verifier score over time
   - `BLOCKERS.md`, TODOs, notes the agents left
   - build, CI and job records: queue wait against run time, timeouts, retries
   - system signals: OOM kills, full disks, rate limits, auth failures
   - `GOAL.md` and the verifier, to judge whether the climb still points at the destination

2. Measure, citing the source of every number. A number you cannot measure is reported as unknown.
   - **Rate**: score or commits per day, recent days against earlier ones. Climbing, flattening or oscillating?
   - **Wait ratio**: per iteration, time working against building, queued and verifying. Usually the headline.
   - **Capacity**: agents that can build or verify at once, against agents running.

3. Ask the agents, if the run has a channel to them (a check-in thread, a notes file they read): "What is slowing you down most? What would make you faster?" Compare their answers with the measurements.

4. Match the evidence to the candidates below and name the constraint.

5. Present the report, then stop.

## Candidates

- **Queue**: jobs wait before they start; agents sit idle. _Widen with_ more concurrent capacity, ideally on-demand machines that flex with load instead of hardware bought for peak.
- **Slow loop**: each build or `./verify` takes minutes. _Widen with_ a fast tier for the inner loop, incremental builds, and a snapshot of a warm build environment for each agent to start from.
- **Crashes**: OOM kills, reboots, runs restarted by hand. _Widen with_ a build queue or lock, and memory caps.
- **Flake**: the same change passes, then fails. _Widen with_ quarantined or fixed flaky cases.
- **Missing tool**: notes that say "can't", workarounds, skipped steps. _Widen with_ the GPU, display, tool or credential.
- **Misaligned verifier**: the score climbs while the result stays flat; edits near goldens; special-cased inputs. _Widen with_ a tighter verifier or a better reference.
- **Effort sink**: many rounds on one minor criterion. _Widen with_ a cap in `GOAL.md`.
- **Plateau**: the same failures for days. _Widen with_ a new approach, a split problem, or a revisited goal.

A constraint that is itself climbable (a compiler too slow to iterate on, say) can become its own project. List it under candidate projects; starting one is the user's call.

## Report

```markdown
# <project>: <date>
**Rate:** <now vs last check> (<trend>)
**Time:** working X% · building Y% · queued Z% (source: …)

## Constraint
**<name>**: evidence … · widen with … · expected gain … · cost …

## Next in line
1. …

## Candidate projects
<constraints worth climbing on their own>

## Warnings
<misalignment, effort sinks, burn rate against remaining budget>
```

Done when every number in the report cites its source and the constraint rests on measured evidence.
