# Changelog

Every change people using these skills would notice, newest first. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Installs read the repository at `HEAD`, so a version marks a snapshot rather than what gets installed. The plugin's `version` in `.claude-plugin/plugin.json` matches the latest one. How to cut a release is in [CONTRIBUTING.md](CONTRIBUTING.md#releasing).

## [Unreleased]

## [0.3.0] - 2026-11-13

### Added

- `ARCHITECTURE.md`, a map of the repository: each skill, the verifier, the plugin and the rules they rely on.

### Changed

- copycat's verifier seals each tier when it records goldens: a hash of every corpus file and golden in it. Scoring refuses to run when any of them was changed, added or removed, and each score line ends with the seal's digest, so a re-record shows up in `PROGRESS.md`. climb and copycat explain the seal, and copycat's checklist asks for a test that an edited golden is refused.
- copycat scores a port command that cannot start as a failing case instead of crashing the run, and `--record` stops without writing goldens when the oracle cannot start.
- The README opens with what the skills are for, lists each one in a Reference list, and has a banner for light and dark mode.

### Removed

- tasteful-icons, and the design category with it. The collection is now the agents skills only.

## [0.2.0] - 2026-11-08

### Added

- climb: turns a big goal into one `./verify` command and a `GOAL.md` an agent can run on for days.
- copycat: ports or rewrites a tool with the original as the oracle, then makes it faster. climb hands ports to it.
- unblock: run `/unblock` on a long run to find the one thing slowing it down.
- tasteful-icons: app, shortcut and integration icons in a frosted-glass squircle style, as SVG and PNG, from one Python script.

### Changed

- The skills are licensed under the PolyForm Noncommercial License 1.0.0, free for any non-commercial use, in place of the MIT License. 0.1.0 keeps the MIT License.
- The README is a short install snippet and a table of the skills.
- CI runs on the latest Python 3 and the current versions of its actions.

### Removed

- whiteboard, and the diagramming category with it.

## [0.1.0] - 2026-06-25

The first release.

### Added

- whiteboard: hand-drawn, whiteboard-style diagrams (flowcharts, architecture, ER, sequence and mind maps) as `.excalidraw` files from a Python builder, exported to PNG or SVG when a browser is available.
- A GitHub Release for each `v*` tag, after the skills' tests pass.

[Unreleased]: https://github.com/devbyshima/skills/compare/v0.3.0...main
[0.3.0]: https://github.com/devbyshima/skills/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/devbyshima/skills/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/devbyshima/skills/releases/tag/v0.1.0
