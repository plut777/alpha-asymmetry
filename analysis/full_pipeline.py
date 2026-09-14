#!/usr/bin/env python3
"""Run the complete alpha-asymmetry replication and specification audit.

The pipeline has one shared implementation for the headline strategy, all
downstream analysis, ledgers, costs, and figures. Raw data are cached locally
and identified by SHA-256 hashes; the cache is not committed.
"""

from __future__ import annotations

import argparse
import json
import os
import warnings
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("MPLCONFIGDIR", str(REPO_ROOT / ".matplotlib"))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.diagnostic import acorr_ljungbox

try:
    from analysis.inference import cr2_inference, wild_cluster_bootstrap
    from analysis.data_access import load_datasets, write_manifest
    from analysis.strategy import compute_ai, run_asymmetry_strategy, simple_strategy, summarize_position_changes
except ModuleNotFoundError:  # direct execution from analysis/
    from inference import cr2_inference, wild_cluster_bootstrap
    from data_access import load_datasets, write_manifest
    from strategy import compute_ai, run_asymmetry_strategy, simple_strategy, summarize_position_changes


ANALYSIS_DIR = REPO_ROOT / "analysis"
PAPER_DIR = REPO_ROOT / "paper"
ALPHA_COLS = ["tail_alpha", "fast_alpha", "pricing_alpha", "coverage_alpha", "hedge_alpha"]
GRID = [0.50, 0.75, 1.00, 1.25]
SEED = 42
# Below this many holding episodes, per-episode performance statistics -- the
# Sharpe ratio, the hit rate, the annualized return -- are not reported as
# performance: they would be sample statistics computed from a single realized
# path.  Two is not a threshold at which inference becomes sound; it is the
# point below which the quantities stop being statistics at all.
#
# The rule is applied wherever such statistics are produced, not only in the
# walk-forward, so that a quantity suppressed in one table cannot reappear in
# another.  Suppressed values are still computed and still written to
# full_pipeline_results.json, so the reporting decision stays checkable.
MIN_EPISODES_FOR_INFERENCE = 2
INFERENCE_REPORTING_RULE = (
    "Where inference_supported is false, the Sharpe ratio, hit rate and annualized return "
    "must not be presented as performance. Report the episode count and the parameter that "
    "produced it, which describe what the procedure did, and state that the episode count is "
    "too small to support inference. Withhold such a figure by removing it and saying so, "
    "never by printing an unexplained placeholder."
)


def supports_inference(episodes: int) -> bool:
    """Whether a result rests on enough holding episodes to be a statistic."""

    return int(episodes) >= MIN_EPISODES_FOR_INFERENCE


warnings.filterwarnings("default")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=ANALYSIS_DIR / "cache")
    parser.add_argument("--output-dir", type=Path, default=ANALYSIS_DIR)
    parser.add_argument("--paper-dir", type=Path, default=PAPER_DIR)
    parser.add_argument("--offline", action="store_true", help="require local cached CSV inputs")
    parser.add_argument("--refresh", action="store_true", help="redownload and replace cached CSV inputs")
    return parser.parse_args()


def build_weekly_alphas(daily_px: pd.DataFrame, dxy: pd.DataFrame | None = None) -> pd.DataFrame:
    d = daily_px[["Close"]].copy()
    d["returns"] = d["Close"].pct_change(fill_method=None)
    q95 = d["returns"].abs().rolling(252, min_periods=60).quantile(0.95)
    d["tail_alpha"] = np.where(
        d["returns"].abs() > q95,
        np.sign(d["returns"]) * d["returns"].abs(),
        0.0,
    )
    d["ret_5d"] = d["Close"].pct_change(5, fill_method=None)
    d["vol_20d"] = d["returns"].rolling(20).std()
    d["fast_alpha"] = d["ret_5d"] / (d["vol_20d"] * np.sqrt(5))
    d["ma_60d"] = d["Close"].rolling(60).mean()
    d["std_60d"] = d["Close"].rolling(60).std()
    d["pricing_alpha"] = (d["Close"] - d["ma_60d"]) / d["std_60d"]
    d["coverage_alpha"] = d["vol_20d"] / d["vol_20d"].shift(5) - 1
    if dxy is not None:
        corr_data = pd.DataFrame(
            {"eurjpy": d["returns"], "dxy": dxy["Close"].pct_change(fill_method=None)}
        ).dropna()
        corr = corr_data["eurjpy"].rolling(100).corr(corr_data["dxy"])
        d["hedge_alpha"] = corr.reindex(d.index) * -0.02

    w = d.resample("W-FRI").last()
    # Primary execution: a Friday signal is realised from the first trading-session
    # open strictly AFTER it, held to the first open after the following Friday.
    # first_open[i] is the first session open of the week ending on Friday F[i], so
    # first_open[i+1] is the first open after F[i] -- the Monday open in an ordinary
    # week, and the next available session open when that Monday is a holiday,
    # because groupby().first() takes the first row that exists.
    #
    # The strategy applies position[j-1] to weekly_return[j], so a decision at
    # F[j-1] earns first_open[j] -> first_open[j+1]: execution at the first open
    # after its own signal, held to the first open after the next signal. Nothing
    # is read before it exists.
    first_open = daily_px.groupby(pd.Grouper(freq="W-FRI"))["Open"].first().reindex(w.index)
    w["execution_open"] = first_open
    w["weekly_return"] = first_open.shift(-1) / first_open - 1.0

    # The market return is a separate object from the strategy's executable
    # return and must not follow the execution convention. Friday-close to
    # Friday-close is what the EVT section characterises -- "absolute
    # Friday-close-to-Friday-close EUR/JPY returns" -- and what the proxy
    # momentum factor is built from, alongside the carry and dollar factors
    # which are close-to-close market series. Execution timing describes how a
    # position is realised; it does not redefine the market.
    w["market_return"] = w["Close"].pct_change(fill_method=None)
    w = w.loc["2015-11-01":"2025-08-31"]
    w["fast_skew_20w"] = w["fast_alpha"].rolling(20, min_periods=10).apply(
        lambda x: stats.skew(x, nan_policy="omit", bias=False), raw=False
    )
    w["price_skew_20w"] = w["pricing_alpha"].rolling(20, min_periods=10).apply(
        lambda x: stats.skew(x, nan_policy="omit", bias=False), raw=False
    )
    w["pricing_std_20w"] = w["pricing_alpha"].rolling(20, min_periods=10).std()
    w["fast_std_20w"] = w["fast_alpha"].rolling(20, min_periods=10).std()
    w["ai_20w"] = w["fast_alpha"].rolling(20, min_periods=10).apply(compute_ai, raw=False)
    return w.dropna(subset=["fast_skew_20w", "price_skew_20w", "ai_20w"])


PRIMARY_TIMING = "monday_open"

EXECUTION_TIMINGS = {
    "friday_close": "Friday close",
    "monday_open": "Monday open (reported baseline)",
    "monday_close": "Monday close",
    "tuesday_open": "Tuesday open",
}

EXECUTION_COST_TIERS = (0.0, 0.3, 0.7, 1.3, 2.0)


