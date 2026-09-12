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
    # \multicolumn{2}{c}{0.011} must read as 0.011, not as the span count 2.
    clean = re.sub(r"\\multicolumn\{[^}]*\}\{[^}]*\}\{([^}]*)\}", r"\1", cell)
    clean = re.sub(r"\\(textbf|emph|text)\{([^}]*)\}", r"\2", clean)
    clean = clean.replace("$-$", "-").replace("---", " ").replace("--", " ")
    clean = clean.replace(r"\%", " ").replace("$", " ")
    return NUMBER.findall(clean)


def _norm(text: str) -> str:
    """Row labels carry math delimiters; '$F$-statistic' must match the key 'F-statistic'."""

    return text.replace("$", "").replace("\\", "").lower()


def _decimals(shown: str) -> int:
    return len(shown.split(".")[1]) if "." in shown else 0


@pytest.mark.parametrize("label", sorted(PROVENANCE))
def test_every_row_has_declared_provenance(label):
    """Coverage first: a row nobody declared is a row nobody computed."""

    declared = PROVENANCE[label]
    for row_label, cells in _table_rows(label):
        # A row is an empirical claim when its CELLS carry numbers. Testing the
        # label instead was a real defect here: a fabricated "Wednesday open" row
        # was skipped entirely because its label has no digits, while the earlier
        # fabricated "CR1" row was caught only because "CR1" happens to contain a
        # 1. Coverage must not depend on the spelling of a row name.
        if not any(_numbers(c) for c in cells):
            continue
        assert any(_norm(key) in _norm(row_label) for key in declared), (
            f"{label}: row {row_label!r} has no declared provenance. Every empirical "
            f"row must name the canonical field its numbers come from; a row with no "
            f"declaration has no evidence that it was computed at all."
        )


# Known unrepaired defects, marked per-table so that a clean table still fails
# loudly.  strict=True: correcting the value makes the xfail itself fail, which
# forces the marker to be removed rather than quietly masking the next defect.
KNOWN_DEFECTS: dict[str, str] = {
    # Empty by design. The -2.17 HC3 defect this originally held was corrected
    # once reported. Entries here are unrepaired defects only, and strict=True
    # means a repair makes the xfail itself fail, forcing the entry's removal
    # rather than letting it mask the next defect in the same table.
}

_VALUE_CASES = [
    pytest.param(label, marks=pytest.mark.xfail(strict=True, reason=KNOWN_DEFECTS[label]))
    if label in KNOWN_DEFECTS
    else pytest.param(label)
    for label in sorted(PROVENANCE)
]


@pytest.mark.parametrize("label", _VALUE_CASES)
def test_declared_cells_match_their_canonical_fields(label):
    data = canonical()
    for key, spec in PROVENANCE[label].items():
        rows = [r for r in _table_rows(label) if _norm(key) in _norm(r[0])]
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


# ---------------------------------------------------------------------------
# Prose statistics: same principle, applied to running text
# ---------------------------------------------------------------------------

from analysis.table_provenance import COVERAGE_PATTERNS, PROSE_CLAIMS  # noqa: E402


@pytest.mark.parametrize("claim", PROSE_CLAIMS, ids=lambda c: c["name"])
def test_prose_claim_occurs_as_declared_and_matches_canonical(claim):
    text = TEX.read_text()
    found = list(re.finditer(claim["pattern"], text))

    assert len(found) == claim["occurrences"], (
        f"{claim['name']}: declared {claim['occurrences']} occurrence(s), found "
        f"{len(found)}. A new occurrence is an undeclared claim; a missing one means "
        f"the declaration is stale. Either way the manuscript and this file disagree.")

    if "external" in claim:
        return  # provenance is the stated reason, not a pipeline field

    data = canonical()
    actual = resolve(claim["field"], data)
    for match in found:
        shown = match.group(1)
        dp = _decimals(shown)
        assert round(float(actual), dp) == round(float(shown), dp), (
            f"{claim['name']}: manuscript shows {shown} but {claim['field']} is "
            f"{actual}. This is the defect class that put a withdrawn Newey-West "
            f"t-statistic in the text beside a correctly regenerated table.")


@pytest.mark.parametrize("family", sorted(COVERAGE_PATTERNS))
def test_every_prose_statistic_of_a_covered_family_is_declared(family):
    """A statistic of a covered family that nobody declared must fail."""

    text = TEX.read_text()
    declared_spans = []
    for claim in PROSE_CLAIMS:
        declared_spans.extend(m.span() for m in re.finditer(claim["pattern"], text))

    for match in re.finditer(COVERAGE_PATTERNS[family], text):
        start, end = match.span()
        covered = any(d_start <= start and end <= d_end for d_start, d_end in declared_spans)
        line = text[:start].count("\n") + 1
        assert covered, (
            f"undeclared {family} {match.group(0)!r} at line {line}. Every statistic "
            f"of this family must name the canonical field it comes from; an "
            f"undeclared one has no evidence behind it.")
