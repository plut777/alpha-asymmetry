"""Semantic provenance for manuscript table cells: PROTOTYPE, one table only.

The rejected bag-of-values audit (see ``rejected_provenance_audit.py``) asked
"does this number appear somewhere in canonical output?"  With thousands of
lookup keys the answer is yes for essentially any plausible number, so it
accepted a fabricated table row without complaint.

This module inverts the question.  Every numeric cell must have a *declared*
field path, and the check fails when a cell has no declaration.  The failure
mode being detected is **absence of a source**, not disagreement between two
numbers that happen to look alike.  A new row pasted into a table fails
immediately, because nothing declares where its numbers came from.

Three kinds of provenance are distinguished:

``field path``   a dotted path into canonical pipeline output.
``EXTERNAL``     a value that is not pipeline output and must not be forced into
                 it: an externally sourced figure, a historical number from an
                 earlier draft, or a fixed declared parameter.  Carries a reason
                 string, which is the provenance.
``NOT_NUMERIC``  a cell carrying no empirical value, such as an em-dash.

Only ``tab:sevariants`` is declared so far.  This is a prototype for costing,
not a completed mechanism; the other tables are inventoried in REVIEW_NOTES.md.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Canonical outputs a field path may name, as "source:dotted.path". A bare path
# means the pipeline results, which is the default source.
SOURCES = {
    "pipeline": ROOT / "full_pipeline_results.json",
    "entry_symmetry": ROOT / "entry_symmetry_results.json",
}
CANONICAL = SOURCES["pipeline"]

NOT_NUMERIC = object()


class EXTERNAL:
    """A value whose provenance is real but is not pipeline output."""

    def __init__(self, reason: str):
        self.reason = reason


_IP = "factor_attribution.in_position"

_WF = "walk_forward"
_TCOST = "transaction_costs"

_WINDOW = EXTERNAL(
    "expanding training window implied by the walk-forward protocol: 2016 to the "
    "year before the test year. Determined by the design, not emitted as a field")


def _oos_row(i: int) -> dict:
    """Row label carries the test year; cells are window, threshold, new episodes."""
    return {"label": [f"{_WF}.rows[{i}].year"],
            "cells": [[_WINDOW, _WINDOW],
                      f"{_WF}.rows[{i}].threshold",
                      f"{_WF}.rows[{i}].new_episodes"]}


def _tcost_row(i: int) -> dict:
    return {"label": [], "cells": [f"{_TCOST}.rows[{i}].pips",
                                   f"{_TCOST}.rows[{i}].net_return",
                                   f"{_TCOST}.rows[{i}].sharpe"]}


_AS = "alpha_statistics"
_TC = "tail_construction_sensitivity.constructions"

_ALPHA_ROWS = {"Tail": "tail_alpha", "Fast": "fast_alpha", "Pricing": "pricing_alpha",
               "Coverage": "coverage_alpha", "Hedge": "hedge_alpha"}


def _tests_row(key: str) -> dict:
    """gamma-hat, iid t, block CI (one cell, two values), SW, JB, K2, Ljung-Box Q(4)."""
    return {"label": [], "cells": [
        f"{_AS}.{key}.skew", f"{_AS}.{key}.skew_t_iid",
        [f"{_AS}.{key}.skew_ci[0]", f"{_AS}.{key}.skew_ci[1]"],
        f"{_AS}.{key}.sw", f"{_AS}.{key}.jb", f"{_AS}.{key}.k2", f"{_AS}.{key}.lb_q4"]}


def _boot_row(key: str) -> dict:
    """gamma-hat, normal-theory SE, iid bootstrap SE, iid CI, block CI."""
    return {"label": [], "cells": [
        f"{_AS}.{key}.skew", f"{_AS}.{key}.normal_theory_se", f"{_AS}.{key}.skew_boot_se_iid",
        [f"{_AS}.{key}.skew_ci_iid[0]", f"{_AS}.{key}.skew_ci_iid[1]"],
        [f"{_AS}.{key}.skew_ci[0]", f"{_AS}.{key}.skew_ci[1]"]]}


def _tailagg_row(key: str) -> dict:
    return {"label": [], "cells": [
        f"{_TC}.{key}.nonzero_obs", f"{_TC}.{key}.skew", f"{_TC}.{key}.ex_kurt",
        f"{_TC}.{key}.ai",
        [f"{_TC}.{key}.skew_ci[0]", f"{_TC}.{key}.skew_ci[1]"]]}


_BM = "benchmarks"
_BM_COLS = ("ret", "vol", "sharpe", "sortino", "mdd")
_SNOOP = "data_snooping"


def _bench_row(key: str) -> dict:
    return {"label": [], "cells": [f"{_BM}.{key}.{c}" for c in _BM_COLS]
            + [[f"{_BM}.{key}.holding_episodes", f"{_BM}.{key}.execution_legs"]]}


_FA = "factor_attribution"

_FACTOR_VARS = {"Intercept": "const", "Carry": "carry", "Momentum": "mom", "Dollar": "dollar"}


def _factor_row(var: str) -> dict:
    return {"label": [], "cells": [
        f"{_FA}.full.coef.{var}.b", f"{_FA}.full.coef.{var}.t",
        f"{_FA}.in_position.coef.{var}.b", f"{_FA}.in_position.coef.{var}.t",
    ]}


_SYM = "entry_symmetry:variants"

_SYM_COLUMNS = ("return", "net_return", "sharpe", "mdd", "holding_episodes",
                "in_position_weeks", "mean_gross_return_per_in_position_week_bps")


def _sym_row(key: str) -> dict:
    return {"label": [], "cells": [f"{_SYM}.{key}.{col}" for col in _SYM_COLUMNS]}


_ET = "execution_timing.timings"

_EXEC_COLUMNS = ("cumulative_return", "mean_weekly_bps", "sharpe", "mdd", "net_return_2p0_pips")


def _exec_row(key: str) -> dict:
    return {"label": [], "cells": [f"{_ET}.{key}.{col}" for col in _EXEC_COLUMNS]}


PROVENANCE = {
    # Formerly the only table in the manuscript with no canonical source at all:
    # the execution-timing grid was computed by a standalone script that was never
    # committed.  The computation now lives in full_pipeline.execution_timing_grid
    # and all twenty cells were verified to reproduce the committed figures exactly
    # before this mapping was declared.
    # Generated from analysis/entry_symmetry_results.json at insertion time rather
    # than transcribed, so the declaration below records a mapping that already held.
    # Execution-independent by construction: these read the alpha signal series and
    # the daily exceedance rule, never weekly_return, and the panel's row count is
    # set by dropna on the three alpha columns. Adopting a different execution
    # convention does not touch them. A mapping is field paths rather than values,
    # so it also survives a rerun that changes the values.
    # Execution-dependent, and mapped deliberately as a Friday-close snapshot.
    # The canonical paths do NOT name a timing: weekly_return is set in one place
    # in build_weekly_alphas and every consumer reads it, so these paths denote
    # "the primary specification's" walk-forward and cost results and would carry
    # Monday-open values automatically if the baseline switched. The paths keep
    # denoting the same manuscript quantity across that change; only the values
    # move. Contrast execution_timing.timings.friday_close.*, which names a
    # specific timing on purpose.
    "tab:oos": {
        **{str(2018 + i): _oos_row(i) for i in range(8)},
        "Eight test years": {"label": [], "cells": [
            NOT_NUMERIC,
            EXTERNAL("summary of the eight rows above, not a separate field"),
            f"{_WF}.pooled.new_episodes"]},
    },
    "tab:tcosts": {
        "Zero Cost": _tcost_row(0), "Prime": _tcost_row(1), "Institutional": _tcost_row(2),
        "Tight": _tcost_row(3), "Wide": _tcost_row(4),
    },
    "tab:tests": {name: _tests_row(key) for name, key in _ALPHA_ROWS.items()},
    "tab:bootcompare": {name: _boot_row(key) for name, key in _ALPHA_ROWS.items()},
    "tab:tailagg": {
        "Friday observation": _tailagg_row("friday_sampled"),
        "signed sum": _tailagg_row("all_days_signed_sum"),
        "largest": _tailagg_row("all_days_largest_abs"),
    },
    "tab:backtest": {
        "Asymmetry": _bench_row("Asymmetry"),
        "Momentum (20w)": _bench_row("Momentum (20w)"),
        "Mean Rev": _bench_row("Mean reversion (2.0 sigma)"),
        "Buy": _bench_row("Buy and hold"),
    },
    # The same two test names appear twice: once for the twelve-strategy formal
    # universe and once for the thirteen-candidate diagnostic. They are declared
    # by occurrence so the two cannot be confused for one another.
    "tab:snooping": {
        "White": {"label": [], "occurrences": 2, "occurrence": 0,
                  "cells": [f"{_SNOOP}.real_only.white_rc_stat", f"{_SNOOP}.real_only.white_rc_p"]},
        "Hansen": {"label": [], "occurrences": 2, "occurrence": 0,
                   "cells": [f"{_SNOOP}.real_only.spa_stat", f"{_SNOOP}.real_only.spa_p"]},
        "Candidate Strategies": {"label": [], "cells": [f"{_SNOOP}.real_only.n_strategies"]},
    },
    "tab:factors": {
        **{name: _factor_row(var) for name, var in _FACTOR_VARS.items()},
        "R^2": {"label": [], "cells": [f"{_FA}.full.r2", f"{_FA}.in_position.r2"]},
        "F-statistic": {"label": [], "cells": [f"{_FA}.full.f", f"{_FA}.in_position.f"]},
    },
    "tab:entrysymmetry": {
        "Published hybrid": _sym_row("published"),
        "Pure-fast": _sym_row("pure_fast"),
        "Pure-pricing": _sym_row("pure_pricing"),
        "Equal-threshold": _sym_row("equal_threshold"),
    },
    "tab:exectiming": {
        "Friday close": _exec_row("friday_close"),
        "Monday open": _exec_row("monday_open"),
        "Monday close": _exec_row("monday_close"),
        "Tuesday open": _exec_row("tuesday_open"),
    },
    "tab:sevariants": {
        # row-matching substring -> (label values, cell provenance in column order)
        "Wild cluster bootstrap": {
            "label": [],
            "cells": [
                f"{_IP}.coef.mom.b",
                NOT_NUMERIC,  # SE deliberately not reported for the bootstrap row
                f"{_IP}.wild_cluster_bootstrap.mom.observed_t",
                f"{_IP}.wild_cluster_bootstrap.mom.p",
            ],
        },
        "CR2": {
            "label": [f"{_IP}.coef.mom.dof"],
            "cells": [
                f"{_IP}.coef.mom.b",
                f"{_IP}.coef.mom.se",
                f"{_IP}.coef.mom.t",
                f"{_IP}.coef.mom.p",
            ],
        },
        "HC3": {
            "label": [],
            "cells": [
                f"{_IP}.robustness_hc3.mom.b",
                f"{_IP}.robustness_hc3.mom.se",
                f"{_IP}.robustness_hc3.mom.t",
                f"{_IP}.robustness_hc3.mom.p",
            ],
        },
        "Newey-West HAC": {
            "label": [],
            "cells": [
                f"{_IP}.withdrawn_hac.mom.b",
                f"{_IP}.withdrawn_hac.mom.se",
                f"{_IP}.withdrawn_hac.mom.t",
                f"{_IP}.withdrawn_hac.mom.p",
            ],
        },
    }
}


def canonical() -> dict:
    """Every canonical source, keyed by name."""

    return {name: json.loads(path.read_text()) for name, path in SOURCES.items()}


def resolve(path: str, data: dict | None = None):
    """Look up ``source:dotted.path``. Raises KeyError when the field is absent.

    A bare dotted path resolves against the pipeline results. The KeyError is the
    point of the whole mechanism: a cell naming a field that does not exist fails
    here rather than being silently matched against some equal-looking number.
    """

    all_sources = data if data is not None else canonical()
    source, _, dotted = path.rpartition(":")
    source = source or "pipeline"
    if source not in all_sources:
        raise KeyError(f"unknown canonical source {source!r} in field path {path!r}")
    node = all_sources[source]
    # Some canonical keys contain dots of their own, e.g. the benchmark named
    # "Mean reversion (2.0 sigma)". Resolution is therefore greedy: at each level
    # the longest matching key wins, so a dotted key is not split through.
    parts = dotted.split(".")
    i = 0
    while i < len(parts):
        for j in range(len(parts), i, -1):
            candidate = ".".join(parts[i:j])
            index = None
            bracket = re.match(r"^(.*)\[(\d+)\]$", candidate)
            if bracket:
                candidate, index = bracket.group(1), int(bracket.group(2))
            if isinstance(node, dict) and candidate in node:
                node = node[candidate]
                if index is not None:
                    if not isinstance(node, list) or index >= len(node):
                        raise KeyError(
                            f"{source}: {candidate!r} is not a list with index {index}")
                    node = node[index]
                i = j
                break
        else:
            raise KeyError(
                f"{source} output has no field {dotted!r} (missing at {parts[i]!r})")
    return node


# ---------------------------------------------------------------------------
# Prose statistics
#
# Two of the first three provenance defects found were not in tables at all.
# They were t-statistics in running text that stayed at their Newey-West values
# after the reported inference moved to CR2, while the table beside them was
# regenerated correctly.  Tables get rebuilt wholesale; prose is edited by hand,
# which makes it the higher-risk surface and the one with no mechanism.
#
# Each declared claim carries a regex that anchors it in the manuscript, the
# canonical field it must equal, and the number of occurrences expected.  The
# occurrence count matters as much as the value: it is what makes a *new*
# undeclared instance of a declared family fail, rather than being ignored.
#
# COVERAGE_PATTERNS close the remaining gap for the highest-risk family. Every
# numeric t-statistic in the manuscript must fall inside some declared claim, so
# a t-statistic of a family nobody declared fails rather than passing unseen.
# This does not extend to every number in prose; percentages, counts and
# coefficients outside a declared claim remain uncovered, and that limit is
# deliberate rather than overlooked.
# ---------------------------------------------------------------------------

PROSE_CLAIMS = [
    {
        "name": "in-position intercept t-statistic",
        "pattern": r"\$t = (-?\d+\.\d+)\$ on in-position weeks",
        "field": "factor_attribution.in_position.coef.const.t",
        "occurrences": 2,
    },
    {
        "name": "full-sample intercept t-statistic",
        "pattern": r"\$t = (-?\d+\.\d+)\$ full sample",
        "field": "factor_attribution.full.coef.const.t",
        "occurrences": 1,
    },
    {
        "name": "original preprint momentum t, full sample",
        "pattern": r"\(\$t = (-?\d+\.\d+)\$, \$p = 0\.71\$\)",
        "external": EXTERNAL(
            "value as published in the original preprint under the earlier "
            "specification, quoted to identify what changed; not an output of "
            "the current pipeline and must not be forced into one"),
        "occurrences": 1,
    },
    {
        "name": "original preprint momentum t, in position",
        "pattern": r"\(\$t = (-?\d+\.\d+)\$, \$p = 0\.61\$\)",
        "external": EXTERNAL(
            "value as published in the original preprint under the earlier "
            "specification; not an output of the current pipeline"),
        "occurrences": 1,
    },
]

# Families where every occurrence in the manuscript must be declared above.
COVERAGE_PATTERNS = {
    "numeric t-statistic": r"\$t = (-?\d+\.\d+)\$",
}
