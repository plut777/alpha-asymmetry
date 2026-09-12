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
CANONICAL = ROOT / "full_pipeline_results.json"

NOT_NUMERIC = object()


class EXTERNAL:
    """A value whose provenance is real but is not pipeline output."""

    def __init__(self, reason: str):
        self.reason = reason


_IP = "factor_attribution.in_position"

PROVENANCE = {
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
    return json.loads(CANONICAL.read_text())


def resolve(path: str, data: dict | None = None):
    """Look up a dotted field path. Raises KeyError when the field is absent."""

    node = data if data is not None else canonical()
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            raise KeyError(f"canonical output has no field {path!r} (missing at {part!r})")
        node = node[part]
    return node
