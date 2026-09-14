"""Entry-rule symmetry variants (Reviewer 3, round two, comment #4).

The published rule's long and short legs differ in source series, confirmation
threshold, and direction of response all at once, and the manuscript argues for
none of it.  This module runs the three symmetrizations specified in advance in
``docs/PREREGISTRATION_ENTRY_SYMMETRY.md`` and writes them to
``analysis/entry_symmetry_results.json`` so that every reported figure has a
canonical source rather than being transcribed by hand.

The published hybrid is the control and must reproduce the committed baseline
exactly.  That check reads the expected values out of
``analysis/full_pipeline_results.json`` rather than comparing against numbers
written into this file, so the assertion cannot silently agree with a mistake.

These variants are sensitivity exhibits.  None of them is a candidate
replacement for the published rule, and realised performance is pre-declared not
to decide which symmetrization is defensible.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from .full_pipeline import build_weekly_alphas
from .strategy import run_asymmetry_strategy

ROOT = Path(__file__).resolve().parent
CANONICAL = ROOT / "full_pipeline_results.json"
OUTPUT = ROOT / "entry_symmetry_results.json"

# Pre-registered: net figures are quoted at the widest published cost tier.
NET_COST_PIPS = 2.0

VARIANTS = {
    "published": "P - published hybrid (control)",
    "pure_fast": "A - pure-fast (trend-following both ways)",
    "pure_pricing": "B - pure-pricing (mean-reverting both ways)",
    "equal_threshold": "C - equalised confirmation threshold",
}

# Fields compared for invariant I1, read from the canonical JSON.
I1_FIELDS = (
    "return", "sharpe", "mdd", "holding_episodes",
    "in_position_weeks", "execution_legs", "resizes", "turnover",
)


def _metrics(weekly: pd.DataFrame, entry_rule: str) -> dict:
    gross = run_asymmetry_strategy(weekly, 0.75, entry_rule=entry_rule)
    net = run_asymmetry_strategy(
        weekly, 0.75, entry_rule=entry_rule, round_trip_cost_pips=NET_COST_PIPS
    )
    m = dict(gross.metrics)
    m["net_return"] = net.metrics["net_return"]

    # Pre-registered exposure diagnostic: mean gross weekly return over the
    # weeks actually held, so that a variant which is merely out of the market
    # more often cannot read as better.
    exposed = gross.returns[gross.applied_position.abs() > 0]
    m["mean_gross_return_per_in_position_week_bps"] = (
        float(exposed.mean() * 1e4) if len(exposed) else float("nan")
    )
    return m


def run(weekly: pd.DataFrame | None = None) -> dict:
    if weekly is None:
        px = pd.read_csv(ROOT / "cache" / "eurjpy.csv", index_col=0, parse_dates=True)
        weekly = build_weekly_alphas(px)

    results = {key: _metrics(weekly, key) for key in VARIANTS}

    # --- I2: the sample is unchanged ---
    # Two distinct concepts, kept apart because conflating them is how a
    # non-executable week gets counted as data:
    #   analysis panel      -- every week the alpha signals are defined for;
    #   executable strategy -- the weeks that carry a realisable return, which
    #                          excludes the final week under post-signal-open
    #                          execution, since no subsequent open exists.
    sample = {
        "analysis_panel_n": int(len(weekly)),
        "executable_strategy_n": int(weekly["weekly_return"].notna().sum()),
        "start": str(weekly.index[0].date()),
        "end": str(weekly.index[-1].date()),
    }

    # --- I1: the published hybrid reproduces the committed baseline ---
    baseline = json.loads(CANONICAL.read_text())["baseline"]
    i1 = {}
    for field in I1_FIELDS:
        got, want = results["published"][field], baseline[field]
        i1[field] = {
            "committed": want,
            "recomputed": got,
            "match": bool(abs(got - want) < 1e-9),
        }

    payload = {
        "preregistration": "docs/PREREGISTRATION_ENTRY_SYMMETRY.md",
        "net_cost_pips": NET_COST_PIPS,
        "labels": VARIANTS,
        "sample": sample,
        "invariant_I1_published_reproduces_baseline": i1,
        "variants": results,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n")
    return payload


if __name__ == "__main__":
    p = run()
    i1 = p["invariant_I1_published_reproduces_baseline"]
    ok = all(v["match"] for v in i1.values())
    print(f"I1 published reproduces committed baseline: {'PASS' if ok else 'FAIL'}")
    for f, v in i1.items():
        if not v["match"]:
            print(f"   MISMATCH {f}: committed {v['committed']} vs recomputed {v['recomputed']}")
    s = p["sample"]
    print(f"I2 sample: analysis panel n={s['analysis_panel_n']}; "
          f"executable strategy n={s['executable_strategy_n']}; "
          f"{s['start']} to {s['end']}")
