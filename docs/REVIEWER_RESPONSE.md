# Response to Reviewer 3

**Manuscript:** Alpha Asymmetry in Foreign Exchange Markets: An Investigation of
Exploitability (DAI-2605)
**Authors:** Murad Farzulla, Tofik Israfilov

---

We thank the reviewer for a careful and technically substantial report. Four of
the eight comments identify errors in our manuscript, two of which change what
the paper claims. We have accepted all four, and we have also acted on the two
comments where we disagree with the reviewer's stated mechanism, because the
underlying design suggestions improve the paper regardless of the mechanism.

Every point below is answered with a computation rather than an argument. All
supporting figures are reproducible from `analysis/full_pipeline.py`; the new
material appears in Tables 3, 8, 10 and 12 of the revised manuscript.

Summary of dispositions:

| # | Comment | Disposition |
|---|---|---|
| 1 | Inconsistent bootstrap schemes | **Accepted** — justification added, sensitivity table added |
| 2 | Random candidate dilutes the tests | **Design adopted**, stated mechanism does not hold here |
| 3 | Omitted window size for $AI_t$ | **Accepted — our error** |
| 4 | Excessive declustering window | **Accepted** — 1- and 2-week windows run and reported |
| 5 | Inapplicable normal-theory standard error | **Accepted — our attribution was wrong** |
| 6 | Invalid Newey-West on non-contiguous observations | **Accepted — our error; HAC withdrawn, small-cluster correction applied, a claim withdrawn** |
| 7 | Temporal aliasing in tail signal sampling | **Accepted**; all-days aggregations built and reported as a sensitivity, two figures corrected |
| 8 | Intercept unit mismatch | **Accepted — our error** |

---

## Comment 6 — Newey-West on non-contiguous observations

**We accept this in full. It is the most consequential comment in the report,
and it obliges us to withdraw a claim.**

The reviewer is right that stacking 55 non-contiguous weeks drawn from 15
holding episodes and applying a lag-based autocorrelation correction is invalid.
Adjacent rows in that stacked sample can be years apart, and Newey-West presumes
they are not. **We have not retained it as a robustness check.** Presenting a
correction we agree is inapplicable, alongside one we agree is correct, would
concede the point and then ignore it. It appears in the revision only as the
withdrawn figure, labelled as such.

Inference is now clustered by holding episode. We also took the reviewer's
implicit further point seriously: fifteen clusters is few, and ordinary
cluster-robust errors are asymptotic in the *number of clusters*, biased
downward and over-rejecting when that number is small. Flagging this would not
have been enough, so we corrected for it:

- **CR2** (Bell and McCaffrey, 2002) supplies the standard error and interval,
  with Satterthwaite degrees of freedom of **10.2** rather than the naive 14.
- A **restricted wild cluster bootstrap-t** (Cameron, Gelbach and Miller, 2008),
  Rademacher weights, null imposed, B = 9,999, supplies the primary p-value.

| Inference | $\hat{\beta}_2$ | SE | $t$ | $p$ | Role |
|---|---|---|---|---|---|
| **Wild cluster bootstrap-$t$** | −0.823 | — | −2.54 | **0.038** | **Primary** |
| CR2, BM dof = 10.2 | −0.823 | 0.324 | −2.54 | 0.029 | SE and interval |
| HC3 | −0.823 | 0.380 | −2.16 | 0.030 | Robustness |
| Newey-West HAC, 4 lags | −0.823 | 0.221 | −3.73 | 0.0002 | *Withdrawn* |

**What we withdraw.** The previous version reported $p = 0.00019$ and said it
"clears that bar comfortably", referring to a Bonferroni threshold of 0.0083 at
family size six. Under appropriate small-cluster inference the p-value is
**0.038**. The revised text states that the loading is nominally significant at
the 5% level under each reported inference specification but does not meet the
paper's pre-specified Bonferroni-adjusted threshold — and that the appropriate
inference places it an order of magnitude away from that threshold rather than
below it.

