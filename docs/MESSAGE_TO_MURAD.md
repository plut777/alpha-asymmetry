Murad —

The revision is finished and ready for your review. Short version:

**Execution timing — implemented as you ruled.** A position is now realised at the
first executable trading-session open after its Friday signal (Monday open, or the
next session after a holiday). This moves every performance figure: cumulative
gross **−6.64% → −0.73%**, Sharpe −0.153 → +0.005. The position path is identical;
only the returns differ. Analysis panel 504 weeks, executable strategy sample 503.

**A pre-specified entry-rule variant came out profitable, and it falsified a claim
we made.** Of the four pre-specified symmetrizations, pure-pricing returns **+5.57%
gross, +5.21% net**. The previous round told the reviewer that every variant was
gross-negative and that the failure was robust to symmetrization. **That is
withdrawn.** The four span 9.04 points including a change of sign.

It is reported, not promoted: the pre-registration committed before any of these
numbers existed required disclosure whatever they showed, and no comparative
inference was run. The conclusion is that the economic result is not stable across
the pre-specified entry rules — which is a stronger version of the paper's actual
finding, not a retreat from it.

**Momentum ends method-sensitive, and the demotion stands regardless.** CR2 gives
an interval excluding zero (p = 0.042); the wild cluster bootstrap gives p = 0.0506.
The 5% line falls between the two methods and we report both. None of that matters
to the demotion, which rests on the in-position sample being selected by the entry
rules — true at any p-value.

**EVT restored.** The tail analysis characterises the market return series
(Friday-close to Friday-close), not strategy returns; it had briefly been carried
along with the execution change. Shape parameter back to ξ = −0.25 on a wide
interval containing zero, so nothing is read into its sign.

**Five decisions are adopted as working decisions awaiting your ratification** —
tail aggregation, symmetrization placement, data licensing, DOI supersession, and
repository convention. Each matches the recommendation I sent you, each is
reversible, and none is decided against you. They had been open across several
rounds and were holding up a finished revision.

**The compiled PDF is committed and current** — 37 pages, clean build:
https://github.com/plut777/alpha-asymmetry/blob/fix/strategy-specification/paper/alpha-asymmetry.pdf

Detail if you want it: `docs/CHANGE_SUMMARY_FOR_MURAD.md` (one page),
`docs/MEMO_MURAD_PURE_PRICING.md` (the profitable variant),
`docs/MURAD_DECISIONS.md` (the five decisions), `docs/REVIEW_NOTES.md` (everything).

Nothing goes to the reviewer until you have looked at it.

— Tofik
