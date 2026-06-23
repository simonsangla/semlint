from __future__ import annotations

from semlint.contracts import Finding, RuleSpec, Severity

SPEC_DUPLICATE = RuleSpec("R1", "duplicate definition", 15, Severity.FAIL)
SPEC_COLLISION = RuleSpec("R2", "definition collision", 20, Severity.FAIL)
SPEC_OWNER = RuleSpec("R3", "missing owner", 8, Severity.WARN)
SPEC_DESCRIPTION = RuleSpec("R4", "missing description", 7, Severity.WARN)
SPEC_GRAIN = RuleSpec("R5", "undefined or ambiguous grain", 15, Severity.FAIL)
SPEC_ORPHAN = RuleSpec("R6", "orphaned dimension", 15, Severity.FAIL)
SPEC_AI = RuleSpec("R7", "ai-readiness gaps", 12, Severity.WARN)
SPEC_PORTABLE = RuleSpec("R8", "non-portable construct", 8, Severity.WARN)

NON_PORTABLE_TOKENS = (
    "IFF(",
    "DATEADD(",
    "NVL(",
    "QUALIFY",
    "LISTAGG(",
    "FLATTEN(",
    "PARSE_JSON(",
    "::",
)


def _pass(spec: RuleSpec) -> Finding:
    return Finding(spec.id, spec.name, Severity.PASS, None, "no issues found", "")


def rule_duplicate_definition(metrics: list[dict], dimensions: dict) -> list[Finding]:
    spec = SPEC_DUPLICATE
    counts: dict[str, int] = {}
    for m in metrics:
        counts[m["name"]] = counts.get(m["name"], 0) + 1
    dupes = sorted(name for name, c in counts.items() if c > 1)
    if not dupes:
        return [_pass(spec)]
    return [
        Finding(
            spec.id,
            spec.name,
            spec.violation_severity,
            name,
            f"metric '{name}' is defined {counts[name]} times",
            f"keep one canonical definition of '{name}' and remove or rename the duplicates",
        )
        for name in dupes
    ]


def rule_definition_collision(metrics: list[dict], dimensions: dict) -> list[Finding]:
    spec = SPEC_COLLISION
    formulas: dict[str, set[str]] = {}
    for m in metrics:
        f = str(m.get("formula") or "").strip()
        formulas.setdefault(m["name"], set())
        if f:
            formulas[m["name"]].add(f)
    colliding = sorted(name for name, fs in formulas.items() if len(fs) > 1)
    if not colliding:
        return [_pass(spec)]
    out = []
    for name in colliding:
        variants = ", ".join(sorted(formulas[name]))
        out.append(
            Finding(
                spec.id,
                spec.name,
                spec.violation_severity,
                name,
                f"metric '{name}' has conflicting formulas: {variants}",
                f"reconcile '{name}' to a single agreed formula",
            )
        )
    return out


def _missing_field_rule(metrics, spec, field_name, label):
    offenders = sorted(
        (m for m in metrics if not str(m.get(field_name) or "").strip()),
        key=lambda m: m["name"],
    )
    if not offenders:
        return [_pass(spec)]
    return [
        Finding(
            spec.id,
            spec.name,
            spec.violation_severity,
            m["name"],
            f"metric '{m['name']}' has no {label}",
            f"add a {label} to '{m['name']}'",
        )
        for m in offenders
    ]


def rule_missing_owner(metrics: list[dict], dimensions: dict) -> list[Finding]:
    return _missing_field_rule(metrics, SPEC_OWNER, "owner", "owner")


def rule_missing_description(metrics: list[dict], dimensions: dict) -> list[Finding]:
    return _missing_field_rule(metrics, SPEC_DESCRIPTION, "description", "description")


def rule_grain(metrics: list[dict], dimensions: dict) -> list[Finding]:
    spec = SPEC_GRAIN
    allowed = (dimensions.get("date") or {}).get("grains")
    findings = []
    for m in sorted(metrics, key=lambda x: x["name"]):
        grain = str(m.get("grain") or "").strip()
        if not grain:
            findings.append(
                Finding(
                    spec.id,
                    spec.name,
                    Severity.FAIL,
                    m["name"],
                    f"metric '{m['name']}' has no grain",
                    f"declare a time grain for '{m['name']}'",
                )
            )
        elif allowed and grain not in allowed:
            findings.append(
                Finding(
                    spec.id,
                    spec.name,
                    Severity.WARN,
                    m["name"],
                    f"metric '{m['name']}' uses grain '{grain}' not in date.grains {allowed}",
                    f"use one of {allowed} for '{m['name']}' or extend date.grains",
                )
            )
    return findings or [_pass(spec)]


def rule_orphaned_dimension(metrics: list[dict], dimensions: dict) -> list[Finding]:
    spec = SPEC_ORPHAN
    defined = set(dimensions.keys())
    findings = []
    for m in sorted(metrics, key=lambda x: x["name"]):
        for dim in m.get("dimensions") or []:
            if dim not in defined:
                findings.append(
                    Finding(
                        spec.id,
                        spec.name,
                        Severity.FAIL,
                        m["name"],
                        f"metric '{m['name']}' references undefined dimension '{dim}'",
                        f"define dimension '{dim}' or remove it from '{m['name']}'",
                    )
                )
    return findings or [_pass(spec)]


def rule_ai_readiness(metrics: list[dict], dimensions: dict) -> list[Finding]:
    spec = SPEC_AI
    findings = []
    for m in sorted(metrics, key=lambda x: x["name"]):
        missing = []
        if not (m.get("aliases") or []):
            missing.append("aliases/synonyms")
        if not (m.get("dimensions") or []):
            missing.append("allowed dimensions")
        if not str(m.get("access") or "").strip():
            missing.append("access rule")
        if missing:
            joined = ", ".join(missing)
            findings.append(
                Finding(
                    spec.id,
                    spec.name,
                    Severity.WARN,
                    m["name"],
                    f"metric '{m['name']}' missing {joined} for AI grounding",
                    f"add {joined} to '{m['name']}'",
                )
            )
    return findings or [_pass(spec)]


def rule_non_portable(metrics: list[dict], dimensions: dict) -> list[Finding]:
    spec = SPEC_PORTABLE
    findings = []
    for m in sorted(metrics, key=lambda x: x["name"]):
        upper = str(m.get("formula") or "").upper()
        hits = [tok for tok in NON_PORTABLE_TOKENS if tok in upper]
        if hits:
            joined = ", ".join(hits)
            findings.append(
                Finding(
                    spec.id,
                    spec.name,
                    Severity.WARN,
                    m["name"],
                    f"metric '{m['name']}' formula uses non-portable construct(s): {joined}",
                    f"rewrite '{m['name']}' formula using ANSI/OSI-neutral SQL",
                )
            )
    return findings or [_pass(spec)]


ALL_RULES = [
    (SPEC_DUPLICATE, rule_duplicate_definition),
    (SPEC_COLLISION, rule_definition_collision),
    (SPEC_OWNER, rule_missing_owner),
    (SPEC_DESCRIPTION, rule_missing_description),
    (SPEC_GRAIN, rule_grain),
    (SPEC_ORPHAN, rule_orphaned_dimension),
    (SPEC_AI, rule_ai_readiness),
    (SPEC_PORTABLE, rule_non_portable),
]

RULE_WEIGHTS = {spec.id: spec.weight for spec, _ in ALL_RULES}
