"""Shared, testable strategy and accounting primitives.

Timing convention
-----------------
Every row is a Friday close.  Signals on row ``t`` are formed only from data
available through that close.  ``decision_position[t]`` is the position chosen
at that close and it earns ``weekly_return[t + 1]``.  Equivalently, realized
returns are ``decision_position.shift(1) * weekly_return``.  This is one lag,
not two.

The Friday close is used as the execution proxy.  That is a *choice*, not a
data limitation: the daily bars carry an ``Open`` column, so Monday's opening
price -- which the published paper names as the execution point -- is present
and could be used.  Implementing it is deferred; see docs/REVIEW_NOTES.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd


REQUIRED_COLUMNS = {
    "Close",
    "weekly_return",
    "fast_skew_20w",
    "fast_alpha",
    "price_skew_20w",
    "pricing_alpha",
    "pricing_std_20w",
    "ai_20w",
}


def compute_ai(values: Iterable[float]) -> float:
    """Return the paper's upside/downside mean-squared-deviation ratio.

    Both sides are centred on the *overall* finite-sample mean and divided by
    their own observation counts.  This is deliberately not ``Series.var``:
    subgroup variance would re-centre each side and normally use an ``n - 1``
    denominator, defining a different statistic.

    The index is undefined when either side is empty or when the downside
    mean-squared deviation is zero.  Those cases return ``NaN`` explicitly.
    A single observation on either side is valid because this is a mean square,
    not an estimated subgroup variance.
    """

    x = pd.Series(values, dtype="float64").dropna()
    if x.empty:
        return np.nan
    mean_x = float(x.mean())
    pos = x[x > mean_x] - mean_x
    neg = x[x < mean_x] - mean_x
    if pos.empty or neg.empty:
        return np.nan
    downside = float(np.mean(np.square(neg.to_numpy())))
    if not np.isfinite(downside) or downside <= 0:
        return np.nan
    upside = float(np.mean(np.square(pos.to_numpy())))
    return upside / downside if np.isfinite(upside) else np.nan


def position_size(ai_value: float, lower: float = 1.0, upper: float = 2.0) -> float:
    """Map AI to entry size; missing AI uses the neutral one-unit size.

    ``1 + |AI - 1|`` can never be below one, so the previous lower bound of
    0.5 was unreachable.  The explicit range is therefore [1, 2] units.
    Values above one imply gross notional exposure above capital (leverage).
    """

    if not np.isfinite(ai_value):
        return 1.0
    return float(np.clip(1.0 + abs(float(ai_value) - 1.0), lower, upper))


@dataclass(frozen=True)
class StrategyResult:
    metrics: dict
    returns: pd.Series
    net_returns: pd.Series
    position: pd.Series
    applied_position: pd.Series
    position_ledger: pd.DataFrame
    trade_ledger: pd.DataFrame


def _event_type(previous: float, new: float) -> str:
    if previous == new:
        return "hold" if new != 0 else "none"
    if previous == 0 and new != 0:
        return "entry"
    if previous != 0 and new == 0:
        return "exit"
    if np.sign(previous) != np.sign(new):
        return "reversal"
    return "resize"


def _direction(value: float) -> str:
    return "long" if value > 0 else "short" if value < 0 else "flat"


def summarize_position_changes(position: pd.Series) -> dict:
    """Count episodes, legs, reversals, resizing, and absolute turnover."""

    position = pd.Series(position, dtype="float64")
    previous = position.shift(1).fillna(0.0)
    entries = (previous.eq(0) & position.ne(0)).sum()
    exits = (previous.ne(0) & position.eq(0)).sum()
    reversals = (previous.mul(position) < 0).sum()
    resizes = (previous.mul(position).gt(0) & previous.ne(position)).sum()
    return {
        "holding_episodes": int(entries + reversals),
        "execution_legs": int(entries + exits + 2 * reversals + resizes),
        "reversals": int(reversals),
        "resizes": int(resizes),
        "turnover": float(position.sub(previous).abs().sum()),
    }


def _performance(rets: pd.Series, applied_position: pd.Series) -> dict:
    cum = float((1.0 + rets).prod() - 1.0)
    curve = (1.0 + rets).cumprod()
    mdd = float((curve / curve.cummax() - 1.0).min()) if len(curve) else 0.0
    sd = float(rets.std())
    sharpe = float(rets.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0
    in_position = rets[applied_position.abs() > 0]
    # dropna first: a non-executable week is not a losing week, and "NaN > 0"
    # is False, which would silently count it as one.
    in_position = in_position.dropna()
    hit = float((in_position > 0).mean() * 100) if len(in_position) else np.nan
    return {
        "return": cum * 100,
        "sharpe": sharpe,
        "mdd": mdd * 100,
        "hit": hit,
        "in_position_weeks": int((applied_position.abs() > 0).sum()),
    }


def _build_trade_ledger(position_ledger: pd.DataFrame) -> pd.DataFrame:
    """Build one row per directional holding episode from the weekly ledger."""

    episodes: list[dict] = []
    active: dict | None = None
    next_id = 1

    for signal_date, row in position_ledger.iterrows():
        event = row["event_type"]
        previous = float(row["previous_position"])
        new = float(row["new_position"])

        if active is not None:
            active["gross_growth"] *= 1.0 + float(row["gross_return"])
            active["cost"] += float(row["closing_cost"])
            if abs(float(row["applied_position"])) > 0:
                active["holding_period"] += 1

        closes_episode = active is not None and event in {"exit", "reversal"}
        if closes_episode:
            active["exit_signal_date"] = signal_date
            active["exit_execution_date"] = row["execution_date"]
            active["exit_price"] = float(row["execution_price"])
            active["exit_reason"] = row["reason"]
            active["gross_return"] = active.pop("gross_growth") - 1.0
            active["net_return"] = active["gross_return"] - active["cost"]
            episodes.append(active)
            active = None

        opens_episode = event in {"entry", "reversal"}
        if opens_episode:
            active = {
                "episode_id": next_id,
                "direction": _direction(new),
                "entry_signal_date": signal_date,
                "entry_execution_date": row["execution_date"],
                "entry_price": float(row["execution_price"]),
                # Notional at entry. Under weekly sizing the notional varies
                # across the episode; position_ledger.csv carries the full path.
                "entry_position_size": abs(new),
                "entry_reason": row["reason"],
                "gross_growth": 1.0,
                "cost": float(row["opening_cost"]),
                "holding_period": 0,
                "exit_signal_date": pd.NaT,
                "exit_execution_date": pd.NaT,
                "exit_price": np.nan,
                "exit_reason": "sample_end",
            }
            next_id += 1

    if active is not None:
        active["gross_return"] = active.pop("gross_growth") - 1.0
        active["net_return"] = active["gross_return"] - active["cost"]
        episodes.append(active)

    columns = [
        "episode_id", "direction", "entry_signal_date", "entry_execution_date",
        "entry_price", "entry_position_size", "entry_reason", "exit_signal_date",
        "exit_execution_date", "exit_price", "exit_reason", "holding_period",
        "gross_return", "cost", "net_return",
    ]
    return pd.DataFrame(episodes, columns=columns)


SIZING_MODES = ("weekly", "entry")


ENTRY_RULES = ("published", "pure_fast", "pure_pricing", "equal_threshold")


def entry_signals(
    d: pd.DataFrame,
    thresholds: pd.Series,
    entry_rule: str = "published",
) -> tuple[pd.Series, pd.Series]:
    """Long and short entry conditions, published rule or a symmetry variant.

    The published rule's two legs differ in four ways at once: skewness gate,
    confirmation series, confirmation threshold, and direction of response.  A
    positive fast alpha makes the rule go long; a positive pricing alpha makes
    it go short.  The manuscript argues for none of this, which is Reviewer 3's
    fourth round-two comment.

    The three variants each collapse that asymmetry a different way, and they
    are sensitivity exhibits rather than candidate replacements: every reported
    result uses ``"published"``.  Their exact definitions and the economic
    question each answers were fixed in advance in
    ``docs/PREREGISTRATION_ENTRY_SYMMETRY.md``, committed before any of them was
    computed.

    Comparisons against NaN are already False in pandas, so no missing-value
    handling is applied here; the published path is left exactly as it was.
    """

    if entry_rule not in ENTRY_RULES:
        raise ValueError(f"unknown entry_rule {entry_rule!r}; expected one of {ENTRY_RULES}")

    if entry_rule == "published":
        long_signal = (d["fast_skew_20w"] > thresholds) & (d["fast_alpha"] > 0)
        short_signal = (d["price_skew_20w"] > thresholds) & (
            d["pricing_alpha"] > 0.5 * d["pricing_std_20w"]
        )
    elif entry_rule == "pure_fast":
        # Published long leg preserved verbatim, short leg reflected about zero.
        gate = d["fast_skew_20w"] > thresholds
        long_signal = gate & (d["fast_alpha"] > 0)
        short_signal = gate & (d["fast_alpha"] < 0)
    elif entry_rule == "pure_pricing":
        # Published short leg preserved verbatim, long leg reflected about zero.
        gate = d["price_skew_20w"] > thresholds
        band = 0.5 * d["pricing_std_20w"]
        long_signal = gate & (d["pricing_alpha"] < -band)
        short_signal = gate & (d["pricing_alpha"] > band)
    else:  # equal_threshold
        if "fast_std_20w" not in d.columns:
            raise ValueError('entry_rule="equal_threshold" requires a fast_std_20w column')
        long_signal = (d["fast_skew_20w"] > thresholds) & (
            d["fast_alpha"] > 0.5 * d["fast_std_20w"]
        )
        short_signal = (d["price_skew_20w"] > thresholds) & (
            d["pricing_alpha"] > 0.5 * d["pricing_std_20w"]
        )

    return long_signal, short_signal


def run_asymmetry_strategy(
    data: pd.DataFrame,
    threshold: float | pd.Series = 0.75,
    *,
    max_holding_weeks: int = 4,
    round_trip_cost_pips: float = 0.0,
    pip_size: float = 0.01,
    entry_rule: str = "published",
    sizing: str = "weekly",
) -> StrategyResult:
    """Run the two-sided strategy with one execution lag.

    Rules:
    - enter on exactly one qualifying signal;
    - hold the direction until the opposite signal, a simultaneous-signal
      conflict, or the four-return-period maximum;
    - an opposite signal reverses directly and starts a new holding episode;
    - simultaneous signals flatten an existing position and never open one.

    ``sizing`` selects how the notional is set while a direction is held, and
    is a specification choice rather than an implementation detail:

    ``"weekly"`` (default)
        Re-evaluate Equation 10 at every Friday close from the contemporaneous
        ``ai_20w``, per the manuscript's "Rebalancing: Weekly (end of Friday
        close)" and its "contemporaneous asymmetry index".  Resizing never
        opens or closes a holding episode and never resets the holding clock.

    ``"entry"``
        Freeze the notional at its entry value for the life of the episode.
        Retained as the reported robustness alternative.

    Neither mode is a pure restoration of the published rule.  Repairing the
    dead exit branch creates weeks in which a direction is held while no signal
    fires, a state the published specification never had to size, because the
    original implementation could not reach it.  See docs/REVIEW_NOTES.md.
    """

    missing = REQUIRED_COLUMNS - set(data.columns)
    if missing:
        raise ValueError(f"missing required strategy columns: {sorted(missing)}")
    if max_holding_weeks < 1:
        raise ValueError("max_holding_weeks must be positive")
    if sizing not in SIZING_MODES:
        raise ValueError(f"sizing must be one of {SIZING_MODES}, got {sizing!r}")

    d = data.sort_index().copy()
    if not d.index.is_unique:
        raise ValueError("strategy index must be unique")
    if not d.index.is_monotonic_increasing:
        raise ValueError("strategy index must be chronological")

    if isinstance(threshold, pd.Series):
        thresholds = threshold.reindex(d.index)
        if thresholds.isna().any():
            raise ValueError("threshold series must cover every strategy date")
    else:
        thresholds = pd.Series(float(threshold), index=d.index)

    long_signal, short_signal = entry_signals(d, thresholds, entry_rule)

    positions: list[float] = []
    holding: list[int] = []
    reasons: list[str] = []
    events: list[str] = []
    previous = 0.0
    weeks_held = 0

    for date in d.index:
        sig_long = bool(long_signal.loc[date])
        sig_short = bool(short_signal.loc[date])
        size = position_size(float(d.at[date, "ai_20w"]))

        if sig_long and sig_short:
            new = 0.0
            reason = "simultaneous_signals"
        elif previous == 0:
            if sig_long:
                new, reason = size, "long_signal"
            elif sig_short:
                new, reason = -size, "short_signal"
            else:
                new, reason = 0.0, "no_signal"
        elif previous > 0 and sig_short:
            new, reason = -size, "opposing_short_signal"
        elif previous < 0 and sig_long:
            new, reason = size, "opposing_long_signal"
        elif weeks_held >= max_holding_weeks:
            new, reason = 0.0, "max_holding_period"
        elif sizing == "weekly":
            # Direction is unchanged; the notional tracks the contemporaneous
            # AI.  np.sign keeps the held direction and discards the stale
            # magnitude, so a size change here is a resize, never a reversal.
            new, reason = np.sign(previous) * size, "hold"
        else:
            new, reason = previous, "hold"

        event = _event_type(previous, new)
        if new == 0:
            new_weeks_held = 0
        elif event in {"entry", "reversal"}:
            new_weeks_held = 1
        else:
            new_weeks_held = weeks_held + 1

        positions.append(float(new))
        holding.append(int(new_weeks_held))
        reasons.append(reason)
        events.append(event)
        previous, weeks_held = float(new), int(new_weeks_held)

    position = pd.Series(positions, index=d.index, name="decision_position")
    applied = position.shift(1).fillna(0.0).rename("applied_position")
    # A missing weekly_return means the return interval does not exist -- under
    # first-post-signal-open execution the terminal week has no subsequent
    # executable open. That is NOT the same as an interval during which the
    # strategy happened to hold nothing, which legitimately returns zero and is
    # produced here by applied == 0 against a real return.
    #
    # Filling the missing interval with 0.0 made a non-executable observation
    # indistinguishable from a flat one, and it entered the mean, the standard
    # deviation, the Sharpe ratio, the return bootstrap, the factor regression
    # and the regime buckets as a real zero. NaN is preserved instead, and every
    # statistic below skips it.
    gross = (applied * d["weekly_return"]).rename("gross_return")
    previous_position = position.shift(1).fillna(0.0)
    turnover = (position - previous_position).abs().rename("turnover")
    price = d["Close"].replace(0, np.nan)
    # ``pip_size`` is YEN-PAIR SPECIFIC.  A pip is 0.01 only for pairs quoted to
    # two decimals (EUR/JPY here, and the other JPY crosses).  For a
    # conventional four-decimal pair such as GBP/USD a pip is 0.0001, and for a
    # non-FX instrument the notion does not apply at all.  Passing JPY pips to a
    # non-JPY market overstates cost by a factor of 100 with no error raised.
    #
    # The cost table is only ever run on EUR/JPY, and the cross-market section
    # calls this function at zero cost, so nothing is currently mispriced.  That
    # is a property of the callers, not of this default -- anyone adding costs to
    # the cross-market runs must set pip_size per market first.
    # A pip is 0.01 only for pairs quoted to two decimals. Passing JPY pips to a
    # four-decimal pair overstates cost by a factor of 100, and nothing in the
    # arithmetic would object. The relationship that does hold across FX
    # conventions is that one pip is on the order of 1e-4 of the quoted level:
    # EUR/JPY 0.01/171 = 5.8e-5, GBP/USD 0.0001/1.27 = 7.9e-5. A JPY pip applied
    # to a dollar-quoted pair lands near 8e-3, two orders out.
    #
    # The check runs only when cost is actually charged, so zero-cost callers --
    # which is every cross-market run today -- are unaffected.
    if round_trip_cost_pips > 0:
        level = float(price.median())
        ratio = pip_size / level if level > 0 else float("inf")
        if not 1e-5 < ratio < 1e-3:
            raise ValueError(
                f"pip_size={pip_size} is implausible for a market quoted around "
                f"{level:.4f} (ratio {ratio:.2e}, expected order 1e-4). A pip is "
                f"0.01 for two-decimal pairs such as the JPY crosses and 0.0001 "
                f"for four-decimal pairs. Pass the pip convention for this market "
                f"explicitly before charging transaction costs.")

    # Two different zeros, which the previous .fillna(0.0) wrote identically.
    #
    # A zero-pip cost specification is an OBSERVED zero: the rate is identically
    # zero whatever the price, because the numerator is zero. A missing price
    # under a positive cost specification is UNDEFINED: the cost of that trade
    # cannot be computed, and writing it as zero would report a free trade.
    if round_trip_cost_pips == 0:
        unit_cost = pd.Series(0.0, index=d.index)
    else:
        unit_cost = (round_trip_cost_pips / 2.0) * pip_size / price
    # Cost is charged strictly in proportion to the notional actually traded:
    # unit_cost is a per-unit rate, and every branch below multiplies it by a
    # quantity of notional.  There is no fixed per-leg or per-ticket term, so
    # total charged units equal total turnover exactly.  All four branches are
    # reachable under weekly sizing; under sizing="entry" the resize branch is
    # unreachable, which is why the mode is a parameter and not a fork.
    opening_units = pd.Series(0.0, index=d.index)
    closing_units = pd.Series(0.0, index=d.index)
    for date, event in zip(d.index, events):
        if event == "entry":
            opening_units.at[date] = abs(position.at[date])
        elif event == "exit":
            closing_units.at[date] = abs(previous_position.at[date])
        elif event == "reversal":
            closing_units.at[date] = abs(previous_position.at[date])
            opening_units.at[date] = abs(position.at[date])
        elif event == "resize":
            delta = abs(position.at[date]) - abs(previous_position.at[date])
            if delta > 0:
                opening_units.at[date] = delta
            else:
                closing_units.at[date] = -delta
    # A week with no trade costs nothing regardless of whether a price exists, so
    # the undefined rate must not propagate there. Only a week that actually
    # trades at an uncomputable rate is left undefined.
    opening_cost = opening_units.mul(unit_cost).where(opening_units > 0, 0.0)
    closing_cost = closing_units.mul(unit_cost).where(closing_units > 0, 0.0)
    cost = (opening_cost + closing_cost).rename("cost")
    net = (gross - cost).rename("net_return")

    execution_dates = pd.Series(d.index, index=d.index)
    period_end_dates = pd.Series(d.index, index=d.index).shift(-1)
    ledger = pd.DataFrame(
        {
            "signal_date": d.index,
            "execution_date": execution_dates,
            "return_period_end": period_end_dates,
            "direction": [_direction(v) for v in position],
            "long_signal": long_signal,
            "short_signal": short_signal,
            "previous_position": previous_position,
            "new_position": position,
            "applied_position": applied,
            "reason": reasons,
            "event_type": events,
            "entry": np.array(events) == "entry",
            "resize": np.array(events) == "resize",
            "reversal": np.array(events) == "reversal",
            "exit": np.array(events) == "exit",
            "holding_period": holding,
            "execution_price": d["Close"],
            "gross_return": gross,
            "turnover": turnover,
            "opening_cost": opening_cost,
            "closing_cost": closing_cost,
            "cost": cost,
            "net_return": net,
        },
        index=d.index,
    )
    ledger.index.name = "signal_date_index"
    trades = _build_trade_ledger(ledger)

    metrics = _performance(gross, applied)
    metrics.update(
        {
            "holding_episodes": int(len(trades)),
            "closed_episodes": int(trades["exit_signal_date"].notna().sum()) if len(trades) else 0,
            "execution_legs": int((opening_units > 0).sum() + (closing_units > 0).sum()),
            "reversals": int((ledger["event_type"] == "reversal").sum()),
            "resizes": int((ledger["event_type"] == "resize").sum()),
            "turnover": float(turnover.sum()),
            "net_return": float((1.0 + net).prod() - 1.0) * 100,
        }
    )
    return StrategyResult(metrics, gross, net, position, applied, ledger, trades)


def simple_strategy(position: pd.Series, weekly_return: pd.Series) -> pd.Series:
    """Apply the same one-lag Friday-close convention to any benchmark."""

    # weekly_return is deliberately not filled: see run_asymmetry_strategy. A
    # benchmark cannot earn a return over an interval that does not exist either.
    return (position.reindex(weekly_return.index).shift(1).fillna(0.0) * weekly_return).rename(
        "strategy_return"
    )
