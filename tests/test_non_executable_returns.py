"""A return interval that does not exist must not be reported as a zero return.

Under first-post-signal-open execution the terminal week has no subsequent
executable open, so its return interval does not exist. The strategy previously
computed `applied * weekly_return.fillna(0.0)`, which made that non-executable
observation indistinguishable from a week in which the strategy simply held
nothing -- and it entered the mean, standard deviation, Sharpe ratio, return
bootstrap, factor regression and regime buckets as a real zero.

The distinction these tests enforce:

* an OBSERVABLE interval over which the position is zero  -> return 0, counted;
* an interval with no executable price                    -> NaN, not counted.

The second case is dangerous precisely because it is usually invisible: it costs
nothing while the terminal position happens to be flat, and silently fabricates a
zero return the moment it is not.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from analysis.strategy import run_asymmetry_strategy, simple_strategy

PERIODS = 60


def _frame(active_at_end: bool):
    """Panel whose final week has no realisable return.

    With active_at_end the entry signal fires continuously, so a position is
    applied in the terminal week; without it the strategy is flat throughout.
    """
    idx = pd.date_range("2020-01-03", periods=PERIODS, freq="W-FRI")
    rng = np.random.default_rng(11)
    returns = rng.normal(0, 0.01, PERIODS)
    fires = np.ones(PERIODS) if active_at_end else np.zeros(PERIODS)
    frame = pd.DataFrame(
        {
            "Close": 100 * np.cumprod(1 + returns),
            "weekly_return": returns,
            "fast_skew_20w": np.where(fires > 0, 1.5, -1.0),
            "fast_alpha": np.where(fires > 0, 1.0, -1.0),
            "price_skew_20w": np.full(PERIODS, -1.0),
            "pricing_alpha": np.zeros(PERIODS),
            "pricing_std_20w": np.ones(PERIODS),
            "ai_20w": np.full(PERIODS, 1.5),
        },
        index=idx,
    )
    # the terminal week has no subsequent executable open
    frame.iloc[-1, frame.columns.get_loc("weekly_return")] = np.nan
    return frame


def test_active_terminal_position_is_not_silently_assigned_zero():
    """The defect this file exists for."""

    frame = _frame(active_at_end=True)
    result = run_asymmetry_strategy(frame, 0.75)

    applied = float(result.applied_position.iloc[-1])
    assert applied != 0, (
        "coverage precondition: this panel must apply a position in the terminal "
        "week, otherwise the test cannot discriminate")

    terminal = result.returns.iloc[-1]
    assert pd.isna(terminal), (
        f"the terminal week has no executable return, but the strategy reported "
        f"{terminal!r} while holding a position of {applied}. A non-executable "
        f"interval must stay NaN; reporting 0.0 fabricates a flat week that never "
        f"existed and feeds it to every return statistic.")


def test_a_flat_week_over_a_real_interval_still_returns_zero():
    """The other half of the distinction: zero position, real interval, return 0."""

    frame = _frame(active_at_end=False)
    result = run_asymmetry_strategy(frame, 0.75)
    interior = result.returns.iloc[1:-1]
    assert interior.notna().all(), "interior weeks have real intervals and must not be NaN"
    assert (interior == 0).all(), "a flat strategy over a real interval returns exactly zero"


def test_non_executable_weeks_are_excluded_from_reported_statistics():
    frame = _frame(active_at_end=True)
    result = run_asymmetry_strategy(frame, 0.75)
    assert int(result.returns.notna().sum()) == PERIODS - 1, (
        "exactly one week is non-executable, so the reported series must carry "
        "one fewer observation than the panel")
    assert not np.isnan(result.metrics["sharpe"]), "statistics must skip the gap, not propagate it"


def test_benchmarks_do_not_earn_over_non_existent_intervals():
    """simple_strategy carried the same fill and the same defect."""

    idx = pd.date_range("2020-01-03", periods=10, freq="W-FRI")
    weekly_return = pd.Series([0.01] * 9 + [np.nan], index=idx)
    position = pd.Series(1.0, index=idx)
    out = simple_strategy(position, weekly_return)
    assert pd.isna(out.iloc[-1]), (
        "a benchmark holding a position cannot earn a return over an interval "
        "with no executable price")


def test_a_non_executable_week_is_not_counted_as_a_losing_week():
    """`NaN > 0` is False, which would quietly depress the hit rate."""

    frame = _frame(active_at_end=True)
    result = run_asymmetry_strategy(frame, 0.75)
    exposed = result.returns[result.applied_position.abs() > 0].dropna()
    expected = float((exposed > 0).mean() * 100)
    assert result.metrics["hit"] == pytest.approx(expected), (
        "the hit rate must be computed over executable exposed weeks only")
