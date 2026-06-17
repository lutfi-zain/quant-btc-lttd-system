#!/usr/bin/env python3
"""
DATA QUALITY AUDIT — Statistical Analysis of LTTD System
=========================================================
Loads data from SQLite, computes per-indicator stats, cross-correlation,
VIF trends, PCA variance, regime analysis, and generates charts + JSON report.
"""

import json
import sqlite3 as _sqlite3
import warnings
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats as sp_stats
from scipy.linalg import inv
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.stattools import adfuller

warnings.filterwarnings("ignore", category=FutureWarning)

# ── Paths ───────────────────────────────────────────────────────────────────
ROOT = Path("/run/media/lutfizain/Work/Projects/1.WORKING/lttd-worktree-01-pi")
DB_PATH = ROOT / "database" / "lttd.db"
CHART_DIR = ROOT / "scripts" / "audit_charts"
REPORT_PATH = ROOT / "scripts" / "audit_data_quality_report.json"

CHART_DIR.mkdir(parents=True, exist_ok=True)

# ── Indicators ──────────────────────────────────────────────────────────────
INDICATORS = [
    "FDI",
    "AdvancedStochastic",
    "KalmanRSI",
    "FourierSupertrend",
    "TrendStrengthIndex",
    "QuantileDEMA",
]
REGIMES = ["BULL", "BEAR", "SIDEWAYS"]

# ── 1. LOAD DATA ────────────────────────────────────────────────────────────
print("Loading data from SQLite...")
_conn = _sqlite3.connect(str(DB_PATH))
daily = pd.read_sql("SELECT * FROM daily_lttd", _conn)
scores = pd.read_sql("SELECT * FROM indicator_scores", _conn)
pca_raw = pd.read_sql("SELECT * FROM pca_components", _conn)
transitions = pd.read_sql("SELECT * FROM regime_transitions", _conn)
_conn.close()

daily["date"] = pd.to_datetime(daily["date"])
scores["date"] = pd.to_datetime(scores["date"])
pca_raw["date"] = pd.to_datetime(pca_raw["date"])

# Pivot indicator scores: date x indicator_name -> score
pivot = scores.pivot_table(index="date", columns="indicator_name", values="score")
pivot = pivot[INDICATORS].dropna()
print(f"  Indicator matrix: {pivot.shape[0]} dates x {pivot.shape[1]} indicators")

# Pivot PCA components (filter to PC* columns only — table also has VIF_* and pca_variance_explained)
pca_pc_rows = pca_raw[pca_raw["component_name"].str.startswith("PC")]
pca_pivot = pca_pc_rows.pivot_table(
    index="date", columns="component_name", values="value"
)
pca_pivot = pca_pivot.sort_index()
pca_cols = sorted(pca_pivot.columns.tolist(), key=lambda x: int(x.replace("PC", "")))
pca_pivot = pca_pivot[pca_cols]
print(f"  PCA matrix: {pca_pivot.shape[0]} dates x {pca_pivot.shape[1]} components")

# ── 2. PER-INDICATOR STATISTICS ─────────────────────────────────────────────
print("\nComputing per-indicator statistics...")


def indicator_stats(series: pd.Series) -> dict:
    """Compute distribution, stationarity, autocorrelation, normality stats."""
    vals = series.dropna().to_numpy(dtype=float)
    n = len(vals)
    if n < 20:
        return {"error": "insufficient_data", "n": n}

    # Distribution
    mean_val = float(np.mean(vals))
    std_val = float(np.std(vals, ddof=1))
    skew_val = float(sp_stats.skew(vals))
    kurt_val = float(sp_stats.kurtosis(vals))

    # Jarque-Bera normality test
    jb_stat, jb_pval = sp_stats.jarque_bera(vals)

    # Shapiro-Wilk normality (max 5000 samples for performance)
    sample = vals[:5000]
    sw_stat, sw_pval = sp_stats.shapiro(sample)

    # ADF stationarity test
    try:
        adf_result = adfuller(vals, maxlag=21, autolag="AIC")
        adf_stat = float(adf_result[0])
        adf_pval = float(adf_result[1])
        adf_lags = int(adf_result[2])
    except Exception:
        adf_stat = float("nan")
        adf_pval = float("nan")
        adf_lags = 0

    # Autocorrelation at key lags
    acf_vals: dict[str, float | None] = {}
    for lag in [1, 5, 10, 21]:
        if n > lag + 1:
            c = float(np.corrcoef(vals[:-lag], vals[lag:])[0, 1])
            acf_vals[f"lag_{lag}"] = round(c, 4) if not np.isnan(c) else None
        else:
            acf_vals[f"lag_{lag}"] = None

    return {
        "n": n,
        "mean": round(mean_val, 6),
        "std": round(std_val, 6),
        "skewness": round(skew_val, 4),
        "kurtosis": round(kurt_val, 4),
        "jarque_bera_stat": round(float(jb_stat), 4),
        "jarque_bera_pval": round(float(jb_pval), 6),
        "shapiro_wilk_stat": round(float(sw_stat), 4),
        "shapiro_wilk_pval": round(float(sw_pval), 6),
        "adf_stat": round(adf_stat, 4),
        "adf_pval": round(adf_pval, 6),
        "adf_lags_used": adf_lags,
        "acf": acf_vals,
    }


