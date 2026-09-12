"""REJECTED. This is not a provenance check. Do not use it as one.

Kept as a documented negative result, because the way it failed is the useful
part: it looked like a working audit, produced a confident and clean-looking
report, and was incapable of detecting the defect it was built for.

WHAT IT DID
    For each numeric cell in a manuscript table it asked "does a number equal to
    this appear anywhere in canonical pipeline output, at any rounding or any of
    several rescalings?"  If yes, the cell was reported as traced.

WHY THAT IS WORTHLESS
    The lookup universe built this way holds 6,240 keys.  Measured against
    uniform random numbers of the shapes that actually occur in these tables:

        3dp coefficients in [-1, 1]      100.0% called "traced"
        3dp p-values / SEs in [0, 1]     100.0% called "traced"
        2dp percentages / t-stats        91.7%  called "traced"
        integers 1..200                  56.1%  called "traced"

    It was answering "is this number numerically unremarkable?", not "where did
    this number come from."

THE MUTATION TEST THAT CONDEMNED IT
    The fabricated CR1 row that had already reached this manuscript once
    (beta -0.823, SE 0.315, t -2.61, p 0.009, none of which any pipeline ever
    produced) was re-inserted into tab:sevariants.  This audit marked all four
    fabricated cells as traced, raised nothing, and its untraced count did not
    move.  Its whole-manuscript report of "7 untraced" was therefore
    uninformative, and the 7 were parser artefacts in any case.

WHAT REPLACED IT
    analysis/table_provenance.py, which requires every empirical cell to declare
    a named canonical field and fails when a cell has no declaration.  It detects
    absence of a source rather than presence of a numerical coincidence.  Run
    against the same fabricated row it fails immediately with "no declared
    provenance".

This file is retained for the audit record only.  It is deliberately not
importable as a check and refuses to run without an explicit flag.
"""

import sys

REJECTED = True
REASON = (
    "bag-of-values matching; non-discriminating; accepted a fabricated table row "
    "and called 100% of random 3-decimal coefficients traced"
)

if __name__ == "__main__":
    if "--demonstrate-failure" not in sys.argv:
        raise SystemExit(
            "REJECTED CHECK. This script does not verify provenance and must not be\n"
            f"used as if it did. Reason: {REASON}.\n"
            "Use analysis/table_provenance.py instead.\n"
            "To reproduce the failure for the audit record, pass --demonstrate-failure."
        )
    print(__doc__)
