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
| 4 | Excessive declustering window | **Accepted in principle**, consequence quantified and shown immaterial |
| 5 | Inapplicable normal-theory standard error | **Accepted — our attribution was wrong** |
| 6 | Invalid Newey-West on non-contiguous observations | **Accepted — our error; a claim is withdrawn** |
| 7 | Temporal aliasing in tail signal sampling | **Accepted as a limitation**, two figures corrected |
| 8 | Intercept unit mismatch | **Accepted — our error** |

---

## Comment 6 — Newey-West on non-contiguous observations

**We accept this in full. It is the most consequential comment in the report,
and it obliges us to withdraw a claim.**

The reviewer is right that stacking 55 non-contiguous weeks drawn from 15
holding episodes and applying a lag-based autocorrelation correction is
invalid. Adjacent rows in that stacked sample can be years apart, and
Newey-West presumes they are not.

We have re-estimated with standard errors clustered by holding episode, which is
now the **primary** specification for the in-position regression. Both
alternatives are reported alongside so the reader can see the coefficient under
every convention rather than one chosen for them (new Table 10):

| Standard errors | $\hat{\beta}_2$ | SE | $t$ | $p$ |
|---|---|---|---|---|
| **Clustered by holding episode (primary)** | −0.823 | 0.315 | **−2.61** | **0.0091** |
| Newey-West HAC, 4 lags *(previously reported)* | −0.823 | 0.221 | −3.73 | 0.00019 |
| HC3 heteroskedasticity-robust | −0.823 | 0.380 | −2.17 | 0.0304 |

**What we withdraw.** The previous version stated that the in-position estimate
"clears that bar comfortably", referring to a Bonferroni threshold of 0.0083 at
family size six. Under the appropriate standard errors $p = 0.0091$, which
**falls just short of that threshold**. The revised text says so explicitly and
records that the earlier claim rested on a correction inappropriate to the
sample.

**What survives.** The loading remains negative, economically large, and
significant at the 5% level under all three conventions. We have added a fourth
qualification noting that 15 clusters is a small number for cluster-robust
inference, which is asymptotic in the number of clusters, and that the $p$-value
should be read as indicative.

We would rather report this than have it found later, and we are grateful the
reviewer caught it.

---

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
| 12 real strategies | 0.015 | **0.30** | 1.90 | 0.25 | always-long |
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

**We accept that a five-week separation requires justification on weekly data,
and we have quantified its effect rather than assert it is harmless. The
quantification does not support the consequence the report attributes to it.**

The reviewer is right that persistence in weekly returns is far shorter than in
the daily series for which runs declustering was developed, and that a five-week
window is aggressive. We should have justified it or tested it; we have now
tested it (new Table 8):

| Separation | Cluster maxima | $\hat{\xi}$ | 95% CI | KS $p$ |
|---|---|---|---|---|
| 1 week | 22 | −0.209 | [−1.53, 0.22] | 0.997 |
| 2 weeks | 21 | −0.241 | [−1.51, 0.22] | 0.981 |
| 3 weeks | 20 | −0.248 | [−1.51, 0.25] | 0.971 |
| **5 weeks (reported)** | **20** | **−0.248** | **[−1.51, 0.25]** | **0.971** |

The three- and five-week settings are identical. The loosest setting recovers
**two** additional cluster maxima and moves the shape estimate by 0.04, inside an
interval spanning more than 1.7.

The report describes the five-week window as "unnecessarily reducing the sample
size of exceedances from 26 to 20" and thereby "further weaken[ing] the power of
an already underpowered" analysis. The first half is accurate as arithmetic; the
second is not borne out — one week instead of five yields 22 maxima rather than
20 and changes nothing about the precision of the estimate. The imprecision
comes from having 26 exceedances in ten years, not from how they are grouped.

We have added the table and a statement that the choice is immaterial.

---

## Comment 7 — temporal aliasing in the tail signal

**Accepted as a limitation, and it is a real one. Two figures in the report are
inaccurate, which we note only because they understate the sparsity in one
respect and overstate the discarding in another.**

The reviewer is right that a signal constructed from daily exceedances but read
only on Fridays discards most of what it detects, and that every statistic
computed on the weekly series inherits that sparsity.

Two corrections to the figures. The report gives "only 14 non-zero observations
out of 504 weeks"; the actual count is **35**. The figure of 14 corresponds to
2.78% of 504, which is the positive-observation ratio reported in Table 1 — that
statistic counts observations strictly greater than zero, and the tail signal is
signed, so it omits the negative exceedances. The report also states that
Friday-only sampling "discards approximately 80%" of exceedance events. Measured
across weeks: 105 of 504 weeks contain at least one daily exceedance and 35 have
one on the Friday, so **roughly two-thirds** are discarded rather than four
fifths.

Neither correction weakens the point. We have added the figures to §2.2 and to
the Limitations section, stating that 70 of the 105 exceedance weeks enter the
panel as zeros and that the sparsity is the proximate reason the tail-alpha
skewness interval is so wide.

**On the remedy.** We agree that a weekly indicator registering an exceedance on
any trading day, or a threshold defined directly on weekly returns, would be a
better construction. We have not made that change. The present revision is a
correction of a published paper against its own specification, and redefining a
signal is a change of specification rather than a correction of one; making it
here would also break comparability with the published results this revision
exists to correct. We have recorded it as a limitation and as the natural next
change, and we would welcome the editor's view on whether it belongs in this
revision or a subsequent one.

---

## Summary of changes to the manuscript

| Change | Location |
|---|---|
| Cluster-robust standard errors primary; three-convention table | §5.5, Tables 9–10 |
| Bonferroni claim withdrawn; $p = 0.0091$ reported | §5.5 |
| i.i.d. versus block bootstrap comparison | §3.2, Table 3 |
| Tail-alpha interval attributed to sparsity, not dependence | §3.2 |
| $AI_t$ window stated (20 weeks, minimum 10 observations) | §2.4, Eq. 10 |
| Intercept units corrected to −1.2 bps | Table 9 note |
| Bootstrap scheme justification; block-length sensitivity | §5.7, Table 12 |
| Formal universe reduced to 12; random sequence a diagnostic | §5.7, Table 11 |
| Declustering sensitivity | §5.6, Table 8 |
| Tail-signal aliasing disclosed | §2.2, §4.3 |

All figures in the manuscript are machine-checked against the pipeline output,
and the analysis is covered by deterministic tests. The sample is unchanged:
$n = 504$, 8 January 2016 to 29 August 2025.
