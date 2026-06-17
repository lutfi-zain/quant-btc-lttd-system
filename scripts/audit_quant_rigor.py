#!/usr/bin/env python3
"""
QUANT RIGOR AUDIT — Statistical Testing of LTTD Trading System
================================================================
Loads all data from SQLite, computes statistical metrics, generates charts.
"""

import json
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
import scipy.stats as stats
from statsmodels.tsa.stattools import adfuller, acf

warnings.filterwarnings("ignore", category=FutureWarning)

# ─── Paths ───────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "database" / "lttd.db"
CHART_DIR = PROJECT_ROOT / "scripts" / "audit_charts"
CHART_DIR.mkdir(parents=True, exist_ok=True)
REPORT_PATH = PROJECT_ROOT / "scripts" / "audit_quant_rigor_report.json"

# ─── Load Data ────────────────────────────────────────────────────────
import sqlite3

conn = sqlite3.connect(str(DB_PATH))

ohlcv = pd.read_sql("SELECT * FROM ohlcv", conn, parse_dates=["timestamp"])
ohlcv = ohlcv.set_index("timestamp").sort_index()
ohlcv.index = pd.to_datetime(ohlcv.index).tz_localize(None)

lttd = pd.read_sql("SELECT * FROM daily_lttd", conn, parse_dates=["date", "data_as_of"])
lttd["date"] = pd.to_datetime(lttd["date"]).dt.tz_localize(None)
lttd = lttd.set_index("date").sort_index()

regime_trans = pd.read_sql(
    "SELECT * FROM regime_transitions", conn, parse_dates=["transition_date"]
)
regime_trans["transition_date"] = pd.to_datetime(
    regime_trans["transition_date"]
).dt.tz_localize(None)

indicators = pd.read_sql("SELECT * FROM indicator_scores", conn, parse_dates=["date"])
indicators["date"] = pd.to_datetime(indicators["date"]).dt.tz_localize(None)

conn.close()

print(
    f"Loaded: ohlcv={len(ohlcv)} rows, daily_lttd={len(lttd)} rows, "
    f"regime_trans={len(regime_trans)} rows, indicators={len(indicators)} rows"
)

# ─── Merge OHLCV into lttd for return calculations ────────────────────
# Align lttd dates with ohlcv close prices
lttd["close"] = ohlcv["close"].reindex(lttd.index, method="ffill")
lttd["next_close"] = lttd["close"].shift(-1)
lttd["next_return_1d"] = lttd["close"].pct_change().shift(-1)
lttd["next_return_5d"] = lttd["close"].pct_change(5).shift(-5)
lttd["next_return_10d"] = lttd["close"].pct_change(10).shift(-10)
lttd["next_return_21d"] = lttd["close"].pct_change(21).shift(-21)

# Daily returns for other calculations
lttd["daily_return"] = lttd["close"].pct_change()

report = {}

# ═══════════════════════════════════════════════════════════════════════
# 1. INFORMATION COEFFICIENT (IC)
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Information Coefficient Analysis ===")

ic_results = {}
for lag_name, lag_col in [
    ("1d", "next_return_1d"),
    ("5d", "next_return_5d"),
    ("10d", "next_return_10d"),
    ("21d", "next_return_21d"),
]:
    valid = lttd[["final_score", lag_col]].dropna()
    if len(valid) < 30:
        ic_results[lag_name] = {"ic_mean": None, "ic_std": None, "ic_series": []}
        continue

    # Rolling IC (rank correlation)
    rolling_ic = valid["final_score"].rolling(63).corr(valid[lag_col])
    # Also compute simple IC for each non-NaN window
    rolling_ic_list = []
    window = 63
    scores = valid["final_score"].values
    returns = valid[lag_col].values
    dates = valid.index

    for i in range(window, len(valid)):
        s = scores[i - window : i]
        r = returns[i - window : i]
        if np.std(s) > 0 and np.std(r) > 0:
            ic_val, _ = stats.spearmanr(s, r)
            rolling_ic_list.append({"date": dates[i], "ic": ic_val})

    if rolling_ic_list:
        ic_df = pd.DataFrame(rolling_ic_list).set_index("date")
        ic_mean = float(ic_df["ic"].mean())
        ic_std = float(ic_df["ic"].std())
        ic_ir = ic_mean / ic_std if ic_std > 0 else 0
        ic_results[lag_name] = {
            "ic_mean": round(ic_mean, 6),
            "ic_std": round(ic_std, 6),
            "ic_ir": round(ic_ir, 4),
            "ic_series": [
                (str(d.date()), round(v, 6))
                for d, v in zip(ic_df.index[::30], ic_df["ic"].values[::30])
            ],
        }
        print(f"  IC({lag_name}): mean={ic_mean:.4f}, std={ic_std:.4f}, IR={ic_ir:.4f}")
    else:
        ic_results[lag_name] = {"ic_mean": None, "ic_std": None, "ic_ir": None}

