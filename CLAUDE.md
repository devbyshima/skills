# CLAUDE.md

Instructions for an agent working **in this repo** (it's a collection of Agent Skills, not an app).

## Layout

```
skills/<category>/<name>/SKILL.md   # each skill — self-contained folder
.claude-plugin/plugin.json          # plugin manifest (lists every skill path)
scripts/list-skills.sh              # list all skills
scripts/link-skills.sh              # symlink skills into ~/.claude/skills & ~/.agents/skills for local dev
```

## Adding or changing a skill

1. Put it at `skills/<category>/<name>/` with a `SKILL.md` (`name` + `description` frontmatter required; the description is the trigger — make it specific). Push detail into `references/`; keep the body lean (progressive disclosure).
2. Keep it **self-contained**: scripts resolve paths from their own location (`__dirname` / `os.path.dirname(__file__)`), heavy deps are optional and degrade gracefully. Add a `tests/` folder if it ships scripts.
3. Wire it up in **three places** (all are checked by reviewers/CI):
   - `.claude-plugin/plugin.json` → add the skill path to the `skills` array
   - `skills/<category>/README.md` → add it under User-invoked or Model-invoked
   - root `README.md` → add a row to the catalog table
4. `bash scripts/list-skills.sh` to sanity-check discovery; run the skill's tests (`python3 skills/<category>/<name>/tests/test_scripts.py`).

## Conventions

- `kebab-case` folder names; one concern per skill.
- Don't commit `node_modules/`, `scripts/.cache/`, or lockfiles (see `.gitignore`).
- Retire a skill by moving it under `skills/deprecated/` rather than deleting it.
- If a skill is adapted from another project, keep that project's license/attribution in the skill folder.

See [CONTRIBUTING.md](CONTRIBUTING.md) for the human-facing version.
