"""The manuscript's specification table must match the code's parameters.

Reviewer 3 found a sizing parameter that existed only in code.  This test makes
that class of divergence impossible: the table in the paper is generated from
analysis/specification.py, and this asserts the file still contains exactly what
that module produces.
"""

import pathlib
import re

from analysis.specification import BY_KEY, latex_rows

PAPER = pathlib.Path(__file__).resolve().parents[1] / "paper" / "alpha-asymmetry.tex"


def _table_body() -> str:
    text = PAPER.read_text(encoding="utf-8")
    block = text.split(r"\label{tab:spec}")[1].split(r"\end{tabular}")[0]
    body = block.split(r"\midrule")[1].split(r"\bottomrule")[0]
    return body.strip()


def test_specification_table_matches_the_code():
    assert _table_body() == latex_rows().strip()


def test_key_parameters_match_the_values_the_pipeline_uses():
    from analysis import full_pipeline as fp
    from analysis import strategy as st

    assert BY_KEY["max_holding_weeks"] == 4
    assert BY_KEY["min_episodes"] == fp.MIN_EPISODES_FOR_INFERENCE
    assert BY_KEY["seed"] == fp.SEED
    assert [float(x) for x in BY_KEY["threshold_grid"].split(", ")] == fp.GRID
    assert BY_KEY["sizing_mode"] in st.SIZING_MODES
    assert (BY_KEY["position_lower"], BY_KEY["position_upper"]) == (1.0, 2.0)
    assert st.position_size(float("nan")) == BY_KEY["position_lower"]


def test_ai_window_is_stated_in_the_manuscript():
    text = PAPER.read_text(encoding="utf-8")
    assert f"trailing {BY_KEY['ai_window']}-week window" in text
    assert f"minimum of {BY_KEY['ai_minobs']} observations" in text
