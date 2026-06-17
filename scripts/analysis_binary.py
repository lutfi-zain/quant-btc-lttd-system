import sqlite3
import pandas as pd
import numpy as np

# Connect to database
conn = sqlite3.connect('database/lttd.db')

# Load LTTD target exposure and scores
df_lttd = pd.read_sql('SELECT data_as_of as date, final_score, target_exposure FROM daily_lttd ORDER BY date', conn)

# Load OHLCV
df_ohlcv = pd.read_sql('SELECT timestamp as date, close FROM ohlcv ORDER BY date', conn)

# Normalize dates
df_lttd['date'] = pd.to_datetime(df_lttd['date']).dt.normalize()
df_ohlcv['date'] = pd.to_datetime(df_ohlcv['date']).dt.normalize()

# Merge
df = pd.merge(df_lttd, df_ohlcv, on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

# 1. Proportion of days in 0 vs 100
total_days = len(df)
days_0 = (df['target_exposure'] == 0.0).sum()
days_100 = (df['target_exposure'] == 1.0).sum()

print(f"Total days: {total_days}")
print(f"Days at 0% exposure: {days_0} ({days_0/total_days*100:.2f}%)")
print(f"Days at 100% exposure: {days_100} ({days_100/total_days*100:.2f}%)")

# Determine binary signal mathematically
# Trade extraction for Binary
df['prev_exposure'] = df['target_exposure'].shift(1).fillna(0)
df['signal_change'] = df['target_exposure'] - df['prev_exposure']
# +1 means 0->1 (buy), -1 means 1->0 (sell)

trades = []
entry_idx = None
entry_price = None

for i, row in df.iterrows():
    if row['signal_change'] == 1.0:
        entry_idx = i
        entry_price = row['close']
    elif row['signal_change'] == -1.0 and entry_idx is not None:
        exit_price = row['close']
        duration = i - entry_idx
        trades.append({
            'entry_idx': entry_idx,
            'exit_idx': i,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'duration': duration,
            'return': (exit_price - entry_price) / entry_price
        })
        entry_idx = None

trades_df = pd.DataFrame(trades)
if len(trades_df) > 0:
    win_rate = (trades_df['return'] > 0).mean()
    whipsaws = (trades_df['duration'] <= 5).sum()
    whipsaw_rate = whipsaws / len(trades_df)
    
    print(f"Total trades: {len(trades_df)}")
    print(f"Win Rate: {win_rate*100:.2f}%")
    print(f"Whipsaws (duration <= 5 days): {whipsaws} ({whipsaw_rate*100:.2f}%)")
else:
    print("No trades found.")

# Calculate Equity curves
df['return'] = df['close'].pct_change().fillna(0)

# Shift exposure by 1 day because we trade on the next open/close after the signal (standard backtest logic).
# Actually, target_exposure of day T tells us the exposure for day T+1
df['trading_exposure'] = df['target_exposure'].shift(1).fillna(1.0) # Assume fully invested until first signal

df['strat_binary_return'] = df['trading_exposure'] * df['return']

# Continuous baseline (0.5 + 0.5*score)
df['continuous_target'] = 0.5 + 0.5 * df['final_score']
df['trading_continuous'] = df['continuous_target'].shift(1).fillna(1.0)
df['strat_continuous_return'] = df['trading_continuous'] * df['return']

df['cum_bh'] = (1 + df['return']).cumprod()
df['cum_binary'] = (1 + df['strat_binary_return']).cumprod()
df['cum_continuous'] = (1 + df['strat_continuous_return']).cumprod()

print(f"Final Return - Buy & Hold: {df['cum_bh'].iloc[-1]:.2f}x")
print(f"Final Return - Binary: {df['cum_binary'].iloc[-1]:.2f}x")
print(f"Final Return - Continuous: {df['cum_continuous'].iloc[-1]:.2f}x")

# Calculate metrics to explain mathematically
vol_bh = df['return'].std() * np.sqrt(365)
vol_bin = df['strat_binary_return'].std() * np.sqrt(365)
vol_cont = df['strat_continuous_return'].std() * np.sqrt(365)

print(f"Annualized Volatility - Buy & Hold: {vol_bh*100:.2f}%")
print(f"Annualized Volatility - Binary: {vol_bin*100:.2f}%")
print(f"Annualized Volatility - Continuous: {vol_cont*100:.2f}%")

