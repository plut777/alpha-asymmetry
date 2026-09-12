# Review notes

> **Status: working audit record. Not part of the pull request's argument.**
>
> This file documents the audit process — who originated each change, what was
> checked, and what was found — so that the work is traceable. It is written
> against `5135bac`, the unreviewed AI-generated draft this branch started from,
> because that is what was being audited.
>
> **The pull request itself is framed against the published paper (`4d21c69`),
> not against that draft.** Murad never adopted `5135bac`; its numbers have no
> standing, and nothing in it is his to answer for. Where a change needs
> justifying to the repository owner, it is justified in
> `docs/CORRECTION_CHANGELOG.md` and `docs/PROPOSED_PR.md` against the published
> paper. Read those two for the argument; read this one for the trail.

Running record of every change on branch `fix/strategy-specification`, who
originated it, and whether it is a **bug fix** (code did not do what the
published paper said) or a **specification decision** (a choice that changes
what the paper claims, and that no amount of code reading can settle).

Originators:

- **Murad** — Murad Farzulla / Dissensus AI, author of the published preprint
  and of everything at `upstream/master` (`4d21c69`).
- **Codex** — the AI agent that produced `alpha-asymmetry-corrected-branch.zip`,
  imported here as commit `5135bac`. Not reviewed at the time of import.
- **Claude** — this audit.
- **Tofig** — the contributor submitting this pull request.

Base for every comparison below: `upstream/master` = `4d21c69`
("Voice pass + README/CFF/DOI currency fixes", 21 Jul 2026).

Ground rule adopted for this branch, at Tofig's direction:

> Where the code and the paper disagree, fix the code. Any exception gets
> argued in the open and disclosed, never edited in quietly.

---

## Step 0 — Repository set up and Codex branch imported

**Originator:** Tofig (instruction), Claude (execution). **Neither a bug fix nor
a specification decision — provenance only.**

Cloned `plut777/alpha-asymmetry`, added `dissensus-ai/alpha-asymmetry` as
`upstream`, branched `fix/strategy-specification` from `upstream/master`, and
committed the Codex archive unmodified as a single labelled commit (`5135bac`)
so that every later change is separately reviewable. Nothing in that commit is
endorsed by this review.

---

## Step 0b — Audit of the Codex branch against the real history

**Originator:** Claude. **No files changed; findings only.**

### Verified: the four original bug claims

Checked against `git show 4d21c69:analysis/full_pipeline.py`.

| # | Claim | Verdict | Direction |
|---|---|---|---|
| 1 | Exit branch was dead code | **Confirmed** | Code was wrong, paper was right → fix the code ✔ |
| 2 | Strategy carried two lags, benchmarks one | **Confirmed** | Code was wrong, paper was right → fix the code ✔ |
| 3 | `compute_ai` used `pos.var()/neg.var()` | **Confirmed** | Code was wrong, paper (Eq. 5) was right → fix the code ✔ |
| 4 | Trade counter counted events, not round trips | **Confirmed as behaviour, misclassified as a bug** | Code matched the paper's own stated formula → see SD-3 |

Detail on 1: in the original loop the hold branch was guarded by
`prev_pos > 0 and not long_signal.iloc[i-1]`, but that branch was only reached
when `not long_signal.iloc[i-1]` was already true. The condition was therefore
always satisfied and `new_pos = prev_pos` was unreachable for any open
position. A position closed the moment its entry signal stopped firing.

Detail on 2: signals were read at `iloc[i-1]` inside the loop, stored at `i`,
then multiplied by `position.shift(1)`. Two lags. Benchmarks
(`simple_strategy`, `wk["mom"]`) used one.

Detail on 3: the original also returned `1.0` — not a missing value — for
`len(x) < 5` and for degenerate denominators, silently reporting a neutral
asymmetry index where the statistic was undefined.

### Verified: the "before" column is accurate

Codex hard-codes the pre-correction results as Python literals in
`analysis/full_pipeline.py` labelled "Values published in commit 4d21c69".
Every one of them checks out against `4d21c69:analysis/full_pipeline_results.json`
and `...results.txt`: return 3.6016, Sharpe 0.1489, MDD −7.9572, trades 17,
in-position weeks 25, walk-forward 2.46 % / 3 trades, and all five AI values
(0.1716, 0.9577, 0.8050, 3.4533, 1.4018). An earlier draft of this review
doubted these; the doubt was unfounded.

### Specification decisions Codex made and did not label as such

**SD-1 — The rebalancing rule was rewritten to match the code. Undisclosed.**
**Originator: Codex. Specification decision, presented as nothing at all.**

- `4d21c69:paper/alpha-asymmetry.tex:313` — `Rebalancing: Weekly (end of Friday close)`
- Codex `paper/alpha-asymmetry.tex:316` — `Rebalancing: none within an episode; changes occur only on entry, reversal, conflict, or expiry`

This change appears in no changelog entry and in no PR text. It is the failure
mode this correction exists to fix: the manuscript was edited so the paper
would agree with the code.

Compounding it, the original code *also* resized weekly in effect. Position size
was recomputed from the contemporaneous `ai_20w` on every bar where the entry
signal fired, and — because of bug 1 — those were the only bars on which a
position was held. Published paper and published code therefore **agreed** on
weekly resizing. Codex departed from both.

**SD-2 — Position size frozen at entry.**
**Originator: Codex. Listed as "confirmed implementation bug" #4; it is not a bug.**

Equation 10 is unchanged from the published version in its essentials and still
reads `1 + |AI_t - 1.0|` "where `AI_t` is the contemporaneous asymmetry index".
Codex appended "Size is fixed at entry and is not reset or resized by
subsequent same-direction signals" to the same paragraph, so the branch now
contradicts itself within four sentences.

Note that fixing bug 1 creates a question the original specification never had
to answer: what size applies during a *held* week in which no signal fires?
The original code never reached that state. Both answers are extensions of the
published rule; weekly resizing is the smaller one, because it preserves the
paper's stated words.

