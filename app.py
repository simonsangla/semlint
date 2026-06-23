from __future__ import annotations

import math
from pathlib import Path

import streamlit as st

from semlint.contracts import AuditResult, Severity
from semlint.engine import load_metrics_text, run_audit
from semlint.reality import Diff, build_diffs, load_observations
from semlint.report import to_json, to_markdown
from semlint.rules import RULE_WEIGHTS

ROOT = Path(__file__).resolve().parent
DEMO = ROOT / "metrics_demo.yml"
REALITY = ROOT / "reality_demo.yml"

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

PALETTE = {
    "ink": "#1a1c1a",
    "muted": "#5f5e5a",
    "line": "#e5e7e6",
    "accent": "#1d9e75",
    "amber": "#ba7517",
    "fail_bg": "#fcebeb",
    "fail_fg": "#a32d2d",
    "warn_bg": "#faeeda",
    "warn_fg": "#854f0b",
    "pass_bg": "#eaf3de",
    "pass_fg": "#3b6d11",
    "na_bg": "#f1efe8",
    "na_fg": "#5f5e5a",
}
DIFF_STYLE = {
    "mismatch": (PALETTE["fail_bg"], PALETTE["fail_fg"], "MISMATCH"),
    "not_checked": (PALETTE["na_bg"], PALETTE["na_fg"], "NOT CONNECTED"),
    "match": (PALETTE["pass_bg"], PALETTE["pass_fg"], "MATCH"),
}


def _counts(result: AuditResult) -> dict[str, int]:
    c = {"pass": 0, "warn": 0, "fail": 0}
    for f in result.findings:
        c[f.severity.value] += 1
    return c


def priority_key(f):
    return (SEV_RANK[f.severity], -RULE_WEIGHTS.get(f.rule_id, 0), f.metric or "")


def remediation_block(text: str) -> None:
    try:
        st.code(text or "-", language="text", wrap_lines=True)
    except TypeError:
        st.code(text or "-", language="text")


def _score_color(score: int) -> str:
    if score >= 80:
        return PALETTE["accent"]
    if score >= 50:
        return PALETTE["amber"]
    return PALETTE["fail_fg"]


def _gauge_html(score: int) -> str:
    r = 52
    circ = 2 * math.pi * r
    offset = circ * (1 - score / 100)
    color = _score_color(score)
    return (
        f'<svg width="130" height="130" viewBox="0 0 130 130" role="img" '
        f'aria-label="score {score} of 100">'
        f'<circle cx="65" cy="65" r="{r}" fill="none" '
        f'stroke="{PALETTE["line"]}" stroke-width="12"/>'
        f'<circle cx="65" cy="65" r="{r}" fill="none" stroke="{color}" stroke-width="12" '
        f'stroke-linecap="round" stroke-dasharray="{circ:.1f}" stroke-dashoffset="{offset:.1f}" '
        f'transform="rotate(-90 65 65)"/>'
        f'<text x="65" y="62" text-anchor="middle" '
        f'style="font-size:30px;font-weight:600;fill:{PALETTE["ink"]}">{score}</text>'
        f'<text x="65" y="82" text-anchor="middle" '
        f'style="font-size:12px;fill:{PALETTE["muted"]}">/ 100</text></svg>'
    )


def _severity_bar_html(counts: dict) -> str:
    total = max(1, counts["fail"] + counts["warn"] + counts["pass"])
    segs = [
        (counts["fail"], PALETTE["fail_fg"]),
        (counts["warn"], PALETTE["amber"]),
        (counts["pass"], PALETTE["accent"]),
    ]
    bars = "".join(
        f'<div style="width:{(c / total * 100):.1f}%;background:{col};height:10px"></div>'
        for c, col in segs
        if c > 0
    )
    return (
        f'<div style="display:flex;border-radius:6px;overflow:hidden;'
        f'border:1px solid {PALETTE["line"]}">{bars}</div>'
    )


