from __future__ import annotations

import json
from pathlib import Path

from semlint.contracts import AuditResult, Severity

_SEV_LABEL = {Severity.PASS: "PASS", Severity.WARN: "WARN", Severity.FAIL: "FAIL"}
_EMPTY = "-"


def _counts(result: AuditResult) -> dict[str, int]:
    c = {"pass": 0, "warn": 0, "fail": 0}
    for f in result.findings:
        c[f.severity.value] += 1
    return c


def to_markdown(result: AuditResult) -> str:
    c = _counts(result)
    lines = [
        "# semlint audit report",
        "",
        f"**Semantic Trust Score (v0 heuristic):** {result.score}/100",
        "",
        f"- metrics audited: {result.metric_count}",
        f"- rules run: {result.rule_count}",
        f"- findings: {c['fail']} fail, {c['warn']} warn, {c['pass']} pass",
        "",
        "| rule | severity | metric | finding | remediation |",
        "|---|---|---|---|---|",
    ]
    for f in result.findings:
        metric = f.metric or _EMPTY
        remediation = f.remediation or _EMPTY
        lines.append(
            f"| {f.rule_id} {f.rule_name} | {_SEV_LABEL[f.severity]} | "
            f"{metric} | {f.message} | {remediation} |"
        )
    lines.append("")
    return "\n".join(lines)


def to_json(result: AuditResult) -> str:
    payload = {
        "score": result.score,
        "metric_count": result.metric_count,
        "rule_count": result.rule_count,
        "findings": [
            {
                "rule_id": f.rule_id,
                "rule_name": f.rule_name,
                "severity": f.severity.value,
                "metric": f.metric,
                "message": f.message,
                "remediation": f.remediation,
            }
            for f in result.findings
        ],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def write_report(result: AuditResult, md_path: str) -> dict[str, str]:
    md = Path(md_path)
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(to_markdown(result), encoding="utf-8")
    json_path = md.with_suffix(".json")
    json_path.write_text(to_json(result), encoding="utf-8")
    return {"markdown": str(md), "json": str(json_path)}