**A later comment overtook this one.** Round-two comment 1 observes that the
in-position sample is selected by the strategy's own entry rules, which are
functions of the same prices the momentum factor is built from. We accept that,
and it changes what this coefficient can be used for regardless of how its
standard errors are computed. The loading is now reported as a mechanical
property of the entry rules rather than as a factor exposure, and is excluded
from the paper's stated contribution. The inference corrections above stand as
corrections; they are no longer the binding constraint on the claim. See our
response to round-two comment 1.

The CR2 interval is $[-1.54, -0.10]$, wider than the $[-1.26, -0.39]$ previously
reported. We have propagated it to the abstract, the discussion and the
conclusion.

We would rather report this than have it found later, and we are grateful the
reviewer caught it.

## Comment 5 — the normal-theory standard error is a strawman

**Accepted. Our attribution of the interval widening was wrong, and we have run
the bootstrap that settles it rather than argue the point.**

The reviewer is correct that $\sqrt{6/n} = 0.109$ presumes a Gaussian null which
tail alpha violates severely, and that attributing the widening to serial
dependence alone is not supportable. To separate the two effects we added an
i.i.d. bootstrap, which relaxes normality but applies no dependence correction
(new Table 3):

| Signal | Normal SE | i.i.d. bootstrap SE | i.i.d. CI | Block CI |
|---|---|---|---|---|
| Tail | 0.109 | **0.941** | [−3.14, 0.62] | [−3.10, 0.54] |
| Fast | 0.109 | 0.114 | [−0.21, 0.23] | [−0.21, 0.21] |
| Pricing | 0.109 | 0.078 | [−0.32, −0.02] | [−0.45, 0.09] |
| Coverage | 0.109 | 0.342 | [0.98, 2.30] | [1.18, 2.16] |
| Hedge | 0.109 | 0.073 | [0.00, 0.29] | [−0.25, 0.54] |

For tail alpha the i.i.d. and block intervals are **almost identical**, and the
i.i.d. standard error is nearly nine times the normal-theory value. The reviewer
is exactly right: the $t$-test fails on this signal through non-normality and
sparsity, before dependence is considered at all.

We would add one observation the comparison also produces, which supports the
retention of the block bootstrap elsewhere. For *pricing* and *hedge* alpha the
relationship reverses — the block interval is substantially wider than the
i.i.d. one, and in both cases it converts an interval excluding zero into one
including it. There the dependence correction is doing real work, as their
Ljung-Box statistics of 679 and 1716 would predict. The block bootstrap is not
redundant; it was simply not what widened the tail-alpha interval.

The revised §3.2 states this directly and no longer attributes the tail-alpha
interval to dependence.

---

## Comment 3 — omitted window size for the asymmetry index

**Accepted. This is our error and the reviewer's characterisation is exact: the
strategy was not reproducible from the paper as written.**

$AI_t$ is computed on a trailing 20-week window of weekly fast-alpha
observations, requiring a minimum of 10 observations; below that minimum it is
undefined and the neutral one-unit size applies. It is the same 20-week window
used for the rolling skewness entry conditions.

The window appeared nowhere in the specification. It was mentioned once,
incidentally, in a paragraph about turnover — which is not where a replicator
would look. The revised Equation 10 discussion states it explicitly.

---

## Comment 8 — intercept unit mismatch

**Accepted. Our error, and the reviewer's arithmetic is correct.**

The coefficient is −0.00012 in weekly decimal return, which is −0.012 **percent**
or **−1.2 basis points**. The text said "−0.012 bps", off by a factor of 100. The
revised note reads "an intercept of −1.2 bps weekly (−0.00012 in weekly decimal
return)", giving both so the units cannot be misread again.

---

## Comment 1 — inconsistent bootstrap schemes and block lengths

**Accepted. The justification was missing and is now supplied, together with a
sensitivity check.**

The two schemes are applied to different objects, and we should have said so.

The alpha signals are constructed from **overlapping** rolling windows — 20
weeks for the skewness signals, 60 to 100 trading days for the underlying
constructions. Their dependence is mechanical, long, and of approximately known
length, so a fixed block comparable to the construction window is appropriate;
we use a 13-week circular block.

Strategy returns are not overlapping constructions. Their dependence is short
and of unknown length, which is the case the stationary bootstrap's randomised
block length is designed for; we use an expected block of 4 weeks.

