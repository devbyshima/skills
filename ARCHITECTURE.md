# The Skills Architecture

<https://github.com/devbyshima/skills>

## Introduction

Skills is a collection of Agent Skills for handing an agent work that takes hours or days. Each skill is a folder with a `SKILL.md`: YAML frontmatter whose `description` is the trigger an agent harness matches on, and a body of phases the agent follows. They install with `npx skills@latest add devbyshima/skills`, or as a Claude Code plugin through `.claude-plugin/plugin.json`.

There are three skills, all under `skills/agents/`. `climb` turns a big goal into one `./verify` command and a `GOAL.md` an agent can run on for days; for ports it hands over to `copycat`, which makes the original program the oracle and ships the only code in the repository, a verifier template and its tests. `unblock` is run by name on a long run to find the one constraint slowing it down. CI runs those tests and publishes a release for each tag; nothing is built.

## What Skills is NOT

- Skills is not an app or a library. It is a collection of Agent Skills: Markdown, with one Python template.
- The skills do not start or steer a run on their own. `climb` builds the setup and starting the run is the user's call; `unblock` is read-only, it recommends and the user decides.
- A release is not what installs read. Installs read the repository at `HEAD`; a tag only marks a snapshot.

## Major Components

### Skills [MARKDOWN]

#### [skills/agents](skills/agents)

The one category. Its `README.md` lists each skill under User-invoked or Model-invoked.

#### [skills/agents/climb](skills/agents/climb)

`SKILL.md`: pin the target, build the verifier (oracle, mutations, threshold, properties, judge panel, human, in that order), find the gaming paths, equip the agent, write `GOAL.md`, then the hand-off. `JUDGE-PANEL.md` is the verifier for looks and feel.

#### [skills/agents/copycat](skills/agents/copycat)

`SKILL.md`: pin the oracle, build a tiered corpus (smoke, standard, full), record goldens, add mutations, build the harness from the template, climb. `SPEED.md` makes the port faster once parity holds.

#### [skills/agents/unblock](skills/agents/unblock)

`SKILL.md` with `disable-model-invocation: true`, so it runs only as `/unblock`: read the primary sources, measure rate, wait ratio and capacity, match the evidence to the candidate constraints, and print the report.

### Verifier [PYTHON]

#### [skills/agents/copycat/scripts](skills/agents/copycat/scripts)

`verify.template.py`, copied to a project as `./verify`. A config block (`ORACLE_CMD`, `PORT_CMD`, `TIMEOUT_S`, `normalize`), `--record` to write goldens and seal the tier (`write_seal`), `check_seal` before scoring, `--tier`, `--shard` and `--jobs`, and failures clustered by `first_diff`. Standard library only.

#### [skills/agents/copycat/tests](skills/agents/copycat/tests)

`test_scripts.py` (`TestVerifyTemplate`, unittest): copies the template into a temporary project with a toy oracle and port, then checks recording, passing and broken ports, missing goldens, sharding, the seal and commands that cannot start.

### Plugin [JSON]

#### [.claude-plugin](.claude-plugin)

`plugin.json`: the `devbyshima-skills` plugin, its version and licence, and the `skills` array naming every skill's folder.

## External Pieces

- **Agent Skills** ([agentskills.io](https://agentskills.io)): the `SKILL.md` format with `name` and `description` frontmatter.
- **The `skills` CLI** (vercel-labs/skills): finds `skills/<category>/<name>/SKILL.md` and installs from the repository; the README's badge is from skills.sh.
- **Claude Code plugins:** `.claude-plugin/plugin.json`.
- **GitHub Actions:** `actions/checkout`, `actions/setup-python` and `softprops/action-gh-release`.
- No third-party code is bundled. A skill adapted from another project keeps that project's licence in its folder.

## Tooling

`scripts/list-skills.sh` prints every skill's name and description; `scripts/link-skills.sh` symlinks every skill into `~/.claude/skills` and `~/.agents/skills`, so a `git pull` updates them. Both skip `skills/deprecated/`. `.github/workflows/test.yml` runs every `skills/**/tests/test_scripts.py` on pushes to `main` and on pull requests; `.github/workflows/release.yml` runs them again and publishes a release on a `v*` tag.

# Workflows

## What does a climb look like?

1. The user asks for a long or overnight run, and the agent loads `climb` by its description.
2. Phase 1 settles the destination, reference, scope and budget with the user, one sentence each.
3. Phase 2 builds `./verify`. For a port it follows `../copycat/SKILL.md` Phases 1 to 5; otherwise it takes the strongest verifier that fits, down to a judge panel (`JUDGE-PANEL.md`) or a human.
4. Phases 3 to 5 close the gaming paths, provide what the agent needs and write `GOAL.md`. The hand-off gives the user the command that starts the run.

## What does a port look like?

1. `copycat` pins the oracle as `oracle/run <case>` and writes `normalize` rules until two oracle runs match.
2. It lays out `corpus/<tier>/<category>/<case>` and copies `scripts/verify.template.py` to `./verify`.
3. `./verify --record --tier smoke` runs the oracle, writes `goldens/` and seals the tier.
4. `./verify --tier smoke` runs the port, prints the pass rate overall and per category and the biggest failure clusters, and exits 0 only at 100%. The agent works the biggest cluster first, then `SPEED.md`.

## What does the Development flow look like?

A new skill goes in `skills/<category>/<name>/` with a `SKILL.md`, and is registered in `.claude-plugin/plugin.json`, the category's `README.md` and the root README's Reference list. `bash scripts/list-skills.sh` checks it is found, and a skill that ships scripts gets a `tests/test_scripts.py`. The steps are in [CONTRIBUTING.md](CONTRIBUTING.md) and, for agents, [CLAUDE.md](CLAUDE.md).

## What does the Release flow look like?

Changes people would notice are noted under `Unreleased` in [CHANGELOG.md](CHANGELOG.md) as they land. A release dates that section and bumps `plugin.json`'s `version` in one pull request; then a `v*` tag on the merge commit makes `release.yml` run the skill tests and publish a GitHub Release with generated notes. Installs keep reading `HEAD`, so a release only tags a snapshot.

# Invariants

Things the repository relies on that are easy to break:

- **Registration:** a skill is wired in three places, `plugin.json`'s `skills`, its category README and the root README. One left out of `plugin.json` is missing from the Claude Code plugin.
- **Frontmatter:** every `SKILL.md` has `name` and `description`, and the description is the trigger. `unblock`'s `disable-model-invocation: true` keeps it to `/unblock`.
- **Self-contained:** scripts resolve paths from their own location, and skills refer to each other by relative path (`climb` reads `../copycat/SKILL.md`), so they work wherever they are installed.
- **The seal:** the verifier refuses to score (exit 2) when the corpus or goldens differ from the seal, and every score line ends with its digest. `test_scripts.py` holds that, so change the template and its tests together.
- **Test location:** CI finds tests only at `skills/**/tests/test_scripts.py`.
- **Retiring:** a skill is retired by moving it under `skills/deprecated/`, which both scripts skip.
- **Kept out of git:** `node_modules/`, `scripts/.cache/` and lockfiles (`.gitignore`).

## License

Skills is source-available under the [PolyForm Noncommercial License 1.0.0](LICENSE): free for non-commercial use.
