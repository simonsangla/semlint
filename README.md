# semlint

Local-only audit for semantic-layer / metric definitions. It inspects a metrics
definition file and returns a deterministic 0-100 Semantic Trust Score with
per-rule findings and one-line remediations - an independent check that your
metric definitions are consistent, governed, and AI-ready, without replacing
your dbt / warehouse / BI stack.

## Why

Native semantic layers lock metrics into one engine; catalogs document metadata
but never the calculation. Nobody independently verifies that the same KPI is
defined consistently across the estate. semlint is that check.

## Rules

| ID | Check |
|----|-------|
| R1 | duplicate definition |
| R2 | definition collision (same name, different formula) |
| R3 | missing owner |
| R4 | missing description |
| R5 | undefined or ambiguous grain |
| R6 | orphaned dimension |
| R7 | AI-readiness gaps (aliases, allowed dimensions, access) |
| R8 | non-portable construct (engine-specific SQL) |

## Built with

Python 3.11 or newer (CI runs 3.13), PyYAML for the metrics file, Streamlit for the
optional UI, pytest and ruff for tests and lint. Dependencies are declared in `pyproject.toml`.

## Use

```
pip install -e ".[dev,app]"
python -m semlint audit metrics_demo.yml --report sample_reports/demo_report.md
streamlit run app.py
```

## What the score means for a buyer

The Semantic Trust Score answers one question: *can the metric definitions an AI
assistant or BI tool reads be trusted to mean one thing each?* It is computed from
the definitions file alone - no warehouse connection, no data access, no
credentials.

**Try it on the fictional demo model** (`metrics_demo.yml`, a made-up retailer
with placeholder `acme.com` owners):

```
pip install -e .
python -m semlint audit metrics_demo.yml
```

The demo scores 89/100 - every run, on every machine. The findings behind it are
what a reviewer would flag by hand: `revenue` is defined twice with two different
formulas (one nets out refunds, one does not), a ratio metric has no declared
grain, one metric references a dimension that does not exist, and others lack a
description, AI-readiness metadata, or use engine-specific SQL.

How to read the number:

| Score | Reading |
|-------|---------|
| 90-100 | Definitions are consistent and governed; remaining findings are hygiene. |
| 70-89 | Usable, but at least one metric can silently mean two things - fix before exposing it to AI or self-serve users. |
| below 70 | Structural problems (collisions, missing grain, orphaned dimensions); expect inconsistent answers. |

Each finding carries a rule ID and a one-line remediation, so the score comes with
its own fix list. Failures (collisions, duplicates, grain, orphaned dimensions)
weigh more than warnings (owner, description, AI metadata, portability).

What the score does **not** tell you:

- It does not check that the data is correct or that a query returns the right
  number - it reads definitions, not results.
- It does not certify compliance, security, or access control.
- It is a deterministic v0 heuristic for prioritizing fixes, not a statistical
  measure; the bands above are guidance, not a benchmark against other companies.

## About the score

The Semantic Trust Score is a deterministic v0 heuristic for prioritizing fixes
- a weighted roll-up of rule findings, not a statistical or certified trust
measure. The same input always produces the same score. No network, no
warehouse connection, no telemetry.
