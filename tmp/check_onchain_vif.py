"""Compute VIF for on-chain features using historical BRK data via the pipeline's own ingestion."""
import sys
sys.path.insert(0, ".")
import pandas as pd
import numpy as np
from src.data.brk_ingestion_service import BRKIngestionService
from src.features.vif import calculate_vif

print("Fetching historical on-chain data from BRK (bitview.space)...")
svc = BRKIngestionService()
df = svc.fetch_historical(lookback_days=1200)
print(f"Shape: {df.shape}")
print(f"Date range: {df.index.min()} → {df.index.max()}")
print(f"Columns: {list(df.columns)}")
print()

# --- 1. VIF on raw levels ---
df_clean = df.dropna()
print(f"After dropna: {df_clean.shape}")
print(f"\n{'='*60}")
print("1. RAW LEVEL correlations & VIF")
print(f"{'='*60}")
print("\nCorrelation matrix:")
print(df_clean.corr().round(4))
print("\nVIF (raw levels):")
vifs_raw = calculate_vif(df_clean)
for col, v in vifs_raw.items():
    print(f"  {col:30s} VIF = {v:.4f}")

# --- 2. Pairwise deep-dive: sth_mvrv vs sth_nupl ---
r = df_clean["sth_mvrv"].corr(df_clean["sth_nupl"])
print(f"\n{'='*60}")
print(f"2. PAIRWISE: sth_mvrv vs sth_nupl")
print(f"{'='*60}")
print(f"  Pearson r  = {r:.6f}")
print(f"  R²         = {r**2:.6f}")
print(f"  1/(1-R²)   = {1/(1-r**2):.4f}  (bivariate VIF approximation)")

# --- 3. With ROC-7 columns (as FeatureMatrixBuilder adds them) ---
print(f"\n{'='*60}")
print("3. WITH ROC-7 MOMENTUM FEATURES")
print(f"{'='*60}")
onchain_cols = ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]
df_roc = df_clean.copy()
for col in onchain_cols:
    shift_col = df_roc[col].shift(7)
    roc = (df_roc[col] - shift_col) / shift_col.replace(0.0, np.nan)
    df_roc[f"{col}_roc_7"] = roc.replace([np.inf, -np.inf], np.nan).fillna(0.0)

df_roc = df_roc.dropna()
print(f"Shape with ROC: {df_roc.shape}")
print("\nCorrelation matrix:")
print(df_roc.corr().round(4))
print("\nVIF (all on-chain + roc_7):")
vifs_all = calculate_vif(df_roc)
for col, v in sorted(vifs_all.items(), key=lambda x: -x[1]):
    marker = " ⚠️  HIGH" if v > 10 else ""
    print(f"  {col:30s} VIF = {v:.4f}{marker}")

# --- 4. What happens if we drop sth_nupl (or sth_mvrv)? ---
print(f"\n{'='*60}")
print("4. VIF AFTER DROPPING sth_nupl")
print(f"{'='*60}")
drop_nupl_cols = [c for c in df_roc.columns if "sth_nupl" not in c]
df_no_nupl = df_roc[drop_nupl_cols]
vifs_no_nupl = calculate_vif(df_no_nupl)
for col, v in sorted(vifs_no_nupl.items(), key=lambda x: -x[1]):
    marker = " ⚠️  HIGH" if v > 10 else ""
    print(f"  {col:30s} VIF = {v:.4f}{marker}")

# --- 5. Scatter plot summary stats ---
print(f"\n{'='*60}")
print("5. SUMMARY STATISTICS")
print(f"{'='*60}")
print(df_clean[["sth_mvrv", "sth_nupl"]].describe().round(6))
