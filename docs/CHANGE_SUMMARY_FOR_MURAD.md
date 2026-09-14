# Change summary — corrected revision, for review before it goes to the reviewer

One page. The full detail is in `docs/REVIEW_NOTES.md`; the point-by-point
replies are in `docs/REVIEWER_RESPONSE.md`.

## The three changes that matter

**1. Execution convention restored to the published specification.** Reviewer 3
objected that the previous draft observed the signal at the Friday close and
executed at that same close, which cannot be done. A position is now realised at
the **first executable trading-session open after its Friday signal** — the Monday
open where available, the next session open after a holiday. Signal and decision
timing are unchanged. Executable sample 503 weeks of a 504-week panel.

**This moves every performance figure.** Cumulative gross **−6.64% → −0.73%**,
Sharpe **−0.153 → +0.005**, drawdown −12.56% → −10.64%. The position path is
identical — same 15 episodes, 55 exposed weeks, 61 legs — only the returns differ.

**2. The economic conclusion is stated more weakly, and more accurately.** The
paper no longer says the rule loses money; it says the analysis **does not
establish a robust exploitable edge**. At −0.73% with a Sharpe indistinguishable
from zero, that is what the evidence supports. There is still no break-even cost,
because the gross return is still negative. Reality Check *p* = 0.30 and SPA
*p* = 0.58 on the twelve-strategy universe.

**3. Specification sensitivity is now the paper's strongest finding, and one
pre-specified variant is profitable.** Four pre-specified readings of the entry
rule span **9.04 percentage points including a change of sign**: published hybrid
−0.73%, pure-fast −3.48%, **pure-pricing +5.57%**, equal-threshold −1.65%.

The earlier claim that the failure is robust to symmetrization is **withdrawn**.
Pure-pricing is reported because a pre-registration committed before any of these
figures existed required all three variants to be disclosed whatever they
returned. It is **not** presented as a preferred strategy: no comparative
inference among the four was pre-specified or run, and nothing establishes that it
has positive expected alpha. The conclusion drawn is that the economic result is
not stable across the pre-specified entry-rule constructions.

## Two claims withdrawn or demoted

**The momentum loading is demoted and no longer significant.** Reviewer 3 observed
that the in-position sample is selected by the strategy's own entry rules, which
are functions of the same prices the momentum factor is built from. It is reported
as a mechanical property of the entry rules, excluded from the contribution, and
under the reported bootstrap reaches *p* = 0.0506 — clearing no conventional
threshold. The dollar proxy now loads more strongly than momentum on in-position
weeks; the selection problem applies to every coefficient in that regression
equally, so none is offered as an identified exposure.

**Newey–West is withdrawn, not retained as robustness.** The in-position weeks are
non-contiguous. Reported inference is CR2 with Bell–McCaffrey degrees of freedom
and a restricted wild cluster bootstrap.

## Unchanged conclusions

The asymmetry inventory (one of five signals survives dependence-robust
inference), the tail-aggregation sensitivity, the walk-forward inertness, and the
EVT section. The EVT analysis characterises the market return series — absolute
Friday-close-to-Friday-close EUR/JPY returns — and is deliberately independent of
the execution convention; ξ = −0.25 on an interval too wide to distinguish
bounded from heavy tails, so nothing is read into its sign.

## Verification

82 deterministic tests plus a network check. Twelve of the nineteen manuscript
tables have every cell tied to a named field of the replication output, so a value
that stops matching fails a test; the remaining seven are checked less formally
and the paper says so. Build is clean at 37 pages.

## Decisions still open for you

`docs/MURAD_DECISIONS.md` carries five: tail-signal aggregation, symmetrization
placement, raw-data licensing, version and DOI supersession, and repository script
convention. Execution timing is closed — you ruled on it and the branch implements
it.
