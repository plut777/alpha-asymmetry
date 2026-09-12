# Pre-registration: entry-rule symmetry variants (Reviewer 3, round two, #4)

**Written and committed before any variant was computed.** Nothing in this file
was chosen after seeing a result. The commit containing this file is timestamped
earlier than the commit containing the variant outputs, and that ordering is the
evidence.

**Status:** prospective specification. **Originated by:** Reviewer 3, comment #4.
**Type:** specification decision, referred to Murad. Not a bug fix.

---

## 1. The defect being tested

The published rule's two legs differ in four ways at once
(`analysis/strategy.py:268-270`):

| | Long leg | Short leg |
|---|---|---|
| Skewness gate | `fast_skew_20w > θ` | `price_skew_20w > θ` |
| Confirmation series | `fast_alpha` | `pricing_alpha` |
| Confirmation threshold | `> 0` | `> 0.5 × pricing_std_20w` |
| Direction of response | positive → **long** (follow) | positive → **short** (fade) |

The manuscript argues for none of these asymmetries. The fourth is the
substantive one: the long leg follows strength in the fast signal, the short leg
fades strength in the pricing signal. The rule is a hybrid of a trend-follower
and a mean-reverter, and that hybrid was never defended.

"Make it symmetric" has no single meaning, because collapsing the hybrid
requires choosing which of its two economics to keep. Three variants are
therefore specified, each answering a different question.

θ denotes the skewness entry threshold, 0.75 at baseline, unchanged in every
variant. All other parameters — `max_holding_weeks=4`, sizing `weekly`,
execution lag 1 week, Friday close, position bounds [1.0, 2.0] — are unchanged
in every variant. Nothing outside the entry rule is touched.

---

## 2. The three variants, stated exactly

### P — Published hybrid (control, untouched)

```
long  :  fast_skew_20w  > θ   AND   fast_alpha    > 0
short :  price_skew_20w > θ   AND   pricing_alpha > 0.5 × pricing_std_20w
```

P is the default code path and must remain byte-identical in behaviour. See §5.

### A — Pure-fast

```
long  :  fast_skew_20w > θ   AND   fast_alpha > 0
short :  fast_skew_20w > θ   AND   fast_alpha < 0
```

Preserves the published **long** leg verbatim and derives the short leg by
reflection about zero. Both legs now read one series in one direction.

**Economic question:** is the rule's content trend-following in the fast signal?
If A resembles P, the pricing leg was contributing little and the strategy is
substantially a fast-alpha trend rule wearing an asymmetry label.

**Known structural consequence, stated in advance:** the two conditions are
complementary given the shared gate, so A is in the market whenever
`fast_skew_20w > θ` (except where `fast_alpha` is exactly zero, a measure-zero
event). A will therefore be **more** exposed than P, probably substantially.
Long and short cannot fire simultaneously in A.

### B — Pure-pricing

```
long  :  price_skew_20w > θ   AND   pricing_alpha < −0.5 × pricing_std_20w
short :  price_skew_20w > θ   AND   pricing_alpha >  0.5 × pricing_std_20w
```

Preserves the published **short** leg verbatim and derives the long leg by
reflection about zero, keeping the ±0.5σ band.

**Economic question:** is the rule's content valuation mean-reversion against the
sixty-day average? B is the fading interpretation taken seriously on both sides.

**Known structural consequence, stated in advance:** the ±0.5σ band leaves a
neutral zone, so B will be **less** exposed than A and may be less exposed than
P. Long and short cannot fire simultaneously in B.

### C — Equalised confirmation threshold

```
long  :  fast_skew_20w  > θ   AND   fast_alpha    > 0.5 × fast_std_20w
short :  price_skew_20w > θ   AND   pricing_alpha > 0.5 × pricing_std_20w
```

C keeps both sources and keeps the follow/fade hybrid intact. It changes exactly
one thing: the long leg's confirmation gate moves from a raw sign test to the
same volatility-scaled test the short leg already uses.

**The common threshold is fixed as: 0.5 × the rolling 20-week standard deviation
of that leg's own confirmation series, `min_periods=10`.** This is stated here
because "equalised thresholds" is otherwise underdetermined. The level (0.5), the
window (20 weeks) and the minimum observations (10) are chosen because they are
the values the published short leg already uses — no new free parameter is
introduced, and every constant already appears in `analysis/specification.py`.
The volatility-scaled *form* is chosen over the raw sign test because it is
scale-free, which is what makes it comparable across two series with different
units; a common raw threshold would not be a common threshold in any meaningful
sense.