**SD-3 — "Trades" redefined as holding episodes and execution legs.**
**Originator: Codex. Listed as "confirmed implementation bug" #5; it is not a bug.**

The published paper defined its own metric explicitly: "Trades = completed
round trips (position-change events divided by two, a sign flip counting as one
event)". The code implemented exactly that. Code and paper agreed. Codex
changed both.

The change is nonetheless defensible, because the published paper's *label*
disagreed with the published paper's *formula*: events ÷ 2 does not count
completed round trips when a sign flip is treated as one event. This is an
internal inconsistency in the paper, and resolving it is worthwhile — but it is
a decision that changes a reported column, not a bug fix.

**SD-4 — The EVT input was changed from tail alpha to weekly absolute returns.**
**Originator: Codex. Disclosed in the changelog. Substantive.**

The published paper presented the GPD fit as characterising the tail-alpha
exceedance distribution — the strategy's own premise. The code fits absolute
Friday-to-Friday returns. Codex relabelled the section and table rather than
changing the code. Under the ground rule the code should have been changed.
Deferred (see backlog); the disclosure is honest in the meantime.

### Paper-follows-code changes that are disclosed and, in this review's
### judgement, correct — but that are exceptions to the ground rule

**EX-1 — Fast alpha equation.** Published: `(P_t − P_{t−5}) / (σ_20 √5)`.
Codex: `(P_t/P_{t−5} − 1) / (σ_20 √5)`. The published formula divides a yen
price difference by a volatility estimated from dimensionless returns, which is
dimensionally incoherent; the code's percentage return is the only reading that
makes the signal a z-score. Recommendation: keep the paper edit, argue it
explicitly rather than listing it as a mere difference.

**EX-2 — Hedge alpha equation.** Published: `ρ_t × Δr_t` with prose already
admitting the pipeline substitutes a constant −2 %. Codex moved the constant
into the equation. Fixing the code would require an interest-rate series the
repository does not contain. Recommendation: keep, disclose as data-limited.

**EX-3 — Monday-open execution.** Published: "Entry: Monday open following
Friday signal generation". Codex replaced it with a Friday-close proxy and
added the assertion that "Monday opening prices are not present in the
dataset."

**That assertion appears to be false.** `analysis/data_access.py` downloads
daily bars via `yf.download(..., interval="1d")`, which returns Open, High,
Low, Close and Volume; `_normalise_download` preserves every column. Monday's
open is in the data. Verification pending against a live download. If it is
present, the paper is asserting a data limitation that does not exist, and the
honest options are to implement Monday-open execution or to state plainly that
the Friday-close proxy is a *choice*. Flagged, not yet acted on.

**EX-4 — Position size range.** Published: `max(0.5, min(2.0, 1 + |AI−1|))`
with "No leverage; positions bounded to [0.5, 2.0]". The 0.5 floor is
unreachable because the inner expression is never below 1. Codex removed the
floor and stated the real [1, 2] range and its leverage implication. This
corrects a mathematical impossibility in the published paper. Correct and
disclosed.

**EX-5 — Tail alpha window wording.** Published: "rolling 52-week 95th
percentile"; Codex: "trailing 252 trading days" with a 60-observation warm-up.
Equivalent horizon, and `sgn(r)·|r| ≡ r`. Cosmetic. Not previously listed.

### Other findings

**F-1 — Provenance footnotes were deleted.** `4d21c69` recorded its own earlier
corrections inside table notes: the tail-skew 5.05 unsigned-magnitude error
(Table 1), benchmark rows that "traced to no committed code" (Table 3), "141
pooled trades" that could not be reproduced (Table 5), a "marginally
significant intercept of 21 bps" (Table 8), and `RC = 2.14 (p = 0.042)`
(Table 11). Codex rewrote those notes and dropped all of them except the GPD
one. In a paper whose contribution is a documented correction history, deleting
the correction history is a real loss. Recommend restoring.

**F-2 — Sharpe ratios are diluted, not risk-adjusted.** `_performance` divides
by the standard deviation of all 504 weeks, 449 of which are exactly zero
because the strategy is flat. −0.173 is a full-sample number, not the Sharpe of
the bets. Inherited from Murad's original; not introduced by Codex; not changed
here. Worth knowing before defending the figure.

**F-3 — `p = 0.037` would not survive the paper's own multiple-testing
discipline.** The manuscript applies Bonferroni at family size 5 elsewhere. The
full-sample momentum loading is marginal by comparison; the in-position
estimate (t = −3.53) is the one that carries weight.

---

## Step 1 — Data verification (download and hash comparison)

**Originator:** Tofig (instruction), Claude (execution). **Verification only; no
analysis result changed.**

### Environment

Reproduced from `requirements.txt` at the exact pins: Python 3.12.14, numpy
2.5.2, pandas 3.0.5, scipy 1.18.1, statsmodels 0.15.0, yfinance 1.7.0,
matplotlib 3.11.1. The manifest records Python 3.12.13; the difference is
patch-level. Baseline `pytest`: **11 passed**.

### Hash comparison against `analysis/data_manifest.json`

Fresh download 2026-09-02 ~15:45 UTC, versus the manifest's recorded run of
2026-09-02 ~10:05 UTC.

| Series | SHA-256 | Rows | Last date |
|---|---|---|---|
| EURJPY | match | 2930 | 2025-08-29 |
| DXY | match | 2831 | 2025-08-29 |
| VIX | match | 2830 | 2025-08-29 |
| AUDJPY | match | 2931 | 2025-08-29 |
| NZDJPY | match | 2929 | 2025-08-29 |
| GBPUSD | match | 2929 | 2025-08-29 |
| **SPY** | **differs** | 2830 | 2025-08-29 |
| GLD | match | 2830 | 2025-08-29 |

Seven of eight reproduce byte-for-byte. This is a stronger reproducibility
result than expected and is worth stating in the PR: the FX and index series
are stable at the byte level across independent fetches.

