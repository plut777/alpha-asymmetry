"""Single source of truth for every free parameter in the analysis.

Reviewer 3 observed that the position-sizing equation referenced a lookback
window the manuscript never stated, which made the strategy unreproducible from
the paper alone.  The underlying problem is not that one parameter went
unreported; it is that parameters lived only as literals in code, so nothing
forced the prose to agree with them.

Every free parameter is therefore declared here, and ``tests/test_specification``
asserts that the specification table printed in ``paper/alpha-asymmetry.tex``
matches this file.  A parameter cannot be changed in the code without the test
failing until the manuscript is updated, and it cannot be changed in the
manuscript without the test failing until the code agrees.

Each entry carries the value, its unit, and the manuscript symbol or table it
appears as, so the printed table is generated from the same object the code
uses rather than transcribed.
"""

from __future__ import annotations

# (key, printed name, value, unit, where it appears / what it governs)
SPEC = [
    # --- signal construction, daily
    ("tail_quantile_window", "Tail exceedance quantile window", 252, "trading days", "Tail alpha"),
    ("tail_quantile_minobs", "Tail quantile minimum observations", 60, "trading days", "Tail alpha warm-up"),
    ("tail_quantile", "Tail exceedance quantile", 0.95, "quantile", "Tail alpha"),
    ("fast_return_window", "Fast alpha return horizon", 5, "trading days", "Fast alpha numerator"),
    ("fast_vol_window", "Fast alpha volatility window", 20, "trading days", "Fast alpha denominator"),
    ("pricing_ma_window", "Pricing alpha moving-average window", 60, "trading days", "Pricing alpha"),
    ("coverage_lag", "Coverage alpha volatility lag", 5, "trading days", "Coverage alpha"),
    ("hedge_corr_window", "Hedge alpha correlation window", 100, "trading days", "Hedge alpha"),
    ("hedge_rate_constant", "Hedge alpha rate constant", -0.02, "annualised decimal", "Hedge alpha"),
    # --- signal construction, weekly
    ("skew_window", "Rolling skewness window", 20, "weeks", "Entry conditions"),
    ("skew_minobs", "Rolling skewness minimum observations", 10, "weeks", "Entry conditions"),
    ("ai_window", "Asymmetry index window", 20, "weeks", "Equation 10 sizing"),
    ("ai_minobs", "Asymmetry index minimum observations", 10, "weeks", "Equation 10 sizing"),
    ("ai_input", "Asymmetry index input series", "fast alpha", "series", "Equation 10 sizing"),
    # --- strategy
    ("entry_threshold", "Entry skewness threshold", 0.75, "skewness units", "Baseline strategy"),
    ("threshold_grid", "Threshold grid", "0.50, 0.75, 1.00, 1.25", "skewness units", "Sensitivity, walk-forward"),
    ("pricing_entry_multiple", "Short-entry pricing multiple", 0.5, "standard deviations", "Entry Short"),
    ("max_holding_weeks", "Maximum holding period", 4, "realized weekly returns", "Exit rule"),
    ("position_lower", "Position size lower bound", 1.0, "gross notional units", "Equation 10"),
    ("position_upper", "Position size upper bound", 2.0, "gross notional units", "Equation 10"),
    ("sizing_mode", "Notional sizing", "weekly", "rebalance frequency", "Equation 10"),
    ("execution_lag", "Execution lag", 1, "weeks", "Timing convention"),
    ("execution_price", "Execution price convention", "Friday close", "price", "Timing convention"),
    # --- costs
    ("pip_size", "Pip size (JPY pairs)", 0.01, "price increment", "Cost model"),
    ("cost_tiers", "Round-trip cost tiers", "0.0, 0.3, 0.7, 1.3, 2.0", "pips", "Cost table"),
    # --- inference
    ("skew_block", "Skewness bootstrap block length", 13, "weeks", "Circular block bootstrap"),
    ("skew_reps", "Skewness bootstrap replications", 2000, "draws", "Circular block bootstrap"),
    ("return_block", "Return bootstrap expected block", 4, "weeks", "Stationary bootstrap"),
    ("return_reps", "Return bootstrap replications", 2000, "draws", "Stationary bootstrap"),
    ("snooping_reps", "Data-snooping bootstrap replications", 1000, "draws", "Reality Check, SPA"),
    ("snooping_candidates", "Formal candidate universe", 12, "strategies", "Reality Check, SPA"),
    ("hac_lags", "Newey-West lags (full sample)", 4, "weeks", "Factor regression"),
    ("wcb_reps", "Wild cluster bootstrap replications", 9999, "draws", "Factor regression"),
    ("evt_threshold", "EVT exceedance threshold", 0.95, "quantile", "GPD fit"),
    ("evt_decluster", "EVT declustering separation", 5, "weeks", "GPD fit"),
    ("min_episodes", "Minimum episodes for reported performance", 2, "holding episodes", "Reporting rule"),
    ("bonferroni_family", "Bonferroni family size (factor coefficients)", 6, "tests", "Factor regression"),
    ("seed", "Random seed", 42, "integer", "All resampling"),
    # --- sample
    ("sample_n", "Analysis-ready weekly observations", 504, "weeks", "Sample"),
    ("sample_start", "Analysis sample start", "2016-01-08", "date", "Sample"),
    ("sample_end", "Analysis sample end", "2025-08-29", "date", "Sample"),
]

BY_KEY = {key: value for key, _, value, _, _ in SPEC}


def latex_rows() -> str:
    """The body of the manuscript's specification table, generated from SPEC."""

    out = []
    for _, name, value, unit, where in SPEC:
        shown = value if isinstance(value, str) else (f"{value:g}" if isinstance(value, float) else str(value))
        out.append(f"{name} & {shown} & {unit} & {where} \\\\")
    return "\n".join(out)


if __name__ == "__main__":
    print(latex_rows())