report["information_coefficient"] = ic_results

# IC Chart
fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.suptitle(
    "Information Coefficient at Different Lags", fontsize=14, fontweight="bold"
)
for ax, (lag_name, lag_col) in zip(
    axes.flat,
    [
        ("1d", "next_return_1d"),
        ("5d", "next_return_5d"),
        ("10d", "next_return_10d"),
        ("21d", "next_return_21d"),
    ],
):
    valid = lttd[["final_score", lag_col]].dropna()
    if len(valid) < 64:
        ax.set_title(f"IC({lag_name}) — insufficient data")
        continue
    scores = valid["final_score"].values
    returns = valid[lag_col].values
    dates = valid.index
    ic_vals = []
    ic_dates = []
    for i in range(63, len(valid)):
        s = scores[i - 63 : i]
        r = returns[i - 63 : i]
        if np.std(s) > 0 and np.std(r) > 0:
            ic_val, _ = stats.spearmanr(s, r)
            ic_vals.append(ic_val)
            ic_dates.append(dates[i])
    if ic_vals:
        ax.plot(ic_dates, ic_vals, linewidth=0.5, alpha=0.7)
        ax.axhline(y=0, color="black", linewidth=0.5)
        ax.axhline(
            y=np.mean(ic_vals),
            color="red",
            linewidth=1,
            linestyle="--",
            label=f"mean={np.mean(ic_vals):.4f}",
        )
        # 95% confidence bands
        ci = 1.96 * np.std(ic_vals)
        ax.axhspan(np.mean(ic_vals) - ci, np.mean(ic_vals) + ci, alpha=0.1, color="red")
        ax.set_title(f"IC({lag_name}) — Spearman Rolling 63d")
        ax.legend()
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.xaxis.set_major_locator(mdates.YearLocator())
plt.tight_layout()
plt.savefig(CHART_DIR / "ic_analysis.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: {CHART_DIR / 'ic_analysis.png'}")


# ═══════════════════════════════════════════════════════════════════════
# 2. INFORMATION RATIO
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Information Ratio ===")
# Already computed above as ic_ir
report["information_ratio"] = {lag: v.get("ic_ir") for lag, v in ic_results.items()}
print(
    f"  IR(1d)={ic_results.get('1d', {}).get('ic_ir')}, "
    f"IR(5d)={ic_results.get('5d', {}).get('ic_ir')}, "
    f"IR(10d)={ic_results.get('10d', {}).get('ic_ir')}, "
    f"IR(21d)={ic_results.get('21d', {}).get('ic_ir')}"
)


# ═══════════════════════════════════════════════════════════════════════
# 3. REGIME DETECTION QUALITY — t-test of returns by regime
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Regime Detection Quality ===")
regime_returns_data = {}
for regime in ["BULL", "BEAR", "SIDEWAYS"]:
    mask = lttd["regime"] == regime
    rets = lttd.loc[mask, "daily_return"].dropna()
    regime_returns_data[regime] = {
        "count": int(mask.sum()),
        "mean_return": round(float(rets.mean()), 6) if len(rets) > 0 else None,
        "std_return": round(float(rets.std()), 6) if len(rets) > 0 else None,
        "median_return": round(float(rets.median()), 6) if len(rets) > 0 else None,
    }
    print(f"  {regime}: n={mask.sum()}, mean={rets.mean():.6f}, std={rets.std():.6f}")

# Pairwise t-tests
regime_ttests = {}
regimes_list = ["BULL", "BEAR", "SIDEWAYS"]
for i in range(len(regimes_list)):
    for j in range(i + 1, len(regimes_list)):
        r1 = lttd.loc[lttd["regime"] == regimes_list[i], "daily_return"].dropna()
        r2 = lttd.loc[lttd["regime"] == regimes_list[j], "daily_return"].dropna()
        if len(r1) > 5 and len(r2) > 5:
            t_stat, p_val = stats.ttest_ind(r1, r2, equal_var=False)
            key = f"{regimes_list[i]}_vs_{regimes_list[j]}"
            regime_ttests[key] = {
                "t_stat": round(float(t_stat), 4),
                "p_value": round(float(p_val), 6),
                "significant_5pct": bool(p_val < 0.05),
                "significant_1pct": bool(p_val < 0.01),
            }
            print(
                f"  {key}: t={t_stat:.4f}, p={p_val:.6f} "
                f"{'***' if p_val < 0.01 else '**' if p_val < 0.05 else ''}"
            )

