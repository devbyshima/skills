# Agents

Skills for long-running agent work: setting a goal an agent can climb for days, porting a tool against its original, and finding what slows a run down.

## User-invoked

Run these by name.

- **[unblock](./unblock)** - `/unblock`: audit a long-running agent project, measure its rate and wait times, and name the one constraint slowing it down. Read-only; it recommends and the user decides.

## Model-invoked

Rich trigger phrasing so the agent can reach for them automatically (also usable on request).

- **[climb](./climb)** - Make a big goal climbable: pin the target, build a `./verify` command that scores it, close the ways to game the score, and write a `GOAL.md` an agent can run on for days.
- **[copycat](./copycat)** - Port or rewrite an existing tool with the original as the oracle: pin it, build a real-world corpus, record goldens, and diff the port against them with a clustering verifier, then make the port faster without losing parity.