SPY is the exception, and the cause is structural rather than accidental. SPY
is downloaded with `auto_adjust=True`, so its entire price history is
back-adjusted by dividend factors. Any distribution recorded between two
fetches rescales every historical row. The FX crosses pay no dividends and are
unaffected; GLD is non-distributing over the window.

### Impact of the SPY difference: none at reporting precision

The complete pipeline was rerun on the fresh data and its output compared
value-by-value against the committed `analysis/full_pipeline_results.json`.
Exactly five values differ, all confined to the SPY cross-market row:

| Value | Committed | Rerun | Rounds to |
|---|---|---|---|
| SPY strategy return | 13.18273 % | 13.18263 % | 13.18 % |
| SPY tail skew | 0.9421965 | 0.9421603 | 0.94 |
| SPY fast skew | −0.2050038 | −0.2050027 | −0.21 |
| SPY pricing skew | −1.0860243 | −1.0860238 | −1.09 |
| SPY coverage skew | 1.8501188 | 1.8501217 | 1.85 |

Every other number in the file is identical, including the entire EUR/JPY
analysis. SPY buy-and-hold is unchanged, as expected: a uniform rescaling
leaves percentage returns invariant. The residual differences are rounding
noise in the stored adjusted prices, not a change in the data's economic
content. **No figure printed in the manuscript changes.**

### Constraint checks on the rerun

- Sample: n = 504, 2016-01-08 to 2025-08-29. ✔
- Identity 1, factor intercept vs. strategy mean weekly return:
  −0.00013783 vs. −0.00013928, difference 1.4e−06. **Holds.**
- Identity 2, low-VIX × high-VIX compounding to full sample:
  (1 − 0.05778836)(1 − 0.01904606) − 1 = −7.573378 %, against a full-sample
  −7.573378 %. Difference 4e−14 percentage points. **Holds.**

### EX-3 resolved: the Monday-open claim is false

The downloaded EUR/JPY frame carries the columns
`['Close', 'High', 'Low', 'Open', 'Volume']`. Monday's opening price is present
in the dataset. The manuscript's assertion that "Monday opening prices are not
present in the dataset" is incorrect as written.

Decision (Tofig): correct the claim in this pull request — state that the
Friday-close proxy is a deliberate choice, not a data limitation — and place
the implementation of Monday-open execution on the backlog rather than
expanding this change.

### Step 1 changes made

**Originator:** Tofig (decision), Claude (execution). **No analysis result
changed — verified by rerunning the pipeline before and after and diffing every
value: zero differences.** `pytest`: 11 passed.

1. **`analysis/cache/` stays in `.gitignore`; the CSVs are not committed.**
   Yahoo Finance data may carry redistribution terms, which is why the line was
   there in the first place (`analysis/data_access.py` says so explicitly). That
   is the repository owner's call to make knowingly, not an outside
   contributor's to make silently inside a correctness PR. Raised in the PR text
   instead.

2. **New `analysis/fetch_data.py`.** Downloads the eight series and checks each
   file's SHA-256 against the committed manifest, reporting expected and
   unexpected differences separately and exiting non-zero only on the latter.
   This is what makes a fresh clone self-service: the inputs are fetchable and
   checkable without the raw files being republished here.

3. **`HASH_STABILITY` recorded in `analysis/data_access.py` and in the
   manifest.** Each series is now labelled with whether its bytes can be
   expected to reproduce. Six are FX spot rates or index levels, which carry no
   corporate-action adjustment and so cannot drift; GLD made no cash
   distribution in the window; SPY is a distributing ETF fetched with
   `auto_adjust=True` and is the only file in the set that can change. The
   committed `data_manifest.json` was *annotated* with these fields — no
   recorded hash or timestamp was altered, so it remains the record of the run
   that produced the committed results.

4. **The pipeline no longer overwrites the reference manifest.**
   `full_pipeline.py` wrote its observed manifest over
   `analysis/data_manifest.json`. That destroyed the very file `fetch_data.py`
   compares against: after one pipeline run a reader would have been checking
   their data against their own data. The run-time manifest now goes to
   `data_manifest.observed.json` (gitignored) and the committed manifest stays
   the reference. Originated by Claude; a defect in the Codex branch, not in
   Murad's original, which had no manifest at all.

5. **README "Data" section rewritten** to state that the raw CSVs are not
   committed and why, and to set the correct expectation that seven of eight
   hashes reproduce and SPY does not.

Note on wording, for accuracy in review: it is six series that structurally
cannot drift, not six *FX pairs* — four FX crosses (EURJPY, AUDJPY, NZDJPY,
GBPUSD) plus two index levels (DXY, VIX). GLD is a seventh that is stable in
this window without being structurally guaranteed.

---

## Step 2 — Position sizing resolved: weekly resizing

**Originator:** conflict created by Codex (SD-1, SD-2); resolution decided by
Tofig on Claude's revised recommendation. **This is a specification decision,
not a bug fix, and must be labelled as one wherever it appears.**

### The conflict

The Codex branch contradicts itself inside a single paragraph. Equation 10 is
carried over from the published paper and still reads
`min(2.0, 1 + |AI_t - 1.0|)` "where `AI_t` is the contemporaneous asymmetry
index", and four sentences later the branch states "Size is fixed at entry and
is not reset or resized by subsequent same-direction signals." Both cannot hold.

### What the published version actually specified

Verified against `4d21c69`, Murad's July 2026 version:

- **The manuscript said weekly.** `paper/alpha-asymmetry.tex:313` read
  `Rebalancing: Weekly (end of Friday close)`. Codex rewrote that line to
  "none within an episode" and disclosed the change nowhere.
- **Equation 10 said contemporaneous.** `AI_t` carries a time subscript that
  indexes every week, not the entry week. Had entry-only been meant, the
  subscript would have named the entry date.
- **The code also resized weekly, in effect.** In
  `4d21c69:analysis/full_pipeline.py` the size was recomputed from the current
  `ai_20w` on every bar where the entry signal fired, and because of the dead
  exit branch those were the only bars on which any position was held. Every
  held week therefore received a freshly computed size.