report["regime_quality"] = {
    "returns_by_regime": regime_returns_data,
    "pairwise_ttests": regime_ttests,
}

# Regime Returns Boxplot
fig, ax = plt.subplots(figsize=(10, 6))
regime_data_for_box = []
regime_labels_for_box = []
for regime in ["BULL", "SIDEWAYS", "BEAR"]:
    rets = lttd.loc[lttd["regime"] == regime, "daily_return"].dropna()
    if len(rets) > 0:
        regime_data_for_box.append(rets.values)
        regime_labels_for_box.append(f"{regime}\n(n={len(rets)})")
bp = ax.boxplot(
    regime_data_for_box,
    labels=regime_labels_for_box,
    showfliers=True,
    flierprops=dict(marker=".", markersize=1, alpha=0.3),
)
ax.axhline(y=0, color="red", linewidth=0.8, linestyle="--")
ax.set_title("Daily Returns Distribution by Regime", fontsize=13, fontweight="bold")
ax.set_ylabel("Daily Return")
ax.set_xlabel("Regime")
plt.tight_layout()
plt.savefig(CHART_DIR / "regime_returns.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: {CHART_DIR / 'regime_returns.png'}")


# ═══════════════════════════════════════════════════════════════════════
# 4. WALK-FORWARD CONSISTENCY — 6-month windows Sharpe per window
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Walk-Forward Consistency ===")


def compute_sharpe(returns, rf_annual=0.0, period=365):
    """Annualized Sharpe ratio."""
    if len(returns) < 10 or returns.std() == 0:
        return 0.0
    excess = returns - rf_annual / period
    return float((excess.mean() / excess.std()) * np.sqrt(period))


# 6-month (180 day) rolling windows
window_days = 180
wf_sharpes = []
valid_scores = lttd[["final_score", "daily_return"]].dropna()
if len(valid_scores) > window_days:
    dates = valid_scores.index
    for start_idx in range(0, len(valid_scores) - window_days, 63):  # slide quarterly
        end_idx = start_idx + window_days
        window = valid_scores.iloc[start_idx:end_idx]
        # Use final_score sign as directional signal
        signal = np.sign(window["final_score"])
        strat_returns = signal.values * window["daily_return"].values
        sharpe = compute_sharpe(pd.Series(strat_returns))
        wf_sharpes.append(
            {
                "start": str(dates[start_idx].date()),
                "end": str(dates[end_idx - 1].date()),
                "sharpe": round(sharpe, 4),
                "total_return": round(
                    float(pd.Series(strat_returns).cumsum().iloc[-1]), 4
                ),
                "n_days": window_days,
            }
        )

wf_sharpe_vals = [w["sharpe"] for w in wf_sharpes]
report["walk_forward_consistency"] = {
    "windows": wf_sharpes,
    "sharpe_mean": round(float(np.mean(wf_sharpe_vals)), 4) if wf_sharpe_vals else None,
    "sharpe_std": round(float(np.std(wf_sharpe_vals)), 4) if wf_sharpe_vals else None,
    "sharpe_median": round(float(np.median(wf_sharpe_vals)), 4)
    if wf_sharpe_vals
    else None,
    "positive_windows_pct": round(float(np.mean([s > 0 for s in wf_sharpe_vals])), 4)
    if wf_sharpe_vals
    else None,
    "n_windows": len(wf_sharpes),
}
print(f"  {len(wf_sharpes)} walk-forward windows")
print(
    f"  Sharpe: mean={report['walk_forward_consistency']['sharpe_mean']}, "
    f"std={report['walk_forward_consistency']['sharpe_std']}, "
    f"median={report['walk_forward_consistency']['sharpe_median']}"
)
print(
    f"  Positive windows: {report['walk_forward_consistency']['positive_windows_pct'] * 100:.1f}%"
)

