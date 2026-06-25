# Contributing

This repo is a collection of [Agent Skills](https://agentskills.io). Each skill is a self-contained folder discovered by the [`skills` CLI](https://github.com/vercel-labs/skills).

## Add a skill

1. **Pick (or create) a category** under `skills/` — e.g. `skills/diagramming/`, `skills/writing/`, `skills/devops/`. Categories are just folders; group by what the skill *does*.

2. **Create the skill folder** with at least a `SKILL.md`:

   ```
   skills/<category>/<skill-name>/
     SKILL.md          # required
     scripts/          # optional — executable helpers (python, node, …)
     references/       # optional — docs the agent reads on demand
     styles/ · data/ · assets/   # optional
   ```

   The `skills` CLI walks `skills/<category>/<name>/SKILL.md` (catalog layout) as well as the flat `skills/<name>/SKILL.md` layout, so either nesting works and stays installable.

3. **Write `SKILL.md`** with YAML frontmatter — `name` and `description` are required (the description is the trigger the agent matches on, so make it specific). Keep the body lean and push detail into `references/` (progressive disclosure: the agent only reads references when needed).

   ```markdown
   ---
   name: my-skill
   description: Use when the user wants to …  (be specific — this is the trigger)
   license: MIT
   ---

   # My Skill

   ## Overview
   …
   ```

4. **Keep it self-contained.** Scripts should resolve paths relative to their own location (`__dirname` / `os.path.dirname(__file__)`) so the skill works wherever it's installed. Heavy/optional dependencies should degrade gracefully and be documented.

5. **Test it.** If the skill ships scripts, add a `tests/` folder. CI (`.github/workflows/test.yml`) runs every `skills/**/tests/test_scripts.py`.

6. **Register it in three places:**
   - [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json) → add the skill path to the `skills` array
   - `skills/<category>/README.md` → add it under **User-invoked** or **Model-invoked**
   - root [`README.md`](README.md) → add a row to the catalog table

   Then `bash scripts/list-skills.sh` to confirm it's discovered.

## Conventions

- One concern per skill; name folders in `kebab-case`.
- Prefer the standard library / tools the user already has; document any extra dependency and make it optional where possible.
- Don't commit `node_modules/`, build caches, or lockfiles (see `.gitignore`).
- If a skill is adapted from another project, keep the original license/attribution in the skill folder.
- **Retire** a skill by moving it under `skills/deprecated/` (with a note) rather than deleting it.

## Install a skill while developing

The `skills` CLI accepts a local path, so you can test discovery before pushing:

```bash
npx skills add /path/to/this/repo            # discovers all skills
npx skills add /path/to/this/repo --skill my-skill
```

## Releasing

Installs read the repo at `HEAD`, so a release is only for tagging a snapshot. Push a `v*` tag and `.github/workflows/release.yml` runs the tests and publishes a GitHub Release with auto-generated notes:

```bash
git tag v0.2.0
git push origin v0.2.0
```