Paper and code agreed. There was no disagreement here for a correction to fix.

### Why this is still not a restoration

**Both options are extensions of the published rule, and the write-up must say
so.** Repairing the dead exit branch creates weeks in which a direction is held
while no signal fires. The published specification never had to size that state
because the original implementation could not reach it: it closed any position
the moment its entry signal stopped firing. "Rebalancing: Weekly" was written
about a strategy that was only ever in the market while signalling.

Weekly resizing is chosen as the **smaller** extension — it keeps the
manuscript's stated rebalancing frequency and Equation 10's contemporaneous
index, and requires changing no published sentence. Freezing at entry is the
larger extension, and it additionally requires rewriting two published
statements to fit. That is the argument. It is not a claim that weekly resizing
is what the published rule unambiguously said about a state it never described.

### The counter-argument, recorded rather than buried

Weekly resizing lets the asymmetry index change exposure every week on new
information, which makes AI something closer to a second timing signal rather
than a sizing multiplier applied to a signal-driven entry. That is a real
methodological objection and it is the reason this review initially recommended
freezing. It was overtaken by the evidence above: the objection argues for
*changing* the published specification, and a correction PR is not the place to
do that silently. It is reported as the alternative instead.

### Framing constraint

**−7.57 % is not a baseline being departed from.** It is the output of a
specification Codex invented and then edited the manuscript to justify. It has
no standing as a prior result, and neither the changelog nor the PR text may
describe the weekly-resizing figure as a movement away from it. The comparison
that matters is between the two candidate specifications, both computed here.

### Implementation

`run_asymmetry_strategy` takes `sizing="weekly"` (default, headline) or
`sizing="entry"` (the reported alternative). Resizing changes only the notional:
it never opens or closes a holding episode, never flips direction, and never
resets the four-return holding clock. Both are run in the pipeline and reported
under `sizing_variants` in `full_pipeline_results.json`.

Also in this step, and consequential:

- `trade_ledger.csv` column `position_size` renamed **`entry_position_size`**.
  Under weekly sizing the notional varies within an episode, so a bare
  "position_size" on an episode row would be misleading; the full weekly path
  is in `position_ledger.csv`.
- **The dead resize branch in the cost accounting is no longer dead.** It is now
  the branch that prices every within-episode notional change. Tofig's original
  item 5 ("remove the dead resize branch") is therefore withdrawn by
  consequence; the `pip_size` comment it also asked for still stands.
- The `strategy.py` module docstring claim that "no Monday-open prices are
  available in the source data" is corrected (EX-3): the daily bars carry an
  `Open` column, so the Friday-close proxy is recorded as a choice.

### Results under each specification

| | weekly (headline) | entry (alternative) |
|---|---|---|
| Cumulative gross return | **−6.64 %** | −7.57 % |
| Sharpe | **−0.153** | −0.173 |
| Maximum drawdown | **−12.56 %** | −14.29 % |
| Hit rate | 47.27 % | 47.27 % |
| In-position weeks | 55 | 55 |
| Holding episodes | 15 | 15 |
| Execution legs | 61 | 30 |
| Resizes | 31 | 0 |
| Turnover (units) | 52.00 | 49.15 |

Entries, exits, direction and exposure are identical under both; only the
notional path differs. The strategy still loses money before costs, still has a
negative Sharpe, still holds a position in 55 of 504 weeks across 15 episodes,
and is still nearly inert out of sample. **No conclusion in the paper turns on
this choice**, which is the most useful thing to be able to say about it.

### Constraint checks

- Sample: n = 504, 2016-01-08 to 2025-08-29. ✔
- Identity 1: intercept −0.00011964 vs. mean weekly return −0.00012029,
  difference 6.4e−07. **Holds.**
- Identity 2: (1 − 0.05077847)(1 − 0.01646441) − 1 = −6.640684 % against a
  full-sample −6.640684 %, difference 1e−14 pp. **Holds.**
- `pytest`: **14 passed**, from 11. See "Rewritten test assertions" below.

### Cost and data-snooping figures under weekly sizing, on the record

| Cost scenario | pips | weekly net | weekly Sharpe | frozen net | frozen Sharpe |
|---|---|---|---|---|---|
| Zero cost | 0.0 | −6.6407 % | −0.1533 | −7.5734 % | −0.1726 |
| Prime brokerage | 0.3 | −6.6981 % | −0.1549 | −7.6272 % | −0.1741 |
| Institutional | 0.7 | −6.7746 % | −0.1570 | −7.6988 % | −0.1760 |
| Retail tight | 1.3 | −6.8893 % | −0.1601 | −7.8063 % | −0.1789 |
| Retail wide | 2.0 | −7.0229 % | −0.1638 | −7.9314 % | −0.1823 |

Cost drag at 2.0 pips: 0.382 pp weekly, 0.358 pp frozen.

**Break-even round-trip cost: not defined under either specification**, because
the zero-cost return is already negative — there is no positive cost at which
the strategy crosses zero, since it starts below it. The July version published
19.2 pips, which was meaningful then only because its gross return was +3.60 %.
This is the correct treatment, and it should be stated as "not applicable"
rather than reported as zero.

| Data-snooping test | statistic | weekly p | frozen p |
|---|---|---|---|
| White's Reality Check | 0.0203 | 0.150 | 0.150 |
| Hansen's SPA | 1.9024 | 0.261 | 0.262 |

Best-performing candidate under both: the seeded random sequence.

The statistics are *identical* across the two sizing modes, which is not a
coincidence and is worth being able to explain: both tests take a maximum over
the 13-candidate universe, and the maximum is attained by the random candidate,
whose returns do not depend on the asymmetry strategy's sizing. Only the
bootstrap covariance sees the changed asymmetry series, which is why the SPA
p-value moves by 0.001 and the Reality Check p-value not at all.

### Rewritten test assertions — part of the specification decision, category (b)

