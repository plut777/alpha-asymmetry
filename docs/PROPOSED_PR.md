# Proposed pull request

<!-- reviewed-at: dca4f05d939b -->


## Title

Correct the strategy specification, regenerate all results, and address Reviewer 3

---

## Summary

The published code did not implement the strategy the published paper describes.
Three defects are corrected here. The largest of them meant that

> **the published strategy held a position in 25 of 504 weeks.**

It closed any open position the moment its entry signal stopped firing, which is
not the exit rule §2.4 states. Corrected, it holds a position in 55 weeks.

Every headline figure in the paper — the +3.60% return, the 0.149 Sharpe ratio,
the factor regression with its 25-observation effective sample, the "immaterial"
transaction costs, the 19.2-pip break-even — described that five percent of the
sample. That is why the published null result had so little content: a strategy
that is almost never invested cannot demonstrate much in either direction.

The corrected strategy **loses 6.64% gross** over the decade, Sharpe **−0.153**,
maximum drawdown **−12.56%**, across 15 holding episodes and 55 in-position
weeks. The corrected analysis preserves the paper's qualitative conclusion while
narrowing and strengthening the empirical basis for it.

**What this revision contributes**, stated as narrowly as the manuscript now
states it:

1. **A corrected implementation and corrected inference.** The strategy the
   paper describes is now the strategy the code runs, and the inference applied
   to it is appropriate to 15 clusters rather than to 504 independent weeks.
2. **One surviving asymmetry result.** Of five alpha signal types, only the
   volatility-expansion (coverage) signal has skewness that survives
   block-bootstrap inference under the paper's primary construction
   (γ̂₁ = 1.75, CI [1.18, 2.16]). The signed tail signal's point estimate is
   *negative* (−1.48), not the pronounced positive value published — the published
   figure described unsigned exceedance magnitude, which is right-skewed by
   construction. Its interval [−3.10, 0.54] includes zero, so this corrects a sign
   error rather than establishing negative skew.
3. **Documented specification sensitivity**, at magnitudes this sample cannot
   resolve, reported rather than resolved.

Two further results follow from the correction and are worth naming because they
replace published claims:

- **There is no break-even transaction cost.** Not a larger one — none. A
  break-even presumes a gross profit to be consumed, and there is none. This
  replaces the published 19.2-pip figure and is a cleaner statement of the null.
- **The economic null is starker, not softer.** Walk-forward selection leaves the
  rule nearly inert (one episode in eight out-of-sample years), and
  data-snooping-corrected tests do not reject the null of no superior performance
  against a zero-return benchmark across the twelve-strategy formal universe
  (Reality Check *p* = 0.30, SPA *p* = 0.25). This is a failure to reject, not a
  finding that every candidate's realised return was non-positive — several were
  positive, buy-and-hold among them.

**One candidate finding was demoted rather than reported.** The corrected factor
regression shows the rule loading negatively on time-series momentum while
invested. Reviewer 3 identified that the in-position sample is selected by the
strategy's own entry rules, which are functions of the same prices the momentum
factor is built from, so sample and regressor are jointly determined. The loading
is reported as **a mechanical property of the entry rules**, not as an
independently discovered factor exposure and not as an explanation of the
strategy's losses. It is explicitly excluded from the revision's empirical
contribution.

The sample is unchanged: n = 504, 8 January 2016 to 29 August 2025.

---

## How to read this PR

Changes are grouped so that each group can be accepted or rejected on its own:

- **(a) Implementation defects** — the paper said X, the code did Y, the code now
  does X. Three items. Nothing is in this group unless the published paper and
  the published code genuinely disagreed.
- **(b) Methodological changes proposed** — the paper and the code agreed, and
  this PR proposes something different. Three items, each reversible without
  disturbing (a).
- **(c) Manuscript corrections** — the code is defensible and the paper describes
  it wrongly.
- **(d) Prose corrected without a wrong figure.**
- **(e) Provenance footnotes restored.**