ind_stats: dict[str, dict] = {}
for ind in INDICATORS:
    if ind in pivot.columns:
        ind_stats[ind] = indicator_stats(pivot[ind])
        print(
            f"  {ind}: mean={ind_stats[ind]['mean']:.4f}, "
            f"adf_p={ind_stats[ind]['adf_pval']:.4f}, "
            f"skew={ind_stats[ind]['skewness']:.2f}"
        )

# ── 3. CROSS-INDICATOR CORRELATION ─────────────────────────────────────────
print("\nComputing cross-indicator correlations...")
pearson_corr = pivot.corr(method="pearson")
spearman_corr = pivot.corr(method="spearman")

pearson_dict = pearson_corr.round(4).to_dict()
spearman_dict = spearman_corr.round(4).to_dict()

# ── 4. VIF OVER TIME (rolling 252-day windows) ─────────────────────────────
print("Computing VIF over time (rolling 252-day windows)...")
VIF_WINDOW = 252
vif_series_list: list[dict] = []

for end_idx in range(VIF_WINDOW, len(pivot)):
    window = pivot.iloc[end_idx - VIF_WINDOW : end_idx]
    valid_cols = [c for c in INDICATORS if window[c].std() > 0]
    if len(valid_cols) < 2:
        row: dict = {"date": pivot.index[end_idx]}
        for c in INDICATORS:
            row[c] = None
        vif_series_list.append(row)
        continue

    corr_mat = window[valid_cols].corr().fillna(0.0)
    eps = 1e-10
    corr_adj = corr_mat.values + np.eye(corr_mat.shape[0]) * eps
    try:
        corr_inv = inv(corr_adj)
        diag = np.diag(corr_inv)
    except Exception:
        diag = np.full(corr_mat.shape[0], float("nan"))

    row = {"date": pivot.index[end_idx]}
    for i, c in enumerate(valid_cols):
        row[c] = round(float(diag[i]), 4)
    for c in INDICATORS:
        if c not in valid_cols:
            row[c] = None
    vif_series_list.append(row)

vif_df = pd.DataFrame(vif_series_list).set_index("date")
print(f"  VIF computed for {len(vif_df)} rolling windows")

# ── 5. PCA VARIANCE EXPLAINED OVER TIME (rolling 252-day) ──────────────────
print("Computing PCA variance explained over time...")

pca_var_list: list[dict] = []
for end_idx in range(VIF_WINDOW, len(pivot)):
    window = pivot.iloc[end_idx - VIF_WINDOW : end_idx]
    valid_cols = [c for c in INDICATORS if window[c].std() > 0]
    if len(valid_cols) < 2:
        pca_var_list.append({"date": pivot.index[end_idx]})
        continue

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(window[valid_cols])
    pca_full = PCA(random_state=42)
    pca_full.fit(X_scaled)

    row = {"date": pivot.index[end_idx], "n_indicators": len(valid_cols)}
    cum_var = np.cumsum(pca_full.explained_variance_ratio_)
    for i in range(len(valid_cols)):
        row[f"PC{i + 1}_cumvar"] = round(float(cum_var[i]), 4)
        row[f"PC{i + 1}_var"] = round(float(pca_full.explained_variance_ratio_[i]), 4)
    pca_var_list.append(row)

pca_var_df = pd.DataFrame(pca_var_list).set_index("date")
print(f"  PCA variance computed for {len(pca_var_df)} windows")