We have added a sensitivity table (new Table 12). Varying the expected block
length from 2 to 13 weeks moves the Sharpe interval within
[−0.78, 0.48] at the widest:

| Expected block | 95% Sharpe interval |
|---|---|
| 2 weeks | [−0.776, 0.475] |
| 4 weeks (reported) | [−0.705, 0.396] |
| 8 weeks | [−0.722, 0.409] |
| 13 weeks | [−0.724, 0.420] |

Every interval contains zero comfortably. No conclusion depends on the choice.
We have not adopted a formal block-length selection algorithm, which we agree
would be preferable in a paper whose conclusions turned on these intervals;
here they do not.

---

## Comment 2 — the random candidate in the data-snooping universe

**We have adopted the reviewer's design recommendation. We report, in the
interest of accuracy, that the mechanism given for it does not hold in this
data.**

The formal Reality Check and SPA tests are now run on the **twelve real
candidate strategies**, with the seeded random sequence reported as a diagnostic
outside the formal universe. We agree with the principle: a data-snooping
correction should control the error rate across the space actually searched, and
a coin-flip rule was never a strategy under consideration.

The reviewer states that including it "bias[es] the $p$-values upward and mak[es]
it more difficult to reject the null". In this sample the effect runs the other
way:

| Universe | RC | RC $p$ | SPA | SPA $p$ | Best candidate |
|---|---|---|---|---|---|
| 12 real strategies | 0.014 | **0.30** | 1.90 | 0.25 | always-long |
| 13, including random | 0.020 | **0.15** | 1.90 | 0.26 | random sequence |

Removing the random sequence **doubles** the Reality Check $p$-value. The reason
is that the random sequence is the argmax of the universe: dropping it lowers
the observed statistic more than it lowers the bootstrap distribution, so the
test becomes harder to reject rather than easier. The SPA $p$-value moves by
0.013 in the other direction.

We note this only because the report presents the direction as a general
consequence. The conclusion is unchanged under either universe — no candidate is
statistically superior to a zero return — and we have adopted the twelve-strategy
universe as primary regardless, because the reviewer's design point stands on its
own.

---

## Comment 4 — declustering separation on weekly data

**Accepted. We have run the shorter windows the reviewer asks for and report
them.**

The reviewer is right that persistence in weekly returns is far shorter than in
the daily series runs declustering was developed for, and that a five-week
window is aggressive on weekly data. We should have justified it or tested it.

Taking the question directly: **at a one-week separation — the shortest
declustering that does anything at all — the fit uses 22 cluster maxima rather
than 20, and the shape estimate is −0.209 rather than −0.248**, with a
confidence interval of [−1.53, 0.22] against [−1.51, 0.25]. Two weeks gives 21
maxima and −0.241. The full grid:

| Separation | Cluster maxima | $\hat{\xi}$ | 95% CI | KS $p$ |
|---|---|---|---|---|
| **1 week** | **22** | **−0.209** | **[−1.53, 0.22]** | 0.997 |
| 2 weeks | 21 | −0.241 | [−1.51, 0.22] | 0.981 |
| 3 weeks | 20 | −0.248 | [−1.51, 0.25] | 0.971 |
| 5 weeks (reported) | 20 | −0.248 | [−1.51, 0.25] | 0.971 |

The shortest separation recovers two additional cluster maxima and moves the
shape estimate by 0.04, inside an interval spanning more than 1.7. The report
describes the five-week window as "unnecessarily reducing the sample size of
exceedances from 26 to 20" and thereby "further weaken[ing] the power of an
already underpowered" analysis. The first half is accurate as arithmetic. On the
second, the sensitivity grid does not show a material loss of precision: the
imprecision comes from having 26 exceedances in ten years, not from how they are
grouped, and no conclusion in the section changes at any separation we tried.

The table is now in the manuscript, and the text leads with the one-week result.

## Comment 7 — temporal aliasing in the tail signal

**Accepted as a limitation, and it is a real one. Two figures in the report are
inaccurate, which we note only because they understate the sparsity in one
respect and overstate the discarding in another.**

The reviewer is right that a signal constructed from daily exceedances but read
only on Fridays discards most of what it detects, and that every statistic
computed on the weekly series inherits that sparsity.

