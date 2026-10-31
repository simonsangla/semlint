# semlint roadmap

semlint is a local-only audit for semantic-layer and metric definitions. This roadmap lists
what is shipped (with its commit), what is still open (with the file that says so), and what is
out of scope. Every item cites a commit or a file in this repo. Priorities are the maintainer's.

## Shipped

| Item | Evidence |
|---|---|
| Eight audit rules R1-R8 (duplicate, collision, owner, description, grain, orphaned dimension, AI-readiness, portability) | `semlint/rules.py`, commit `3f2c244` |
| Deterministic 0-100 Semantic Trust Score with weighted findings | `semlint/engine.py`, commit `3f2c244` |
| CLI and markdown or JSON report | `semlint/cli.py`, `semlint/report.py`, commit `3f2c244` |
| Interactive audit workspace (Streamlit) | `app.py`, commit `dc74a1e` |
| Diff-first redesign: declared versus observed values, bundled sample data | `semlint/reality.py`, `reality_demo.yml`, commit `e3fb17d` |
| CI gate: ruff, compileall, pytest, source guards; Dependabot | `.github/workflows/ci.yml`, commit `49f0dad` |
| Accessibility fixes (heading order, decorative severity bar) | commit `47c7206` |
| README explains the score for a buyer, with what it does not tell you | `README.md`, commit `b82edb3` |
| MIT license | `LICENSE`, commit `207aff4` |

Tests: `pytest -q` runs 42 tests in `tests/`.

## Open

- **Warehouse connection wording.** `app.py` says "Connect a warehouse to diff declared values"
  (around line 209). The redesign spec puts a warehouse connection out of scope
  (`docs/superpowers/specs/2026-06-23-semlint-diff-redesign-design.md`, section "Out of scope").
  Decide: keep it as a future feature, or change the sentence. Until then the UI promises more
  than the code does.
- **Standalone HTML app.** The spec's risks section says a standalone HTML app is the fallback if
  the Streamlit look is too generic, and "remains available later".
- **Plan files still show unchecked boxes.** The two plans in `docs/superpowers/plans/` have
  `- [ ]` steps, but the shipped commits above cover them. Tick the steps with evidence, or move
  the plans to an archive folder.

## Not planned (out of scope, from the spec)

- Real warehouse or database connection, and credentials
  (`docs/superpowers/specs/2026-06-23-semlint-diff-redesign-design.md`, "Out of scope").
- New scoring rules: the eight rules stay as they are (same spec).
- Auth, multi-file projects, persistence, deployment (same spec; the v0 plan also says do not deploy).
- Charts beyond the gauge and severity bar (same spec).