**Not maintenance. Review these with the sizing decision, not with the
housekeeping.** `tests/test_strategy.py` contained
`test_repeated_same_direction_signal_does_not_resize_or_reset_clock`, whose
assertions *encoded the frozen-size specification*: it asserted a flat position
path of `[1, 1, 1, 1, 0, 0]` against a rising AI, and `resizes == 0`. Those
assertions were not testing an implementation detail, they were pinning a
specification, and the specification changed.

It is now
`test_weekly_sizing_tracks_contemporaneous_ai_without_resetting_the_clock`,
asserting `[1, 2, 2, 2, 0, 0]` and `resizes == 1` with the holding clock and
episode count unchanged. Editing a failing test until it passes is the standard
way to conceal a regression, so this is stated in the open: the changed
assertions are a claim about what the strategy is *supposed* to do, and Murad
should approve them on that basis.

Three tests were added: the frozen variant's behaviour, resize cost accounting,
and rejection of an unknown sizing mode. 11 → 14.

### How the cost model scales, and why more legs did not cost more

Execution legs doubled (30 → 61) while turnover rose 5.8 % (49.15 → 52.00), and
the cost table barely moved. Confirmed from the model rather than inferred:

`analysis/strategy.py:329` is the line that decides it:

```python
unit_cost = ((round_trip_cost_pips / 2.0) * pip_size / price).fillna(0.0)
```

`unit_cost` is a cost *per unit of notional*, and every event multiplies it by
the notional actually traded — `abs(position)` on an entry, `abs(previous)` on
an exit, both on a reversal, and `abs(position) - abs(previous)` on a resize.
**There is no fixed per-leg term anywhere in the model.** Verified empirically:
the total units charged equal total turnover exactly, to floating point, under
both sizing modes (51.9968 and 49.1467).

So turnover is the only driver, and cost rose 5.6 % against turnover's 5.8 %
(the small gap is because `unit_cost` divides by that row's price, making cost a
price-weighted turnover rather than raw turnover).

The reason turnover barely moved despite 31 extra legs is that resizes are
small by construction — `ai_20w` is a 20-week rolling statistic and moves
slowly:

| event | n | mean abs. notional change | total |
|---|---|---|---|
| entry | 14 | 1.6214 | 22.6989 |
| exit | 14 | 1.3940 | 19.5167 |
| reversal | 1 | 3.8744 | 3.8744 |
| **resize** | **31** | **0.1905** | **5.9068** |

Resizes are 51 % of the legs and 11 % of the turnover.

**Caveat worth carrying, because it cuts against the reassuring reading.** That
costs stayed immaterial is partly a property of *the cost model*, not only of
the strategy. The model charges spread in proportion to size, which is right for
spread, but it carries no per-ticket or minimum-ticket component. A real
execution schedule with any fixed cost per order would charge the 31 extra
resize orders something, and 31 orders averaging 0.19 units is exactly the
pattern a fixed component penalises. The model as written cannot express that.
Added to the backlog.

### Effect on the momentum finding (item 4)

The figures supplied for the write-up were taken from the frozen-size run and
have moved slightly. Under weekly sizing:

| | frozen (superseded) | weekly (current) |
|---|---|---|
| Full sample | b = −0.0470, t = −2.087, p = 0.0369 | b = −0.0462, t = −2.076, **p = 0.0379** |
| In-position | b = −0.8238, t = −3.532, p = 0.00041 | b = −0.8227, t = −3.725, **p = 0.00019** |

The finding is unchanged in substance and slightly stronger on the in-position
sample. The full-sample p-value remains marginal. Item 4 must be written from
the current column.

---

## Open: the byline name does not match the contributor's other records

**Raised by Tofig. Unresolved by design — to be settled before deposit, not
before the pull request.**

The paper's title page reads **"Tofik Israfilov"**. The GitHub account, the git
commit authorship on this branch, and the personal email all read
**"tofigisrafilov"** — Tofig Israfilov. The forms differ in the given name (k/g)
and in the transliteration of the surname.

**Why it matters and why it is hard to fix later.** The byline is what gets
indexed. Once a version is deposited to Zenodo and SSRN the author string is
attached to a DOI and propagates into Google Scholar, ORCID and Crossref, and
into every citation made from it. Author-disambiguation services key on exact
strings, so "Tofik Israfilov" and "Tofig Israfilov" will be treated as two
people. Merging them afterwards ranges from tedious to impossible depending on
the service. The correction is free now and expensive after the first citation.

**State:** left as "Tofik Israfilov" on instruction. To be confirmed before
anything is deposited.

**Worth deciding at the same time:** whether to register an ORCID. None was
supplied, so none is printed. An ORCID is what makes the name-form question
survivable — it identifies the person independently of how the name is spelled
on any given paper. If both forms are going to exist across records, an ORCID
stops being optional.

---

## Referee report — this is a review of OUR work, not of the published paper

**Registered before responding, at Tofig's direction, because it determines the
posture of the reply.**

Reviewer 3's report is on the **corrected manuscript produced in this revision**,
not on `4d21c69`. The evidence is in the quotations: comment 1 quotes the
annualized return of −0.71% with its interval, comment 3 quotes "evaluated at
each Friday close for as long as a direction is held", and comment 8 quotes
"−0.012 bps weekly" — all three are sentences written in this revision and
absent from the published version.

**Four of the eight comments are correct**, and two of those change what the
paper says. We answer as authors, not as contributors relaying a report about
someone else's paper. The response letter is written in the first person plural
and concedes what is conceded without distancing.

| # | Comment | Verdict |
|---|---|---|
| 8 | Intercept unit mismatch | correct — ours, 100× |
| 6 | Newey-West invalid on non-contiguous weeks | correct — weakens our new finding |
| 5 | Normal-theory SE is a strawman | correct — our attribution was wrong |
| 3 | AI lookback window absent from the specification | correct — ours |
| 7 | Temporal aliasing in the tail signal | direction correct, both figures wrong |
| 4 | 5-week declustering excessive | reasonable, asserted consequence false |
| 1 | Inconsistent bootstrap schemes | fair; needs justification, not a defect |
| 2 | Random candidate dilutes the tests | mechanism runs the other way in this data |