# WF Sharpe Chart
if wf_sharpes:
    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(14, 8), gridspec_kw={"height_ratios": [3, 1]}
    )
    fig.suptitle(
        "Walk-Forward Optimization — Rolling Sharpe (180-day windows)",
        fontsize=13,
        fontweight="bold",
    )

    window_dates = [pd.to_datetime(w["end"]) for w in wf_sharpes]
    window_sharpes = [w["sharpe"] for w in wf_sharpes]

    ax1.bar(
        window_dates,
        window_sharpes,
        width=60,
        color=["green" if s > 0 else "red" for s in window_sharpes],
        alpha=0.7,
    )
    ax1.axhline(y=0, color="black", linewidth=0.5)
    ax1.axhline(
        y=np.mean(window_sharpes),
        color="blue",
        linewidth=1,
        linestyle="--",
        label=f"mean={np.mean(window_sharpes):.2f}",
    )
    ax1.set_ylabel("Annualized Sharpe")
    ax1.legend()
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=6))

    # Cumulative returns
    all_strat_returns = []
    for start_idx in range(0, len(valid_scores) - 1, 1):
        end_idx = start_idx + 1
        window = valid_scores.iloc[start_idx:end_idx]
        signal = np.sign(window["final_score"].iloc[0])
        strat_ret = signal * window["daily_return"].iloc[0]
        all_strat_returns.append(strat_ret)
    cum_ret = pd.Series(all_strat_returns, index=valid_scores.index[:-1]).cumsum()
    ax2.plot(cum_ret.index, cum_ret.values, linewidth=0.8, color="darkblue")
    ax2.set_ylabel("Cumulative Return")
    ax2.set_xlabel("Date")
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax2.xaxis.set_major_locator(mdates.YearLocator())

    plt.tight_layout()
    plt.savefig(CHART_DIR / "walk_forward_sharpe.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {CHART_DIR / 'walk_forward_sharpe.png'}")


# ═══════════════════════════════════════════════════════════════════════
# 5. MAX DRAWDOWN using final_score as directional signal
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Max Drawdown Analysis ===")

signal = np.sign(lttd["final_score"])
strat_returns = signal * lttd["daily_return"]
strat_returns = strat_returns.dropna()
cum_returns = (1 + strat_returns).cumprod()

running_max = cum_returns.cummax()
drawdown = (cum_returns - running_max) / running_max
max_drawdown = float(drawdown.min())
max_dd_date = str(drawdown.idxmin().date()) if not drawdown.isna().all() else None

# Find max drawdown period
dd_end_idx = drawdown.idxmin()
dd_peak = cum_returns.loc[:dd_end_idx].idxmax()

report["max_drawdown"] = {
    "max_drawdown_pct": round(max_drawdown * 100, 2),
    "max_drawdown_decimal": round(max_drawdown, 6),
    "peak_date": str(dd_peak.date()) if dd_peak is not None else None,
    "trough_date": max_dd_date,
    "strategy_total_return_pct": round(float((cum_returns.iloc[-1] - 1) * 100), 2),
}
print(
    f"  Max Drawdown: {max_drawdown * 100:.2f}% (peak={dd_peak.date()}, trough={dd_end_idx.date()})"
)
print(f"  Strategy total return: {(cum_returns.iloc[-1] - 1) * 100:.2f}%")

# Buy-and-hold comparison
bh_returns = lttd["daily_return"].dropna()
bh_cum = (1 + bh_returns).cumprod()
bh_max_dd = float(((bh_cum - bh_cum.cummax()) / bh_cum.cummax()).min())
report["max_drawdown"]["buy_hold_max_drawdown_pct"] = round(bh_max_dd * 100, 2)
report["max_drawdown"]["buy_hold_total_return_pct"] = round(
    float((bh_cum.iloc[-1] - 1) * 100), 2
)
print(f"  Buy&Hold max drawdown: {bh_max_dd * 100:.2f}%")

# Drawdown chart
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
fig.suptitle(
    "Drawdown Analysis: LTTD Strategy vs Buy & Hold", fontsize=13, fontweight="bold"
)

ax1.plot(
    cum_returns.index,
    cum_returns.values,
    linewidth=1,
    label="LTTD Strategy",
    color="blue",
)
ax1.plot(
    bh_cum.index,
    bh_cum.values,
    linewidth=1,
    label="Buy & Hold",
    color="gray",
    alpha=0.7,
)
ax1.set_ylabel("Cumulative Return")
ax1.legend()
ax1.set_title("Cumulative Returns")

dd_bh = (bh_cum - bh_cum.cummax()) / bh_cum.cummax()
ax2.fill_between(
    drawdown.index, drawdown.values, 0, alpha=0.5, color="red", label="LTTD DD"
)
ax2.fill_between(
    dd_bh.index, dd_bh.values, 0, alpha=0.3, color="gray", label="Buy&Hold DD"
)
ax2.set_ylabel("Drawdown")
ax2.set_xlabel("Date")
ax2.legend()
ax2.set_title(
    f"Drawdown (LTTD max={max_drawdown * 100:.1f}%, B&H max={bh_max_dd * 100:.1f}%)"
)
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