def execution_timing_grid(daily_px: pd.DataFrame, weekly: pd.DataFrame) -> dict:
    """Four entry timings applied to the identical Friday-close signal.

    The execution convention is a free choice: the published specification
    entered at the Monday open following Friday signal generation, and this
    revision enters at the Friday close.  Daily bars carry an Open column, so
    all four timings are implementable and the choice is not a data limitation.

    Alignment is the whole difficulty here and an earlier version of this grid
    got it wrong.  The Friday close is the decision instant itself, so its
    one-week return runs close-to-close and is simply ``P / P.shift(1) - 1``.
    The other three are entered *after* the decision, one boundary later, so
    their one-week return runs forward from that entry point and is
    ``P.shift(-1) / P - 1``.  Applying a uniform shift to all four makes the
    delayed timings earn the week *preceding* their own signal, which is
    look-ahead; it read Monday open as -15.10% rather than -0.73%.

    Two guards are permanent rather than incidental.  ``friday_close`` must
    reproduce the pipeline's own ``weekly_return`` to floating-point tolerance,
    which pins the construction to the series every other result uses; and the
    four timings are evaluated on a common sample, so that no differential
    dropping of weeks can be mistaken for an execution effect.
    """

    grouped = daily_px.groupby(pd.Grouper(freq="W-FRI"))
    entry_price = {
        "friday_close": weekly["Close"],
        "monday_open": grouped["Open"].first().reindex(weekly.index),
        "monday_close": grouped["Close"].first().reindex(weekly.index),
        "tuesday_open": grouped["Open"]
        .apply(lambda s: s.iloc[1] if len(s) > 1 else np.nan)
        .reindex(weekly.index),
    }

    returns = {"friday_close": entry_price["friday_close"].pct_change(fill_method=None)}
    for key in ("monday_open", "monday_close", "tuesday_open"):
        returns[key] = entry_price[key].shift(-1) / entry_price[key] - 1.0
    returns = pd.DataFrame(returns)

    # The grid must reproduce the primary series exactly, whichever timing is
    # primary. Re-pointed from friday_close to monday_open when the primary
    # execution convention changed; deleting it because it started failing would
    # have removed the only tie between this grid and the series everything else
    # uses.
    drift = (returns[PRIMARY_TIMING] - weekly["weekly_return"]).abs().max()
    if not drift < 1e-12:
        raise AssertionError(
            f"{PRIMARY_TIMING} must reproduce the pipeline's weekly_return; max deviation {drift}")

    common = returns.notna().all(axis=1)
    dropped = [str(d.date()) for d in weekly.index[~common]]

    rows = {}
    for key, label in EXECUTION_TIMINGS.items():
        frame = weekly.copy()
        frame["weekly_return"] = returns[key]
        frame = frame.loc[common]
        result = run_asymmetry_strategy(frame, 0.75)
        n_weeks = len(result.returns)
        cumulative = result.metrics["return"] / 100.0
        row = {
            "label": label,
            "cumulative_return": result.metrics["return"],
            "mean_weekly_bps": float(result.returns.mean() * 1e4),
            "annualized_return": ((1 + cumulative) ** (52 / n_weeks) - 1) * 100,
            "sharpe": result.metrics["sharpe"],
            "mdd": result.metrics["mdd"],
            "in_position_weeks": int(result.metrics["in_position_weeks"]),
            "holding_episodes": int(result.metrics["holding_episodes"]),
        }
        for pips in EXECUTION_COST_TIERS:
            # dot-free key: field paths in analysis/table_provenance.py are dotted
            tier = str(pips).replace(".", "p")
            row[f"net_return_{tier}_pips"] = run_asymmetry_strategy(
                frame, 0.75, round_trip_cost_pips=pips
            ).metrics["net_return"]
        rows[key] = row

    return {
        "common_sample_n": int(common.sum()),
        "dropped_weeks": dropped,
        "dropped_reason": "no following entry point exists for the delayed timings",
        "friday_close_reproduces_weekly_return": True,
        "alignment_note": (
            "Friday close is the decision instant and uses a close-to-close return; the "
            "three delayed timings enter one boundary later and use a forward return from "
            "their own entry point. A uniform shift across all four is look-ahead."
        ),
        "cost_tiers_pips": list(EXECUTION_COST_TIERS),
        "timings": rows,
    }


def tail_construction_variants(daily_px: pd.DataFrame, weekly_index) -> dict:
    """The published weekly tail signal beside two all-trading-days alternatives.

    The published construction flags exceedances daily and then reads the signal
    only on the Friday, so most weeks containing an exceedance enter the weekly
    panel as zeros.  Two aggregations that use every trading day are computed
    here for comparison.  Neither is self-evidently the right one:

    - the signed sum lets two exceedances of opposite sign within a week cancel,
      so a violent week can register as quiet;
    - the largest absolute exceedance lets a single day define the week and
      discards every other exceedance in it.

    Both are therefore constructions requiring economic justification about what
    weekly tail exposure means, not neutral fixes.  This function exists so the
    sensitivity can be reported; it does not change the primary series, which
    remains the published Friday-sampled one.
    """

    d = daily_px[["Close"]].copy()
    d["returns"] = d["Close"].pct_change(fill_method=None)
    q95 = d["returns"].abs().rolling(252, min_periods=60).quantile(0.95)
    signed = pd.Series(np.where(d["returns"].abs() > q95, d["returns"], 0.0), index=d.index)

    def largest_abs(block):
        arr = block.to_numpy()
        return float(arr[np.argmax(np.abs(arr))]) if len(arr) else 0.0

    weekly_groups = signed.resample("W-FRI")
    return {
        "friday_sampled": weekly_groups.last().reindex(weekly_index),
        "all_days_signed_sum": weekly_groups.sum().reindex(weekly_index),
        "all_days_largest_abs": weekly_groups.apply(largest_abs).reindex(weekly_index),
        "weeks_with_any_exceedance": int(((signed != 0).resample("W-FRI").sum()
                                          .reindex(weekly_index).fillna(0) > 0).sum()),
    }


def block_bootstrap_skew_ci(x, b=2000, block=13, seed=SEED):
    values = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    n = len(values)
    nblocks = int(np.ceil(n / block))
    boot = np.empty(b)
    for i in range(b):
        starts = rng.integers(0, n, nblocks)
        idx = (starts[:, None] + np.arange(block)[None, :]).ravel() % n
        boot[i] = stats.skew(values[idx[:n]], bias=False)
    return np.percentile(boot, [2.5, 97.5]), float(boot.std(ddof=1))


def iid_bootstrap_skew_ci(x, b=2000, seed=SEED):
    """Skewness CI with NO dependence correction.

    The comparison against the block bootstrap separates two explanations for a
    wide interval: serial dependence, and non-normality of the marginal.  If the
    i.i.d. interval is already wide, dependence is not what widened it.
    """
    values = np.asarray(x, dtype=float)
    rng = np.random.default_rng(seed)
    boot = np.array([stats.skew(rng.choice(values, len(values), replace=True), bias=False)
                     for _ in range(b)])
    return np.percentile(boot, [2.5, 97.5]), float(boot.std(ddof=1))


def episode_ids(position_ledger):
    """Episode number governing each week's realized return.

    Needed because the in-position weeks are non-contiguous: 55 weeks drawn from
    15 episodes scattered across a decade.  Lag-based HAC corrections assume the
    rows are consecutive in time, which these are not.
    """
    decision, current = {}, 0
    for date, row in position_ledger.iterrows():
        if row["event_type"] in ("entry", "reversal"):
            current += 1
        decision[date] = current if float(row["new_position"]) != 0 else 0
    order = list(position_ledger.index)
    return pd.Series({d: (decision[order[i - 1]] if i else 0) for i, d in enumerate(order)})


def stationary_bootstrap_indices(n, expected_block=4.0, size=None, rng=None):
    rng = rng or np.random.default_rng()
    size = size or n
    idx = np.empty(size, dtype=int)
    idx[0] = rng.integers(0, n)
    for i in range(1, size):
        idx[i] = rng.integers(0, n) if rng.random() < 1 / expected_block else (idx[i - 1] + 1) % n
    return idx


