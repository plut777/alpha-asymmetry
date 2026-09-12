# Decisions for Murad

Six items. Each is a genuine author decision: a choice where the evidence does
not settle the answer, or where the answer is editorial. Anything with an
objectively preferable technical resolution has been fixed rather than listed
here, and is recorded in `docs/REVIEW_NOTES.md`.

Nothing below blocks the rest of the correction work.

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

## 2. Execution timing — Friday close or Monday open

**This recommendation reverses the position Tofik gave earlier in the review, and
reverses what an earlier draft of this list said. The reasons are set out below.**

**Asked:** The published specification entered at the **Monday open** following
Friday signal generation. This revision entered at the **Friday close** — the
same close at which the signal is observed.

**Reviewer 3 objects to the current convention** (round-two comment 5,
"Look-ahead bias from Friday close execution"):

> Executing at the same Friday close as the signal observation introduces a
> simultaneous execution assumption (or look-ahead bias) because in practice, one
> cannot observe the closing price, compute the rolling 20-week skewness and other
> indicators, and execute a trade at that exact same closing price.

He is describing a real mechanism, not a presentational preference. The rolling
statistics are computed *from* the Friday close, and the trade is then assumed to
happen *at* that same close.

**Recommendation: restore Monday open as the primary specification**, unless
Friday-close execution can be defended as genuinely executable using only
information available before that close. Two reasons, neither of which is about
which return estimate looks better:

1. **Specification fidelity.** Monday open is what the published paper specified.
   Departing from it is a change requiring justification, and the justification
   offered so far has been that it is convenient.
2. **Information timing.** Monday open cannot be executed on information that does
   not yet exist. Friday close, as implemented, can only be executed on
   information available at the instant of execution.

Keep Friday close, Monday close and Tuesday open as robustness timings. The grid
does **not** statistically identify a uniquely correct convention — the
pre-specified paired contrasts all include zero — so the primary choice should
rest on specification fidelity and information timing, not on which return
estimate is preferable.

### What it costs, computed rather than estimated

| | Friday close | Monday open |
|---|---|---|
| Cumulative gross return | **−6.64%** | **−0.73%** |
| Sharpe | −0.153 | **+0.005** |
| Maximum drawdown | −12.56% | −10.64% |
| Net at 2.0 pips | −7.02% | −1.14% |
| In-position weeks | 55 | 55 |
| Holding episodes | 15 | 15 |
| Execution legs | 61 | 61 |
| Turnover | 52.00 | 52.00 |

**The strategy's decisions do not change at all.** Same signal, same entries,
exits, sizing and exposure. Only which weekly return each position earns changes.

**You should weigh this before agreeing.** The paper's economic null currently
rests on a 6.64% gross loss. Under Monday open it is a 0.73% loss with a Sharpe
of essentially zero. The qualitative conclusion — no exploitable edge — survives
under both, and there is still no break-even cost because the gross return remains
negative. But "loses money before frictions" becomes a much weaker statement than
it is today, and the paper would need to say so plainly rather than lean on the
larger figure.

**Sample.** A Monday-open headline needs **n = 503**, dropping one week
(2025-08-29) because the last week has no following open. This is *not* the same
as the grid's common sample of 502, which drops two weeks only because every
timing needs a counterpart. The headline sample and the paired-comparison sample
should be determined separately; they do not have to match.

**Work.** 416 numeric fields in the replication output are strategy-derived and
recompute. 219 are signal- or market-derived and move only through the one-week
sample change. Mechanically this is one pipeline change and a full rerun, plus a
manuscript pass over every claim about realised performance. It is days, not
weeks — the machinery to switch conventions already exists and is tested.

**Manuscript claims needing recheck under it:** the abstract's performance
figures; the contribution statement's "loses money before frictions" and
walk-forward dormancy; the threshold-sensitivity grid; the cross-market strategy
returns; the data-snooping universe, which includes the strategy as a candidate;
the factor regression and therefore the momentum coefficient, though the
sample-selection argument that demotes it is structural and survives; the
transaction-cost table and the no-break-even claim; and every conclusion about
realised strategy performance.

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
