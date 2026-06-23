from __future__ import annotations

from pathlib import Path

from semlint.reality import build_diffs, load_observations

REALITY = Path(__file__).resolve().parents[1] / "reality_demo.yml"
METRICS = Path(__file__).resolve().parents[1] / "metrics_demo.yml"


def test_mismatch_on_different_formula():
    metrics = [{"name": "revenue", "formula": "SUM(order_amount)"}]
    obs = {
        "revenue": {
            "observed_formula": "SUM(order_amount) - SUM(refund_amount)",
            "declared_value": 1250000,
            "observed_value": 1198750,
        }
    }
    d = build_diffs(metrics, obs)[0]
    assert d.status == "mismatch"
    assert d.delta_pct == -4.1


def test_match_when_identical():
    metrics = [{"name": "x", "formula": "SUM(a)"}]
    obs = {"x": {"observed_formula": "SUM(a)", "declared_value": 100, "observed_value": 100}}
    assert build_diffs(metrics, obs)[0].status == "match"


def test_value_drift_is_mismatch_even_if_formula_matches():
    metrics = [{"name": "x", "formula": "SUM(a)"}]
    obs = {"x": {"observed_formula": "SUM(a)", "declared_value": 100, "observed_value": 90}}
    d = build_diffs(metrics, obs)[0]
    assert d.status == "mismatch"
    assert d.delta_pct == -10.0


def test_not_checked_without_observation():
    d = build_diffs([{"name": "y", "formula": "SUM(b)"}], {})[0]
    assert d.status == "not_checked"
    assert d.observed is None


def test_first_declared_used_for_collision():
    metrics = [{"name": "r", "formula": "SUM(a)"}, {"name": "r", "formula": "SUM(a)-SUM(b)"}]
    d = build_diffs(metrics, {"r": {"observed_formula": "SUM(a)"}})[0]
    assert d.declared == "SUM(a)"
    assert d.status == "match"


def test_demo_reality_matches_expected():
    from semlint.engine import load_metrics

    metrics, _ = load_metrics(str(METRICS))
    diffs = {d.metric: d for d in build_diffs(metrics, load_observations(str(REALITY)))}
    assert diffs["revenue"].status == "mismatch"
    assert diffs["revenue"].delta_pct == -4.1
    assert diffs["active_users"].status == "match"
    assert diffs["gmv"].status == "mismatch"
    assert diffs["conversion_rate"].status == "not_checked"
