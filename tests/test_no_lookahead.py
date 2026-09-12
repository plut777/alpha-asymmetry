"""Causal checks for the look-ahead bug class (invariants A.3 and A.4').

A look-ahead bug was introduced during this review by applying one time shift to
execution timings whose entry points differ, crediting a position with a return
that had already occurred when its signal fired.  Nothing in the existing
apparatus caught it: sample size, the factor-intercept identity and the
volatility-regime identity all pass on the defective version.  It was caught only
by disagreement with an independently computed figure.

These tests are the purpose-built check for that class, and they are
deterministic -- fixed panel, fixed perturbation points, fixed seed.

    A.3   Perturbing every input strictly after row t must leave every decision
          and every realized return through row t bit-identical.

    A.4'  Non-degeneracy.  The perturbation must be *capable* of changing a
          decision, or A.3 passes vacuously.

    Mutation test.  A deliberately look-ahead variant of the strategy must FAIL
    A.3.  Without this, A.3 could be satisfied by a test that cannot fire.

The last of these exists because both earlier attempts at this file were
defective in exactly that way: a x3 perturbation that could not lift a negative
skewness above the entry threshold, and a synthetic panel on which the strategy
was flat at the perturbation points so nothing downstream could move.  A test
that cannot fail is indistinguishable from a test that passes.
"""

import numpy as np
import pandas as pd
import pytest

from analysis.strategy import run_asymmetry_strategy

SIGNAL_COLUMNS = [
    "fast_skew_20w", "fast_alpha", "price_skew_20w",
    "pricing_alpha", "pricing_std_20w", "fast_std_20w", "ai_20w", "Close",
    "weekly_return",
]
# The two invariants need different coverage, and this is not a detail.
#
# A.3 and the mutation test require a position to be APPLIED at t, i.e.
# position[t-1] != 0.  Where the strategy is flat, realized[t] is zero under both
# the correct and the look-ahead code and the test cannot discriminate.
#
# A.4' requires the opposite: the strategy flat at t and not in an expiry week,
# since the four-return expiry rule takes precedence over a fresh entry signal
# and would absorb the forced perturbation.
#
# Both earlier versions of this file used one point set for both, and passed
# vacuously at points that failed the coverage condition for one of them.
CAUSALITY_POINTS = (20, 44, 66)      # position[t-1] != 0 at each
RESPONSIVENESS_POINTS = (21, 45, 70)  # flat at t, and not an expiry week
SEED = 20260912
PERIODS = 120


def _frame():
    """Deterministic panel engineered to keep the strategy in position ~50% of weeks.

    Coverage matters: on a panel where the strategy is flat around the
    perturbation points, every test below passes regardless of whether the code
    is correct.
    """
    rng = np.random.default_rng(SEED)
    week = np.arange(PERIODS)
    returns = rng.normal(0, 0.01, PERIODS)
    signalling = (week % 8) < 2
    return pd.DataFrame(
        {
            "Close": 100 * np.cumprod(1 + returns),
            "weekly_return": returns,
            "fast_skew_20w": np.where(signalling, 1.5, -0.5),
            "fast_alpha": np.where(signalling, 1.0, -1.0),
            "price_skew_20w": np.full(PERIODS, -1.0),
            "pricing_alpha": np.zeros(PERIODS),
            "pricing_std_20w": np.ones(PERIODS),
            "ai_20w": np.full(PERIODS, 1.5),
        },
        index=pd.date_range("2020-01-03", periods=PERIODS, freq="W-FRI"),
    )


def _perturb_after(frame, t):
    rng = np.random.default_rng(SEED + t)
    out = frame.copy()
    for column in SIGNAL_COLUMNS:
        if column not in out.columns:
            continue
        col = out.columns.get_loc(column)
        out.iloc[t + 1:, col] *= 1 + rng.normal(0, 0.5, len(out) - t - 1)
    return out


def _lookahead_variant(frame, threshold):
    """The bug: the position earns a return that precedes its own signal."""
    shifted = frame.copy()
    shifted["weekly_return"] = shifted["weekly_return"].shift(-1)
    return run_asymmetry_strategy(shifted, threshold)


