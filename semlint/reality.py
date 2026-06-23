from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Diff:
    metric: str
    declared: str
    observed: str | None
    status: str
    delta_pct: float | None
    note: str


_STATUS_RANK = {"mismatch": 0, "not_checked": 1, "match": 2}


def _norm(formula: str) -> str:
    return " ".join((formula or "").split()).upper()


def load_observations(path: str) -> dict[str, dict]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    obs: dict[str, dict] = {}
    for o in data.get("observations") or []:
        if isinstance(o, dict) and o.get("metric"):
            obs[o["metric"]] = o
    return obs


def _first_declared(metrics: list[dict]) -> dict[str, str]:
    declared: dict[str, str] = {}
    for m in metrics:
        name = m.get("name")
        if name and name not in declared:
            declared[name] = str(m.get("formula") or "")
    return declared


def build_diffs(metrics: list[dict], observations: dict[str, dict]) -> list[Diff]:
    declared = _first_declared(metrics)
    out: list[Diff] = []
    for name in sorted(declared):
        decl = declared[name]
        obs = observations.get(name)
        if not obs:
            out.append(
                Diff(
                    name,
                    decl,
                    None,
                    "not_checked",
                    None,
                    "no observed data; connect a warehouse to check",
                )
            )
            continue
        observed = str(obs.get("observed_formula") or "")
        dv, ov = obs.get("declared_value"), obs.get("observed_value")
        delta = None
        if isinstance(dv, (int, float)) and isinstance(ov, (int, float)) and dv != 0:
            delta = round((ov - dv) / dv * 100, 1)
        formula_diff = _norm(observed) != _norm(decl)
        value_diff = delta is not None and abs(delta) > 0.5
        if formula_diff or value_diff:
            status, note = "mismatch", "declared and observed disagree"
        else:
            status, note = "match", "declared matches observed"
        out.append(Diff(name, decl, observed or None, status, delta, note))
    out.sort(key=lambda d: (_STATUS_RANK[d.status], d.metric))
    return out
