# Memo: a pre-specified entry-rule variant is gross-positive under the decided execution convention

**To:** Murad Farzulla · **From:** Tofik Israfilov · **Re:** entry-rule
symmetrization results after the Monday-open migration

You ruled to restore Monday open as the primary execution specification. Rerunning
the pre-specified entry-rule variants under that convention produced a result you
should see before the revision goes further. **No response is needed unless you
object**; the correction work is continuing.

## 1. What pure-pricing (B) is

The published rule's long and short legs are built from different signals. Its
long leg reads fast alpha; its short leg reads pricing alpha, firing when pricing
alpha exceeds half a rolling standard deviation. Variant **B preserves the
published short leg verbatim and derives the long leg by reflecting it about
zero**, keeping the ±0.5σ band:

```
long  :  price_skew_20w > θ   AND   pricing_alpha < −0.5 × pricing_std_20w
short :  price_skew_20w > θ   AND   pricing_alpha >  0.5 × pricing_std_20w
```

It is the valuation-fading reading of the rule taken seriously on both sides.

## 2. Its realised returns under Monday-open execution

**Gross +5.57%. Net +5.21%** at 2.0 pips round-trip, the widest tier in the cost
table. Sharpe +0.178, maximum drawdown −11.97%, 51 in-position weeks across 14
episodes.

## 3. All four pre-specified rules together

| Entry rule | Gross | Net 2.0p | Sharpe | MDD | Weeks | Episodes | bps/exposed week |
|---|---|---|---|---|---|---|---|
| P published hybrid | −0.73% | −1.14% | +0.005 | −10.64% | 55 | 15 | +0.4 |
| A pure-fast | −3.48% | −3.97% | −0.067 | −12.05% | 44 | 16 | −6.1 |
| **B pure-pricing** | **+5.57%** | **+5.21%** | **+0.178** | −11.97% | 51 | 14 | **+11.8** |
| C equal-threshold | −1.65% | −1.96% | −0.029 | −10.83% | 43 | 12 | −2.4 |

## 4. Three statements now in the manuscript that are false

1. **"Every pre-specified version remains gross-negative in this sample."** B is
   +5.57%.
2. **The range is "nearly as large as" the published hybrid's own loss.** The
   spread is now 9.04 percentage points against a 0.73% loss — more than twelve
   times it, not comparable to it.
3. **The directional reading of the equal-threshold variant.** Under Friday close,
   equalising the confirmation threshold *worsened* realised performance and we
   noted the direction was what a specification-search concern would predict.
   Under Monday open it *improves* performance. The remark has lost the direction
   it was attached to.

## 5. What B is and is not evidence for

B is evidence that **the realised economic conclusion is specification-sensitive**:
performance varies materially across four defensible readings of one entry rule,
including a change of sign.

B is **not** evidence that pure-pricing has positive expected alpha. No
comparative inference was pre-specified or run, and none is offered. The sample
does not support a stable performance conclusion across the pre-specified
entry-rule constructions.

The claim the paper can no longer make is that the failure is robust to
symmetrization. The claim it can make is narrower and, in our view, more useful:
the economic result depends on an entry asymmetry the original specification never
argued for, to a degree that exceeds the result itself.

## 6. This was fixed in advance

The three variants, the metrics, the cost tier, the exposure guard, and a reporting
rule stating that **all three would be disclosed whatever they returned and that
realised performance would not determine which symmetrization is treated as
defensible**, were committed to the repository before any of them was computed —
and before the Monday-open convention existed. The commit ordering is the record.

Two structural predictions recorded in that document were wrong and are left
standing in it rather than quietly corrected.

That is why B is reported rather than promoted, and why the finding is being
handled as specification sensitivity rather than as a new strategy. Had the
variants been constructed after seeing these returns, none of this would be
available to us.