Two corrections to the figures, and because the two statistics rest on
different denominators we state both bases explicitly rather than leave a reader
to reconcile them.

**Non-zero weekly observations: 35, not 14.** After Friday sampling, 35 of the
504 weekly tail-alpha observations are non-zero. The report's figure of 14
corresponds to 2.78% of 504, which is the *positive*-observation ratio in
Table 1 — that statistic counts observations strictly greater than zero, and the
tail signal is signed, so it excludes the negative exceedances. The count of
strictly positive weeks is indeed 14; the count of non-zero weeks is 35.

**Discard rate: two-thirds, not four-fifths.** This is a different base. Of the
504 weeks, **105 contain at least one daily exceedance**; of those 105, only 35
have one falling on the Friday. So 70 of 105 exceedance weeks enter the panel as
zeros: a discard rate of (105 − 35)/105 = **66.7%**.

The two figures are not comparable and neither is a restatement of the other:
35 is a count out of 504 weekly observations, 105 is a count of weeks containing
a daily event. Both are correct on their own base.

Neither correction weakens the point. We have added the figures to §2.2 and to
the Limitations section, stating that 70 of the 105 exceedance weeks enter the
panel as zeros and that the sparsity is the proximate reason the tail-alpha
skewness interval is so wide.

**On the remedy: we built it, and it does not resolve cleanly.**

We have constructed the all-trading-days signal the reviewer proposes and run
the full analysis on it. Because "use every trading day" does not by itself
specify an aggregation, we built the two obvious ones. All three apply the
identical daily rule and differ only in how a week's daily observations are
reduced to one weekly value:

| Weekly aggregation | Non-zero obs. | $\hat{\gamma}_1$ | Ex. kurt. | AI | Block 95% CI |
|---|---|---|---|---|---|
| Friday observation (published, retained as primary) | 35 | −1.48 | 19.20 | 0.03 | [−3.10, 0.54] |
| All days, signed sum | 105 | **+0.22** | 8.84 | 0.13 | [−0.72, 1.09] |
| All days, largest \|exceedance\| | 105 | −1.14 | 8.29 | 0.08 | **[−1.97, −0.09]** |

**The three do not agree.** The skewness estimate changes sign between the
signed-sum aggregation and the other two, and the dependence-robust interval
excludes zero under one of the three. A statement as central to this paper as
"only coverage alpha's skewness survives dependence-robust inference" is
therefore true under the primary construction and not invariant to a sampling
choice the published specification never argued for.

**We have retained the published construction as primary and have not selected
among them.** Choosing an aggregation rule after observing which one yields
significance would be specification selection on outcomes — the practice this
paper criticises in Section 5.7 — and it is not made acceptable by the selection
being ours rather than someone else's.

Nor is either alternative self-evidently correct, which is the substantive
reason not to simply adopt one. The signed sum lets two exceedances of opposite
sign within a week cancel, so a violent week can register as quiet. The largest
absolute exceedance lets a single day define the week and discards every other
exceedance in it. Each encodes a different and unargued claim about what weekly
tail exposure *is*, and choosing between them requires an economic argument this
paper does not make.

What we can report is the sensitivity itself, and we now do: **the tail signal's
distributional character is not robust to the aggregation rule, and is not
established until weekly tail exposure is defined.** That is a statement about
the construction rather than about the market, and it applies equally to the
published result and to both alternatives. It is in the manuscript as
Table 4 with the reasoning above, and the claims that depend on it —
in the abstract, the results, the discussion, the robustness introduction, the
multiple-testing section and the conclusions — are now qualified as holding
under the primary construction rather than stated flat.

We would welcome the editor's and the reviewer's view on whether defining
weekly tail exposure properly belongs in this revision or in subsequent work.
Our own view is that it is a specification question rather than a correction,
and that resolving it inside a paper whose purpose is to correct a published
result would confuse the two.

---

## Summary of changes to the manuscript