This requires one new series, `fast_std_20w`, defined exactly as the existing
`pricing_std_20w` at `analysis/full_pipeline.py:117`:
`fast_alpha.rolling(20, min_periods=10).std()`.

**Economic question:** is the published asymmetry economically meaningful, or is
it an artifact of one leg being gated more loosely than the other? C isolates the
threshold asymmetry from the source-and-direction asymmetry. If C ≈ P, the
threshold difference is immaterial and the real issue is the hybrid. If C differs
materially from P, the published result depends on an unargued threshold choice.

**Known structural consequence, stated in advance:** C tightens the long gate and
loosens nothing, so C will be **less or equally** exposed than P on the long side.
Long and short can still fire in the same week in C, as in P, and that week is
handled by the existing flat branch.

---

## 3. Reporting rule, fixed in advance

1. **All three variants will be disclosed in full regardless of realised
   performance.** No variant will be dropped, demoted, or relegated to a footnote
   because of what it returned.
2. **Observed returns must not determine which symmetrization is treated as the
   defensible one.** If a variant outperforms, that is not evidence that its
   economics is correct; the sample cannot support that inference and this
   document is the record that the claim was ruled out before the numbers existed.
3. **Murad decides placement** — main text, appendix, or response letter — on
   grounds of conceptual relevance and presentation. That is an editorial
   decision about where a disclosed result belongs, not a decision about whether
   to disclose it.
4. **No variant will be promoted to "the correct specification."** The deliverable
   is a sensitivity exhibit and a limitation, not a replacement rule.

---

## 4. Metrics reported for every variant

For each of P, A, B, C, from `run_asymmetry_strategy(...).metrics`:

| Reported | Source key | Definition |
|---|---|---|
| Cumulative gross return % | `return` | `(1+r).prod() − 1`, ×100 |
| Cumulative net return % | `net_return` | same, on cost-charged returns |
| Sharpe (gross, annualised) | `sharpe` | `mean/sd × √52` |
| Max drawdown % | `mdd` | min of `curve/curve.cummax() − 1`, ×100 |
| Holding episodes | `holding_episodes` | rows of the trade ledger |
| In-position weeks | `in_position_weeks` | weeks with non-zero applied position |
| Execution legs | `execution_legs` | opening + closing units |
| Resizings | `resizes` | `event_type == "resize"` |
| Turnover | `turnover` | Σ abs change in position |

**Cost tier for the net figure is fixed now at 2.0 pips round-trip**
(`pip_size = 0.01`) — the widest tier in the published cost table, chosen as the
conservative end. Gross is the primary figure, consistent with the rest of the
paper.

### Exposure guard

A rule that is out of the market more often will usually show a smaller loss and
a flatter drawdown without being better. This is pre-declared so it cannot be
forgotten when the numbers arrive:

> For any variant whose gross return exceeds P's, in-position weeks will be
> reported immediately alongside. If a variant's gross return is higher **and**
> its in-position weeks are lower than P's, it will be reported as **"less
> exposed, not better"** unless its **mean gross return per in-position week**
> also exceeds P's. That per-week figure will be reported for all four regardless.

---

## 5. Invariants that must hold, or the exercise halts

- **I1 — P reproduces exactly.** The default code path must reproduce the
  committed baseline. The check asserts against
  `analysis/full_pipeline_results.json → baseline` **read from the file**, not
  against numbers transcribed into the test. Fields compared: `return`, `sharpe`,
  `mdd`, `holding_episodes`, `in_position_weeks`, `execution_legs`, `resizes`,
  `turnover`. Any deviation halts the exercise and is reported as a regression.
- **I2 — sample unchanged.** n = 504 weekly observations, 2016-01-08 to
  2025-08-29, for every variant.
- **I3 — no look-ahead.** The permanent causality suite in
  `tests/test_no_lookahead.py` runs against all three variants, not only P.
- **I4 — no analysis parameter outside the entry rule changes.** Verified by
  `tests/test_specification.py` continuing to pass unchanged.

---

## 6. What this exercise cannot settle

With 504 weeks and a single currency pair, none of these variants can be
distinguished from each other statistically in any way that would license a claim
about which economics is right. The purpose is to show the reader how much of the
published result rests on entry-rule choices the manuscript never argued for. A
large spread across variants is a statement about the fragility of the
specification, not a discovery about EUR/JPY.
