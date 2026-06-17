#!/usr/bin/env python3
"""
Deep audit of ISP target files (regimes + signals).
Checks: internal consistency, cross-file alignment, regime logic,
label quality, temporal gaps, forward-looking bias, and ML suitability.
"""

import pandas as pd
import numpy as np

# ── Load ──────────────────────────────────────────────────────────
regimes = pd.read_csv("docs/isps/isp-regimes-btcusd-2026-06-13.csv")
signals = pd.read_csv("docs/isps/isp-signals-btcusd-2026-06-13.csv")

regimes["Date"] = pd.to_datetime(regimes["Date"])
signals["Date"] = pd.to_datetime(signals["Date"])

REGIME_ORDER = {
    "Strong Bear": 0,
    "Weak Bear": 1,
    "Neutral": 2,
    "Weak Bull": 3,
    "Strong Bull": 4,
}

print("=" * 80)
print("ISP TARGET FILE DEEP AUDIT")
print("=" * 80)

# ── 1. BASIC STATISTICS ──────────────────────────────────────────
print("\n" + "─" * 80)
print("1. BASIC STATISTICS")
print("─" * 80)

print(
    f"\nRegimes file: {len(regimes)} rows, {regimes.Date.min().date()} → {regimes.Date.max().date()}"
)
print(
    f"Signals file: {len(signals)} rows, {signals.Date.min().date()} → {signals.Date.max().date()}"
)

print("\nRegime distribution:")
print(regimes["Regime"].value_counts().to_string())

print("\nAction distribution:")
print(signals["Action"].value_counts().to_string())

# ── 2. TEMPORAL GAP ANALYSIS ────────────────────────────────────
print("\n" + "─" * 80)
print("2. TEMPORAL GAP ANALYSIS")
print("─" * 80)

regimes = regimes.sort_values("Date").reset_index(drop=True)
regimes["Gap_Days"] = regimes["Date"].diff().dt.days
regimes["Gap_Months"] = regimes["Gap_Days"] / 30.44

print("\nRegime transition gaps:")
print(
    f"  Mean: {regimes['Gap_Days'].mean():.0f} days ({regimes['Gap_Months'].mean():.1f} months)"
)
print(f"  Median: {regimes['Gap_Days'].median():.0f} days")
print(f"  Min: {regimes['Gap_Days'].min():.0f} days")
print(
    f"  Max: {regimes['Gap_Days'].max():.0f} days ({regimes['Gap_Months'].max():.1f} months)"
)
print(f"  Std: {regimes['Gap_Days'].std():.0f} days")

print("\nLargest gaps (>100 days):")
large_gaps = regimes[regimes["Gap_Days"] > 100]
for _, row in large_gaps.iterrows():
    print(
        f"  {row['Date'].date()} → {row['Regime']:15s} | gap = {row['Gap_Days']:.0f} days ({row['Gap_Months']:.1f} months) | ${row['Price']:,.0f}"
    )

print("\nSmallest gaps (<7 days):")
small_gaps = regimes[regimes["Gap_Days"] < 7]
for _, row in small_gaps.iterrows():
    print(
        f"  {row['Date'].date()} → {row['Regime']:15s} | gap = {row['Gap_Days']:.0f} days | ${row['Price']:,.0f}"
    )

# ── 3. REGIME SEQUENCE VALIDATION ────────────────────────────────
print("\n" + "─" * 80)
print("3. REGIME SEQUENCE VALIDATION")
print("─" * 80)

print("\nFull regime sequence:")
for i, row in regimes.iterrows():
    gap = f" (gap: {row['Gap_Days']:.0f}d)" if i > 0 else ""
    price_chg = ""
    if i > 0:
        prev_price = regimes.loc[i - 1, "Price"]
        chg = (row["Price"] / prev_price - 1) * 100
        price_chg = f" | price: {chg:+.1f}%"
    print(
        f"  {row['Date'].date()} {row['Regime']:15s} ${row['Price']:>10,.2f}{gap}{price_chg}"
    )