| Change | Location |
|---|---|
| CR2 clustered by episode; wild cluster bootstrap primary; HAC withdrawn | §5.7, Tables 14–15 |
| Bonferroni claim withdrawn; $p = 0.038$ reported | §5.7 |
| Momentum loading demoted to a mechanical property of the entry rules | Abstract, §1, §5.7, Conclusions |
| i.i.d. versus block bootstrap comparison | §3.2, Table 4 |
| Tail-alpha interval attributed to sparsity, not dependence | §3.2 |
| $AI_t$ window stated (20 weeks, minimum 10 observations) | §2.4, Eq. 10 |
| Intercept units corrected to −1.2 bps | Table 14 note |
| Bootstrap scheme justification; block-length sensitivity | §5.9, Table 18 |
| Formal universe reduced to 12; random sequence a diagnostic | §5.9, Table 19 |
| Declustering sensitivity, 1 to 5 weeks | §5.8, Table 16 |
| Complete specification table generated from the code | §2.4, Table 1 |
| Tail-signal aliasing disclosed | §2.2, §4.3 |
| Tail aggregation sensitivity: three constructions reported | §3.2, Table 5 |
| Execution-timing grid, four entry points on the identical signal | §5.4, Table 11 |
| Entry-rule symmetrization, three pre-specified variants | §5.5, Table 12 |
| Claims depending on the tail construction qualified | Abstract, §3.2, §4.1, §5, §5.9, Conclusions |

The tables carrying the headline performance, factor and data-snooping results
are tied cell by cell to named fields of the replication output, and the analysis
is covered by deterministic tests. That mechanism currently reaches 12 of the
19 manuscript tables; the remainder are checked less formally. The sample is unchanged:
$n = 504$, 8 January 2016 to 29 August 2025.

---

# Round two

## Comment 1 — endogeneity in the in-position factor regression

**Accepted, and it changes an interpretation rather than a number.**

The reviewer is right. The in-position regression runs on the 55 weeks the
strategy chose to hold, and those weeks are selected by entry rules that are
functions of the same price series the momentum factor is built from: the short
leg fires after price has risen against its sixty-day average, and a twelve-week
time-series momentum rule is long in exactly those states. Sample and regressor
are jointly determined.

The loading is close to arithmetic on that reading. A rule that sells strength
will look short momentum during the weeks it is active whether or not any factor
relationship exists in the underlying returns.

We retain the coefficient because it describes what the rule is, and we no longer
present it as an empirical finding. It is not offered as an explanation of the
strategy's losses and is excluded from the paper's stated contribution. The
abstract, the contribution statement, the Discussion heading and §5.7 were all cut
back accordingly.

One point we think worth recording: inference on this coefficient was tightened
three times, and each step was a genuine correction that made the estimate less
impressive. None of them touched this problem. Better standard errors fix the
uncertainty attached to a coefficient given a specification; they cannot make a
selected sample unselected.

---

## Comment 2 — sparse Friday sampling of tail alpha

**Accepted; this extends round-one comment 7 and is answered there in detail.**

The signal is constructed from daily exceedances and read only on Fridays, so 70
of the 105 weeks containing an exceedance enter the weekly panel as zeros and 35
of 504 observations are non-zero. Every tail-alpha statistic inherits that
sparsity, which is the proximate reason the skewness interval is so wide.

Table 5 now reports the identical daily rule under three weekly aggregations. The
point estimate changes sign across them and the interval excludes zero under one
of the three. We report that sensitivity rather than resolve it: selecting an
aggregation on the result it produces is the practice this paper criticises
elsewhere. The published Friday-sampled construction remains primary and is the
sparsest of the three, resting its estimate on 35 non-zero observations against
105 for both alternatives.

---

## Comment 3 — the seeded random candidate

**Already adopted in response to round-one comment 2; nothing further has
changed.** The formal tests run on the twelve real candidates, with the random
sequence reported as a diagnostic outside the formal universe. As noted there,
the direction of the effect in this sample is the opposite of the one the
reviewer's reasoning predicts, and we report that rather than let the adopted
recommendation carry an explanation that does not hold here.

---

## Comment 5 — look-ahead bias from Friday-close execution

**Accepted as a real objection. The convention is under revision and the decision
is not ours alone to make.**

The reviewer is right that observing the close, computing rolling statistics from
it, and executing at that same close is not implementable. The published
specification entered at the Monday open following Friday signal generation, and
this revision departed from it without adequate justification.