`docs/CORRECTION_CHANGELOG.md` has the full detail.
`analysis/before_after_results.csv` gives every changed figure with its published
value, its corrected value, and which category produced the change.

---

## (a) Implementation defects corrected

| | Paper (`4d21c69`) | Published code | Now |
|---|---|---|---|
| **a1** | "Exit: signal reversal OR 4-week maximum" | The hold branch was unreachable — its guard was always true — so positions closed as soon as the entry signal stopped firing | Holds through quiet weeks; reverses on the opposing signal; expires after four returns |
| **a2** | Entry one period after the Friday signal | Signals lagged inside the loop, then the position shifted again: two lags, while benchmarks used one | One lag everywhere — headline, benchmarks, walk-forward, factors, costs, snooping |
| **a3** | Equation 5: mean squared deviations about the overall mean | `pos.var()/neg.var()` — re-centres each subgroup, uses n−1, and returns a neutral-looking `1.0` where the statistic is undefined | Equation 5 as printed; undefined cases return missing |

a1 is the one that matters: 25 → 55 exposed weeks, and the dominant driver of
nearly every changed figure.

---

## (b) Methodological changes proposed

These are judgement calls. The published paper and the published code agreed in
each case; this PR proposes departing from them.

### b1. How to size a week in which a direction is held but no signal fires

Fixing a1 creates a state the published specification never had to describe,
because the published implementation could never reach it. The published rule was
"Rebalancing: Weekly (end of Friday close)" with Equation 10 evaluated at the
contemporaneous `AI_t`, and the published code did resize on every bar it held a
position — so paper and code agreed. Neither ever faced a *held but unsignalled*
week.

**Proposed:** evaluate the sizing equation weekly while a direction is held, as
the smaller of the two available extensions — it keeps the published rebalancing
frequency and the contemporaneous subscript, and changes no published sentence.
Freezing the notional at entry is the alternative; it is computed in the same run
and reported.

| | weekly (proposed) | frozen (alternative) |
|---|---|---|
| Gross return | −6.64% | −7.57% |
| Sharpe | −0.153 | −0.173 |
| Max drawdown | −12.56% | −14.29% |
| In-position weeks | 55 | 55 |
| Holding episodes | 15 | 15 |
| Turnover | 52.00 | 49.15 |

Entries, exits, direction and exposure are identical. **No conclusion depends on
the choice.** The argument against the proposal is in the changelog rather than
omitted.

### b2. "Trades" reported as holding episodes and execution legs

The published paper defined trades as "position-change events divided by two" and
the code implemented exactly that — but the label said "completed round trips",
which that formula does not compute. For the momentum benchmark it reported 27
round trips for 54 directional holdings and 107 executions.

**Proposed:** report holding episodes and execution legs separately, with
resizing and turnover, from dated ledgers. Headline: 17 published "trades" → 15
episodes and 61 legs. The underlying returns are untouched by this item.

### b3. Statistics from a single episode are not reported as performance

The corrected walk-forward opens **one** out-of-sample episode in eight test
years. A Sharpe ratio, a hit rate and an annualized return computed from one
episode are not estimates of anything — the published 60% hit rate meant three
weeks, and one episode would mean one up week and one down week.

**Proposed:** decline to print them. The rule is enforced in code, applied
wherever such statistics arise rather than table by table, and logged when it
fires. Suppressed values stay in `full_pipeline_results.json` so the decision is
checkable. Withheld figures are removed with the reason given, never replaced by
an unexplained placeholder.

The walk-forward table now reports what the procedure did — training window,
selected threshold, episodes opened. **The activity count is the finding**, and
it is a stronger one than any return from a single episode because it does not
depend on how that episode happened to turn out.

---

## (c) Manuscript corrections

The paper mis-stated its own code in four places: the fast-alpha equation showed
a price difference where the code uses a percentage return (the printed version
divides yen by a percentage volatility and is dimensionally incoherent); the
position-size formula carried an unreachable 0.5 floor and a "no leverage" claim
when the real range is [1, 2] gross-notional units; hedge alpha was printed with
a time-varying rate differential that exists nowhere in the repository, the code
using a fixed −2% constant; and the tail-alpha window was described in weeks
where the code uses trading days.