# Check: does regime match price direction?
print("\nRegime vs price direction consistency:")
correct = 0
incorrect = 0
ambiguous = 0
for i in range(1, len(regimes)):
    prev_price = regimes.loc[i - 1, "Price"]
    curr_price = regimes.loc[i, "Price"]
    prev_regime = regimes.loc[i - 1, "Regime"]
    curr_regime = regimes.loc[i, "Regime"]
    price_up = curr_price > prev_price
    regime_bullish = REGIME_ORDER[curr_regime] > REGIME_ORDER[prev_regime]
    regime_bearish = REGIME_ORDER[curr_regime] < REGIME_ORDER[prev_regime]

    if price_up and regime_bullish:
        correct += 1
    elif not price_up and regime_bearish:
        correct += 1
    elif curr_regime == prev_regime:
        ambiguous += 1
    else:
        incorrect += 1
        print(
            f"  INCONSISTENT: {regimes.loc[i - 1, 'Date'].date()} {prev_regime} → {regimes.loc[i, 'Date'].date()} {curr_regime} | price {('UP' if price_up else 'DOWN')}"
        )

total_transitions = len(regimes) - 1
print(
    f"  Consistent: {correct}/{total_transitions} ({correct / total_transitions * 100:.1f}%)"
)
print(
    f"  Inconsistent: {incorrect}/{total_transitions} ({incorrect / total_transitions * 100:.1f}%)"
)
print(f"  Same regime: {ambiguous}/{total_transitions}")

# ── 4. CROSS-FILE ALIGNMENT ─────────────────────────────────────
print("\n" + "─" * 80)
print("4. CROSS-FILE ALIGNMENT (Regimes vs Signals)")
print("─" * 80)

# Merge on Date
merged = pd.merge(
    regimes[["Date", "Regime", "Price"]],
    signals[["Date", "Action", "EquityPct", "Regime"]],
    on="Date",
    how="outer",
    suffixes=("_regime", "_signal"),
    indicator=True,
)

print("\nAlignment summary:")
print(merged["_merge"].value_counts().to_string())

# Check regime labels match where both exist
both = merged[merged["_merge"] == "both"]
if len(both) > 0:
    regime_match = (both["Regime_regime"] == both["Regime_signal"]).sum()
    regime_mismatch = len(both) - regime_match
    print(
        f"\nRegime label agreement: {regime_match}/{len(both)} ({regime_match / len(both) * 100:.1f}%)"
    )
    if regime_mismatch > 0:
        print("MISMATCHES:")
        mismatches = both[both["Regime_regime"] != both["Regime_signal"]]
        for _, row in mismatches.iterrows():
            print(
                f"  {row['Date'].date()}: regime={row['Regime_regime']}, signal={row['Regime_signal']}"
            )

# Dates in signals but not in regimes
signals_only = merged[merged["_merge"] == "right_only"]
if len(signals_only) > 0:
    print(f"\nSignals without regime labels ({len(signals_only)}):")
    for _, row in signals_only.iterrows():
        print(f"  {row['Date'].date()} {row['Action']} ${row['Price']:,.2f}")

# Dates in regimes but not in signals
regimes_only = merged[merged["_merge"] == "left_only"]
if len(regimes_only) > 0:
    print(f"\nRegime transitions without signals ({len(regimes_only)}):")
    for _, row in regimes_only.iterrows():
        print(f"  {row['Date'].date()} {row['Regime_regime']} ${row['Price']:,.2f}")

# ── 5. SIGNAL LOGIC VALIDATION ──────────────────────────────────
print("\n" + "─" * 80)
print("5. SIGNAL LOGIC VALIDATION")
print("─" * 80)

signals = signals.sort_values("Date").reset_index(drop=True)

# Check: BUY should be followed by SELL, and vice versa
print("\nAction sequence:")
prev_action = None
for i, row in signals.iterrows():
    if prev_action is not None and row["Action"] == prev_action:
        print(f"  WARNING: Consecutive {row['Action']} at {row['Date'].date()}")
    prev_action = row["Action"]

# Check: BUY at lower price than subsequent SELL (profitability)
print("\nRound-trip trade analysis:")
buys = signals[signals["Action"] == "BUY"].reset_index(drop=True)
sells = signals[signals["Action"] == "SELL"].reset_index(drop=True)

