# Decisions for Murad

**Status: all six are now closed as working decisions.** Execution timing was
ruled on by Murad directly. The remaining five are adopted as the recommendations
already set out below — his own recommendations in each case, so nothing is
decided against him — because they had been open across several rounds and were
holding up a revision that is otherwise finished.

**Every one is reversible, and Murad reviews the completed package before it goes
to the reviewer.** This is a decision to stop waiting, not a decision to proceed
without him. Where a choice would be expensive to reverse the cost is stated.

| # | Decision | Status |
|---|---|---|
| 1 | Tail aggregation: Friday-sampled remains primary; both all-days constructions remain disclosed sensitivity checks | working decision |
| 2 | Execution timing: first post-signal executable open | **ruled by Murad** |
| 3 | Entry symmetrization: remains in the main text | working decision |
| 4 | Raw Yahoo files: remain uncommitted absent affirmative redistribution permission | working decision |
| 5 | Versioning: new corrected version under the existing concept DOI, with explicit supersession | working decision |
| 6 | Repository convention: manuscript outputs must originate from the canonical pipeline; standalone scripts may not independently define published results | working decision |

The detail behind each follows, unchanged from when these were open questions.

---

## 1. Tail-signal aggregation — which construction is primary

**Asked:** The published tail signal flags exceedances daily but reads them only
on Fridays. Two all-trading-days alternatives give different answers, and across
the three the skewness point estimate **changes sign**.

**Two facts you should have before endorsing the framing.**

*Reviewer 3 raised this directly* (round-two comment 7, temporal aliasing). He is
right that a signal built from daily exceedances but read only on Fridays
discards most of what it detects, and that every statistic on the weekly series
inherits that sparsity. This is not an objection we went looking for.

*The published construction is the sparsest of the three.* Precisely:

| Construction | Skew | Dependence-robust CI | Excludes zero | Non-zero weeks |
|---|---|---|---|---|
| **Friday-sampled (published)** | −1.48 | [−3.10, +0.54] | no | **35** of 504 |
| All-days signed sum | +0.22 | [−0.72, +1.09] | no | 105 |
| All-days largest absolute | −1.14 | [−1.97, −0.09] | **yes** | 105 |

It uses a third of the observations the alternatives use, and it is one of the two
that fail to exclude zero. It is *not* the weakest by point estimate — it has the
largest magnitude of the three. The honest summary is that the published
construction is the sparsest and the only one of the three whose large point
estimate rests on 35 non-zero observations.

**Options:** (a) keep Friday-sampled as primary and report the sensitivity;
(b) adopt an alternative as primary; (c) present all three with no primary.

**Recommendation: (a), which is what the branch does.** Both alternatives redefine
the signal rather than correct it, and choosing one after seeing its result is the
specification search this paper criticises. The recommendation is unchanged by the
two facts above, but you should endorse it knowing them.

---

## 2. Execution timing — DECIDED: Monday open

**Status: ruled on by Murad. He agreed to restore Monday open as the primary
specification.** This item is closed and is retained as the record of what was
asked and what was decided, not as an open question.

The branch implements the decision. A Friday signal is realised from the first
trading-session open strictly after it — the Monday open in an ordinary week, and
the next available session open when that Monday is a holiday — held to the first
open after the following Friday. The signal and decision timing are unchanged;
only the price pair used to realise the return changed.

**What prompted it.** Reviewer 3's round-two comment 5, "Look-ahead bias from
Friday close execution":

> Executing at the same Friday close as the signal observation introduces a
> simultaneous execution assumption (or look-ahead bias) because in practice, one
> cannot observe the closing price, compute the rolling 20-week skewness and other
> indicators, and execute a trade at that exact same closing price.

**Grounds for the decision**, neither of which is about which return estimate
looks better: specification fidelity, since Monday open is what the published
paper specified; and information timing, since Monday open cannot be executed on
information that does not yet exist. The pre-specified paired contrasts in the
execution grid all include zero, so the grid does not identify a uniquely correct
convention and the choice could not rest on it.

Friday close, Monday close and Tuesday open are retained as robustness timings.

**What it cost, as realised.** Cumulative gross moved from −6.64% to −0.73%,
Sharpe from −0.153 to +0.005, drawdown from −12.56% to −10.64%. The position path
is unchanged: 15 episodes, 55 exposed weeks, 61 legs, turnover 51.996835. The
executable sample is 503 weeks; the panel remains 504.

**The consequence that needs stating in the paper.** The economic null previously
rested on a 6.64% gross loss and now rests on 0.73% with a Sharpe indistinguishable
from zero. The qualitative conclusion survives and there is still no break-even
cost, but "loses money before frictions" is a much weaker statement than it was,
and the manuscript must say so rather than lean on the former figure.

---

## 3. Entry-rule symmetrization — where it belongs

**Asked:** The long and short legs differ in four respects the manuscript never
argued for. Three symmetrizations were pre-specified and run; all four rules lose
money gross, with realised losses spanning 6.21 points.

**Options:** main text (current: new §4.6 and Table 12), appendix, or the
response letter only.

**Recommendation: keep it in the main text.** It is the most direct answer to
Reviewer 3's comment and the pre-registration is what makes it credible. Placement
is presentation, not evidence — decide on conceptual relevance, and note that the
reporting rule fixed in advance requires disclosure wherever it lands.

---

## 4. Raw data — commit it or not

**Asked:** The raw CSVs are currently gitignored and not committed. Exact
reproduction of the archived figures is therefore impossible without your files;
the pipeline caches inputs and records SHA-256 hashes and software versions
instead.

**Options:** (a) leave uncommitted, readers re-download and verify against the
manifest; (b) commit the CSVs.

**Recommendation: (a) unless you have checked Yahoo's redistribution terms.** This
is a licensing question about data you sourced, which is why it is yours and not
mine to settle. Seven of eight files reproduce byte-for-byte on an independent
download, so (a) is workable.

---

## 5. Version, DOI and supersession

**Asked:** The corrected results change every headline figure. The concept DOI
resolves to the latest version; v2.0.1 is deposited.

**Options:** (a) new version under the same concept DOI with a supersession note;
(b) withdraw and replace the deposited record.

**Recommendation: (a).** The published version should remain citable and visibly
superseded rather than disappear — a paper arguing for transparent correction
should not erase its own record. The mechanics are yours.

---

## 6. Standalone analysis scripts — form only

**Asked:** The execution-timing grid had been produced by a script that was never
committed, leaving 21 numbers in a headline exhibit with no traceable source.
**The defect is fixed**: the computation now lives in the pipeline and reproduces
every committed figure exactly.

**Options:** whether the repository should keep any standalone analysis scripts at
all, or require everything to run through `full_pipeline.py`.

**Recommendation: require the pipeline.** This is a repository-convention question
rather than a result; raised only because the convention is yours to set.

---

## Not asked of you

These were fixed rather than referred, because each had an objectively correct
resolution settled by the canonical output: three stale or mis-transcribed
statistics, an inferential claim stated as a realised one, a paragraph reasoning
from a superseded candidate universe, and the dead exit branch, double execution
lag and sizing defects from the first round. `docs/REVIEW_NOTES.md` records each
with its origin and class.

One small editorial item I intend to fix unless you object: `tab:gpd` is
referenced nowhere in the text. It should be cited where its numbers are
discussed, or cut.