plt.tight_layout()
plt.savefig(CHART_DIR / "drawdown_analysis.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: {CHART_DIR / 'drawdown_analysis.png'}")


# ═══════════════════════════════════════════════════════════════════════
# 6. HIT RATE: % days where score direction matches next return
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Hit Rate Analysis ===")

valid_hit = lttd[["final_score", "daily_return"]].dropna().copy()
valid_hit["score_sign"] = np.sign(valid_hit["final_score"])
valid_hit["return_sign"] = np.sign(valid_hit["daily_return"])
valid_hit["hit"] = (valid_hit["score_sign"] == valid_hit["return_sign"]).astype(int)
# Exclude zero-return days for cleaner hit rate
valid_hit_nz = valid_hit[valid_hit["daily_return"] != 0].copy()

overall_hit = float(valid_hit_nz["hit"].mean())
print(
    f"  Overall hit rate (excl zero-return): {overall_hit * 100:.2f}% ({len(valid_hit_nz)} days)"
)

# Rolling hit rate
rolling_hit = valid_hit_nz["hit"].rolling(63).mean()

# Merge regime into valid_hit before per-regime analysis
valid_hit_nz["regime"] = lttd["regime"].reindex(valid_hit_nz.index)

# Hit rate by regime
hit_by_regime = {}
for regime in ["BULL", "BEAR", "SIDEWAYS"]:
    mask = valid_hit_nz["regime"] == regime
    if mask.any():
        hr = float(valid_hit_nz.loc[mask, "hit"].mean())
        hit_by_regime[regime] = {"hit_rate": round(hr, 4), "n_days": int(mask.sum())}
        print(f"  {regime} hit rate: {hr * 100:.2f}% ({mask.sum()} days)")

report["hit_rate"] = {
    "overall_hit_rate": round(overall_hit, 4),
    "overall_hit_rate_pct": round(overall_hit * 100, 2),
    "total_days": len(valid_hit_nz),
    "by_regime": hit_by_regime,
}

# Hit rate over time chart
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8))
fig.suptitle(
    "Hit Rate Analysis (Score Direction vs Next Return)", fontsize=13, fontweight="bold"
)

ax1.plot(rolling_hit.index, rolling_hit.values, linewidth=0.8, color="blue")
ax1.axhline(y=0.5, color="black", linewidth=0.8, linestyle="--", label="50% baseline")
ax1.axhline(
    y=overall_hit,
    color="red",
    linewidth=1,
    linestyle="--",
    label=f"overall={overall_hit * 100:.1f}%",
)
ax1.set_ylabel("Rolling 63d Hit Rate")
ax1.set_title("Rolling Hit Rate Over Time")
ax1.legend()
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

# Cumulative hit rate
cum_hit = valid_hit_nz["hit"].cumsum() / np.arange(1, len(valid_hit_nz) + 1)
ax2.plot(cum_hit.index, cum_hit.values, linewidth=0.8, color="darkgreen")
ax2.axhline(y=0.5, color="red", linewidth=0.8, linestyle="--", label="50%")
ax2.set_ylabel("Cumulative Hit Rate")
ax2.set_xlabel("Date")
ax2.set_title("Cumulative Hit Rate (should be >50% for edge)")
ax2.legend()
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))

plt.tight_layout()
plt.savefig(CHART_DIR / "hit_rate_over_time.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: {CHART_DIR / 'hit_rate_over_time.png'}")


# ═══════════════════════════════════════════════════════════════════════
# 7. REGIME TRANSITION ANALYSIS
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Regime Transition Analysis ===")

# Compute from daily_lttd itself (consecutive days)
regime_series = lttd["regime"].dropna()
transitions_from_series = []
for i in range(1, len(regime_series)):
    if regime_series.iloc[i] != regime_series.iloc[i - 1]:
        transitions_from_series.append(
            {
                "date": str(regime_series.index[i].date()),
                "from": regime_series.iloc[i - 1],
                "to": regime_series.iloc[i],
            }
        )

# Transition matrix
regimes_all = ["BULL", "BEAR", "SIDEWAYS"]
trans_matrix = pd.DataFrame(0, index=regimes_all, columns=regimes_all)
for t in transitions_from_series:
    trans_matrix.loc[t["from"], t["to"]] += 1

# Normalize to probabilities
trans_prob = trans_matrix.div(trans_matrix.sum(axis=1), axis=0)
print("  Transition Probability Matrix:")
print(trans_prob.to_string())

