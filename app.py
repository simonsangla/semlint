from __future__ import annotations

from pathlib import Path

import streamlit as st

from semlint.contracts import AuditResult, Severity
from semlint.engine import audit_text
from semlint.report import to_json, to_markdown
from semlint.rules import RULE_WEIGHTS

DEMO = Path(__file__).resolve().parent / "metrics_demo.yml"

SEV_RANK = {Severity.FAIL: 0, Severity.WARN: 1, Severity.PASS: 2}
SEV_BADGE = {
    Severity.FAIL: ":red[**FAIL**]",
    Severity.WARN: ":orange[**WARN**]",
    Severity.PASS: ":green[**PASS**]",
}
WHY = {
    "R1": "Two definitions for one metric name means no single source of truth; "
    "queries silently pick different logic.",
    "R2": "The same metric resolves to different formulas, so dashboards and AI "
    "agents will disagree on the number.",
    "R3": "With no owner, nobody is accountable when the definition drifts or breaks.",
    "R4": "Without a description, people and AI agents guess the meaning and apply "
    "it inconsistently.",
    "R5": "An undefined or off-list grain makes the metric ambiguous to aggregate "
    "over time.",
    "R6": "The metric points at a dimension that does not exist, so slicing by it "
    "fails or returns nothing.",
    "R7": "Missing aliases, allowed dimensions, or access rules degrade how reliably "
    "AI agents can ground on the metric.",
    "R8": "Engine-specific SQL will not port across warehouses or to an OSI-neutral "
    "definition.",
}

def remediation_block(text: str) -> None:
    try:
        st.code(text or "-", language="text", wrap_lines=True)
    except TypeError:
        st.code(text or "-", language="text")


def priority_key(f):
    return (SEV_RANK[f.severity], -RULE_WEIGHTS.get(f.rule_id, 0), f.metric or "")


def render_summary(result: AuditResult, issues: list) -> None:
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for f in result.findings:
        counts[f.severity.value] += 1

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Trust score (v0)", f"{result.score}/100")
    c2.metric("Fail", counts["fail"])
    c3.metric("Warn", counts["warn"])
    c4.metric("Pass", counts["pass"])
    st.caption(
        "v0 heuristic score - a weighted roll-up of rule findings, not a certified "
        "trust guarantee."
    )

    if issues:
        top = issues[0]
        st.warning(
            f"**Next fix:** [{top.rule_id} {top.rule_name}] on `{top.metric or '-'}` "
            f"- {top.remediation}"
        )
    else:
        st.success("No issues found - every rule passed on this file.")


def render_fix_first(issues: list) -> None:
    if not issues:
        return
    st.subheader("Fix these first")
    for i, f in enumerate(issues[:3], 1):
        with st.container(border=True):
            st.markdown(
                f"**{i}. {SEV_BADGE[f.severity]} {f.rule_id} {f.rule_name}** "
                f"- metric `{f.metric or '-'}`"
            )
            st.markdown(f.message)
            st.markdown(f"_Why it matters:_ {WHY.get(f.rule_id, '')}")
            st.markdown("**Recommended fix** (click the copy icon):")
            remediation_block(f.remediation)


def render_findings(result: AuditResult) -> None:
    st.subheader("All findings")
    fcol, scol = st.columns([1, 2])
    sev = fcol.radio("Severity", ["all", "fail", "warn", "pass"], horizontal=True)
    query = scol.text_input("Search metric or rule", "")

    def matches(f) -> bool:
        if sev != "all" and f.severity.value != sev:
            return False
        if query:
            hay = f"{f.metric or ''} {f.rule_id} {f.rule_name} {f.message}".lower()
            if query.lower() not in hay:
                return False
        return True

    shown = sorted((f for f in result.findings if matches(f)), key=priority_key)
    if not shown:
        st.info("No findings match the current filter.")
        return

    for f in shown:
        with st.container(border=True):
            st.markdown(
                f"{SEV_BADGE[f.severity]}  **{f.rule_id} {f.rule_name}**  "
                f"- metric `{f.metric or '-'}`"
            )
            st.markdown(f.message)
            if f.severity is not Severity.PASS:
                with st.expander("Why it matters and how to fix it"):
                    st.markdown(f"**Why it matters:** {WHY.get(f.rule_id, '')}")
                    st.markdown("**Recommended fix** (click the copy icon):")
                    remediation_block(f.remediation)


def render_export(result: AuditResult) -> None:
    st.subheader("Export report")
    d1, d2 = st.columns(2)
    d1.download_button(
        "Download markdown report",
        to_markdown(result),
        file_name="semlint_report.md",
        mime="text/markdown",
        use_container_width=True,
    )
    d2.download_button(
        "Download JSON findings",
        to_json(result),
        file_name="semlint_findings.json",
        mime="application/json",
        use_container_width=True,
    )


def resolve_input() -> str | None:
    st.sidebar.header("Audit input")
    source = st.sidebar.radio(
        "Data source", ["Demo file", "Paste YAML", "Upload file"], index=0
    )

    if source == "Demo file":
        if DEMO.exists():
            return DEMO.read_text(encoding="utf-8")
        st.sidebar.error("metrics_demo.yml not found next to app.py.")
        return None

    if source == "Paste YAML":
        pasted = st.sidebar.text_area(
            "Paste metrics YAML", height=260, placeholder="metrics:\n  - name: revenue\n    ..."
        )
        if st.sidebar.button("Run audit", type="primary", use_container_width=True):
            st.session_state["pasted_yaml"] = pasted
        return st.session_state.get("pasted_yaml")

    upload = st.sidebar.file_uploader("Upload metrics YAML", type=["yml", "yaml"])
    if upload is not None:
        return upload.getvalue().decode("utf-8")
    return None


def main() -> None:
    st.set_page_config(page_title="semlint", layout="wide")
    st.title("semlint")
    st.caption("local-only semantic-layer / metric-definition audit workspace")

    yaml_text = resolve_input()
    if not yaml_text or not yaml_text.strip():
        st.info(
            "Pick a data source on the left: load the bundled demo, paste a metrics "
            "YAML and press **Run audit**, or upload a `.yml` file."
        )
        return

    try:
        result = audit_text(yaml_text)
    except Exception as exc:  # noqa: BLE001 - surface any parse error to the user
        st.error(f"Could not parse this YAML: {exc}")
        st.caption("Check indentation and that the top level is a mapping with `metrics:`.")
        return

    if result.metric_count == 0:
        st.warning("Parsed successfully, but found no metrics. Add a `metrics:` list.")
        return

    issues = sorted(
        (f for f in result.findings if f.severity is not Severity.PASS),
        key=priority_key,
    )

    render_summary(result, issues)
    st.divider()
    render_fix_first(issues)
    st.divider()
    render_findings(result)
    st.divider()
    render_export(result)


main()