Two disagreements were resolved **in favour of the code**, against the working
rule that the code gets fixed to match the paper. Both are flagged so they can be
overruled:

- **Monday-open execution.** The paper specifies it; the code uses the Friday
  close. The Friday close is kept — but a false justification is removed. An
  earlier draft of this correction claimed Monday opening prices are absent from
  the dataset. **They are present**; the daily bars carry an `Open` column. The
  Friday-close proxy is a choice, and the paper now says so. Implementing
  Monday-open execution is on the backlog.
- **The EVT section** is presented in the paper as characterising tail-alpha
  exceedances; the code fits absolute weekly returns. The section is relabelled
  as a weekly-return diagnostic. The rule says the code should have been changed
  instead; refitting is on the backlog, and the relabelling should not be
  mistaken for the fix.

---

## (c2-bis) Tail aggregation sensitivity — RECOMMENDATION, AWAITING YOUR RULING

**This item is a proposal, not a change we are asking to have accepted with the
rest. It is isolated in a single commit and can be removed with one
`git revert`; nothing else in this pull request depends on it.**

Reviewer 3 observed that the tail signal is built from daily exceedances but
read only on Fridays, so most weeks containing an exceedance enter the weekly
panel as zeros. We accepted that as a limitation. We then built the
all-trading-days signal to see what it does, because "use every trading day"
does not by itself specify an aggregation:

| Weekly aggregation | Non-zero obs. | Skew | AI | Block 95% CI |
|---|---|---|---|---|
| Friday observation (published, kept primary) | 35 | −1.48 | 0.03 | [−3.10, 0.54] |
| All days, signed sum | 105 | **+0.22** | 0.13 | [−0.72, 1.09] |
| All days, largest \|exceedance\| | 105 | −1.14 | 0.08 | **[−1.97, −0.09]** |

**The three do not agree.** The skewness estimate changes sign, and the
dependence-robust interval excludes zero under one of them. That bears on your
abstract: "only the volatility-expansion (coverage) signal exhibits skewness
that survives block-bootstrap inference" is true under the primary construction
and is not invariant to the aggregation rule.

**What this PR does.** Keeps your Friday-sampled construction as primary,
reports all three as a sensitivity table, concludes that tail inference is
aggregation-sensitive, and qualifies the six places that claim depends on so
they read "under the primary construction" rather than flat.

**What this PR deliberately does not do.** It does not switch the primary
construction. Selecting an aggregation after seeing which one yields
significance would be specification selection on outcomes — the practice the
paper criticises — and neither alternative is self-evidently correct: the signed
sum lets opposing exceedances within a week cancel, and the largest-exceedance
rule lets one day define the week. Both need an economic argument about what
weekly tail exposure means, which is yours to make.

**The decision is yours** because it touches your abstract and redefines one of
your five signals. Three options: take it as proposed; revert the commit and
keep the limitation stated in prose only; or direct which aggregation should
become primary, with the economic reasoning, and we will implement it.

---

## (d) Prose corrected without a wrong figure

The manuscript sweep changed **38 figures across 21 locations**. But a
figure-by-figure sweep does not catch a sentence whose *argument* depends on a
result that no longer holds, and those matter more.

The published paper argued that a modest gross edge survived measurement and was
not eliminated by costs. Every sentence resting on that architecture is wrong
under the corrected numbers regardless of its digits. Examples, none containing
an incorrect figure: the robustness section described a backtest "statistically
indistinguishable from zero" (defensible on the interval, but it presents a
losing strategy as a null one) and asked whether costs "erode strategy returns"
(presupposing returns to erode); the drawdown paragraph called the figure "only
modestly smaller" than buy-and-hold's, presenting as mitigating what is damning —
four-fifths of a permanently invested position's drawdown, incurred while exposed
in 55 of 504 weeks.