for i in range(min(len(buys), len(sells))):
    buy = buys.iloc[i]
    sell = sells.iloc[i]
    pnl_pct = (sell["Price"] / buy["Price"] - 1) * 100
    hold_days = (sell["Date"] - buy["Date"]).days
    print(
        f"  BUY  {buy['Date'].date()} ${buy['Price']:>10,.2f} → SELL {sell['Date'].date()} ${sell['Price']:>10,.2f} | {pnl_pct:+7.1f}% | {hold_days} days"
    )

# ── 6. EQUITY CURVE VALIDATION ──────────────────────────────────
print("\n" + "─" * 80)
print("6. EQUITY CURVE VALIDATION")
print("─" * 80)

print("\nEquity progression:")
for i, row in signals.iterrows():
    chg = ""
    if i > 0:
        prev_eq = signals.loc[i - 1, "TotalEquity"]
        chg_pct = (row["TotalEquity"] / prev_eq - 1) * 100
        chg = f" | {chg_pct:+.2f}%"
    print(
        f"  {row['Date'].date()} {row['Action']:4s} ${row['Price']:>10,.2f} | EquityPct: {row['EquityPct']}% | BTC: {row['BTCHeld']:.4f} | Total: ${row['TotalEquity']:>14,.2f}{chg}"
    )

# Check equity math
print("\nEquity math verification:")
for i, row in signals.iterrows():
    expected_equity = row["BTCHeld"] * row["Price"] + (
        row["TotalEquity"] - row["BTCHeld"] * row["Price"]
    )
    # TotalEquity should = BTCHeld * Price + Cash
    # For BUY: Cash decreases, BTC increases
    # For SELL: Cash increases, BTC decreases
    if i > 0:
        prev = signals.loc[i - 1]
        if row["Action"] == "BUY":
            # Cash spent = EquityPct% of prev equity
            cash_spent = prev["TotalEquity"] * row["EquityPct"] / 100
            expected_btc = prev["BTCHeld"] + (cash_spent - row["Cost"]) / row["Price"]
            expected_equity = expected_btc * row["Price"] + (
                prev["TotalEquity"] - cash_spent
            )
        elif row["Action"] == "SELL":
            cash_received = row["BTCHeld"] * row["Price"] - row["Cost"]
            expected_equity = cash_received

        diff = abs(row["TotalEquity"] - expected_equity)
        if diff > 100:
            print(
                f"  MATH ERROR at {row['Date'].date()}: expected ${expected_equity:,.2f}, got ${row['TotalEquity']:,.2f} (diff: ${diff:,.2f})"
            )

# ── 7. FORWARD-LOOKING BIAS CHECK ───────────────────────────────
print("\n" + "─" * 80)
print("7. FORWARD-LOOKING BIAS CHECK")
print("─" * 80)

# Check if regime transitions happen near local price extremes
print("\nRegime transitions near price extremes:")
for i, row in regimes.iterrows():
    date = row["Date"]
    price = row["Price"]
    regime = row["Regime"]

    # Check if this date is within 5% of a local max/min in a ±30 day window
    # (We don't have full OHLCV here, but we can check against adjacent regime prices)
    if i > 0 and i < len(regimes) - 1:
        prev_p = regimes.loc[i - 1, "Price"]
        next_p = regimes.loc[i + 1, "Price"]

        is_local_max = price > prev_p and price > next_p
        is_local_min = price < prev_p and price < next_p

        if is_local_max and regime in ["Strong Bull", "Weak Bull"]:
            print(
                f"  ⚠️  BULLISH regime at LOCAL MAX: {date.date()} {regime} ${price:,.2f}"
            )
        elif is_local_min and regime in ["Strong Bear", "Weak Bear"]:
            print(
                f"  ⚠️  BEARISH regime at LOCAL MIN: {date.date()} {regime} ${price:,.2f}"
            )

# Check: does the signal always buy low and sell high?
print("\nHindsight bias check:")
for i, row in signals.iterrows():
    if row["Action"] == "BUY":
        # Is this price lower than the next SELL price?
        next_sell_idx = (
            signals.index[signals.index.get_loc(i) + 1]
            if i < len(signals) - 1
            else None
        )
        if next_sell_idx is not None:
            next_sell = signals.loc[next_sell_idx]
            if next_sell["Action"] == "SELL" and row["Price"] > next_sell["Price"]:
                print(
                    f"  ⚠️  BUY at HIGHER price than subsequent SELL: BUY {row['Date'].date()} ${row['Price']:,.2f} → SELL {next_sell['Date'].date()} ${next_sell['Price']:,.2f}"
                )

