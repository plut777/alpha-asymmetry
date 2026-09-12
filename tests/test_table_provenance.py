"""Every declared table cell must trace to a named canonical field.

PROTOTYPE covering tab:sevariants only.  The defect being guarded against is a
row typed into a table by hand with no computation behind it: that is how a
fabricated CR1 row entered this table and survived a clean LaTeX build and a
fully passing suite.

The guard is that an undeclared row FAILS.  A check that only compares declared
numbers would pass a fabricated row by ignoring it, so the test below asserts
coverage first and values second.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from analysis.table_provenance import EXTERNAL, NOT_NUMERIC, PROVENANCE, canonical, resolve

TEX = Path(__file__).resolve().parents[1] / "paper" / "alpha-asymmetry.tex"
NUMBER = re.compile(r"-?\d+\.?\d*")


def _table_rows(label: str):
    """(row label, [raw cells]) for each body row of the named table."""

    text = TEX.read_text()
    table = text.split(rf"\label{{{label}}}")[1].split(r"\end{tabular}")[0]
    body = table.split(r"\midrule", 1)[1] if r"\midrule" in table else table
    rows = []
    for raw in body.split(r"\\"):
        line = re.sub(r"\\(midrule|bottomrule|toprule)", "", raw).strip()
        if "&" not in line:
            continue
        parts = line.split("&")
        rows.append((parts[0].strip(), [p.strip() for p in parts[1:]]))
    return rows


def _numbers(cell: str):
    clean = re.sub(r"\\(textbf|emph|text)\{([^}]*)\}", r"\2", cell)
    clean = clean.replace("$-$", "-").replace("---", " ").replace("--", " ")
    clean = clean.replace(r"\%", " ").replace("$", " ")
    return NUMBER.findall(clean)


def _decimals(shown: str) -> int:
    return len(shown.split(".")[1]) if "." in shown else 0


@pytest.mark.parametrize("label", sorted(PROVENANCE))
def test_every_row_has_declared_provenance(label):
    """Coverage first: a row nobody declared is a row nobody computed."""

    declared = PROVENANCE[label]
    for row_label, _ in _table_rows(label):
        if not _numbers(row_label) and not any(
            key.lower() in row_label.lower() for key in declared
        ):
            # a pure text row carrying no numbers is not an empirical claim
            continue
        assert any(key.lower() in row_label.lower() for key in declared), (
            f"{label}: row {row_label!r} has no declared provenance. Every empirical "
            f"row must name the canonical field its numbers come from; a row with no "
            f"declaration has no evidence that it was computed at all."
        )


@pytest.mark.xfail(
    strict=True,
    reason="Known unrepaired defect: tab:sevariants prints the HC3 t-statistic as "
    "-2.17 where canonical output is -2.164926, which rounds to -2.16. Found by "
    "this test on its first run. Reported and awaiting a repair decision; the "
    "manuscript is deliberately not being edited yet. strict=True so that this "
    "xfail fails once the value is corrected, forcing the marker's removal.",
)
@pytest.mark.parametrize("label", sorted(PROVENANCE))
def test_declared_cells_match_their_canonical_fields(label):
    data = canonical()
    for key, spec in PROVENANCE[label].items():
        rows = [r for r in _table_rows(label) if key.lower() in r[0].lower()]
        assert len(rows) == 1, f"{label}: expected exactly one {key!r} row, found {len(rows)}"
        row_label, cells = rows[0]

        # strip the row key first: "CR2" would otherwise read as the value 2
        label_text = re.sub(re.escape(key), " ", row_label, flags=re.I)
        for shown, path in zip(_numbers(label_text), spec["label"]):
            actual = resolve(path, data)
            dp = _decimals(shown)
            assert round(float(actual), dp) == round(float(shown), dp), (
                f"{label}/{key}: label shows {shown} but {path} is {actual}")

        shown_cells = [_numbers(c) for c in cells]
        assert len(shown_cells) >= len(spec["cells"]), (
            f"{label}/{key}: declared {len(spec['cells'])} cells, table has {len(shown_cells)}")

        for i, provenance in enumerate(spec["cells"]):
            nums = shown_cells[i]
            if provenance is NOT_NUMERIC:
                assert not nums, f"{label}/{key}: column {i} declared non-numeric but shows {nums}"
                continue
            assert nums, f"{label}/{key}: column {i} declares {provenance} but the cell is empty"
            shown = nums[0]
            if isinstance(provenance, EXTERNAL):
                continue
            actual = resolve(provenance, data)   # KeyError if the field does not exist
            dp = _decimals(shown)
            assert round(float(actual), dp) == round(float(shown), dp), (
                f"{label}/{key}: cell shows {shown} but {provenance} is {actual}")
