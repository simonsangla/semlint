# semlint v0.2 - diff-first sellable redesign (design)

**Date:** 2026-06-23
**Status:** Approved (design accepted; new diff finding-type accepted)
**Supersedes UI of:** v0 (`app.py` static workspace). Audit engine and score are unchanged.

## Goal

Make semlint visual, interactive, and sellable. Lead with a "definition vs reality"
diff that makes the core problem (a metric meaning two different things) instantly
legible to a buyer, and give the score real visual meaning. Stay local-only.

## Decisions (locked with the user)

1. **Diff data source:** bundled sample "observed" dataset (fully offline). A
   "Connect warehouse" affordance is a labeled future stub, not implemented.
2. **UI platform:** polished Streamlit (keep `streamlit run app.py`); add a score
   gauge, severity bar, diff cards, and a light branded theme via CSS / config.
3. **Optimize for:** sellable demo / portfolio first - hero gauge, the diff as the
   centerpiece, a 5-second narrative. Real-file input still works.

## Architecture

Three layers, one-directional dependencies:

1. **Audit engine (unchanged).** `semlint/{contracts,rules,engine,report}.py` and the
   8 rules stay exactly as-is. The deterministic Semantic Trust Score stays **89/100**
   on the demo. This is definition *hygiene*.
2. **Reality-diff layer (new, isolated).** `semlint/reality.py` + `reality_demo.yml`.
   Compares each declared metric definition against an *observed* one from a bundled
   sample dataset. Produces `Diff` objects. Does **not** feed the score (additive, not
   a rewrite). No SQL, no network.
3. **Presentation (rewrite).** `app.py` renders a sellable, visual, light-themed layout
   over the engine result + the diffs. `.streamlit/config.toml` supplies the theme.

## Reality-diff component

### Data: `reality_demo.yml`

```yaml
version: 1
observations:
  - metric: revenue
    observed_formula: SUM(order_amount) - SUM(refund_amount)
    declared_value: 1250000
    observed_value: 1198750
  - metric: active_users
    observed_formula: COUNT(DISTINCT user_id)
    declared_value: 48200
    observed_value: 48200
  - metric: gmv
    observed_formula: SUM(IFF(is_paid, gmv_amount, 0))
    declared_value: 2400000
    observed_value: 2310000
```

Metrics with no `observations` entry render as `not_checked` ("connect to check").

### Logic: `semlint/reality.py`

```python
@dataclass(frozen=True)
class Diff:
    metric: str
    declared: str           # first declared formula from the audited file
    observed: str | None
    status: str             # "match" | "mismatch" | "not_checked"
    delta_pct: float | None
    note: str
```

- `load_observations(path) -> dict[str, dict]` - keyed by metric name.
- `build_diffs(metrics, observations) -> list[Diff]`:
  - `declared` = the **first** declared occurrence of each metric name (so a collided
    metric still diffs against its primary definition).
  - Normalize formulas with `" ".join(f.split()).upper()` for comparison.
  - `status`:
    - `not_checked` if the metric has no observation.
    - `mismatch` if normalized formulas differ, OR both values present and
      `abs(delta_pct) > 0.5`.
    - `match` otherwise.
  - `delta_pct = round((observed_value - declared_value) / declared_value * 100, 1)`
    when both present and `declared_value != 0`, else `None`.
  - Sorted: mismatch first, then not_checked, then match; then metric name.
- Fully deterministic (static data, no RNG, no time). `revenue` -> formula mismatch,
  delta **-4.1%**.

## UI layout (`app.py`, top to bottom)

1. **Brand header** - product name + one-line value prop; minimal, not raw Streamlit feel.
2. **Hero** - inline SVG **score gauge** (89, via `st.markdown(unsafe_allow_html=True)`,
   no new dependency) + one-line verdict ("revenue means two different things") + a
   stacked **severity bar** (4 fail / 3 warn / 1 pass).
3. **Reality check (the star)** - one card per metric that has a diff: declared vs
   observed side-by-side, a git-style red/green unified diff, a status/delta badge
   (`MISMATCH -4.1%`). Mismatches first. A labeled, disabled "Connect warehouse" stub.
4. **Fix these first** - prioritized top-3 (fail-by-weight), why + remediation.
5. **All findings** - severity filter + search, card layout (no wide table), expandable
   why/remediation with copy.
6. **Export** - existing markdown + JSON download buttons.

### Theme: `.streamlit/config.toml`

Light base, one professional accent (e.g. a green/teal that matches the gauge), custom
font if available. Removes the dark "internal tool" feel. Cards and diff colors use
semantic colors that read in the chosen theme.

### Inputs (kept from v0)

Sidebar: demo file / paste YAML / upload. Same `audit_text` path. The reality layer uses
the bundled `reality_demo.yml` for the demo; pasted/uploaded files show diffs only for
metrics present in the bundled observations (others -> `not_checked`).

## Files

- **New:** `semlint/reality.py`, `reality_demo.yml`, `.streamlit/config.toml`,
  `tests/test_reality.py`
- **Rewrite:** `app.py`
- **Unchanged:** `semlint/{contracts,rules,engine,report,cli,__main__}.py`, the 8 rules,
  `metrics_demo.yml`, the Semantic Trust Score.

## Constraints carried forward

- Local-only: no live warehouse connection; "Connect" is a visible stub.
- Deterministic output (score stays 89; diff is static).
- ASCII-only source (`.py`/`.yml`/`.toml`).
- One commit after full validation; no remote push.

## Validation gates

- `pytest -q` green (adds `tests/test_reality.py`; existing 33 still pass).
- `ruff check .` clean.
- Demo Semantic Trust Score still **89/100**.
- Streamlit boots; HTTP 200 on `/` and `/_stcore/health`.
- Desktop (1280x800) and mobile (375x812) screenshots: no clipped table, no horizontal
  overflow; the diff + score gauge legible on narrow.
- Acceptance: a viewer understands the top problem (revenue means two things) and the
  top 3 fixes within seconds, without horizontal scroll or reading source.

## Out of scope (YAGNI)

- Real warehouse/DB connection or credentials.
- New audit *scoring* rules (the 8 stay; the diff is a separate, non-scoring layer).
- Auth, multi-file projects, persistence, deployment.
- Charts beyond the gauge + severity bar (no trend lines, no heatmaps in v0.2).

## Risks

- Streamlit theming limits "product" polish; mitigated by `unsafe_allow_html` cards +
  `.streamlit/config.toml`. If it still looks too "Streamlit", the fallback (a standalone
  HTML app) was option 2 and remains available later.
- The bundled `observed` numbers are illustrative; the UI must label them "sample" so the
  demo stays honest (evidence-over-claims).
