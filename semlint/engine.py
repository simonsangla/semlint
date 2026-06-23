from __future__ import annotations

from pathlib import Path

import yaml

from semlint.contracts import SEVERITY_FACTOR, AuditResult, Severity
from semlint.rules import ALL_RULES, RULE_WEIGHTS


def load_metrics_text(text: str) -> tuple[list[dict], dict[str, dict]]:
    data = yaml.safe_load(text)
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ValueError("top-level YAML must be a mapping with a 'metrics' list")
    metrics = data.get("metrics") or []
    dimensions: dict[str, dict] = {}
    for d in data.get("dimensions") or []:
        if isinstance(d, dict) and d.get("name"):
            dimensions[d["name"]] = d
    return metrics, dimensions


def load_metrics(path: str) -> tuple[list[dict], dict[str, dict]]:
    return load_metrics_text(Path(path).read_text(encoding="utf-8"))


def run_rules(metrics: list[dict], dimensions: dict) -> list:
    findings = []
    for _spec, fn in ALL_RULES:
        findings.extend(fn(metrics, dimensions))
    return findings


def compute_score(findings: list, metric_count: int) -> int:
    if metric_count <= 0:
        return 0
    worst: dict[str, dict[str, float]] = {}
    for f in findings:
        if f.severity is Severity.PASS:
            continue
        key = f.metric or f"_{f.rule_id}"
        bucket = worst.setdefault(f.rule_id, {})
        factor = SEVERITY_FACTOR[f.severity]
        if factor > bucket.get(key, 0.0):
            bucket[key] = factor
    deduction = 0.0
    for rule_id, per_metric in worst.items():
        weight = RULE_WEIGHTS.get(rule_id, 0)
        deduction += weight * (sum(per_metric.values()) / metric_count)
    return max(0, min(100, round(100 - deduction)))


def run_audit(metrics: list[dict], dimensions: dict) -> AuditResult:
    findings = run_rules(metrics, dimensions)
    score = compute_score(findings, len(metrics))
    return AuditResult(
        score=score,
        metric_count=len(metrics),
        rule_count=len(ALL_RULES),
        findings=findings,
    )


def audit_file(path: str) -> AuditResult:
    metrics, dimensions = load_metrics(path)
    return run_audit(metrics, dimensions)


def audit_text(text: str) -> AuditResult:
    metrics, dimensions = load_metrics_text(text)
    return run_audit(metrics, dimensions)
