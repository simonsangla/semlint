from __future__ import annotations

from pathlib import Path

import streamlit as st

from semlint.engine import audit_file

st.set_page_config(page_title="semlint - semantic-layer audit", layout="wide")
st.title("semlint")
st.caption("local-only semantic-layer / metric-definition audit (v0 heuristic score)")

path = st.text_input("metrics file", value="metrics_demo.yml")

if Path(path).exists():
    result = audit_file(path)
    counts = {"pass": 0, "warn": 0, "fail": 0}
    for f in result.findings:
        counts[f.severity.value] += 1
    st.metric("Semantic Trust Score", f"{result.score}/100")
    c1, c2, c3 = st.columns(3)
    c1.metric("fail", counts["fail"])
    c2.metric("warn", counts["warn"])
    c3.metric("pass", counts["pass"])
    rows = [
        {
            "rule": f"{f.rule_id} {f.rule_name}",
            "severity": f.severity.value,
            "metric": f.metric or "-",
            "finding": f.message,
            "remediation": f.remediation or "-",
        }
        for f in result.findings
    ]
    st.dataframe(rows, use_container_width=True)
else:
    st.warning(f"file not found: {path}")