**The break-even statement is the clearest case.** The published paper reported a
break-even round-trip cost of 19.2 pips and read it as reassurance. That figure
was meaningful only while the gross return was positive. It is not that the
corrected break-even is larger, or harder to estimate: **it does not exist**, and
the paper now says so in the cost section, the abstract and the conclusion. It is
a cleaner statement of the null than the cost table it replaces.

One qualification is added rather than removed: costs remain small in magnitude
(0.38pp at two pips), but the model charges spread strictly in proportion to
notional with **no per-order component**, while the corrected specification
generates 31 resizings averaging 0.19 units — exactly the population a per-ticket
charge would fall hardest on. The reported drag is a lower bound.

---

## (e) Provenance footnotes restored

`4d21c69` carried nine table notes recording the paper's own earlier corrections.
Seven had been deleted during the drafting of this branch; all seven are
restored. Two survived — and keeping two of nine is not an editorial decision,
it is what happens when notes get dropped while the prose around them is
rewritten.

**One deserves singling out.** The data-snooping note recorded that the published
`RC = 2.14 (p = 0.042)` was not reproducible from any specification of the stated
candidate universe. That is the paper's most quotable statistic — the one number
in it that reported a significant result. Deleting the note deleted the record
that it was already known to be unreliable.

Each note is restored **verbatim**, with current values appended as a following
sentence rather than woven into the original. These notes are a dated record of
what was wrong and when; editing them to match today's numbers would destroy what
makes them worth keeping.

That preservation was enforced mechanically, not by eye: every one of the nine
original sentences is checked to appear in the current source as an exact
substring. The check earned its place — a first attempt inserted the words "then
reported" *inside* the factor-attribution sentence, a two-word rewrite of the
historical record that reading would not have caught. The claim of verbatim
restoration is worth something only because a machine enforced it.

---

## Round two — response to Reviewer 3

The first round of this PR addressed Reviewer 3's eight code and inference
comments. A second round followed, and the changes below are the substantive
ones. `docs/REVIEWER_RESPONSE.md` has the point-by-point replies.

### Inference appropriate to 15 clusters

The in-position weeks are 55 observations drawn from 15 holding episodes spread
across a decade, and they are not contiguous. A lag-based autocorrelation
correction presumes consecutive observations, so the Newey–West treatment applied
in an earlier draft of this revision is **withdrawn as inapplicable**, not merely
superseded. Reported inference is the bias-reduced **CR2** estimator with
Bell–McCaffrey degrees of freedom (10.2 here, against a naive 14) for standard
errors and intervals, and a **restricted wild cluster bootstrap-*t*** with
Rademacher weights (*B* = 9,999, null imposed) for the *p*-value. Fifteen clusters
is few, and both remain approximations at that number: the *p*-value should be
read as indicative rather than exact.

For the momentum loading this gives β₂ = −0.823, CR2 standard error 0.324,
*t* = −2.54, CR2 interval [−1.54, −0.10], wild cluster bootstrap *p* = 0.038.

### Sample selection, and why the momentum loading is demoted

Reviewer 3's first round-two comment is the one that changed an interpretation
rather than a number. The in-position regression runs on the weeks the strategy
chose to hold, and those weeks are selected by entry rules that are functions of
the same price series the momentum factor is built from: the short leg fires
after price has risen against its sixty-day average, and a twelve-week
time-series momentum rule is long in exactly those states.

The loading is therefore close to arithmetic. A rule that sells strength will
look short momentum during the weeks it is on, whether or not any factor
relationship exists in the underlying returns. The coefficient is retained
because it describes what the rule is, and it is **not** presented as an
empirical finding, **not** offered as an explanation of the strategy's losses,
and **not** counted in the contribution. The abstract, conclusions, discussion
heading and factor section were all cut back accordingly.

Worth recording alongside it: inference on this coefficient was tightened three
times, and each step was a genuine correction that made the estimate less
impressive. None of them touched the problem. Improved standard errors fix the
uncertainty attached to a coefficient given a specification; they cannot make a
selected sample unselected.

