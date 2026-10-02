from __future__ import annotations

import re
from pathlib import Path

from semlint.engine import audit_file

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
BUYER_HEADING = "## What the score means for a buyer"


def _buyer_section() -> str:
    assert BUYER_HEADING in README, "README is missing the buyer section"
    tail = README.split(BUYER_HEADING, 1)[1]
    return tail.split("\n## ", 1)[0]


def test_readme_documents_runnable_demo_command():
    assert "python -m semlint audit metrics_demo.yml" in README
    assert (ROOT / "metrics_demo.yml").is_file()


def test_readme_demo_score_matches_engine():
    section = _buyer_section()
    stated = re.findall(r"scores (\d+)/100", section)
    assert stated, "buyer section must state the demo score as 'scores N/100'"
    actual = audit_file(str(ROOT / "metrics_demo.yml")).score
    assert all(int(s) == actual for s in stated)


def test_buyer_section_states_limits():
    section = _buyer_section().lower()
    for phrase in ("does not", "heuristic", "no warehouse connection"):
        assert phrase in section, phrase