# ── 6. REGIME DISTRIBUTION & TRANSITION MATRIX ──────────────────────────────
print("Computing regime analysis...")
regime_counts = daily["regime"].value_counts().to_dict()
regime_pct = (daily["regime"].value_counts(normalize=True) * 100).round(2).to_dict()

# Transition matrix from daily_lttd consecutive dates
regime_series = daily.set_index("date")["regime"].sort_index()
trans_matrix = pd.DataFrame(0, index=REGIMES, columns=REGIMES, dtype=int)
for i in range(len(regime_series) - 1):
    prev_reg = regime_series.iloc[i]
    nxt_reg = regime_series.iloc[i + 1]
    if prev_reg in REGIMES and nxt_reg in REGIMES:
        trans_matrix.loc[prev_reg, nxt_reg] += 1

# Transition probabilities
row_sums = trans_matrix.sum(axis=1)
trans_prob = trans_matrix.div(row_sums, axis=0).round(4)
# Handle zero-division (if a regime has no outgoing transitions)
trans_prob = trans_prob.fillna(0.0)

# Also use regime_transitions table for additional context
n_transitions = len(transitions)
if n_transitions > 0:
    trans_from_table = (
        transitions.groupby(["previous_regime", "new_regime"])
        .size()
        .unstack(fill_value=0)
    )
    trans_from_table = trans_from_table.reindex(
        index=REGIMES, columns=REGIMES, fill_value=0
    )
else:
    trans_from_table = pd.DataFrame(0, index=REGIMES, columns=REGIMES)

print(f"  Regime counts: {regime_counts}")
print(f"  Total transitions: {n_transitions}")

# ── 7. FINAL SCORE DISTRIBUTION BY REGIME ───────────────────────────────────
print("Computing final score by regime...")
daily_aligned = daily.set_index("date").sort_index()
fs_by_regime: dict[str, dict] = {}
for regime in REGIMES:
    mask = daily_aligned["regime"] == regime
    vals = daily_aligned.loc[mask, "final_score"].dropna()
    if len(vals) > 0:
        fs_by_regime[regime] = {
            "n": int(mask.sum()),
            "mean": round(float(vals.mean()), 4),
            "std": round(float(vals.std()), 4),
            "min": round(float(vals.min()), 4),
            "max": round(float(vals.max()), 4),
            "median": round(float(vals.median()), 4),
            "q25": round(float(vals.quantile(0.25)), 4),
            "q75": round(float(vals.quantile(0.75)), 4),
        }

print("  Score stats by regime computed")

# ── BUILD REPORT JSON ────────────────────────────────────────────────────────
report: dict = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "data_range": {
        "start": str(daily["date"].min()),
        "end": str(daily["date"].max()),
        "total_days": len(daily),
    },
    "indicator_count": len(INDICATORS),
    "indicators": INDICATORS,
    "indicator_statistics": ind_stats,
    "cross_correlation": {
        "pearson": pearson_dict,
        "spearman": spearman_dict,
    },
    "vif_summary": {
        "window_size": VIF_WINDOW,
        "mean_vif": {
            c: round(float(vif_df[c].mean()), 4)
            for c in INDICATORS
            if c in vif_df.columns
        },
        "max_vif": {
            c: round(float(vif_df[c].max()), 4)
            for c in INDICATORS
            if c in vif_df.columns
        },
        "latest_vif": {
            c: round(float(vif_df[c].iloc[-1]), 4)
            for c in INDICATORS
            if c in vif_df.columns
        },
        "n_windows": len(vif_df),
    },
    "pca_variance_summary": {
        "window_size": VIF_WINDOW,
        "mean_cumulative_variance": {},
        "latest_cumulative_variance": {},
    },
    "regime_analysis": {
        "counts": regime_counts,
        "percentages": regime_pct,
        "transition_matrix_counts": trans_matrix.to_dict(),
        "transition_matrix_probabilities": trans_prob.to_dict(),
        "total_transitions_from_transitions_table": n_transitions,
    },
    "final_score_by_regime": fs_by_regime,
}

# PCA summary
pc_cols_in_var = [c for c in pca_var_df.columns if c.endswith("_cumvar")]
for pc_col in pc_cols_in_var:
    label = pc_col.replace("_cumvar", "")
    report["pca_variance_summary"]["mean_cumulative_variance"][label] = round(
        float(pca_var_df[pc_col].mean()), 4
    )
    report["pca_variance_summary"]["latest_cumulative_variance"][label] = round(
        float(pca_var_df[pc_col].iloc[-1]), 4
    )