### Three specification sensitivities, which are not the same phenomenon

Three choices the original specification did not argue for each move the results
materially. They are reported as distinct, because their statistical behaviour
differs, and none of them is described as showing that the results are artefacts.

| Choice | What happens |
|---|---|
| **Tail-signal aggregation** | Across three defensible aggregations of the identical daily rule, the skewness estimate **changes sign**, and under one of them the interval excludes zero. The sign and the inferential conclusion both move. |
| **Execution timing** | Four entry timings applied to the identical signal, on a common sample of 502 weeks, give cumulative gross returns of −6.64% (Friday close), −0.73% (Monday open), −0.92% (Monday close) and −8.03% (Tuesday open). Point estimates move materially and **non-monotonically in delay**, while the **pre-specified paired contrasts all include zero**. |
| **Entry-rule symmetry** | The published hybrid and three pre-specified symmetrizations give −6.64%, −1.65% (pure-fast), −4.13% (pure-pricing) and −7.86% (equal-threshold): a range of 6.21 points, nearly as large as the published hybrid's own 6.64% loss. **Every pre-specified variant remains gross-negative in this sample.** |

On the third: the long and short legs of the published rule differ in four
respects — skewness gate, confirmation series, confirmation threshold, and
direction of response — and the manuscript argued for none of them. Collapsing
the asymmetry is underdetermined, since it requires choosing which of the rule's
two economics to keep, so three symmetrizations were specified rather than one.
Pure-fast and pure-pricing hold positions in fewer weeks than the published rule
(44 and 51 against 55) but both remain negative per exposed week (−1.8 and −7.1
basis points against −11.0), so their less negative cumulative performance is not
solely an artefact of lower exposure.

### Pre-specification and audit trail

Where a robustness exercise could have been steered by its own results, the
specification was written down and committed **before** the computation, and the
commit ordering is the evidence. This covers the execution-timing grid and the
entry-rule symmetrization, the latter in
`docs/PREREGISTRATION_ENTRY_SYMMETRY.md`, which fixes the three variants, the
metrics, the cost tier, an exposure guard, and a reporting rule stating that all
three would be disclosed whatever they returned.

Two structural predictions recorded in that document were wrong and are left
standing in it rather than quietly corrected. A pre-registration that is rewritten
after the fact is worth nothing.

The execution-timing grid was previously computed by a standalone script that was
never committed — twenty numbers on a headline robustness exhibit with no
traceable source. That computation now lives in the pipeline, with the alignment convention
documented and enforced, and all twenty previously committed cells reproduce
exactly.

`docs/REVIEW_NOTES.md` carries the full audit record: what changed, who
originated it, whether it was a defect or a specification decision, and the
verification failures found along the way.

---

## Result changes

Full table with per-item attribution in `analysis/before_after_results.csv`.

| Metric | Published (`4d21c69`) | Corrected |
|---|---|---|
| **In-position weeks** | **25 of 504** | **55 of 504** |
| Cumulative gross return | +3.60% | −6.64% |
| Sharpe | 0.149 | −0.153 |
| Maximum drawdown | −7.96% | −12.56% |
| Holding episodes / execution legs | 17 "trades" | 15 / 61 |
| Break-even round-trip cost | 19.2 pips | does not exist |
| Retail-wide net return | +3.22% | −7.02% |
| Momentum loading (in-position) | −0.247, t = −0.51 | **−0.823, t = −3.73** |
| Factor intercept (full sample) | +0.00008 | −0.00012 |
| In-position factor sample | 25 weeks | 55 weeks |
| Walk-forward pooled return / episodes | +2.46%, 3 trades | +2.74%, 1 episode |
| Walk-forward Sharpe / hit rate | 0.419 / 60.0% | withheld — one episode |
| Low-VIX / high-VIX return | +2.38% / +2.67% | −5.08% / −1.65% |
| GBP/USD cross-market | **+17.18%** | **−13.32%** |
| SPY cross-market | +11.66% | +14.20% |
| GLD cross-market | −30.26% | −15.44% |
| Tail-alpha AI | 0.17 | 0.03 |
| Coverage-alpha AI | 3.45 | 2.22 |

