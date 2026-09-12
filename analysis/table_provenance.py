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
    for part in dotted.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"{source} output has no field {dotted!r} (missing at {part!r})")
        node = node[part]
    return node
