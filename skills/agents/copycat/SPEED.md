# Speed

Parity holds. Now the port gets faster than the oracle without giving any parity back.

- Set the target as a ratio on the standard tier, such as "2x faster than the oracle".
- `./bench` runs port and oracle on the same machine, at least 5 times each, and reports medians and spread. A difference inside the spread is noise.
- `./verify --tier full` stays at 100% after every optimization. Speed is the second **ratchet**; parity is the first and outranks it.
- **Profile first.** The profile picks the next target.
- When outputs differ by design (binaries from a new compiler, say), parity becomes behavioural: the output passes the project's own test suite, and its runtime stays within a stated margin of the oracle's output (for example, within 20%).

Done when the standard-tier median beats the target and full-tier parity holds.