# ── 8. LABEL QUALITY ASSESSMENT ─────────────────────────────────
print("\n" + "─" * 80)
print("8. LABEL QUALITY ASSESSMENT")
print("─" * 80)

# Regime intensity mapping
REGIME_MAP = {
    "Strong Bear": 0.0,
    "Weak Bear": 0.25,
    "Neutral": 0.50,
    "Weak Bull": 0.75,
    "Strong Bull": 1.0,
}

regimes["Intensity"] = regimes["Regime"].map(REGIME_MAP)
regimes["Intensity_Change"] = regimes["Intensity"].diff()

print("\nRegime intensity transitions:")
for i, row in regimes.iterrows():
    if i > 0:
        chg = row["Intensity_Change"]
        direction = "↑" if chg > 0 else "↓" if chg < 0 else "="
        print(
            f"  {row['Date'].date()} {row['Regime']:15s} ({row['Intensity']:.2f}) {direction} {chg:+.2f}"
        )

# Check: are there impossible transitions? (e.g., Strong Bear → Strong Bull)
print("\nImpossible transitions (jumping >2 levels):")
for i in range(1, len(regimes)):
    prev_level = REGIME_ORDER[regimes.loc[i - 1, "Regime"]]
    curr_level = REGIME_ORDER[regimes.loc[i, "Regime"]]
    jump = abs(curr_level - prev_level)
    if jump > 2:
        print(
            f"  ⚠️  {regimes.loc[i - 1, 'Date'].date()} {regimes.loc[i - 1, 'Regime']} → {regimes.loc[i, 'Date'].date()} {regimes.loc[i, 'Regime']} (jump: {jump} levels)"
        )

# ── 9. ML SUITABILITY ASSESSMENT ─────────────────────────────────
print("\n" + "─" * 80)
print("9. ML SUITABILITY ASSESSMENT")
print("─" * 80)

# Create full daily index and forward-fill
full_idx = pd.date_range(
    start=regimes["Date"].min(), end=regimes["Date"].max(), freq="D"
)
daily_regimes = regimes.set_index("Date")["Regime"].reindex(full_idx).ffill()
daily_intensities = regimes.set_index("Date")["Intensity"].reindex(full_idx).ffill()

# Compute statistics
total_days = len(daily_regimes)
unique_regimes = daily_regimes.nunique()
regime_counts = daily_regimes.value_counts()
transition_count = (daily_regimes != daily_regimes.shift()).sum() - 1  # minus first

# Entropy
probs = regime_counts / total_days
entropy = -np.sum(probs * np.log2(probs + 1e-10))
max_entropy = np.log2(5)  # 5 classes

# Effective sample size (ACF-based)
intensity_series = daily_intensities.values
n = len(intensity_series)
mean = np.mean(intensity_series)
var = np.var(intensity_series)
acf1 = np.sum((intensity_series[1:] - mean) * (intensity_series[:-1] - mean)) / (
    n * var
)
effective_n = n * (1 - acf1) / (1 + acf1)

print(f"Total days in range: {total_days}")
print(f"Unique regimes in forward-filled series: {unique_regimes}")
print(f"Regime transitions: {transition_count}")
print(f"Mean gap between transitions: {regimes['Gap_Days'].mean():.0f} days")
print(
    f"Target entropy: {entropy:.3f} / {max_entropy:.3f} ({entropy / max_entropy * 100:.1f}%)"
)
print(f"ACF(1) of intensity series: {acf1:.4f}")
print(f"Effective sample size: {effective_n:.0f} (of {total_days})")
print(f"Effective N / Total N ratio: {effective_n / total_days * 100:.1f}%")

print("\nRegime duration distribution (forward-filled):")
for regime in ["Strong Bear", "Weak Bear", "Neutral", "Weak Bull", "Strong Bull"]:
    mask = daily_regimes == regime
    if mask.any():
        # Find consecutive runs
        runs = mask.ne(mask.shift()).cumsum()
        run_lengths = mask.groupby(runs).sum()
        run_lengths = run_lengths[run_lengths > 0]
        print(
            f"  {regime:15s}: n={len(run_lengths):4d} runs, mean={run_lengths.mean():.1f} days, max={run_lengths.max():.0f} days"
        )