def performance(rets: pd.Series, position: pd.Series) -> dict:
    rets = rets.fillna(0.0)
    cum = float((1 + rets).prod() - 1)
    sd = float(rets.std())
    neg = rets[rets < 0]
    downside = float(neg.std()) if len(neg) > 1 else 0.0
    curve = (1 + rets).cumprod()
    return {
        "ret": cum * 100,
        "vol": sd * np.sqrt(52) * 100,
        "sharpe": float(rets.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0,
        "sortino": float(rets.mean() / downside * np.sqrt(52)) if downside > 0 else 0.0,
        "mdd": float((curve / curve.cummax() - 1).min() * 100),
        **summarize_position_changes(position),
    }


def hac_reg(frame: pd.DataFrame, clusters=None) -> dict | None:
    """Factor regression.

    Full sample: Newey-West HAC, which is appropriate there because the weekly
    observations are consecutive.

    In-position sample: the 55 weeks are non-contiguous, drawn from separate
    holding episodes spread across the sample, so a lag-based correction is not
    applicable and Newey-West is NOT reported as an alternative -- it appears
    only as the withdrawn published figure.  Inference is clustered by episode.
    With fifteen clusters, CR1 is biased downward, so CR2 with Bell-McCaffrey
    degrees of freedom supplies the standard error and interval, and a
    restricted wild cluster bootstrap-t supplies the primary p-value.  HC3 is a
    robustness check.
    """

    dat = frame.dropna()
    if len(dat) <= 10:
        return None
    y, X = dat["strat"], sm.add_constant(dat[["carry", "mom", "dollar"]])
    names = list(X.columns)

    if clusters is None:
        fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
        coef = {}
        for name in names:
            lo, hi = fit.conf_int().loc[name]
            coef[name] = {"b": float(fit.params[name]), "t": float(fit.tvalues[name]),
                          "p": float(fit.pvalues[name]), "se": float(fit.bse[name]),
                          "ci": [float(lo), float(hi)]}
        return {"n": int(fit.nobs), "r2": float(fit.rsquared), "adj_r2": float(fit.rsquared_adj),
                "f": float(fit.fvalue), "inference": "newey_west_hac_4_lags",
                "inference_note": "Consecutive weekly observations; a lag-based correction applies.",
                "coef": coef}

    g = pd.Series(clusters).reindex(dat.index).to_numpy()
    Xa, ya = X.to_numpy(), y.to_numpy()
    coef = {name: cr2_inference(ya, Xa, g, j) for j, name in enumerate(names)}
    wcb = {name: wild_cluster_bootstrap(ya, Xa, g, j, reps=9999, seed=SEED)
           for j, name in enumerate(names) if name == "mom"}
    hc3 = sm.OLS(y, X).fit(cov_type="HC3")
    hac = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": 4})
    ols = sm.OLS(y, X).fit()

    def summarise(fit):
        out = {}
        for name in names:
            lo, hi = fit.conf_int().loc[name]
            out[name] = {"b": float(fit.params[name]), "t": float(fit.tvalues[name]),
                         "p": float(fit.pvalues[name]), "se": float(fit.bse[name]),
                         "ci": [float(lo), float(hi)]}
        return out

    return {
        "n": int(ols.nobs), "r2": float(ols.rsquared), "adj_r2": float(ols.rsquared_adj),
        "f": float(ols.fvalue), "n_clusters": int(pd.Series(g).nunique()),
        "inference": "cr2_clustered_by_episode_with_wild_cluster_bootstrap",
        "inference_note": (
            "The in-position weeks are non-contiguous. Standard errors and intervals are CR2 "
            "clustered by holding episode with Bell-McCaffrey degrees of freedom; the primary "
            "p-value is a restricted wild cluster bootstrap-t with Rademacher weights."),
        "coef": coef,
        "wild_cluster_bootstrap": wcb,
        "robustness_hc3": summarise(hc3),
        "withdrawn_hac": {
            "note": ("Newey-West with 4 lags, as published in an earlier draft of this revision. "
                     "Reported only to identify the withdrawn figure: a lag-based correction "
                     "presumes consecutive observations and is inappropriate to this sample. "
                     "It is NOT an alternative specification."),
            **summarise(hac)},
    }


def ferro_segers_theta(exc_idx):
    gaps = np.diff(exc_idx)
    if len(gaps) < 2:
        return np.nan
    if gaps.max() <= 2:
        numerator = 2 * gaps.sum() ** 2
        denominator = len(gaps) * np.square(gaps).sum()
    else:
        numerator = 2 * np.square((gaps - 1).sum())
        denominator = len(gaps) * ((gaps - 1) * (gaps - 2)).sum()
    return min(1.0, numerator / denominator) if denominator > 0 else np.nan


def json_safe(value):
    if isinstance(value, dict):
        return {str(k): json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [json_safe(v) for v in value]
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    return value


def portable_path(path: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def make_figures(weekly, table_stats, strategy_returns, benchmarks, paper_dir):
    paper_dir.mkdir(parents=True, exist_ok=True)
    labels = ["Tail", "Fast", "Pricing", "Coverage", "Hedge"]
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    for ax, col, label in zip(axes.ravel()[:5], ALPHA_COLS, labels):
        x = weekly[col].dropna()
        row = table_stats[col]
        ax.hist(x, bins=48, color="#6e0e1e", alpha=0.75, edgecolor="white", linewidth=0.3, density=True)
        ax.axvline(x.mean(), color="#555555", lw=0.9, ls="--")
        ax.set_title(f"{label} alpha", fontsize=11)
        lo, hi = row["skew_ci"]
        ax.text(0.97, 0.95, f"skew = {row['skew']:.2f}\nCI [{lo:.2f}, {hi:.2f}]", transform=ax.transAxes,
                ha="right", va="top", fontsize=9, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#555555"))
    ax = axes.ravel()[5]
    ypos = np.arange(5)[::-1]
    for y, col in zip(ypos, ALPHA_COLS):
        row = table_stats[col]
        lo, hi = row["skew_ci"]
        color = "#6e0e1e" if lo > 0 or hi < 0 else "#555555"
        ax.plot([lo, hi], [y, y], color=color, lw=2)
        ax.plot(row["skew"], y, "o", color=color)
    ax.axvline(0, color="black", lw=0.8)
    ax.set_yticks(ypos, labels)
    ax.set_xlabel("Skewness (95% block-bootstrap CI)")
    ax.set_title("Dependence-robust skewness")
    fig.suptitle(f"Signed weekly alpha signals, EUR/JPY ({weekly.index[0].date()} to {weekly.index[-1].date()}, n={len(weekly)})")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(paper_dir / "alpha_asymmetry_analysis.png", dpi=200)
    plt.close(fig)

    series = {"Asymmetry (0.75)": strategy_returns, **benchmarks}
    colors = ["#6e0e1e", "#888888", "#4a6a8a", "#b0892d"]
    fig, axes = plt.subplots(2, 1, figsize=(11, 7), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    for (label, rets), color in zip(series.items(), colors):
        curve = (1 + rets).cumprod()
        axes[0].plot(curve.index, (curve - 1) * 100, label=label, color=color, lw=1.4)
        axes[1].plot(curve.index, (curve / curve.cummax() - 1) * 100, color=color, lw=1.2)
    axes[0].axhline(0, color="black", lw=0.7)
    axes[0].set_ylabel("Cumulative return (%)")
    axes[0].legend(frameon=False, fontsize=9)
    axes[1].set_ylabel("Drawdown (%)")
    fig.suptitle("Strategy equity curves and drawdowns, one-lag Friday-close convention")
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(paper_dir / "backtest_results.png", dpi=200)
    plt.close(fig)


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    lines = []

    def log(message=""):
        print(message)
        lines.append(str(message))

    log("=" * 80)
    log("ALPHA-ASYMMETRY CORRECTED REPLICATION PIPELINE")
    log(f"Generated UTC: {datetime.now(timezone.utc).isoformat()}")
    log("Timing: Friday-close signal, one shift, next Friday-close return")
    log("=" * 80)

    datasets, manifest = load_datasets(args.cache_dir, refresh=args.refresh, offline=args.offline)
    # The committed data_manifest.json is the *reference*: it records the inputs
    # the committed results were produced from, and analysis/fetch_data.py checks
    # a reader's downloads against it.  Writing this run's *observed* manifest
    # over it would overwrite the reference with whatever the reader happens to
    # have, and the comparison would then be against itself.  Keep the two apart.
    write_manifest(manifest, args.output_dir / "data_manifest.observed.json")
    for name, info in manifest["datasets"].items():
        log(f"{name:7s}: {info['rows']} rows, {info['first_date']} to {info['last_date']}, sha256={info['sha256'][:12]}...")
    log("LIMITATION: original raw snapshots were not committed; exact numerical reproduction of the archived run cannot be claimed.")

    weekly = build_weekly_alphas(datasets["EURJPY"], datasets["DXY"])
    n = len(weekly)
    log(f"Analysis-ready weekly sample: n={n}, {weekly.index[0].date()} to {weekly.index[-1].date()}")

    table_stats = {}
    for col in ALPHA_COLS:
        x = weekly[col].dropna()
        skew = float(stats.skew(x, bias=False))
        kurt = float(stats.kurtosis(x, bias=False))
        ci, bse = block_bootstrap_skew_ci(x)
        iid_ci, iid_bse = iid_bootstrap_skew_ci(x)
        lb = acorr_ljungbox(x, lags=[4], return_df=True)
        sw, sw_p = stats.shapiro(x)
        k2, k2_p = stats.normaltest(x)
        n_col = len(x)
        jb = n_col / 6 * (skew ** 2 + kurt ** 2 / 4)
        table_stats[col] = {
            "n": n_col, "skew": skew, "ex_kurt": kurt, "skew_ci": list(ci),
            "skew_boot_se": bse, "skew_ci_iid": list(iid_ci), "skew_boot_se_iid": iid_bse,
            "normal_theory_se": float(np.sqrt(6 / n_col)),
            "ai": compute_ai(x), "por": float((x > 0).mean() * 100),
            "nonzero_obs": int((x != 0).sum()),
            "skew_t_iid": skew / np.sqrt(6 / n_col), "jb": float(jb), "sw": float(sw), "sw_p": float(sw_p),
            "k2": float(k2), "k2_p": float(k2_p), "lb_q4": float(lb["lb_stat"].iloc[0]),
            "lb_q4_p": float(lb["lb_pvalue"].iloc[0]),
        }
        log(f"{col:15s} skew={skew:6.2f} CI=[{ci[0]:.2f},{ci[1]:.2f}] AI={table_stats[col]['ai']:.2f}")

    # Tail-signal aggregation sensitivity. The primary series is unchanged; this
    # reports what the same statistics look like under two all-trading-days
    # aggregations, because the reviewer is right that Friday sampling discards
    # most of the exceedances the daily rule detects.
    tail_variants = tail_construction_variants(datasets["EURJPY"], weekly.index)
    tail_sensitivity = {
        "primary": "friday_sampled",
        "primary_note": (
            "The published Friday-sampled construction remains primary. An aggregation rule is "
            "not selected on which one yields significance; that would be specification "
            "selection on outcomes, which this paper criticises elsewhere."),
        "weeks_with_any_daily_exceedance": tail_variants["weeks_with_any_exceedance"],
        "constructions": {},
    }
    for label in ("friday_sampled", "all_days_signed_sum", "all_days_largest_abs"):
        series = pd.Series(tail_variants[label]).dropna()
        ci_v, se_v = block_bootstrap_skew_ci(series.to_numpy())
        iid_v, _ = iid_bootstrap_skew_ci(series.to_numpy())
        tail_sensitivity["constructions"][label] = {
            "nonzero_obs": int((series != 0).sum()),
            "skew": float(stats.skew(series, bias=False)),
            "ex_kurt": float(stats.kurtosis(series, bias=False)),
            "ai": compute_ai(series),
            "por": float((series > 0).mean() * 100),
            "skew_ci": list(ci_v),
            "skew_ci_iid": list(iid_v),
            "ci_excludes_zero": bool(ci_v[0] > 0 or ci_v[1] < 0),
        }
    excl = [k for k, v in tail_sensitivity["constructions"].items() if v["ci_excludes_zero"]]
    tail_sensitivity["conclusion"] = (
        "Tail inference is aggregation-sensitive: across three defensible weekly aggregations "
        "of the same daily exceedance rule the skewness point estimate changes sign and the "
        f"dependence-robust interval excludes zero under {len(excl)} of 3. The signal is not "
        "robust until weekly tail exposure is defined.")
    log(f"TAIL SENSITIVITY: {tail_sensitivity['conclusion']}")

    base = run_asymmetry_strategy(weekly, 0.75)
    log(f"Baseline: return={base.metrics['return']:.2f}% Sharpe={base.metrics['sharpe']:.3f} "
        f"episodes={base.metrics['holding_episodes']} legs={base.metrics['execution_legs']} "
        f"reversals={base.metrics['reversals']} turnover={base.metrics['turnover']:.2f}")
    base.position_ledger.to_csv(args.output_dir / "position_ledger.csv", date_format="%Y-%m-%d")
    base.trade_ledger.to_csv(args.output_dir / "trade_ledger.csv", index=False, date_format="%Y-%m-%d")

    ma20 = weekly["Close"].rolling(20).mean()
    sd20 = weekly["Close"].rolling(20).std()
    z = (weekly["Close"] - ma20) / sd20
    positions = {
        "Momentum (20w)": np.sign(weekly["Close"].pct_change(20, fill_method=None)).fillna(0.0),
        "Mean reversion (2.0 sigma)": pd.Series(np.where(z > 2, -1.0, np.where(z < -2, 1.0, 0.0)), index=weekly.index),
        "Buy and hold": pd.Series(1.0, index=weekly.index),
    }
    benchmark_returns = {name: simple_strategy(pos, weekly["weekly_return"]) for name, pos in positions.items()}
    table3 = {"Asymmetry": performance(base.returns, base.position)}
    table3.update({name: performance(benchmark_returns[name], pos) for name, pos in positions.items()})

    selected = {}
    for year in range(2018, 2026):
        train = weekly.loc[: f"{year - 1}-12-31"]
        scores = [(t, run_asymmetry_strategy(train, t).metrics["sharpe"]) for t in GRID]
        selected[year] = max(scores, key=lambda item: item[1])[0]
    oos_data = weekly.loc["2017-12-29":].copy()
    threshold_path = pd.Series([selected.get(date.year, selected[2018]) for date in oos_data.index], index=oos_data.index)
    oos = run_asymmetry_strategy(oos_data, threshold_path)
    oos_rows = []
    for year, threshold in selected.items():
        rets = oos.returns[oos.returns.index.year == year]
        events = oos.position_ledger[oos.position_ledger.index.year == year]
        applied_year = oos.applied_position[oos.applied_position.index.year == year]
        active_rets = rets[applied_year.abs() > 0]
        sd = float(rets.std())
        year_episodes = int(events["event_type"].isin(["entry", "reversal"]).sum())
        oos_rows.append({"year": year, "threshold": threshold, "return": float((1 + rets).prod() - 1) * 100,
                         "sharpe": float(rets.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0,
                         "hit": float((active_rets > 0).mean() * 100) if len(active_rets) else None,
                         "new_episodes": year_episodes,
                         "inference_supported": supports_inference(year_episodes)})
    pooled = oos.returns[oos.returns.index.year >= 2018]
    pooled_applied = oos.applied_position[oos.applied_position.index.year >= 2018]
    pooled_active = pooled[pooled_applied.abs() > 0]
    pooled_episodes = int(oos.position_ledger.loc["2018-01-01":, "event_type"].isin(["entry", "reversal"]).sum())
    # Every metric below is computed and kept, because this file is the audit
    # record and silently dropping numbers would make it unauditable. What the
    # flag governs is whether they may be *reported as performance*. A Sharpe
    # ratio, a hit rate and an annualized return are sample statistics; over a
    # single holding episode they have no sampling distribution to speak of and
    # describe one realized path, not an expected one.
    table5 = {"rows": oos_rows, "pooled": {
        "cum_return": float((1 + pooled).prod() - 1) * 100,
        "annualized_return": float(((1 + pooled).prod() ** (52 / len(pooled)) - 1) * 100),
        "sharpe": float(pooled.mean() / pooled.std() * np.sqrt(52)) if pooled.std() > 0 else 0.0,
        "hit": float((pooled_active > 0).mean() * 100) if len(pooled_active) else None,
        "new_episodes": pooled_episodes,
        "inference_supported": supports_inference(pooled_episodes)},
        "min_episodes_for_inference": MIN_EPISODES_FOR_INFERENCE,
        "reporting_rule": INFERENCE_REPORTING_RULE}
    if not table5["pooled"]["inference_supported"]:
        log(f"WALK-FORWARD: {pooled_episodes} out-of-sample episode(s) in "
            f"{len(selected)} test years; below the {MIN_EPISODES_FOR_INFERENCE}-episode "
            f"minimum, so pooled Sharpe/hit/annualized return are not reportable as performance.")

    vix_weekly = datasets["VIX"]["Close"].resample("W-FRI").mean().reindex(weekly.index)
    regimes = {}
    for name, mask in {"low_vix": vix_weekly < 20, "high_vix": vix_weekly >= 20}.items():
        mask = mask.fillna(False)
        regimes[name] = {"n": int(mask.sum()), "tail_skew": float(stats.skew(weekly.loc[mask, "tail_alpha"], bias=False)),
                         "fast_skew": float(stats.skew(weekly.loc[mask, "fast_alpha"], bias=False)),
                         "pricing_skew": float(stats.skew(weekly.loc[mask, "pricing_alpha"], bias=False)),
                         "strategy_return": float((1 + base.returns.loc[mask]).prod() - 1) * 100}
    temporal_masks = {
        "pre_covid": weekly.index.year <= 2019,
        "covid_2020": weekly.index.year == 2020,
        "post_covid": weekly.index.year >= 2021,
        "rate_hike_2022_2025": weekly.index.year >= 2022,
    }
    for name, mask in temporal_masks.items():
        regimes[name] = {
            "n": int(mask.sum()),
            "tail_skew": float(stats.skew(weekly.loc[mask, "tail_alpha"], bias=False)),
            "fast_skew": float(stats.skew(weekly.loc[mask, "fast_alpha"], bias=False)),
            "pricing_skew": float(stats.skew(weekly.loc[mask, "pricing_alpha"], bias=False)),
            "strategy_return": float((1 + base.returns.loc[mask]).prod() - 1) * 100,
        }
    # The same rule governs the threshold grid. At a high enough threshold the
    # strategy opens a single episode, and its Sharpe ratio and hit rate are then
    # the same unreportable quantities the walk-forward suppresses -- in fact the
    # same episode. Flagging it here, rather than editing one table by hand,
    # keeps a statistic from being withheld in one place and printed in another.
    sensitivity = {}
    for t in GRID:
        metrics = run_asymmetry_strategy(weekly, t).metrics
        metrics["inference_supported"] = supports_inference(metrics["holding_episodes"])
        sensitivity[str(t)] = metrics
    for label, metrics in sensitivity.items():
        if not metrics["inference_supported"]:
            log(f"SENSITIVITY: threshold {label} opens {metrics['holding_episodes']} episode(s); "
                f"below the {MIN_EPISODES_FOR_INFERENCE}-episode minimum, so its Sharpe ratio "
                f"and hit rate are not reportable as performance.")

    # Position sizing is a specification choice, not an implementation detail,
    # so both readings are reported rather than one being adopted silently.
    # "weekly" is the headline: it is what Equation 10's contemporaneous AI_t
    # and the manuscript's "Rebalancing: Weekly (end of Friday close)" say.
    # "entry" freezes the notional at entry and is the reported alternative.
    entry_sized = run_asymmetry_strategy(weekly, 0.75, sizing="entry")
    sizing_variants = {
        "headline": "weekly",
        "note": (
            "Neither mode is a pure restoration of the published rule: repairing the "
            "dead exit branch creates held-but-unsignalled weeks that the published "
            "specification never had to size. Weekly is the smaller extension because "
            "it keeps the manuscript's stated rebalancing frequency and Equation 10's "
            "contemporaneous index."
        ),
        "weekly": base.metrics,
        "entry": entry_sized.metrics,
    }

    factor = pd.DataFrame(index=weekly.index)
    factor["strat"] = base.returns
    factor["dollar"] = datasets["DXY"]["Close"].resample("W-FRI").last().pct_change(fill_method=None).reindex(weekly.index)
    aud = datasets["AUDJPY"]["Close"].resample("W-FRI").last().pct_change(fill_method=None).reindex(weekly.index)
    nzd = datasets["NZDJPY"]["Close"].resample("W-FRI").last().pct_change(fill_method=None).reindex(weekly.index)
    factor["carry"] = pd.concat([aud, nzd], axis=1).mean(axis=1)
    # market basis, consistent with the carry and dollar regressors beside it
    factor["mom"] = simple_strategy(np.sign(weekly["Close"].pct_change(12, fill_method=None)), weekly["market_return"])
    factor = factor.dropna()
    inpos_mask = base.applied_position.reindex(factor.index).abs() > 0
    clusters = episode_ids(base.position_ledger).reindex(factor.index)
    factors = {"full": hac_reg(factor),
               "in_position": hac_reg(factor.loc[inpos_mask], clusters=clusters.loc[inpos_mask]),
               "n_in_position": int(inpos_mask.sum()),
               "standard_error_note": (
                   "The in-position weeks are non-contiguous: they arise from separate holding "
                   "episodes spread across the sample. Cluster-robust errors by episode are "
                   "primary there; Newey-West assumes consecutive observations and is reported "
                   "for comparison only.")}

    cost_rows = []
    for label, pips in [("Zero cost", 0.0), ("Prime brokerage", 0.3), ("Institutional", 0.7), ("Retail tight", 1.3), ("Retail wide", 2.0)]:
        result = run_asymmetry_strategy(weekly, 0.75, round_trip_cost_pips=pips)
        sd = float(result.net_returns.std())
        cost_rows.append({"name": label, "pips": pips, "net_return": result.metrics["net_return"],
                          "sharpe": float(result.net_returns.mean() / sd * np.sqrt(52)) if sd > 0 else 0.0})
    if base.metrics["return"] <= 0:
        break_even = None
    else:
        lo, hi = 0.0, 100.0
        for _ in range(60):
            mid = (lo + hi) / 2
            net = run_asymmetry_strategy(weekly, 0.75, round_trip_cost_pips=mid).metrics["net_return"]
            lo, hi = (mid, hi) if net > 0 else (lo, mid)
        break_even = (lo + hi) / 2
    costs = {"rows": cost_rows, "break_even_pips": break_even,
             "break_even_note": "not applicable when the zero-cost strategy return is non-positive" if break_even is None else None}

    candidates = {}
    for col in ALPHA_COLS:
        sk = weekly[col].rolling(20, min_periods=10).apply(lambda x: stats.skew(x, bias=False), raw=False)
        candidates[f"asym_{col}"] = simple_strategy(((sk > 0.75) & (weekly[col] > 0)).astype(float), weekly["weekly_return"])
    candidates["asym_full"] = base.returns
    for k in [10, 20, 40]:
        candidates[f"momentum_{k}w"] = simple_strategy(np.sign(weekly["Close"].pct_change(k, fill_method=None)), weekly["weekly_return"])
    for k in [1.5, 2.0]:
        candidates[f"mean_reversion_{k}"] = simple_strategy(pd.Series(np.where(z > k, -1.0, np.where(z < -k, 1.0, 0.0)), index=weekly.index), weekly["weekly_return"])
    candidates["always_long"] = benchmark_returns["Buy and hold"]
    rng_random = np.random.default_rng(SEED)
    candidates["random_candidate"] = simple_strategy(pd.Series(rng_random.choice([-1.0, 1.0], len(weekly)), index=weekly.index), weekly["weekly_return"])
    universe = pd.DataFrame(candidates).fillna(0.0)
    values = universe.to_numpy()
    n_obs, n_k = values.shape
    means = values.mean(axis=0)
    observed_rc = np.sqrt(n_obs) * means.max()
    rng_boot = np.random.default_rng(SEED)
    boot_means = np.empty((1000, n_k))
    for b in range(1000):
        boot_means[b] = values[stationary_bootstrap_indices(n_obs, rng=rng_boot)].mean(axis=0)
    boot_rc = np.sqrt(n_obs) * (boot_means - means).max(axis=1)
    omega = np.sqrt(n_obs) * boot_means.std(axis=0, ddof=1)
    omega[omega == 0] = 1e-12
    t_spa = np.sqrt(n_obs) * means / omega
    observed_spa = max(float(t_spa.max()), 0.0)
    cutoff = -omega / np.sqrt(n_obs) * np.sqrt(2 * np.log(np.log(max(n_obs, 3))))
    recenter = np.where(means >= cutoff, means, 0.0)
    boot_spa = np.maximum((np.sqrt(n_obs) * (boot_means - recenter) / omega).max(axis=1), 0.0)
    real_only = {k: v for k, v in candidates.items() if k != "random_candidate"}
    values_r = pd.DataFrame(real_only).fillna(0.0).to_numpy()
    n_r, k_r = values_r.shape
    means_r = values_r.mean(axis=0)
    observed_rc_r = np.sqrt(n_r) * means_r.max()
    rng_r = np.random.default_rng(SEED)
    boot_means_r = np.empty((1000, k_r))
    for b in range(1000):
        boot_means_r[b] = values_r[stationary_bootstrap_indices(n_r, rng=rng_r)].mean(axis=0)
    boot_rc_r = np.sqrt(n_r) * (boot_means_r - means_r).max(axis=1)
    omega_r = np.sqrt(n_r) * boot_means_r.std(axis=0, ddof=1)
    omega_r[omega_r == 0] = 1e-12
    observed_spa_r = max(float((np.sqrt(n_r) * means_r / omega_r).max()), 0.0)
    cutoff_r = -omega_r / np.sqrt(n_r) * np.sqrt(2 * np.log(np.log(max(n_r, 3))))
    recenter_r = np.where(means_r >= cutoff_r, means_r, 0.0)
    boot_spa_r = np.maximum((np.sqrt(n_r) * (boot_means_r - recenter_r) / omega_r).max(axis=1), 0.0)

    # Sizing invariance of the formal test, computed rather than asserted.
    # Only asym_full depends on the sizing convention; every other candidate is
    # built with fixed unit sizing or is buy-and-hold. The reported statistic is
    # set by the universe maximum, so if that maximum is attained by a candidate
    # independent of the asymmetry rule the statistic cannot move, and the
    # p-value shifts only through the bootstrap distribution, which does include
    # the changed candidate. That is a claim about this universe, so it is tested.
    frozen_full = run_asymmetry_strategy(weekly, 0.75, sizing="entry").returns
    real_frozen = dict(real_only, asym_full=frozen_full)
    values_f = pd.DataFrame(real_frozen).fillna(0.0).to_numpy()
    means_f = values_f.mean(axis=0)
    observed_rc_f = np.sqrt(n_r) * means_f.max()
    rng_f = np.random.default_rng(SEED)
    boot_means_f = np.empty((1000, k_r))
    for b in range(1000):
        boot_means_f[b] = values_f[stationary_bootstrap_indices(n_r, rng=rng_f)].mean(axis=0)
    boot_rc_f = np.sqrt(n_r) * (boot_means_f - means_f).max(axis=1)
    omega_f = np.sqrt(n_r) * boot_means_f.std(axis=0, ddof=1)
    omega_f[omega_f == 0] = 1e-12
    observed_spa_f = max(float((np.sqrt(n_r) * means_f / omega_f).max()), 0.0)
    cutoff_f = -omega_f / np.sqrt(n_r) * np.sqrt(2 * np.log(np.log(max(n_r, 3))))
    boot_spa_f = np.maximum(
        (np.sqrt(n_r) * (boot_means_f - np.where(means_f >= cutoff_f, means_f, 0.0)) / omega_f).max(axis=1), 0.0)
    white_rc_p_f = float((boot_rc_f >= observed_rc_f).mean())
    spa_p_f = float((boot_spa_f >= observed_spa_f).mean())
    sizing_invariance = {
        "candidates_that_change_with_sizing": [
            k for k in real_only if not np.allclose(
                pd.Series(real_only[k]).fillna(0.0).to_numpy(),
                pd.Series(real_frozen[k]).fillna(0.0).to_numpy())],
        "argmax_weekly": pd.DataFrame(real_only).fillna(0.0).mean().idxmax(),
        "argmax_frozen": pd.DataFrame(real_frozen).fillna(0.0).mean().idxmax(),
        "white_rc_stat_weekly": observed_rc_r, "white_rc_stat_frozen": observed_rc_f,
        "spa_stat_weekly": observed_spa_r, "spa_stat_frozen": observed_spa_f,
        "white_rc_stat_identical": bool(observed_rc_r == observed_rc_f),
        "spa_stat_identical": bool(observed_spa_r == observed_spa_f),
        "white_rc_p_weekly": float((boot_rc_r >= observed_rc_r).mean()),
        "white_rc_p_frozen": white_rc_p_f,
        "spa_p_weekly": float((boot_spa_r >= observed_spa_r).mean()),
        "spa_p_frozen": spa_p_f,
    }
    sizing_invariance["white_rc_p_abs_diff"] = abs(
        sizing_invariance["white_rc_p_weekly"] - white_rc_p_f)
    sizing_invariance["spa_p_abs_diff"] = abs(
        sizing_invariance["spa_p_weekly"] - spa_p_f)

    snooping = {"formal_benchmark": "zero weekly return",
                "random_role": "reported as a diagnostic outside the formal universe; the formal test uses the 12 real strategies",
                "primary_universe": "twelve real candidate strategies",
                "sizing_invariance": sizing_invariance,
                "real_only": {"n_strategies": k_r, "white_rc_stat": observed_rc_r,
                              "white_rc_p": float((boot_rc_r >= observed_rc_r).mean()),
                              "spa_stat": observed_spa_r,
                              "spa_p": float((boot_spa_r >= observed_spa_r).mean()),
                              "best_candidate": pd.DataFrame(real_only).fillna(0.0).mean().idxmax()},
                "with_random_candidate_note": "retained for comparison; the random sequence is the argmax, so removing it lowers the observed statistic more than the bootstrap distribution and raises the RC p-value",
                 "n_strategies": n_k, "white_rc_stat": observed_rc, "white_rc_p": float((boot_rc >= observed_rc).mean()),
                 "spa_stat": observed_spa, "spa_p": float((boot_spa >= observed_spa).mean()),
                 "best_candidate": universe.mean().idxmax(),
                 "annualized_mean_pct": {k: float(v * 52 * 100) for k, v in universe.mean().items()}}

    # market tail object, not strategy P&L -- see build_weekly_alphas
    ret = weekly["market_return"].dropna()
    threshold_u = float(ret.abs().quantile(0.95))
    exceed_idx = np.where(ret.abs().to_numpy() > threshold_u)[0]
    theta = ferro_segers_theta(exceed_idx)
    gaps = np.diff(exceed_idx)
    rng_evt = np.random.default_rng(SEED)
    theta_boot = [ferro_segers_theta(np.r_[0, np.cumsum(rng_evt.choice(gaps, len(gaps), replace=True))]) for _ in range(2000)]
    clusters, current = [], [exceed_idx[0]]
    for idx in exceed_idx[1:]:
        if idx - current[-1] <= 5:
            current.append(idx)
        else:
            clusters.append(current)
            current = [idx]
    clusters.append(current)
    excess = np.array([ret.abs().to_numpy()[cluster].max() for cluster in clusters]) - threshold_u
    xi, _, scale = stats.genpareto.fit(excess, floc=0)
    ks_stat, ks_p = stats.kstest(excess, "genpareto", args=(xi, 0, scale))
    xi_boot = []
    for _ in range(2000):
        try:
            xi_boot.append(stats.genpareto.fit(rng_evt.choice(excess, len(excess), replace=True), floc=0)[0])
        except Exception:
            pass
    declustering = []
    for sep in (1, 2, 3, 5):
        cl, cur = [], [exceed_idx[0]]
        for i in exceed_idx[1:]:
            if i - cur[-1] <= sep:
                cur.append(i)
            else:
                cl.append(cur); cur = [i]
        cl.append(cur)
        exc = np.array([ret.abs().to_numpy()[c].max() for c in cl]) - threshold_u
        xi_s, _, sc_s = stats.genpareto.fit(exc, floc=0)
        rng_s = np.random.default_rng(SEED)
        boot_s = [stats.genpareto.fit(rng_s.choice(exc, len(exc), replace=True), floc=0)[0]
                  for _ in range(1000)]
        declustering.append({"separation_weeks": sep, "clusters": len(cl), "xi": float(xi_s),
                             "xi_ci": list(np.percentile(boot_s, [2.5, 97.5])),
                             "ks_p": float(stats.kstest(exc, "genpareto", args=(xi_s, 0, sc_s))[1])})

    evt = {"input": "absolute Friday-close-to-Friday-close EURJPY returns",
           "declustering_sensitivity": declustering, "threshold_pct": threshold_u * 100,
           "raw_exceedances": len(exceed_idx), "clusters": len(clusters),
           "theta": theta, "theta_ci": list(np.percentile(theta_boot, [2.5, 97.5])), "xi": xi,
           "xi_ci": list(np.percentile(xi_boot, [2.5, 97.5])), "scale": scale, "ks_stat": ks_stat, "ks_p": ks_p}

    rng_ci = np.random.default_rng(SEED)
    ann_boot, sharpe_boot = [], []
    xret = base.returns.to_numpy()
    for _ in range(2000):
        sample = xret[stationary_bootstrap_indices(len(xret), rng=rng_ci)]
        growth = float(np.prod(1 + sample))
        ann_boot.append((growth ** (52 / len(sample)) - 1) * 100)
        sample_sd = sample.std(ddof=1)
        sharpe_boot.append(sample.mean() / sample_sd * np.sqrt(52) if sample_sd > 0 else 0.0)
    block_sensitivity = []
    for eb in (2.0, 4.0, 8.0, 13.0):
        rng_b = np.random.default_rng(SEED)
        sh = []
        for _ in range(1000):
            s = xret[stationary_bootstrap_indices(len(xret), expected_block=eb, rng=rng_b)]
            sd_s = s.std(ddof=1)
            sh.append(s.mean() / sd_s * np.sqrt(52) if sd_s > 0 else 0.0)
        block_sensitivity.append({"expected_block_weeks": eb,
                                  "sharpe_ci": list(np.percentile(sh, [2.5, 97.5]))})

    inference = {"block_length_sensitivity": block_sensitivity,
                 "annualized_return": ((1 + base.metrics["return"] / 100) ** (52 / len(xret)) - 1) * 100,
                 "annualized_return_ci": list(np.percentile(ann_boot, [2.5, 97.5])),
                 "sharpe": base.metrics["sharpe"], "sharpe_ci": list(np.percentile(sharpe_boot, [2.5, 97.5]))}

    cross_market = {}
    for name in ["EURJPY", "GBPUSD", "SPY", "GLD"]:
        market_weekly = weekly if name == "EURJPY" else build_weekly_alphas(datasets[name])
        if "hedge_alpha" not in market_weekly:
            market_weekly["hedge_alpha"] = np.nan
        result = run_asymmetry_strategy(market_weekly, 0.75)
        cross_market[name] = {"n": len(market_weekly), "tail_skew": float(stats.skew(market_weekly["tail_alpha"], bias=False)),
                              "fast_skew": float(stats.skew(market_weekly["fast_alpha"], bias=False)),
                              "pricing_skew": float(stats.skew(market_weekly["pricing_alpha"], bias=False)),
                              "coverage_skew": float(stats.skew(market_weekly["coverage_alpha"], bias=False)),
                              "strategy_return": result.metrics["return"], "holding_episodes": result.metrics["holding_episodes"],
                              "buy_hold_return": float(market_weekly["Close"].iloc[-1] / market_weekly["Close"].iloc[0] - 1) * 100}

    make_figures(weekly, table_stats, base.returns, benchmark_returns, args.paper_dir)

    execution_grid = execution_timing_grid(datasets["EURJPY"], weekly)
    log(f"Execution-timing grid: common sample n={execution_grid['common_sample_n']}, "
        f"dropped {execution_grid['dropped_weeks']}")

    results = {
        "specification": {"execution": "Friday-close signal; position executes at the first trading-session open after the signal (Monday open, or the next available session open after a holiday) and earns to the first open after the following Friday",
                          "execution_proxy_is_a_choice": "The published specification entered at the Monday open following Friday signal generation; this is restored as primary. Friday close is retained as a robustness timing in the execution grid",
                          "max_holding_return_periods": 4, "simultaneous_signals": "flat", "weekly_resizing": True,
                          "position_size_units": "1.0 to 2.0 gross notional units; values above 1 imply leverage",
                          "hedge_alpha": "100-day rolling correlation multiplied by fixed -0.02 proxy",
                          "evt_input": "absolute Friday-close-to-Friday-close EURJPY returns, independent of the execution convention, separate from daily tail-alpha flags"},
        "data_manifest": manifest,
        "sample": {"raw_weekly_start": "2015-11-06", "analysis_start": weekly.index[0], "analysis_end": weekly.index[-1], "n": n},
        "alpha_statistics": table_stats, "tail_construction_sensitivity": tail_sensitivity,
        "baseline": base.metrics, "benchmarks": table3,
        "walk_forward": table5, "regimes": regimes, "sensitivity": sensitivity,
        "factor_attribution": factors, "transaction_costs": costs, "data_snooping": snooping,
        "sizing_variants": sizing_variants,
        "execution_timing": execution_grid,
        "evt": evt, "return_inference": inference, "cross_market": cross_market,
    }

    safe_results = json_safe(results)
    (args.output_dir / "full_pipeline_results.json").write_text(json.dumps(safe_results, indent=2) + "\n", encoding="utf-8")
    log(f"Regime rows: low VIX={regimes['low_vix']['n']}, high VIX={regimes['high_vix']['n']} (classified after one full run)")
    log(f"White RC p={snooping['white_rc_p']:.3f}; SPA p={snooping['spa_p']:.3f}; best candidate={snooping['best_candidate']}")
    log(f"Outputs: {portable_path(args.output_dir)}")
    (args.output_dir / "full_pipeline_results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ------------------------------------------------------------------
    # Published-versus-corrected comparison.
    #
    # The "before" column is the PUBLISHED paper, commit 4d21c69 (July 2026):
    # every value is transcribed from 4d21c69:analysis/full_pipeline_results
    # .{json,txt} or from the tables of 4d21c69:paper/alpha-asymmetry.tex.
    # The original raw inputs were not committed, so these are the reported
    # results of that run, not an independent rerun of it.
    #
    # "stage" attributes each change to the correction that produced it:
    #   implementation  the three defects where the published code did not do
    #                   what the published paper said (dead exit branch,
    #                   double execution lag, AI formula)
    #   accounting      a reported quantity redefined, the underlying returns
    #                   unchanged
    #   sizing          the weekly-versus-frozen notional specification choice
    #   reporting       a figure withheld or restated, nothing recomputed
    # Where a change spans stages, the dominant one is named and the
    # attribution is quantified in docs/CORRECTION_CHANGELOG.md.
    # ------------------------------------------------------------------
    published = {
        "return": 3.6016, "sharpe": 0.1489, "mdd": -7.9572, "trades": 17,
        "in_position_weeks": 25, "vol": 2.69, "sortino": 0.062,
        "wf_cum": 2.46, "wf_trades": 3, "wf_sharpe": 0.419, "wf_hit": 60.0,
        "low_vix": 2.38, "high_vix": 2.67, "pre_covid": 1.06,
        "covid_2020": -0.19, "post_covid": 2.71, "rate_hike": 2.86,
        "intercept": 0.00008, "n_in_position": 25,
        "mom_b_full": -0.00696, "mom_t_full": -0.37, "mom_p_full": 0.710,
        "mom_b_inpos": -0.24705, "mom_t_inpos": -0.51, "mom_p_inpos": 0.609,
        "retail_wide": 3.22, "breakeven": 19.21, "rc_p": 0.15, "spa_p": 0.28,
        "annualized": 0.366, "gbpusd": 17.18, "spy": 11.66, "gld": -30.26,
    }
    published_ai = {"tail_alpha": 0.1716, "fast_alpha": 0.9577,
                    "pricing_alpha": 0.8050, "coverage_alpha": 3.4533,
                    "hedge_alpha": 1.4018}
    f_full, f_pos = factors["full"]["coef"], factors["in_position"]["coef"]
    comparisons = [
        ("Baseline cumulative return (%)", published["return"], base.metrics["return"], "implementation",
         "Sign flips. Holding through unsignalled weeks and removing the second execution lag; weekly sizing accounts for +0.93pp of the move."),
        ("Baseline Sharpe", published["sharpe"], base.metrics["sharpe"], "implementation",
         "Follows the corrected return series."),
        ("Baseline maximum drawdown (%)", published["mdd"], base.metrics["mdd"], "implementation",
         "Deeper because the strategy is now exposed for 55 weeks rather than 25."),
        ("Baseline annualized volatility (%)", published["vol"], performance(base.returns, base.position)["vol"], "implementation",
         "Higher for the same reason: more weeks with a position."),
        ("Baseline Sortino", published["sortino"], performance(base.returns, base.position)["sortino"], "implementation",
         "Follows the corrected return series."),
        ("In-position weeks", published["in_position_weeks"], base.metrics["in_position_weeks"], "implementation",
         "THE HEADLINE DEFECT: 25 of 504 weeks published, 55 corrected. The published strategy closed every position the moment its entry signal stopped firing, so it was in the market 5% of the time."),
        ("Holding episodes", published["trades"], base.metrics["holding_episodes"], "accounting",
         "Published 'trades' were position-change events divided by two, as the published note stated. Now one row per continuous directional holding."),
        ("Execution legs", None, base.metrics["execution_legs"], "accounting",
         "Not reported in the published paper. Entries and exits counted separately; a reversal is two legs."),
        ("Absolute turnover (units)", None, base.metrics["turnover"], "accounting",
         "Not reported in the published paper."),
        ("Walk-forward cumulative return (%)", published["wf_cum"], table5["pooled"]["cum_return"], "implementation",
         "Corrected strategy on one sequential out-of-sample state path."),
        ("Walk-forward new episodes", published["wf_trades"], table5["pooled"]["new_episodes"], "accounting",
         "Newly opened directional holdings, not event pairs."),
        ("Walk-forward pooled Sharpe", published["wf_sharpe"], None, "reporting",
         "WITHHELD. One out-of-sample episode supplies no sample over which a Sharpe ratio can be computed. Value retained in walk_forward.pooled.sharpe."),
        ("Walk-forward pooled hit rate (%)", published["wf_hit"], None, "reporting",
         "WITHHELD, same reason. 50% would mean one profitable and one unprofitable week."),
        ("Low-VIX strategy return (%)", published["low_vix"], regimes["low_vix"]["strategy_return"], "implementation",
         "Sign flips. Also fixes regime attribution: the published routine reran a stateful strategy on filtered, nonconsecutive dates."),
        ("High-VIX strategy return (%)", published["high_vix"], regimes["high_vix"]["strategy_return"], "implementation",
         "Sign flips, same causes."),
        ("Pre-COVID strategy return (%)", published["pre_covid"], regimes["pre_covid"]["strategy_return"], "implementation", "Sign flips."),
        ("COVID-2020 strategy return (%)", published["covid_2020"], regimes["covid_2020"]["strategy_return"], "implementation",
         "Sign flips. Identical under both sizing specifications: 2020 holds one episode whose notional was never revised."),
        ("Post-COVID strategy return (%)", published["post_covid"], regimes["post_covid"]["strategy_return"], "implementation", "Sign flips."),
        ("Rate-hike strategy return (%)", published["rate_hike"], regimes["rate_hike_2022_2025"]["strategy_return"], "implementation",
         "Remains positive; the only subsample that does."),
        ("Full-sample factor intercept", published["intercept"], f_full["const"]["b"], "implementation",
         "Sign flips. Matches the corrected strategy's own mean weekly return, as it must."),
        ("In-position factor sample", published["n_in_position"], factors["n_in_position"], "implementation",
         "25 to 55 weeks, the same exposure defect."),
        ("Momentum loading, full sample", published["mom_b_full"], f_full["mom"]["b"], "implementation",
         "Was insignificant, now significant and negative."),
        ("Momentum t-stat, full sample", published["mom_t_full"], f_full["mom"]["t"], "implementation", "p = 0.710 published, p = 0.038 corrected."),
        ("Momentum loading, in-position", published["mom_b_inpos"], f_pos["mom"]["b"], "implementation",
         "NEW FINDING: while invested the strategy is close to a one-for-one short momentum position."),
        ("Momentum t-stat, in-position", published["mom_t_inpos"], f_pos["mom"]["t"], "implementation", "p = 0.609 published, p = 0.00019 corrected."),
        ("Retail-wide net return (%)", published["retail_wide"], costs["rows"][-1]["net_return"], "implementation",
         "Sign flips. Cost drag is 0.38pp; the gross return was already negative."),
        ("Break-even round-trip cost (pips)", published["breakeven"], None, "implementation",
         "NO LONGER EXISTS. A break-even cost presumes a positive gross return to consume, and there is none."),
        ("White Reality Check p-value", published["rc_p"], snooping["white_rc_p"], "implementation",
         "Unchanged. The maximum is attained by the seeded random candidate, which no change to the asymmetry rule affects."),
        ("Hansen SPA p-value", published["spa_p"], snooping["spa_p"], "implementation", "Essentially unchanged, same reason."),
        ("Annualized return (%)", published["annualized"], inference["annualized_return"], "implementation", "Sign flips."),
        ("GBP/USD strategy return (%)", published["gbpusd"], cross_market["GBPUSD"]["strategy_return"], "implementation",
         "SIGN FLIPS, +17.18% to -13.32%. Attributable to the implementation fixes, not to sizing: with the fixes and frozen sizing the figure is -14.11%. The published claim that FX offers more favourable conditions rested on this number."),
        ("SPY strategy return (%)", published["spy"], cross_market["SPY"]["strategy_return"], "implementation",
         "Stays positive and still trails buy-and-hold by roughly 280 percentage points."),
        ("GLD strategy return (%)", published["gld"], cross_market["GLD"]["strategy_return"], "implementation",
         "Stays negative; magnitude roughly halves."),
    ]
    for col in ALPHA_COLS:
        comparisons.append((f"{col} AI", published_ai[col], table_stats[col]["ai"], "implementation",
                            "Mean squared deviations about the overall mean, per Equation 5, replacing subgroup sample variances."))
    pd.DataFrame(comparisons, columns=["metric", "published_4d21c69", "corrected", "stage", "note"]).to_csv(
        args.output_dir / "before_after_results.csv", index=False
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