# ── CHART 1: INDICATOR DISTRIBUTIONS (6-panel histogram) ────────────────────
print("\nGenerating charts...")
fig, axes = plt.subplots(2, 3, figsize=(16, 10))
fig.suptitle("Indicator Score Distributions", fontsize=14, fontweight="bold")
for idx, ind in enumerate(INDICATORS):
    ax = axes[idx // 3, idx % 3]
    if ind in pivot.columns:
        data = pivot[ind].dropna()
        ax.hist(
            data, bins=40, color="steelblue", alpha=0.7, edgecolor="white", density=True
        )
        ax.axvline(
            data.mean(),
            color="red",
            linestyle="--",
            linewidth=1,
            label=f"mean={data.mean():.3f}",
        )
        ax.axvline(
            data.median(),
            color="orange",
            linestyle=":",
            linewidth=1,
            label=f"median={data.median():.3f}",
        )
        ax.set_title(f"{ind} (n={len(data)})", fontsize=11)
        ax.legend(fontsize=8)
        ax.set_xlabel("Score")
        ax.set_ylabel("Density")
plt.tight_layout(rect=[0, 0, 1, 0.95])
plt.savefig(CHART_DIR / "indicator_distributions.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done indicator_distributions.png")

# ── CHART 2: CORRELATION HEATMAP ───────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle("Cross-Indicator Correlation", fontsize=14, fontweight="bold")

plot_data = [(axes[0], pearson_corr, "Pearson"), (axes[1], spearman_corr, "Spearman")]
for ax, corr_mat, title in plot_data:
    im = ax.imshow(corr_mat.values, cmap="RdBu_r", vmin=-1, vmax=1, aspect="auto")
    ax.set_xticks(range(len(corr_mat.columns)))
    ax.set_yticks(range(len(corr_mat.columns)))
    ax.set_xticklabels(corr_mat.columns, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(corr_mat.columns, fontsize=9)
    ax.set_title(title, fontsize=12)
    for i in range(len(corr_mat)):
        for j in range(len(corr_mat)):
            color = "white" if abs(corr_mat.values[i, j]) > 0.6 else "black"
            ax.text(
                j,
                i,
                f"{corr_mat.values[i, j]:.2f}",
                ha="center",
                va="center",
                fontsize=9,
                color=color,
            )
    plt.colorbar(im, ax=ax, shrink=0.8)

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(CHART_DIR / "correlation_heatmap.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done correlation_heatmap.png")

# ── CHART 3: VIF TRENDS ────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(14, 6))
for col in INDICATORS:
    if col in vif_df.columns:
        ax.plot(vif_df.index, vif_df[col], label=col, linewidth=1.2)
ax.axhline(y=10, color="red", linestyle="--", linewidth=1, label="VIF=10 threshold")
ax.axhline(y=5, color="orange", linestyle=":", linewidth=1, label="VIF=5 mild")
ax.set_title(
    "Variance Inflation Factor Over Time (Rolling 252-day)",
    fontsize=13,
    fontweight="bold",
)
ax.set_xlabel("Date")
ax.set_ylabel("VIF")
ax.legend(fontsize=9)
ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig(CHART_DIR / "vif_trends.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done vif_trends.png")

# ── CHART 4: PCA VARIANCE EXPLAINED ────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle(
    "PCA Variance Explained Over Time (Rolling 252-day)", fontsize=13, fontweight="bold"
)

chart_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"]

# Left: cumulative variance
ax = axes[0]
cumvar_cols = [c for c in pca_var_df.columns if c.endswith("_cumvar")][:6]
for i, pc_col in enumerate(cumvar_cols):
    label = pc_col.replace("_cumvar", "")
    ax.plot(
        pca_var_df.index,
        pca_var_df[pc_col],
        label=label,
        color=chart_colors[i % len(chart_colors)],
        linewidth=1.2,
    )
ax.axhline(y=0.85, color="red", linestyle="--", linewidth=1, label="85% threshold")
ax.set_title("Cumulative Variance by Component", fontsize=11)
ax.set_xlabel("Date")
ax.set_ylabel("Cumulative Variance Explained")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

# Right: stacked area of individual component variance
ax = axes[1]
var_cols = [c for c in pca_var_df.columns if c.endswith("_var")]
if var_cols:
    stacked_data = pca_var_df[var_cols].copy()
    stacked_data.columns = [c.replace("_var", "") for c in var_cols]
    stacked_data.plot.area(ax=ax, alpha=0.7, color=chart_colors[: len(var_cols)])
ax.set_title("Individual Component Variance", fontsize=11)
ax.set_xlabel("Date")
ax.set_ylabel("Variance Explained")
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(CHART_DIR / "pca_variance.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done pca_variance.png")

# ── CHART 5: REGIME DISTRIBUTION (pie + transition heatmap) ─────────────────
fig, axes = plt.subplots(1, 2, figsize=(14, 6))
fig.suptitle("Regime Analysis", fontsize=14, fontweight="bold")

regime_colors = {"BULL": "#2ecc71", "BEAR": "#e74c3c", "SIDEWAYS": "#3498db"}

# Pie chart
ax = axes[0]
labels = [f"{r}\n{regime_counts.get(r, 0)} ({regime_pct.get(r, 0)}%)" for r in REGIMES]
sizes = [regime_counts.get(r, 0) for r in REGIMES]
colors_pie = [regime_colors[r] for r in REGIMES]
ax.pie(
    sizes,
    labels=labels,
    colors=colors_pie,
    autopct="",
    startangle=90,
    textprops={"fontsize": 10},
)
ax.set_title(f"Regime Distribution (n={len(daily)})", fontsize=11)

# Transition heatmap
ax = axes[1]
trans_prob_arr = trans_prob.values.astype(float)
im = ax.imshow(trans_prob_arr, cmap="YlOrRd", vmin=0, vmax=1, aspect="auto")
ax.set_xticks(range(len(REGIMES)))
ax.set_yticks(range(len(REGIMES)))
ax.set_xticklabels(REGIMES, fontsize=10)
ax.set_yticklabels(REGIMES, fontsize=10)
ax.set_xlabel("To Regime")
ax.set_ylabel("From Regime")
ax.set_title("Transition Probability Matrix", fontsize=11)
for i in range(len(REGIMES)):
    for j in range(len(REGIMES)):
        val = trans_prob_arr[i, j]
        color = "white" if val > 0.5 else "black"
        ax.text(
            j,
            i,
            f"{val:.3f}\n(n={int(trans_matrix.values[i, j])})",
            ha="center",
            va="center",
            fontsize=10,
            color=color,
        )
plt.colorbar(im, ax=ax, shrink=0.8)

plt.tight_layout(rect=[0, 0, 1, 0.93])
plt.savefig(CHART_DIR / "regime_distribution.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done regime_distribution.png")

# ── CHART 6: FINAL SCORE BY REGIME (boxplot) ────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 6))
box_data = []
box_labels = []
box_colors = []
for regime in REGIMES:
    mask = daily_aligned["regime"] == regime
    vals = daily_aligned.loc[mask, "final_score"].dropna().to_numpy(dtype=float)
    if len(vals) > 0:
        box_data.append(vals)
        box_labels.append(f"{regime}\n(n={len(vals)})")
        box_colors.append(regime_colors[regime])

bp = ax.boxplot(
    box_data,
    labels=box_labels,
    patch_artist=True,
    widths=0.6,
    medianprops={"color": "black", "linewidth": 2},
)
for patch, color in zip(bp["boxes"], box_colors, strict=True):
    patch.set_facecolor(color)
    patch.set_alpha(0.7)

ax.axhline(y=0, color="gray", linestyle="--", linewidth=0.8, alpha=0.5)
ax.set_title("Final Score Distribution by Regime", fontsize=13, fontweight="bold")
ax.set_ylabel("Final Score")
ax.set_xlabel("Regime")
ax.grid(True, axis="y", alpha=0.3)

# Add summary stats as text
for i, regime in enumerate(REGIMES):
    if regime in fs_by_regime:
        s = fs_by_regime[regime]
        ax.text(
            i + 1,
            s["max"] + 0.02,
            f"mean={s['mean']:.3f}\nstd={s['std']:.3f}",
            ha="center",
            va="bottom",
            fontsize=8,
            color="gray",
        )

plt.tight_layout()
plt.savefig(CHART_DIR / "final_score_by_regime.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done final_score_by_regime.png")

# ── CHART 7: STATIONARITY TESTS (ADF p-values) ─────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
adf_pvals = [ind_stats.get(ind, {}).get("adf_pval", float("nan")) for ind in INDICATORS]
bar_colors = [
    "#2ecc71" if (not np.isnan(p) and p < 0.05) else "#e74c3c" for p in adf_pvals
]
bars = ax.bar(INDICATORS, adf_pvals, color=bar_colors, edgecolor="white", width=0.6)
ax.axhline(y=0.05, color="red", linestyle="--", linewidth=1, label="p=0.05 threshold")
ax.axhline(y=0.01, color="darkred", linestyle=":", linewidth=1, label="p=0.01 strong")
ax.set_title(
    "ADF Stationarity Test p-values by Indicator", fontsize=13, fontweight="bold"
)
ax.set_ylabel("p-value")
max_pval = max((p for p in adf_pvals if not np.isnan(p)), default=0.5)
ax.set_ylim(0, max(1.0, max_pval * 1.1))
ax.legend(fontsize=9)
ax.grid(True, axis="y", alpha=0.3)

for bar_item, val in zip(bars, adf_pvals, strict=True):
    if not np.isnan(val):
        ax.text(
            bar_item.get_x() + bar_item.get_width() / 2,
            bar_item.get_height() + 0.01,
            f"{val:.4f}",
            ha="center",
            va="bottom",
            fontsize=9,
        )

plt.tight_layout()
plt.savefig(CHART_DIR / "stationarity_tests.png", dpi=150, bbox_inches="tight")
plt.close()
print("  done stationarity_tests.png")


# ── SAVE JSON REPORT ────────────────────────────────────────────────────────
def sanitize(obj: object) -> object:
    """Recursively convert numpy/pandas types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: sanitize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return str(obj)
    return obj


report = sanitize(report)  # type: ignore[assignment]
with open(REPORT_PATH, "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"\nReport saved to {REPORT_PATH}")

# ── PRINT KEY FINDINGS ──────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("KEY FINDINGS SUMMARY")
print("=" * 70)

print(
    f"\nData range: {report['data_range']['start']} to {report['data_range']['end']} "
    f"({report['data_range']['total_days']} days)"
)

print("\n-- Stationarity (ADF) --")
for ind in INDICATORS:
    s = ind_stats.get(ind, {})
    p = s.get("adf_pval", float("nan"))
    status = "STATIONARY" if (not np.isnan(p) and p < 0.05) else "NON-STATIONARY"
    print(f"  {ind:25s}  p={p:.4f}  {status}")

print("\n-- Normality (Jarque-Bera) --")
for ind in INDICATORS:
    s = ind_stats.get(ind, {})
    p = s.get("jarque_bera_pval", float("nan"))
    status = "NORMAL" if p > 0.05 else "NON-NORMAL"
    print(f"  {ind:25s}  p={p:.6f}  {status}")

print("\n-- High Autocorrelation (lag-21) --")
for ind in INDICATORS:
    s = ind_stats.get(ind, {})
    acf21 = s.get("acf", {}).get("lag_21", None)
    if acf21 is not None and abs(acf21) > 0.3:
        print(
            f"  {ind:25s}  ACF(21)={acf21:.4f}  "
            f"{'positive' if acf21 > 0 else 'negative'}"
        )

print("\n-- VIF Concerns (max > 10) --")
for ind in INDICATORS:
    mx = report["vif_summary"]["max_vif"].get(ind)
    if mx and mx > 10:
        print(f"  WARNING  {ind:25s}  max_VIF={mx:.2f}")

print("\n-- Regime Transition --")
for r_from in REGIMES:
    total = int(trans_matrix.loc[r_from].sum())
    if total > 0:
        most_likely = trans_matrix.loc[r_from].idxmax()
        prob = float(trans_prob.loc[r_from, most_likely])
        print(f"  {r_from:10s} -> {most_likely:10s}  p={prob:.3f}  (n={total} obs)")

print("\n-- PCA Variance (latest window) --")
latest = report["pca_variance_summary"]["latest_cumulative_variance"]
for pc_name in ["PC1", "PC2", "PC3", "PC4", "PC5", "PC6"]:
    if pc_name in latest:
        print(f"  {pc_name} cumulative: {latest[pc_name]:.4f}")

print("\n-- Final Score by Regime --")
for regime in REGIMES:
    if regime in fs_by_regime:
        s = fs_by_regime[regime]
        print(
            f"  {regime:10s}  mean={s['mean']:+.4f}  std={s['std']:.4f}  "
            f"range=[{s['min']:+.4f}, {s['max']:+.4f}]  n={s['n']}"
        )

print("\n" + "=" * 70)
print(f"Audit complete. Charts: {CHART_DIR}")
print(f"Report: {REPORT_PATH}")
print("=" * 70)
