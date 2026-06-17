import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('database/lttd.db')
df_lttd = pd.read_sql('SELECT data_as_of as date, final_score, target_exposure FROM daily_lttd ORDER BY date', conn)
df_ohlcv = pd.read_sql('SELECT timestamp as date, close FROM ohlcv ORDER BY date', conn)

df_lttd['date'] = pd.to_datetime(df_lttd['date']).dt.normalize()
df_ohlcv['date'] = pd.to_datetime(df_ohlcv['date']).dt.normalize()

df = pd.merge(df_lttd, df_ohlcv, on='date', how='inner')
df = df.sort_values('date').reset_index(drop=True)

df['return'] = df['close'].pct_change().fillna(0)

# The exposure is what we had at the end of the PREVIOUS day
df['exposure_binary'] = df['target_exposure'].shift(1).fillna(1.0)
df['exposure_cont'] = (0.5 + 0.5 * df['final_score']).shift(1).fillna(1.0)

# Calculate Arithmetic mean return (annualized) and Volatility (annualized)
def calc_metrics(returns):
    ann_ret = returns.mean() * 365
    ann_vol = returns.std() * np.sqrt(365)
    geom_ret = ann_ret - 0.5 * ann_vol**2
    return ann_ret, ann_vol, geom_ret

ret_bh = df['return']
ret_bin = df['exposure_binary'] * df['return']
ret_cont = df['exposure_cont'] * df['return']

stats = []
for name, r in [("Buy & Hold", ret_bh), ("Binary", ret_bin), ("Continuous", ret_cont)]:
    a_ret, a_vol, g_ret = calc_metrics(r)
    # Actual geometric return from compounding
    actual_g_ret = (np.prod(1 + r))**(365 / len(r)) - 1
    stats.append({
        "Strategy": name,
        "Arithmetic Mean (Ann)": a_ret,
        "Volatility (Ann)": a_vol,
        "Approx Geom Return": g_ret,
        "Actual Geom Return": actual_g_ret,
        "Final Multiple": np.prod(1+r)
    })

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 1000)
print(pd.DataFrame(stats))