**The GBP/USD sign flip is a finding, not a rounding.** The published paper reads
+17.18% on GBP/USD as evidence that FX offers more favourable conditions for the
strategy than equities or gold. Corrected, it is −13.32%, and **the flip is
attributable to the implementation fixes, not to the sizing proposal**: with the
implementation fixes and the frozen-notional alternative the figure is −14.11%.
Rejecting (b1) does not restore the published reading. The cross-market section's
claim about FX conditions no longer has a basis.

For the same reason, the widened cross-market spread is traceable: the
`cross_market` code block is byte-identical to the version this branch started
from, and rerunning it under the frozen alternative reproduces the intermediate
figures exactly. The movement is the sizing default alone; the input skewness
statistics are unchanged in all four markets.

---

## Verification

- 67 deterministic tests, all passing, run offline without credentials: the AI edge cases, the dated timing
  convention, entry, hold, expiry, reversal, simultaneous signals, no-signal
  periods, both sizing modes, resize and reversal cost accounting, a no-look-ahead
  causality suite run against all four entry rules, table- and prose-level
  provenance, and a guard resolving every commit hash cited in the audit record.
  A further check, marked `network` and deselected by default, verifies that this
  document and the published pull-request description have not diverged; run it
  with `pytest -m network`.
- The complete pipeline runs online and reruns identically with `--offline`.
- Seven of the eight input files reproduce byte-for-byte on an independent
  download (see **Data** below).
- **Table provenance, with its coverage stated honestly.** Each covered table
  cell names the canonical output field it comes from, so a cell with no declared
  source fails rather than being matched against any equal-looking number.
  Coverage is **7 of the 19 manuscript tables**: six semantically mapped
  (`tab:backtest`, `tab:factors`, `tab:sevariants`, `tab:snooping`,
  `tab:exectiming`, `tab:entrysymmetry`) plus `tab:spec`, which is generated from
  the specification module and asserted against it. Among prose figures the
  mechanism currently reaches the regression statistics only. The remaining 12
  tables are checked less formally and we do not claim otherwise.
- The nine original provenance sentences are machine-checked for verbatim
  presence.
- After every rerun: n = 504 spanning 2016-01-08 to 2025-08-29; the factor
  intercept matches the strategy's own mean weekly return
  (−0.00011964 against −0.00012029); the low- and high-VIX returns compound to
  the full-sample return (−6.640684% against −6.640684%).

### The PDF was rebuilt and inspected

`paper/alpha-asymmetry.pdf` is rebuilt from the corrected source. It compiles
clean: 35 pages, **zero** overfull boxes, **zero** underfull boxes, no undefined
references or citations, bibliography resolved against `references.bib`.

Both figures were regenerated from the current pipeline and compared
byte-for-byte against the committed versions. `backtest_results.png` is drawn
from the corrected return series. `alpha_asymmetry_analysis.png` is unchanged
since before the sizing change, which is correct: it shows the alpha
distributions, which do not depend on the strategy.

The PDF's own text was extracted and checked. The corrected figures are present;
none of the superseded ones appear anywhere.

**A note on this section, because it is the third time this document has made a
claim about its own provenance.** The draft this branch started from asserted
that the PDF had been compiled and visually inspected when it had not. That was
removed and replaced with a statement that no LaTeX toolchain was available and
the PDF was stale. **That statement was true when written and later stopped being
true**, when a self-contained engine was installed and the paper compiled. A
document asserting something about itself that has since become false is the
failure this pull request exists to correct, so the sequence is recorded rather
than tidied away, and the build was deliberately left until last so that the
claim and the artefact became true at the same moment.

### Version, DOI and supersession — decisions for you

The manuscript now carries `\paperver 3.1.0`, incremented from the 3.0.0 you set
in `f04ae08` for the July manuscript. Three things need your decision:

**The version identifiers in this repository disagree with each other, and did
before this branch.** `paper/alpha-asymmetry.tex` carried `3.0.0` for the July
manuscript; `CITATION.cff` called the same work `2.1.0-dev`; the last *deposited*
version is `v2.0.1` (`10.5281/zenodo.20635291`). Neither `3.0.0` nor `2.1.0-dev`
was ever deposited. `CITATION.cff` is set to `3.1.0-dev` to follow the number
printed on the paper, with the disagreement documented in the file. Reconciling
them properly is yours.

**Depositing mints a new Zenodo version DOI**, which cannot be known in advance.
`\paperdoi` is therefore left as the concept DOI `10.5281/zenodo.18638784`, which
resolves to the newest version. After deposit, record the new version DOI in
`CITATION.cff` and `CLAUDE.md`. The SSRN record (`SSRN:6147567`) is separate and
needs its own revision; Zenodo does not propagate to it.

**We recommend posting a correction notice against the superseded record**, not
merely depositing a new version. The headline result changes sign: +3.60% to
−6.64%. A reader who lands on v2.0.1 through a citation or a search result has no
way to know it has been superseded, and the specific claim they would take away —
that the strategy earns a small positive gross return — is wrong rather than
imprecise. Depositing a new version alone leaves that reader uninformed. This is
your call as author and it carries reputational weight either way, but asked
directly: we would post the notice.

---

## Data, and a decision for you

The raw CSVs are **not committed**, and `analysis/cache/` remains gitignored.
`analysis/data_access.py` gives the reason: Yahoo Finance data may be subject to
redistribution terms. Publishing eight files of vendor data in a public
repository is a licensing decision for the repository owner, not one an outside
contributor should make inside a correctness PR — **so it is raised here for you
to decide rather than taken.**

What is provided instead: `analysis/fetch_data.py` downloads the inputs and
verifies each file's SHA-256 against the committed manifest, so a fresh clone can
obtain the data and confirm it is the same data.

Seven of eight hashes reproduce byte-for-byte. Six of the eight series are FX
spot rates or index levels, which carry no corporate-action adjustment and
structurally cannot drift; GLD paid no distribution over the window. SPY, a
distributing ETF fetched with `auto_adjust=True`, has its entire history rescaled
by every new distribution — the only file in the set that *could* differ, and it
did. That is the expected outcome rather than a near miss. The difference moves
five values in the SPY cross-market row in their fifth or sixth significant
figure, each rounding to the same printed number, and nothing else in the
pipeline.

---

## Reproduction

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python analysis/fetch_data.py
.venv/bin/python analysis/full_pipeline.py --offline
```

---

## Questions for you

1. **The data licensing question above** — commit the raw CSVs, or keep the
   fetch-and-verify approach?
2. **(b1), the sizing proposal.** Weekly evaluation or frozen at entry? Both are
   computed; no conclusion depends on it.
3. **(b2) and (b3)** — the trade-accounting redefinition and the refusal to
   report single-episode statistics. Both are reversible.
4. **(c2), the two exceptions** — keeping the Friday close despite the paper
   specifying Monday open, and relabelling the EVT section rather than refitting
   it. Either could be done properly instead.
5. **The stale PDF.** You have the toolchain.
6. Whether an approved EUR–JPY rate or forward series can be supplied, which
   would let hedge alpha stop being a constant multiplied by a correlation.

---

## Provenance

This branch began from an unreviewed draft produced by an AI agent, committed
unmodified as `5135bac` and labelled as such. That commit was **audited rather
than adopted**: its claims were checked against `4d21c69`, its manuscript edits
were reviewed line by line, several were reversed, and every change that survives
is justified in this PR and in the changelog against the published paper. It
carries no authority and is kept in the history only so that the work done after
it is separately reviewable.

`docs/REVIEW_NOTES.md` is the working audit record from that process. It is not
part of the argument here.

This branch is pushed to `plut777/alpha-asymmetry` and opened as a pull request
against `dissensus-ai/alpha-asymmetry`. Nothing has been merged.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