### The retreat on comment 6, recorded in full

Cluster-robust standard errors by holding episode are adopted as the primary
specification. The momentum finding survives at 5% under every specification
tried, and weakens substantially:

| Standard errors | t | p |
|---|---|---|
| HAC Newey-West, 4 lags (what we published) | −3.73 | 0.00019 |
| **Cluster-robust by episode (now primary)** | **−2.61** | **0.0091** |
| HC3 | −2.17 | 0.0304 |

Our sentence "the in-position estimate at p = 0.00019 clears that bar
comfortably", referring to a Bonferroni threshold of 0.008, **is now false**. At
p = 0.0091 it falls just short. That sentence is deleted rather than reframed.
Tofig pre-committed to reporting whatever the check produced, and this is what it
produced.

**The confidence pass is the reason this retreat is survivable.** That pass had
already removed "a disguised short-momentum bet", "largely explained", the
one-for-one claim and the section heading "It Is Not Trading Asymmetry", and had
already corrected an argument that ran opposite to its own conclusion. Had the
reviewer met the pre-confidence-pass text, the retreat forced by comment 6 would
have been considerably larger: a claim that the strategy *is* a disguised
momentum bet, resting on p = 0.00019, would have had to be withdrawn rather than
qualified. Softening a claim before it is challenged is cheaper than defending
it after.

### Comments 3 and 8 were ours, and we shipped them

Both are errors this revision introduced, and neither was caught by any check
this project built. That is worth knowing about the method, not only about the
two errors.

**Comment 3 — a parameter that exists only in code.** Equation 10 sizes the
position from `AI_t` and never states the lookback window. The code uses a
20-week rolling window with `min_periods=10` on fast alpha. The window is
mentioned once in the manuscript, incidentally, in a Trading Frequency paragraph
about turnover — never in the specification where a replicator would look. The
strategy is not reproducible from the paper alone.

**No check could have caught this**, because every check compares reported
figures against pipeline output. Both agreed. The defect is an *absence* in the
paper, and there is nothing for a value-comparison to compare.

**Comment 8 — a correct figure in the wrong units.** The factor table note
reported "an intercept of −0.012 bps weekly". The coefficient is −0.00012 in
decimal weekly return, which is −0.012 **percent**, or −1.2 bps. Off by 100×.

**The machine check passed it**, because the check verified that the string
"−0.00012" in the table matched the JSON. It did. The error was in a different
sentence, restating the same correct number in a unit the checker knew nothing
about.

**What this says about the verification method.** It is strong against one class
of error — a reported number disagreeing with the number that was computed — and
blind to at least two others: a parameter that is never reported at all, and a
correct number restated in wrong units. Both were caught by a human reading for
meaning. The apparatus reduces the surface a reader has to check; it does not
remove the need for one.

---

## Referee round two — small-cluster inference, and two audits

**Originator: Tofig.** `pytest`: 17 passed (was 14).

### The HAC framing was wrong and is corrected

Reporting HAC "alongside" cluster-robust errors as one of three specifications
conceded the reviewer's point and then ignored it: if a lag-based correction is
inapplicable to a non-contiguous sample, it is not a robustness check. HAC now
appears only as the withdrawn published figure, labelled as such. CR2 is the
specification; HC3 is the robustness check.

### Small-cluster correction applied, and it moved the number again

Flagging that 15 clusters is few was not the same as fixing it.
`analysis/inference.py` implements CR2 with Bell--McCaffrey Satterthwaite
degrees of freedom and a restricted wild cluster bootstrap-t with Rademacher
weights.

| Inference | t | p |
|---|---|---|
| Newey-West HAC (published, now withdrawn) | −3.73 | 0.00019 |
| CR1 clustered (previous revision) | −2.61 | 0.0091 |
| CR2, BM dof = 10.2 | −2.54 | 0.0288 |
| **Wild cluster bootstrap-t (primary)** | **−2.54** | **0.0379** |

The p-value has moved by more than two orders of magnitude across this
revision's three attempts at it. It remains below 0.05 and is now an order of
magnitude from the 0.0083 Bonferroni threshold rather than just short of it.
Tofig pre-committed to reporting whatever emerged, twice, and the number moved
against us both times.

### #3 broadened: parameters centralised

`analysis/specification.py` declares every free parameter with its value, unit
and role, and generates the manuscript's specification table.
`tests/test_specification.py` fails if the table and the code disagree, so a
parameter cannot change in one without the other. This addresses the class of
defect, not the instance: the AI window was unreported because parameters lived
only as literals, and nothing forced the prose to agree with them.

### #8 broadened: unit audit swept the whole manuscript

Checked bps against percent against decimal returns, weekly against annualised,
volatility units, regression slopes, turnover units and pip size, each against
the computed value. **`−0.012 bps` was the only unit error in the paper.** The
July note's "21 bps weekly (10.9% annualized)" is arithmetically right and is a
historical quotation left verbatim.

### The 67% discard figure, verified again and stated with both bases

Confirmed from raw outputs: 504 weekly observations; 35 non-zero after Friday
sampling; 105 weeks contain at least one daily exceedance; 70 of those 105 are
zero after sampling, giving 66.7%. The reviewer's 14 is exactly the
positive-observation count, confirming it came from the POR rather than a
non-zero count. The letter now states both denominators explicitly, because
correcting a reviewer's arithmetic with an ambiguous statistic of our own would
be worse than saying nothing.

---

## Tail aggregation sensitivity — ISOLATED COMMIT, REVERTIBLE, AWAITING MURAD

**Originator: Tofig, as a proposal for Murad rather than a decision. Deliberately
confined to one commit.**

**This entire treatment lives in a single commit. `git revert` on that commit
removes the code, the manuscript table, every qualification, the letter section
and the PR block together, and nothing else in the branch depends on it.** That
isolation is the point: the item touches Murad's abstract and redefines the
character of one of his five signals, and he has not ruled on it.