def test_the_panel_keeps_the_strategy_active():
    """Coverage precondition. Without it every test below can pass vacuously."""
    result = run_asymmetry_strategy(_frame(), 0.75)
    exposed = (result.applied_position.abs() > 0)
    assert exposed.sum() > PERIODS // 3
    for t in CAUSALITY_POINTS:
        assert result.position.iloc[t - 1] != 0, f"no applied position at t={t}"
    for t in RESPONSIVENESS_POINTS:
        assert result.position.iloc[t] == 0, f"not flat at t={t}"
        assert result.position_ledger.iloc[t]["reason"] != "max_holding_period", (
            f"t={t} is an expiry week; the forced signal would be absorbed")


@pytest.mark.parametrize("t", CAUSALITY_POINTS)
def test_decisions_do_not_depend_on_later_data(t):
    """A.3."""
    frame = _frame()
    base = run_asymmetry_strategy(frame, 0.75)
    after = run_asymmetry_strategy(_perturb_after(frame, t), 0.75)
    assert np.array_equal(after.position.iloc[:t + 1].to_numpy(),
                          base.position.iloc[:t + 1].to_numpy())
    assert np.array_equal(after.returns.iloc[:t + 1].to_numpy(),
                          base.returns.iloc[:t + 1].to_numpy())


@pytest.mark.parametrize("t", CAUSALITY_POINTS)
def test_a_lookahead_variant_is_caught(t):
    """Mutation test: the check must reject a strategy that does peek ahead."""
    frame = _frame()
    base = _lookahead_variant(frame, 0.75)
    after = _lookahead_variant(_perturb_after(frame, t), 0.75)
    assert not np.array_equal(after.returns.iloc[:t + 1].to_numpy(),
                              base.returns.iloc[:t + 1].to_numpy()), (
        f"A.3 cannot detect look-ahead at t={t}; the test is vacuous there")


@pytest.mark.parametrize("t", RESPONSIVENESS_POINTS)
def test_perturbation_is_capable_of_changing_a_decision(t):
    """A.4': non-degeneracy of the forced-signal perturbation."""
    frame = _frame()
    base = run_asymmetry_strategy(frame, 0.75)
    forced = frame.copy()
    forced.iloc[t, forced.columns.get_loc("fast_skew_20w")] = 5.0
    forced.iloc[t, forced.columns.get_loc("fast_alpha")] = 1.0
    forced.iloc[t, forced.columns.get_loc("price_skew_20w")] = -5.0
    after = run_asymmetry_strategy(forced, 0.75)
    assert (after.position.iloc[t:].to_numpy()
            != base.position.iloc[t:].to_numpy()).any(), "perturbation cannot fire"
    assert np.array_equal(after.position.iloc[:t].to_numpy(),
                          base.position.iloc[:t].to_numpy())


def test_realized_return_is_the_one_lag_join():
    """A.1 on the synthetic panel."""
    frame = _frame()
    result = run_asymmetry_strategy(frame, 0.75)
    expected = result.position.shift(1).fillna(0.0) * frame["weekly_return"].fillna(0.0)
    assert np.array_equal(result.returns.to_numpy(), expected.to_numpy())
    assert np.array_equal(result.applied_position.to_numpy(),
                          result.position.shift(1).fillna(0.0).to_numpy())


# ---------------------------------------------------------------------------
# I3: the causality property holds for the entry-symmetry variants too
#
# The variants were pre-registered in docs/PREREGISTRATION_ENTRY_SYMMETRY.md.
# They are sensitivity exhibits, but a sensitivity exhibit computed by
# look-ahead code is worse than no exhibit, so they are covered here.
#
# _frame() cannot be reused: it pins price_skew_20w at -1.0, so the pricing gate
# never opens and the pure-pricing variant would be flat for the whole panel.
# Every assertion below would then pass while testing nothing.  A separate panel
# is engineered to activate all four rules, and the coverage points are derived
# per rule rather than shared, because each rule is in position on different
# weeks.
# ---------------------------------------------------------------------------

VARIANT_RULES = ("published", "pure_fast", "pure_pricing", "equal_threshold")


