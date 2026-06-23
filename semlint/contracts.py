from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Severity(str, Enum):
    PASS = "pass"
    WARN = "warn"
    FAIL = "fail"


SEVERITY_FACTOR = {Severity.FAIL: 1.0, Severity.WARN: 0.5, Severity.PASS: 0.0}


@dataclass(frozen=True)
class Finding:
    rule_id: str
    rule_name: str
    severity: Severity
    metric: str | None
    message: str
    remediation: str


@dataclass(frozen=True)
class RuleSpec:
    id: str
    name: str
    weight: int
    violation_severity: Severity


@dataclass(frozen=True)
class AuditResult:
    score: int
    metric_count: int
    rule_count: int
    findings: list[Finding] = field(default_factory=list)