### What was found

Three defensible weekly aggregations of the identical daily exceedance rule:

| Aggregation | Non-zero | Skew | Block CI | Excludes zero |
|---|---|---|---|---|
| Friday observation (published, kept primary) | 35 | −1.48 | [−3.10, 0.54] | no |
| All days, signed sum | 105 | +0.22 | [−0.72, 1.09] | no |
| All days, largest abs. exceedance | 105 | −1.14 | [−1.97, −0.09] | **yes** |

The estimate changes sign and the interval excludes zero under one of three.

### What was implemented, and what deliberately was not

Implemented: the Friday-sampled construction stays primary; all three are
reported as a sensitivity table; the conclusion is that tail inference is
aggregation-sensitive; the six locations claiming "only coverage survives" are
qualified to hold under the primary construction.

Not implemented: switching the primary construction. Two reasons are stated in
the paper and the letter. First, choosing an aggregation after observing which
one yields significance is specification selection on outcomes, which is the
practice this paper criticises — and it is not made acceptable by the selection
being ours. Second, neither alternative is self-evidently correct: the signed
sum lets opposing exceedances cancel within a week, the largest-exceedance rule
lets one day define the week, and both encode unargued claims about what weekly
tail exposure means.

### A framing instruction, recorded because it changed the writing

Tofig directed that the published construction must **not** be framed as the
weakest of the three. That framing invites a reading about which choice
flattered the result, which is an accusation the evidence does not support and
which is beside the point. The point is that reasonable choices produce
different signs and significance levels. The paper and the letter say that and
do not rank the constructions.

### Locations qualified

Abstract; §3.2 block-bootstrap yardstick; §3.2 "What survives"; §4.1 "Little
Asymmetry to Exploit"; §5 robustness introduction; §5.7 Bonferroni paragraph;
Conclusions item 1, with the sensitivity added as a new conclusion item. Under
the primary construction every one of these claims still holds; each now says so
rather than stating it flat.

---

# PRE-REGISTRATION — execution-timing robustness grid

**Recorded 2026-09-12T11:53:56Z, before any grid result existed. The commit
containing this section is the evidence for that claim; its timestamp precedes
the commit containing the results.**

**Partial blindness, stated up front.** Two of the four cells are *not* blind.
Friday close is the current baseline and Monday open was computed and reported
earlier on 2026-09-12 (cumulative −0.73%, Sharpe 0.005, mean weekly difference
+1.25 bps, annualized +0.64 pp, paired stationary-bootstrap CI on the annualized
difference [−0.66, +2.01]). **Monday close and Tuesday open are unseen at the
time of writing.** A pre-registration that concealed the first fact would be
worth nothing, so it is recorded as partial.

## The grid — fixed now, not to be extended

Four execution timings, all from the **identical** Friday-close signal. No
timing is added after results are seen.

| Label | Entry point | One-week return earned |
|---|---|---|
| **FC** | Friday close of week $t$ (current baseline) | $C_{t+1}/C_t - 1$ |
| **MO** | Open of the first trading day of week $t+1$ | $O_{t+2}/O_{t+1} - 1$ |
| **MC** | Close of the first trading day of week $t+1$ | $\mathrm{MC}_{t+2}/\mathrm{MC}_{t+1} - 1$ |
| **TO** | Open of the second trading day of week $t+1$ | $\mathrm{TO}_{t+2}/\mathrm{TO}_{t+1} - 1$ |

Every variant holds for exactly one week from its own entry point, so holding
periods are comparable. Signals, entry rules, exit rules, holding clock and
position sizing are identical across all four; only the return series changes.

## Primary contrasts — three, declared now

1. **FC vs MO** — published-versus-current convention. *Not blind.*
2. **MO vs MC** — same-day execution delay, no weekend crossed. *Blind.*
3. **MC vs TO** — overnight execution delay, no weekend crossed. *Blind.*

Any other pairwise contrast is **secondary** and will be labelled as such, with
a family-wise max-statistic block-bootstrap adjustment or simultaneous
intervals. The grid is a robustness check, not a specification search.

### What each contrast isolates, declared before seeing the numbers

- FC vs MO crosses a weekend; MO vs MC and MC vs TO do not.
- **If the weekend-crossing contrast moves and the two non-weekend contrasts do
  not, the effect is weekend-specific** and the decomposition paragraph stands.
- **If all three move, it is general execution-delay sensitivity**, and that
  paragraph must be rewritten rather than adjusted.
- If only the non-weekend contrasts move, the current decomposition is wrong.

## Inference

Paired **moving-block bootstrap**: fixed block length, overlapping blocks drawn
with replacement, concatenated to sample length, **the same sampled block
indices applied to all four variants** so the comparison is paired.

- Primary block length **4 weeks**, $B = 2000$, seed 42. Four weeks is the
  dependence scale already adopted for strategy returns in this paper; the
  13-week block used elsewhere was chosen for overlapping-window *signals* and
  is not the right scale for returns.
- Pre-registered block-length sensitivity: **8 and 13 weeks**, same procedure.
- The paired **stationary** bootstrap already run is retained as a comparison,
  and whether the conclusion changes between the two schemes is reported.

## Reported per timing

Cumulative gross return, mean weekly return, annualized return, Sharpe, maximum
drawdown, and transaction-cost-adjusted return at the paper's existing cost
tiers (0.0 / 0.3 / 0.7 / 1.3 / 2.0 pips).

## Common-sample rule

Every paired comparison is computed on the **exact set of signal weeks available
under both conventions in the pair**, and the number of observations dropped and
the reason are reported. The common-sample figure is the **headline** for every
paired comparison; the full-sample figure appears as a footnote where it
differs. If any comparison changes materially between the two, that is stated
explicitly, because it would mean part of the apparent execution effect is a
sample-endpoint effect rather than an execution effect.

Known in advance: MO loses the final week (no following open). MC and TO may
lose further weeks to holidays.

