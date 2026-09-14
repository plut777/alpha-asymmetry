# Expected-change map: migrating the primary execution to next-session open

**Written and committed before the migration was run.** The commit containing
this file is timestamped earlier than the commit containing the rerun outputs,
and that ordering is the evidence. Nothing below was adjusted after seeing a
result.

## What changes

The signal and the decision timing are unchanged. A signal is still computed from
the Friday close, and the position is still decided at that instant. Only the
price pair used to realise the strategy return changes: instead of earning
Friday-close to Friday-close, a position earns from the **first trading-session
open strictly after the Friday signal date** to the first session open after the
following Friday. That is the Monday open in an ordinary week, and the next
available session open when the Monday is a holiday.

Formally, with `F[i]` the Friday signal dates and `M[i]` the first session open of
the week ending `F[i]`, so that `M[i+1]` is the first session open after `F[i]`:

```
weekly_return[j] = M[j+1] / M[j] - 1
```

The strategy applies `position[j-1]` to `weekly_return[j]`, so a decision at
`F[j-1]` earns `M[j] -> M[j+1]`: execution at the first open after its own signal,
held to the first open after the next signal. No quantity is read before it
exists.

## 1. Expected to CHANGE — consume `weekly_return`

| Section | Numeric fields | Why |
|---|---|---|
| `baseline` | 12 | strategy returns |
| `benchmarks` | 40 | every benchmark is `simple_strategy(pos, weekly_return)` |
| `walk_forward` | 47 | out-of-sample strategy returns |
| `regimes` | 30 | `strategy_return` per regime |
| `sensitivity` | 48 | per-threshold strategy returns |
| `factor_attribution` | 113 | dependent variable is the strategy return |
| `transaction_costs` | 15 | net strategy returns |
| `data_snooping` | 33 | every candidate is built on `weekly_return` |
| `sizing_variants` | 24 | strategy returns under both sizings |
| `return_inference` | 18 | bootstrap on the strategy return series |
| `evt` | 36 | EVT input is `weekly["weekly_return"].dropna()` |
| `cross_market` | 32 | the EUR/JPY row's `strategy_return`; other markets have their own inputs and should move only in their EUR/JPY-derived entries |

Expected: **448 numeric fields** in these sections, most of which should move.
Not every individual field must move — integer counts such as episode and leg
totals are expected to hold (§4) — but the return, Sharpe, drawdown and inference
fields should.

## 2. Expected to REMAIN INVARIANT — do not consume `weekly_return`

| Section | Numeric fields | Why |
|---|---|---|
| `alpha_statistics` | 105 | computed from `weekly[col]` for the five alpha columns only |
| `tail_construction_sensitivity` | 28 | built from daily exceedances and the weekly index |
| `sample` | 1 | panel rows come from `dropna` on three alpha columns, which does not involve `weekly_return` |
| `data_manifest` | 8 | input files unchanged |

Expected: **142 fields exactly unchanged.** Any movement here means the panel was
altered when it should not have been, and must be investigated before anything
else proceeds.

## 3. Expected to change ONLY IF the executable sample boundary moves

`weekly_return` becomes NaN in the final week (2025-08-29), because no session
open follows it in the data. The panel itself keeps 504 rows; the strategy is
evaluated on the 503 weeks that carry a realisable return.

- `sample.n` — **expected to stay 504**, because the panel is not truncated.
- Any statistic computed over the strategy return series is computed on 503
  observations rather than 504 and moves accordingly. This is a consequence of
  the boundary, not of the price pair.
- `execution_timing.common_sample_n` — **expected to stay 502**. That sample
  requires all four timings to exist and is unrelated to which one is primary.

## 4. Expected to be EXACTLY IDENTICAL

The decision path depends only on the signal columns, none of which change:

| Quantity | Expected value |
|---|---|
| Signal path (`long_signal`, `short_signal`) | identical, element by element |
| Position-decision path (`position`) | identical over the 503 shared weeks |
| Holding episodes | **15** |
| In-position weeks | **55** |
| Execution legs | **61** |
| Reversals | **1** |
| Resizes | **31** |
| Turnover | **51.996835** |

These hold only if the dropped final week carries no position and no position
change. **That is a prediction, not an assumption**: if the strategy holds a
position in the final week, the episode and leg counts will differ and the
prediction is wrong. It is recorded so that it can fail.

## 5. Expected direction, recorded to be checked rather than assumed

From the previously computed four-timing grid, the Monday-open column gave
cumulative gross −0.73% against Friday close's −6.64%, on the 502-week common
sample. The migrated primary is on 503 weeks, so the figure is expected to be
**close to but not necessarily equal to −0.73%**. An exact match would itself be
surprising and would warrant checking that the samples really are different.

## 6. Guards that must continue to hold

- `execution_timing` must still reproduce the primary series: the assertion that
  tied `friday_close` to `weekly_return` has to be re-pointed at the new primary,
  not deleted. A guard that is removed because it now fails is not a guard.
- The two standing identities: the factor intercept against the strategy's own
  mean weekly return, and low- plus high-VIX compounding to the full-sample
  return.
- Every provenance mapping must still resolve, since field paths do not change.

## 7. Independent verification, before the outputs are treated as canonical

The rebuilt series will be checked against a direct construction from each Friday
signal date to the first subsequent trading-session open, built without the
weekly `groupby` used in the pipeline — including at least one week where the
Monday is a holiday, to confirm the fallback lands on the next available session
rather than skipping a week or reusing a stale price.