def _variant_frame():
    """Panel engineered so all four entry rules are actually in position.

    The eight-week cycle opens the fast gate for weeks 0-3 and the pricing gate
    for weeks 4-7, so the two gates never open together and no week is decided
    by the simultaneous-signal branch.  Within each gate the confirmation series
    changes sign halfway, which is what gives the reflected legs of the pure-fast
    and pure-pricing variants something to fire on.
    """
    rng = np.random.default_rng(SEED + 1)
    week = np.arange(PERIODS)
    phase = week % 8
    returns = rng.normal(0, 0.01, PERIODS)
    fast_gate = phase < 4
    pricing_gate = phase >= 4
    return pd.DataFrame(
        {
            "Close": 100 * np.cumprod(1 + returns),
            "weekly_return": returns,
            "fast_skew_20w": np.where(fast_gate, 1.5, -0.5),
            "fast_alpha": np.where(phase < 2, 1.0, np.where(phase < 4, -1.0, 0.0)),
            "fast_std_20w": np.ones(PERIODS),
            "price_skew_20w": np.where(pricing_gate, 1.5, -0.5),
            "pricing_alpha": np.where(phase >= 6, -1.0, np.where(pricing_gate, 1.0, 0.0)),
            "pricing_std_20w": np.ones(PERIODS),
            "ai_20w": np.full(PERIODS, 1.5),
        },
        index=pd.date_range("2020-01-03", periods=PERIODS, freq="W-FRI"),
    )


def _causality_points(rule, frame):
    """Weeks where a position is actually applied, so a peek could change a return."""
    result = run_asymmetry_strategy(frame, 0.75, entry_rule=rule)
    applied = result.position.shift(1).fillna(0.0).abs() > 0
    return [t for t in range(10, PERIODS - 10) if applied.iloc[t]]


@pytest.mark.parametrize("rule", VARIANT_RULES)
def test_variant_panel_keeps_each_rule_active(rule):
    """Coverage precondition. Without it the two tests below pass vacuously."""
    points = _causality_points(rule, _variant_frame())
    assert len(points) > PERIODS // 10, (
        f"entry_rule={rule!r} is barely in position on this panel; "
        f"the causality test would be vacuous")


@pytest.mark.parametrize("rule", VARIANT_RULES)
def test_variant_decisions_do_not_depend_on_later_data(rule):
    """I3. No variant's decision at t uses data after t."""
    frame = _variant_frame()
    base = run_asymmetry_strategy(frame, 0.75, entry_rule=rule)
    for t in _causality_points(rule, frame)[:6]:
        after = run_asymmetry_strategy(_perturb_after(frame, t), 0.75, entry_rule=rule)
        assert np.array_equal(after.position.iloc[:t + 1].to_numpy(),
                              base.position.iloc[:t + 1].to_numpy()), (
            f"entry_rule={rule!r}: position before t={t} moved when only later data changed")
        assert np.array_equal(after.returns.iloc[:t + 1].to_numpy(),
                              base.returns.iloc[:t + 1].to_numpy()), (
            f"entry_rule={rule!r}: returns before t={t} moved when only later data changed")


@pytest.mark.parametrize("rule", VARIANT_RULES)
def test_variant_lookahead_is_caught(rule):
    """Mutation test: the I3 check must reject a variant that does peek ahead."""
    frame = _variant_frame()
    shifted = frame.copy()
    shifted["weekly_return"] = shifted["weekly_return"].shift(-1)

    caught = False
    for t in _causality_points(rule, frame)[:6]:
        base = run_asymmetry_strategy(shifted, 0.75, entry_rule=rule)
        bad = _perturb_after(frame, t).copy()
        bad["weekly_return"] = bad["weekly_return"].shift(-1)
        after = run_asymmetry_strategy(bad, 0.75, entry_rule=rule)
        if not np.array_equal(after.returns.iloc[:t + 1].to_numpy(),
                              base.returns.iloc[:t + 1].to_numpy()):
            caught = True
            break
    assert caught, (
        f"entry_rule={rule!r}: the causality check cannot detect look-ahead "
        f"anywhere on this panel; it is vacuous for this variant")