§5.4 and Table 11 now report four entry timings applied to the identical signal on
a common sample of 502 weeks: Friday close −6.64%, Monday open −0.73%, Monday
close −0.92%, Tuesday open −8.03%. The point estimates move materially and
non-monotonically in delay, while the pre-specified paired contrasts all include
zero, so the grid does not identify a uniquely correct convention.

Because it does not, we take the choice to rest on specification fidelity and
information timing rather than on which return estimate is preferable, and on
those grounds Monday open is the better primary. That change is before the
corresponding author; it moves the headline sample to 503 weeks, dropping one week
for want of a following open, and it would change every figure derived from
strategy returns. We will report the outcome rather than pre-empt it.

---

## Comment 6 — JB statistic reported alongside p-values

**Accepted and corrected. The reviewer identified a genuine ambiguity.**

§3.2 listed "SW $p = 0.55$, JB $\approx 0$, $K^2$ $p = 0.99$". Two of those three
are p-values and the middle one is a test statistic, so "JB ≈ 0" reads as a
p-value indicating strong rejection — the opposite of the sentence containing it.
The value is the Jarque-Bera statistic (0.005 for fast alpha), which is
compatibility with the Gaussian null, not rejection of it. The text now says "JB
*statistic* ≈ 0" explicitly. The substance was correct; the presentation invited
exactly the reading the reviewer gave it.

---

## Comment 4 — the long and short entry rules are not symmetric

The reviewer is right, and the asymmetry is wider than a threshold difference.
The two legs differ in four respects: the skewness series gating them, the
confirmation series, the confirmation threshold, and the direction of response.
A positive fast alpha opens a long; a positive pricing alpha opens a short. The
rule follows strength in one signal and fades it in the other, and the original
specification argues for none of it.

Collapsing the asymmetry is underdetermined, because it requires choosing which
of the two economics to keep. We therefore specified three symmetrizations in
advance — pure-fast, which preserves the published long leg and reflects it;
pure-pricing, which preserves the published short leg and reflects it; and an
equal-threshold hybrid, which keeps both sources and moves only the long leg's
gate onto the same volatility-scaled footing the short leg already uses, at 0.5
times the rolling 20-week standard deviation of its own confirmation series.
The metrics, the cost tier, an exposure guard and a reporting rule fixing that
all three would be disclosed whatever they returned were committed before any of
them was computed.

The published hybrid and all three pre-specified symmetrizations produce negative
realised gross returns in this sample; the magnitude varies materially across
specifications. Realised gross returns are −6.64% for the published hybrid,
−1.65% pure-fast, −4.13% pure-pricing and −7.86% for the equal-threshold hybrid:
a range of 6.21 percentage points, nearly as large as the published hybrid's own
6.64% cumulative loss.

Pure-fast and pure-pricing hold positions in fewer weeks than the published rule,
44 and 51 against 55, but both also remain negative per exposed week, at −1.8 and
−7.1 basis points against −11.0. Their less negative cumulative performance is
therefore not solely an artefact of lower exposure. Pure-pricing records the
deepest drawdown of the four, −16.01%.

Equalising the confirmation threshold worsens realised performance in this
sample. This is one comparison and is not evidence that the published threshold
was tuned; its direction is merely consistent with what a specification-search
concern would predict.

These are sensitivity exhibits. No variant is offered as a replacement rule, and
realised performance was pre-specified not to determine which symmetrization is
treated as defensible. New Section 4.6 and Table 12 report the grid; the
pre-registration is `docs/PREREGISTRATION_ENTRY_SYMMETRY.md`.

Two structural predictions in that pre-registration were wrong and are left
standing in it: pure-fast was predicted to be more exposed than the published
rule and is less so, and pure-pricing was predicted to be less exposed than
pure-fast and is more so. Both share a cause — the published rule draws entries
from the union of two skewness gates while each collapsed variant has only one.
Section 6 of the same document asserts that the variants cannot be distinguished
statistically; no paired inferential comparison among the four was pre-specified
or run, so that statement is untested rather than established or rejected, no
conclusion reported here relies on it, and it is not repeated in the manuscript.