def render_hero(result: AuditResult, issues: list) -> None:
    counts = _counts(result)
    if issues:
        v = issues[0]
        verdict = f"<span style='color:{PALETTE['fail_fg']}'>{v.metric} - {v.rule_name}</span>"
    else:
        verdict = "<span>all rules passed</span>"
    html = (
        f'<div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center;'
        f'background:{PALETTE["na_bg"]};border-radius:14px;padding:18px 20px;">'
        f"<div>{_gauge_html(result.score)}</div>"
        f'<div style="flex:1;min-width:230px;">'
        f'<div style="font-size:13px;color:{PALETTE["muted"]}">'
        "Semantic trust score (v0 heuristic)</div>"
        f'<div style="font-size:16px;color:{PALETTE["ink"]};margin:4px 0 10px;">'
        f"{result.metric_count} metrics, {result.rule_count} rules. {verdict}.</div>"
        f"{_severity_bar_html(counts)}"
        f'<div style="font-size:12px;color:{PALETTE["muted"]};margin-top:6px;">'
        f"{counts['fail']} fail &nbsp; {counts['warn']} warn &nbsp; {counts['pass']} pass</div>"
        f"</div></div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def _diff_card_html(d: Diff) -> str:
    bg, fg, label = DIFF_STYLE[d.status]
    delta = ""
    if d.delta_pct is not None:
        sign = "+" if d.delta_pct > 0 else ""
        delta = (
            f'<span style="font-family:monospace;font-size:12px;color:{fg};">'
            f"{sign}{d.delta_pct}%</span>"
        )
    observed = d.observed or "not connected"
    decl_norm = " ".join((d.declared or "").split()).upper()
    obs_norm = " ".join((d.observed or "").split()).upper()
    diff_block = ""
    if d.status == "mismatch" and d.observed and decl_norm != obs_norm:
        diff_block = (
            f'<div style="border-radius:6px;overflow:hidden;margin-top:10px;">'
            f'<div style="background:{PALETTE["fail_bg"]};color:{PALETTE["fail_fg"]};'
            f'padding:5px 12px;font-family:monospace;font-size:13px;word-break:break-word;">'
            f"- {d.declared}</div>"
            f'<div style="background:{PALETTE["pass_bg"]};color:{PALETTE["pass_fg"]};'
            f'padding:5px 12px;font-family:monospace;font-size:13px;word-break:break-word;">'
            f"+ {observed}</div></div>"
        )
    elif d.status == "mismatch" and d.observed and d.delta_pct is not None:
        sign = "+" if d.delta_pct > 0 else ""
        diff_block = (
            f'<div style="background:{PALETTE["warn_bg"]};color:{PALETTE["warn_fg"]};'
            f'border-radius:6px;margin-top:10px;padding:6px 12px;font-size:13px;">'
            f"formula matches; observed value drifts {sign}{d.delta_pct}% from declared</div>"
        )
    return (
        f'<div style="border:1px solid {PALETTE["line"]};border-radius:12px;'
        f'padding:14px 16px;margin-bottom:10px;background:#fff;">'
        f'<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;">'
        f'<span style="background:{bg};color:{fg};font-size:12px;padding:3px 10px;'
        f'border-radius:6px;">{label}</span>'
        f'<span style="font-family:monospace;font-size:14px;'
        f'color:{PALETTE["ink"]};">{d.metric}</span>'
        f"{delta}</div>"
        f'<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));'
        f'gap:10px;margin-top:10px;">'
        f'<div style="border:1px solid {PALETTE["line"]};border-radius:8px;padding:8px 10px;">'
        f'<div style="font-size:12px;color:{PALETTE["muted"]};">declared (yaml)</div>'
        f'<div style="font-family:monospace;font-size:13px;word-break:break-word;">'
        f'{d.declared or "-"}</div></div>'
        f'<div style="border:1px solid {PALETTE["line"]};border-radius:8px;padding:8px 10px;">'
        f'<div style="font-size:12px;color:{PALETTE["muted"]};">observed (sample)</div>'
        f'<div style="font-family:monospace;font-size:13px;word-break:break-word;">'
        f"{observed}</div></div>"
        f"</div>{diff_block}"
        f'<div style="font-size:12px;color:{PALETTE["muted"]};margin-top:8px;">{d.note}</div></div>'
    )


def render_reality(diffs: list) -> None:
    st.subheader("Reality check - definition vs observed")
    st.caption(
        "Observed values are a bundled sample. Connect a warehouse to diff declared "
        "definitions against live data."
    )
    mism = [d for d in diffs if d.status == "mismatch"]
    if mism:
        st.markdown(
            f"<div style='font-size:14px;color:{PALETTE['fail_fg']};margin-bottom:8px;'>"
            f"{len(mism)} metric(s) drift from their declared definition.</div>",
            unsafe_allow_html=True,
        )
    st.markdown("".join(_diff_card_html(d) for d in diffs), unsafe_allow_html=True)
    st.button("Connect warehouse (coming soon)", disabled=True)


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
    source = st.sidebar.radio("Data source", ["Demo file", "Paste YAML", "Upload file"], index=0)
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
    st.markdown(
        "<h1 style='margin-bottom:0'>semlint</h1>"
        f"<div style='color:{PALETTE['muted']};font-size:15px;margin-bottom:10px;'>"
        "see when a metric means two different things - "
        "before your dashboards and AI agents do</div>",
        unsafe_allow_html=True,
    )

    yaml_text = resolve_input()
    if not yaml_text or not yaml_text.strip():
        st.info("Pick a data source on the left: load the demo, paste YAML, or upload a file.")
        return
    try:
        metrics, dims = load_metrics_text(yaml_text)
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not parse this YAML: {exc}")
        return
    if not metrics:
        st.warning("Parsed, but found no metrics. Add a `metrics:` list.")
        return

    result = run_audit(metrics, dims)
    observations = load_observations(str(REALITY)) if REALITY.exists() else {}
    diffs = build_diffs(metrics, observations)
    issues = sorted(
        (f for f in result.findings if f.severity is not Severity.PASS), key=priority_key
    )

    render_hero(result, issues)
    st.divider()
    render_reality(diffs)
    st.divider()
    render_fix_first(issues)
    st.divider()
    render_findings(result)
    st.divider()
    render_export(result)


main()