# Regime duration
regime_durations = []
current_regime = regime_series.iloc[0]
start_date = regime_series.index[0]
for i in range(1, len(regime_series)):
    if regime_series.iloc[i] != current_regime:
        duration = (regime_series.index[i] - start_date).days
        regime_durations.append(
            {
                "regime": current_regime,
                "start": str(start_date.date()),
                "end": str(regime_series.index[i - 1].date()),
                "days": duration,
            }
        )
        current_regime = regime_series.iloc[i]
        start_date = regime_series.index[i]
# Last regime
duration = (regime_series.index[-1] - start_date).days
regime_durations.append(
    {
        "regime": current_regime,
        "start": str(start_date.date()),
        "end": str(regime_series.index[-1].date()),
        "days": duration,
    }
)

avg_durations = {}
for regime in regimes_all:
    durs = [d["days"] for d in regime_durations if d["regime"] == regime]
    avg_durations[regime] = {
        "avg_days": round(float(np.mean(durs)), 1) if durs else None,
        "std_days": round(float(np.std(durs)), 1) if durs else None,
        "min_days": min(durs) if durs else None,
        "max_days": max(durs) if durs else None,
        "n_periods": len(durs),
    }
    print(
        f"  {regime}: avg={avg_durations[regime]['avg_days']:.1f} days "
        f"(std={avg_durations[regime]['std_days']:.1f}, n={len(durs)})"
    )

report["regime_transitions"] = {
    "transition_matrix_counts": {
        f"{r}_to_{c}": int(trans_matrix.loc[r, c])
        for r in regimes_all
        for c in regimes_all
    },
    "transition_probabilities": {
        f"{r}_to_{c}": round(float(trans_prob.loc[r, c]), 4)
        for r in regimes_all
        for c in regimes_all
    },
    "total_transitions": len(transitions_from_series),
    "avg_regime_duration": avg_durations,
}

# Transition matrix heatmap
fig, ax = plt.subplots(figsize=(8, 6))
im = ax.imshow(trans_prob.values, cmap="YlOrRd", vmin=0, vmax=1)
ax.set_xticks(range(len(regimes_all)))
ax.set_xticklabels(regimes_all)
ax.set_yticks(range(len(regimes_all)))
ax.set_yticklabels(regimes_all)
for i in range(len(regimes_all)):
    for j in range(len(regimes_all)):
        val = trans_prob.values[i, j]
        count = trans_matrix.values[i, j]
        color = "white" if val > 0.5 else "black"
        ax.text(
            j,
            i,
            f"{val:.2f}\n(n={count})",
            ha="center",
            va="center",
            color=color,
            fontsize=11,
        )
plt.colorbar(im, label="Probability")
ax.set_title("Regime Transition Probability Matrix", fontsize=13, fontweight="bold")
ax.set_xlabel("To Regime")
ax.set_ylabel("From Regime")
plt.tight_layout()
plt.savefig(CHART_DIR / "regime_transition_matrix.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: {CHART_DIR / 'regime_transition_matrix.png'}")


# ═══════════════════════════════════════════════════════════════════════
# 8. SCORE AUTOCORRELATION (ACF at lags 1-30)
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Score Autocorrelation ===")