## Power bound for the weekend-gap test

The null result for "does the entry signal predict the weekend gap it bears"
will be reported with a detectable-effect bound estimated **by simulation using
the observed dependence structure** — resampling by holding episode, injecting a
known position-gap relationship of magnitude $\delta$, and locating the
$\delta$ at which the wild cluster bootstrap rejects 80% of the time. **No
i.i.d. analytical power formula will be used**, since that would contradict the
cluster-aware inference used everywhere else.

The bound will be stated against the **effective sample of 15 holding episodes**,
not 55 weeks, since that is what cluster-robust inference is asymptotic in.

## Wording rules fixed in advance

- "We find no detectable relationship **in this sample**" — never "there is no
  relationship". $p = 0.65$ fails to detect; it does not establish a zero
  population effect.
- Every null is reported with its power bound attached.

---

## Directives on the synthesis (Tofig, recorded with the pre-registration)

**The three sensitivities are not equivalent and must not be written as though
they were.**

- **Tail aggregation** genuinely changes sign and significance across reasonable
  constructions.
- **Momentum** is weakened by both tighter inference and endogenous sample
  selection, but survives.
- **Execution** moves the point estimate materially while the paired bootstrap
  cannot distinguish the conventions.

The common lesson is **sensitivity to under-justified design choices**. It is
*not* that all three headline results are proven artefacts.

**The successive inference tightenings are a verification and process lesson,
not evidence for the paper's substantive thesis.** If claims weakening under
tighter checks validated the method, claims strengthening would have to
invalidate it. What the sequence shows is that stronger checks exposed
fragility — nothing more. Recording this because the temptation to read the
pattern as confirmation is exactly the reasoning error the paper criticises.

**Placement: Discussion and Limitations only.** The synthesis is not promoted to
the abstract or the headline conclusion until the endogeneity comment and the
asymmetric-design comment are resolved, since those may change what the
defensible overarching claim is. (Tofig withdrew an earlier line calling this a
reframing of the paper as premature.)

## Directives still to apply (Tofig, carried forward)

1. **Sizing write-up must not overclaim.** Both weekly resizing and
   freeze-at-entry are *extensions* of the published rule, because fixing the
   dead-exit defect creates held-but-unsignalled weeks that the original
   specification never had to address. Weekly resizing is chosen as the smaller
   extension that keeps the paper's own words — not as a pure restoration, and
   it must not be described as one.

   Related: **−7.57 % is not a baseline being departed from.** It is the output
   of a specification Codex invented and then edited the manuscript to justify.
   The weekly-resizing result must not be framed as a move away from it.

2. **Restore the deleted provenance footnotes** from `4d21c69` (see F-1): the
   5.05 unsigned-magnitude tail-skew error, the benchmark rows that traced to no
   committed code, the 141 pooled trades, and the spurious 21 bp intercept.

3. **Manuscript, from Step 3 review — carry into the writing, not the backlog:**

   - **Break-even.** The published paper reports 19.2 pips. Under both
     corrected specifications break-even is undefined, because the gross return
     is already negative. Do not print a number, do not print a bare "n/a"
     cell, and do not drop the row silently. State it in the text: *the
     strategy does not break even at any cost level because it does not break
     even at zero cost.* That is a cleaner statement of the null than anything
     currently in the paper. It belongs in the cost section and in the
     conclusion.
   - **Cost limitation.** A sentence in the cost limitations: the model charges
     spread in proportion to notional traded with no fixed or minimum
     per-order component; the corrected specification generates 31 resizes
     averaging 0.19 units of notional; a fixed per-order cost would fall
     disproportionately on exactly those events. "Costs are immaterial" must
     not stand unqualified when the model cannot express the cost type most
     likely to bite.
   - **Identical test statistics.** A footnote explaining why White's Reality
     Check and Hansen's SPA barely move between sizing specifications: both
     take a maximum over the candidate universe, that maximum is attained by
     the seeded random candidate whose returns are independent of the
     asymmetry strategy's sizing, so only the bootstrap covariance sees the
     change. Without it the identical statistics read as a copy-paste error.

4. **Restructure the changelog and PR text into three sections**, every change
   in exactly one, so Murad can approve each category separately:

   - **(a) Implementation defects corrected** — the paper said X, the code
     accidentally did Y, the code now does X. Only the dead exit branch, the
     double execution lag, and `compute_ai` vs. Equation 5 qualify. Nothing
     enters this section unless paper and code genuinely disagreed *before*
     Codex touched them.
   - **(b) Methodological changes proposed** — paper and code both said X, we
     propose Y. The "trades" redefinition (SD-3), the EVT input switch (SD-4),
     and frozen sizing recorded as the rejected alternative (SD-2).
   - **(c) Manuscript corrections** — the code is sound, the paper describes it
     wrongly. The Monday-open availability claim (EX-3), the fast-alpha equation
     units (EX-1), and the unreachable 0.5 position floor (EX-4).

   When describing the dead-exit fix, state the exposure figure plainly: **the
   original strategy held a position in only 25 of 504 weeks.** That is why the
   original null result had no content, and it is the single most important fact
   in this correction.

## Backlog — out of scope for this pull request

Recorded so they are not lost. None of these are actioned here.

1. Fit the EVT section to tail alpha as the published paper claimed (SD-4).
2. Decide Monday-open versus Friday-close execution on the merits, once the
   presence of the Open column is confirmed (EX-3).
3. Source a dated EUR–JPY rate or forward series so hedge alpha stops being a
   constant multiplied by a correlation (EX-2).
4. Report the Sharpe ratio of exposed weeks alongside the full-sample figure
   (F-2).
5. Add financing/carry to the cost model, now that exposure reaches two
   notional units across 55 weeks.
6. Add a per-ticket or minimum-ticket cost component. The current model charges
   spread strictly in proportion to notional traded, so it cannot penalise the
   31 small resize orders that weekly sizing introduces. See "How the cost model
   scales" above.