# ── 10. SIGNAL FILE SPECIFIC CHECKS ─────────────────────────────
print("\n" + "─" * 80)
print("10. SIGNAL FILE SPECIFIC CHECKS")
print("─" * 80)

# Starting equity
start_equity = 10000  # implied from first BUY with Cost=5000 and EquityPct=50
print(f"Implied starting equity: ${start_equity:,.2f}")

# Final equity
final_equity = signals.iloc[-1]["TotalEquity"]
total_return = (final_equity / start_equity - 1) * 100
years = (signals.iloc[-1]["Date"] - signals.iloc[0]["Date"]).days / 365.25
cagr = ((final_equity / start_equity) ** (1 / years) - 1) * 100

print(f"Final equity: ${final_equity:,.2f}")
print(f"Total return: {total_return:,.1f}%")
print(f"Time period: {years:.1f} years")
print(f"CAGR: {cagr:.1f}%")

# Count total trades
n_buys = len(signals[signals["Action"] == "BUY"])
n_sells = len(signals[signals["Action"] == "SELL"])
print(f"Total trades: {n_buys} buys + {n_sells} sells = {len(signals)}")

# Check: does the last action leave us flat?
last_action = signals.iloc[-1]["Action"]
last_btc = signals.iloc[-1]["BTCHeld"]
print(f"Last action: {last_action} | BTC held: {last_btc:.4f}")
if last_action == "SELL" and last_btc == 0:
    print("  ✅ System ends flat (all cash)")
elif last_action == "BUY":
    print("  ⚠️  System ends LONG (exposed to BTC)")

# Check: are there any missing sell signals after a buy?
print("\nOpen position check:")
position = 0
for _, row in signals.iterrows():
    if row["Action"] == "BUY":
        position += row["EquityPct"]
    elif row["Action"] == "SELL":
        position -= row["EquityPct"]
    if position > 100:
        print(f"  ⚠️  OVER-POSITION at {row['Date'].date()}: {position}%")
    if position < 0:
        print(f"  ⚠️  UNDER-POSITION at {row['Date'].date()}: {position}%")

# ── 11. PRICE DATA QUALITY ──────────────────────────────────────
print("\n" + "─" * 80)
print("11. PRICE DATA QUALITY")
print("─" * 80)

# Check for price inconsistencies
print("\nPrice at regime transitions:")
for i, row in regimes.iterrows():
    if i > 0:
        prev_price = regimes.loc[i - 1, "Price"]
        chg = (row["Price"] / prev_price - 1) * 100
        if abs(chg) > 100:
            print(
                f"  ⚠️  MASSIVE PRICE CHANGE: {regimes.loc[i - 1, 'Date'].date()} ${prev_price:,.2f} → {row['Date'].date()} ${row['Price']:,.2f} ({chg:+.1f}%)"
            )

# Check signal prices vs regime prices at same dates
print("\nPrice alignment at cross-file dates:")
both_dates = set(regimes["Date"]) & set(signals["Date"])
for date in sorted(both_dates):
    reg_price = regimes[regimes["Date"] == date]["Price"].values[0]
    sig_price = signals[signals["Date"] == date]["Price"].values[0]
    if abs(reg_price - sig_price) > 1:
        print(
            f"  ⚠️  {date.date()}: regime=${reg_price:,.2f}, signal=${sig_price:,.2f} (diff: ${abs(reg_price - sig_price):,.2f})"
        )

# ── SUMMARY ──────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("AUDIT SUMMARY")
print("=" * 80)

findings = []
findings.append(
    f"Regimes: {len(regimes)} transitions over {(regimes['Date'].max() - regimes['Date'].min()).days} days"
)
findings.append(
    f"Signals: {len(signals)} trades, final equity ${final_equity:,.2f} ({cagr:.1f}% CAGR)"
)
findings.append(
    f"Mean gap between regime transitions: {regimes['Gap_Days'].mean():.0f} days"
)
findings.append(f"Forward-fill effective N: {effective_n:.0f} (ACF(1)={acf1:.4f})")
findings.append(f"Target entropy: {entropy / max_entropy * 100:.1f}% of maximum")

for f in findings:
    print(f"  • {f}")

print("\n" + "=" * 80)