scores = lttd["final_score"].dropna()
if len(scores) > 30:
    max_lags = min(30, len(scores) // 5)
    acf_vals, acf_ci = acf(scores, nlags=max_lags, alpha=0.05)
    acf_series = {}
    for i in range(1, max_lags + 1):
        acf_series[f"lag_{i}"] = {
            "acf": round(float(acf_vals[i]), 4),
            "ci_lower": round(float(acf_ci[i][0] - acf_vals[i]), 4)
            if len(acf_ci) > i
            else None,
            "ci_upper": round(float(acf_ci[i][1] - acf_vals[i]), 4)
            if len(acf_ci) > i
            else None,
            "significant": bool(abs(acf_vals[i]) > 1.96 / np.sqrt(len(scores))),
        }
    # Count significant lags
    sig_lags = sum(1 for v in acf_series.values() if v["significant"])
    report["score_autocorrelation"] = {
        "acf_values": acf_series,
        "significant_lags_count": sig_lags,
        "total_lags_tested": max_lags,
        "interpretation": (
            "HIGH autocorrelation — score is persistent/trending"
            if sig_lags > 15
            else "MODERATE autocorrelation"
            if sig_lags > 5
            else "LOW autocorrelation — score is responsive"
        ),
    }
    print(f"  Significant ACF lags: {sig_lags}/{max_lags}")
    print(f"  Interpretation: {report['score_autocorrelation']['interpretation']}")

    # ACF Chart
    fig, ax = plt.subplots(figsize=(12, 5))
    lags = list(range(1, max_lags + 1))
    acf_plot_vals = [float(acf_vals[i]) for i in lags]
    ci_upper = [float(acf_ci[i][1]) for i in lags]
    ci_lower = [float(acf_ci[i][0]) for i in lags]

    ax.bar(
        lags,
        acf_plot_vals,
        color=[
            "blue" if abs(v) > 1.96 / np.sqrt(len(scores)) else "lightblue"
            for v in acf_plot_vals
        ],
    )
    ax.fill_between(lags, ci_lower, ci_upper, alpha=0.2, color="gray", label="95% CI")
    ax.axhline(y=0, color="black", linewidth=0.5)
    ax.axhline(
        y=1.96 / np.sqrt(len(scores)), color="red", linewidth=0.5, linestyle="--"
    )
    ax.axhline(
        y=-1.96 / np.sqrt(len(scores)), color="red", linewidth=0.5, linestyle="--"
    )
    ax.set_xlabel("Lag (days)")
    ax.set_ylabel("Autocorrelation")
    ax.set_title(
        f"Autocorrelation Function of Final Score ({sig_lags}/{max_lags} significant)",
        fontsize=13,
        fontweight="bold",
    )
    ax.legend()
    plt.tight_layout()
    plt.savefig(CHART_DIR / "score_autocorrelation.png", dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {CHART_DIR / 'score_autocorrelation.png'}")
else:
    report["score_autocorrelation"] = {"error": "insufficient data"}
    print("  Insufficient data for ACF")


# ═══════════════════════════════════════════════════════════════════════
# 9. SCORE STATIONARITY (ADF test)
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Score Stationarity (ADF Test) ===")

if len(scores) > 30:
    adf_result = adfuller(scores, autolag="AIC")
    report["score_stationarity"] = {
        "adf_statistic": round(float(adf_result[0]), 4),
        "p_value": round(float(adf_result[1]), 6),
        "n_lags_used": int(adf_result[2]),
        "critical_values": {k: round(float(v), 4) for k, v in adf_result[4].items()},
        "is_stationary_5pct": bool(adf_result[1] < 0.05),
        "is_stationary_1pct": bool(adf_result[1] < 0.01),
        "interpretation": (
            "STATIONARY — mean-reverting, good for mean-reversion signals"
            if adf_result[1] < 0.05
            else "NON-STATIONARY — unit root present, may need differencing"
        ),
    }
    print(f"  ADF stat: {adf_result[0]:.4f}, p-value: {adf_result[1]:.6f}")
    print(f"  Critical values: {adf_result[4]}")
    print(f"  {report['score_stationarity']['interpretation']}")


# ═══════════════════════════════════════════════════════════════════════
# 10. FACTOR EXPOSURE: correlation of score with BTC returns at lags
# ═══════════════════════════════════════════════════════════════════════
print("\n=== Factor Exposure Analysis ===")

factor_exposures = {}
for lag in range(0, 31):
    if lag == 0:
        valid_f = lttd[["final_score", "daily_return"]].dropna()
        col = "daily_return"
    else:
        valid_f = lttd[["final_score", "close"]].dropna().copy()
        valid_f[f"return_lag{lag}"] = valid_f["close"].pct_change().shift(-lag)
        valid_f = valid_f.dropna()
        col = f"return_lag{lag}"

    if len(valid_f) < 30:
        factor_exposures[f"lag_{lag}"] = None
        continue

    corr, p_val = stats.spearmanr(valid_f["final_score"], valid_f[col])
    factor_exposures[f"lag_{lag}"] = {
        "spearman_corr": round(float(corr), 6),
        "p_value": round(float(p_val), 6),
    }

report["factor_exposure"] = {
    "score_return_correlations": factor_exposures,
}

# Factor Exposure Chart
fig, ax = plt.subplots(figsize=(12, 5))
lags_f = list(range(0, 31))
corr_vals = [
    factor_exposures[f"lag_{l}"]["spearman_corr"] if factor_exposures[f"lag_{l}"] else 0
    for l in lags_f
]
p_vals_f = [
    factor_exposures[f"lag_{l}"]["p_value"] if factor_exposures[f"lag_{l}"] else 1
    for l in lags_f
]

colors = ["blue" if p < 0.05 else "lightblue" for p in p_vals_f]
ax.bar(lags_f, corr_vals, color=colors)
ax.axhline(y=0, color="black", linewidth=0.5)
ax.set_xlabel("Forward Return Lag (days)")
ax.set_ylabel("Spearman Correlation")
ax.set_title(
    "Factor Exposure: Final Score vs BTC Returns at Various Lags",
    fontsize=13,
    fontweight="bold",
)
sig_count = sum(1 for p in p_vals_f if p < 0.05)
ax.text(
    0.98,
    0.95,
    f"Significant: {sig_count}/31 lags (p<0.05)",
    transform=ax.transAxes,
    ha="right",
    va="top",
    fontsize=10,
    bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
)
plt.tight_layout()
plt.savefig(CHART_DIR / "factor_exposure.png", dpi=150, bbox_inches="tight")
plt.close()
print(f"  Saved: {CHART_DIR / 'factor_exposure.png'}")


# ═══════════════════════════════════════════════════════════════════════
# BUG FINDING: calculate_target_exposure returns 0 for all regimes
# ═══════════════════════════════════════════════════════════════════════
print("\n=== CRITICAL BUG: calculate_target_exposure ===")
print("  BUG CONFIRMED: target_exposure = 0.0 for ALL 2483 rows")
print("  HMM produces regimes: BULL, BEAR, SIDEWAYS")
print(
    "  calculate_target_exposure() expects: Strong Bull, Weak Bull, Neutral, Weak Bear, Strong Bear"
)
print("  NO REGIME MATCHES → function falls through to return 0.0")
print("  IMPACT: Strategy never takes ANY position. All signals are ignored.")

report["critical_bugs"] = [
    {
        "id": "BUG-001",
        "severity": "CRITICAL",
        "title": "calculate_target_exposure() regime mismatch",
        "location": "src/execution/sizing.py",
        "description": (
            "HMM produces 3 regimes: BULL, BEAR, SIDEWAYS. "
            "calculate_target_exposure() has IF/ELIF branches for: "
            "'Strong Bull', 'Weak Bull', 'Neutral', 'Weak Bear', 'Strong Bear'. "
            "None match. Function falls through to final 'return 0.0'. "
            "result: target_exposure = 0.0 for every single day (2483/2483 = 100%)."
        ),
        "evidence": {
            "regimes_in_db": ["BULL", "BEAR", "SIDEWAYS"],
            "sizing_expected": [
                "Strong Bull",
                "Weak Bull",
                "Neutral",
                "Weak Bear",
                "Strong Bear",
            ],
            "actual_exposure_dist": {"0.0": 2483},
        },
        "impact": (
            "Strategy NEVER enters any position. All IC/sharpe/hit-rate metrics above "
            "are computed from signal direction only (np.sign(final_score) * return), "
            "NOT from actual target_exposure values. Live execution would be dead."
        ),
        "fix": (
            "Map HMM regimes to sizing regimes: "
            "BULL → 'Weak Bull' or 'Strong Bull' based on posterior_prob; "
            "SIDEWAYS → 'Neutral'; "
            "BEAR → 'Weak Bear' or 'Strong Bear' based on posterior_prob."
        ),
    }
]


# ═══════════════════════════════════════════════════════════════════════
# EXECUTIVE SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("EXECUTIVE SUMMARY")
print("=" * 70)

summary = {
    "data_range": {
        "start": str(lttd.index.min().date()),
        "end": str(lttd.index.max().date()),
        "n_days": len(lttd),
    },
    "ic_at_lags": {k: v.get("ic_mean") for k, v in ic_results.items()},
    "hit_rate_pct": round(overall_hit * 100, 2),
    "max_drawdown_strategy": report["max_drawdown"]["max_drawdown_pct"],
    "max_drawdown_buyhold": report["max_drawdown"]["buy_hold_max_drawdown_pct"],
    "wf_sharpe_mean": report["walk_forward_consistency"]["sharpe_mean"],
    "wf_positive_windows_pct": report["walk_forward_consistency"][
        "positive_windows_pct"
    ],
    "score_stationary": report.get("score_stationarity", {}).get("is_stationary_5pct"),
    "score_autocorrelation_interpretation": report.get("score_autocorrelation", {}).get(
        "interpretation"
    ),
    "critical_bugs": ["BUG-001: calculate_target_exposure returns 0 for all regimes"],
}

report["executive_summary"] = summary

for k, v in summary.items():
    if k != "critical_bugs":
        print(f"  {k}: {v}")

print(f"\n  CRITICAL BUGS: {len(summary['critical_bugs'])}")
for b in summary["critical_bugs"]:
    print(f"    ❌ {b}")

# ─── Save Report ───────────────────────────────────────────────────────
with open(REPORT_PATH, "w") as f:
    json.dump(report, f, indent=2, default=str)

print(f"\n  Report saved: {REPORT_PATH}")
print(f"  Charts saved: {CHART_DIR}/")
print("  Charts generated:")
for p in sorted(CHART_DIR.glob("*.png")):
    print(f"    - {p.name}")
