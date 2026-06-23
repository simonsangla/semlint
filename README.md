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

## Use

```
pip install -e ".[dev,app]"
python -m semlint audit metrics_demo.yml --report sample_reports/demo_report.md
streamlit run app.py
```

## About the score

The Semantic Trust Score is a deterministic v0 heuristic for prioritizing fixes
- a weighted roll-up of rule findings, not a statistical or certified trust
measure. The same input always produces the same score. No network, no
warehouse connection, no telemetry.
