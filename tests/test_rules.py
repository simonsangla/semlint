from __future__ import annotations

import json
from pathlib import Path

import semlint.rules as R
from semlint.contracts import SEVERITY_FACTOR, Finding, Severity
from semlint.engine import audit_file, compute_score, load_metrics, run_audit
from semlint.report import to_json, to_markdown, write_report

DIMS = {
    "date": {"name": "date", "grains": ["day", "week", "month"]},
    "region": {"name": "region"},
}

DEMO = Path(__file__).resolve().parents[1] / "metrics_demo.yml"


def _clean_metric(**over):
    m = {
        "name": "m",
        "description": "a description",
        "owner": "owner@acme.com",
        "formula": "SUM(x)",
        "grain": "day",
        "dimensions": ["date"],
        "aliases": ["mm"],
        "access": "team",
    }
    m.update(over)
    return m


def test_severity_factor_values():
    assert SEVERITY_FACTOR[Severity.FAIL] == 1.0
    assert SEVERITY_FACTOR[Severity.WARN] == 0.5
    assert SEVERITY_FACTOR[Severity.PASS] == 0.0


def test_finding_is_frozen():
    f = Finding("R1", "duplicate definition", Severity.FAIL, "revenue", "msg", "fix")
    assert f.metric == "revenue"
    assert f.severity is Severity.FAIL


def test_load_metrics_splits_metrics_and_dimensions(tmp_path):
    p = tmp_path / "m.yml"
    p.write_text(
        "version: 1\n"
        "dimensions:\n"
        "  - name: date\n"
        "    grains: [day, week]\n"
        "metrics:\n"
        "  - name: revenue\n"
        "    formula: SUM(x)\n",
        encoding="utf-8",
    )
    metrics, dimensions = load_metrics(str(p))
    assert metrics[0]["name"] == "revenue"
    assert dimensions["date"]["grains"] == ["day", "week"]


def test_load_metrics_handles_empty_file(tmp_path):
    p = tmp_path / "empty.yml"
    p.write_text("", encoding="utf-8")
    metrics, dimensions = load_metrics(str(p))
    assert metrics == []
    assert dimensions == {}


def test_duplicate_definition_fails_on_repeat():
    metrics = [_clean_metric(name="revenue"), _clean_metric(name="revenue")]
    fs = R.rule_duplicate_definition(metrics, DIMS)
    assert any(f.severity is Severity.FAIL and f.metric == "revenue" for f in fs)


def test_duplicate_definition_passes_when_unique():
    fs = R.rule_duplicate_definition([_clean_metric(name="a"), _clean_metric(name="b")], DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_definition_collision_fails_on_diff_formula():
    metrics = [
        _clean_metric(name="r", formula="SUM(a)"),
        _clean_metric(name="r", formula="SUM(a)-SUM(b)"),
    ]
    fs = R.rule_definition_collision(metrics, DIMS)
    assert any(f.severity is Severity.FAIL for f in fs)


def test_definition_collision_passes_on_same_formula():
    metrics = [
        _clean_metric(name="r", formula="SUM(a)"),
        _clean_metric(name="r", formula="SUM(a)"),
    ]
    fs = R.rule_definition_collision(metrics, DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_missing_owner_warns():
    fs = R.rule_missing_owner([_clean_metric(owner="")], DIMS)
    assert any(f.severity is Severity.WARN for f in fs)


def test_owner_present_passes():
    fs = R.rule_missing_owner([_clean_metric()], DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_missing_description_warns():
    fs = R.rule_missing_description([_clean_metric(description="")], DIMS)
    assert any(f.severity is Severity.WARN for f in fs)


def test_missing_grain_fails():
    fs = R.rule_grain([_clean_metric(grain="")], DIMS)
    assert any(f.severity is Severity.FAIL for f in fs)


def test_ambiguous_grain_warns():
    fs = R.rule_grain([_clean_metric(grain="hour")], DIMS)
    assert any(f.severity is Severity.WARN for f in fs)


def test_valid_grain_passes():
    fs = R.rule_grain([_clean_metric(grain="day")], DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_orphaned_dimension_fails():
    fs = R.rule_orphaned_dimension([_clean_metric(dimensions=["date", "store"])], DIMS)
    assert any(f.severity is Severity.FAIL and "store" in f.message for f in fs)


def test_defined_dimensions_pass():
    fs = R.rule_orphaned_dimension([_clean_metric(dimensions=["date", "region"])], DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_ai_readiness_warns_on_missing_aliases_and_access():
    fs = R.rule_ai_readiness([_clean_metric(aliases=[], access="")], DIMS)
    assert any(f.severity is Severity.WARN for f in fs)


def test_ai_readiness_passes_when_complete():
    fs = R.rule_ai_readiness([_clean_metric()], DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_non_portable_warns_on_iff():
    fs = R.rule_non_portable([_clean_metric(formula="SUM(IFF(p, a, 0))")], DIMS)
    assert any(f.severity is Severity.WARN for f in fs)


def test_portable_formula_passes():
    fs = R.rule_non_portable([_clean_metric(formula="SUM(a)")], DIMS)
    assert all(f.severity is Severity.PASS for f in fs)


def test_registry_has_eight_rules():
    assert len(R.ALL_RULES) == 8
    assert sum(spec.weight for spec, _ in R.ALL_RULES) == 100


def test_perfect_set_scores_100():
    result = run_audit([_clean_metric(name="a"), _clean_metric(name="b")], DIMS)
    assert result.score == 100
    assert result.rule_count == 8


def test_score_is_deterministic():
    metrics = [_clean_metric(name="a"), _clean_metric(name="b", owner="")]
    assert run_audit(metrics, DIMS).score == run_audit(metrics, DIMS).score


def test_compute_score_single_fail_deducts_weight():
    findings = [Finding("R6", "orphaned dimension", Severity.FAIL, "aov", "m", "f")]
    assert compute_score(findings, metric_count=1) == 85


def test_markdown_contains_score_and_table():
    md = to_markdown(run_audit([_clean_metric(name="a")], DIMS))
    assert "Semantic Trust Score" in md
    assert "/100" in md
    assert "| rule | severity | metric |" in md


def test_json_is_valid_and_round_trips(tmp_path):
    result = run_audit([_clean_metric(name="a", owner="")], DIMS)
    payload = json.loads(to_json(result))
    assert payload["score"] == result.score
    assert isinstance(payload["findings"], list)

    written = write_report(result, str(tmp_path / "r.md"))
    assert (tmp_path / "r.md").exists()
    assert (tmp_path / "r.json").exists()
    assert written["json"].endswith("r.json")


def test_cli_audit_writes_report_and_returns_zero(tmp_path):
    from semlint.cli import main

    src = tmp_path / "m.yml"
    src.write_text(
        "dimensions:\n  - name: date\n    grains: [day]\n"
        "metrics:\n  - name: a\n    description: d\n    owner: o@a.com\n"
        "    formula: SUM(x)\n    grain: day\n    dimensions: [date]\n"
        "    aliases: [aa]\n    access: team\n",
        encoding="utf-8",
    )
    out = tmp_path / "rep.md"
    code = main(["audit", str(src), "--report", str(out)])
    assert code == 0
    assert out.exists()
    assert (tmp_path / "rep.json").exists()


def test_demo_file_exists():
    assert DEMO.exists()


def test_demo_has_pass_warn_fail():
    sevs = {f.severity for f in audit_file(str(DEMO)).findings}
    assert Severity.PASS in sevs
    assert Severity.WARN in sevs
    assert Severity.FAIL in sevs


def test_demo_score_is_deterministic_89():
    assert audit_file(str(DEMO)).score == 89
