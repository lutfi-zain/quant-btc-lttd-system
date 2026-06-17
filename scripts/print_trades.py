import sqlite3
import pandas as pd
conn = sqlite3.connect('database/lttd.db')
df = pd.read_sql('SELECT data_as_of as date, final_score, target_exposure FROM daily_lttd ORDER BY date', conn)
df['prev_exposure'] = df['target_exposure'].shift(1).fillna(0)
df['signal_change'] = df['target_exposure'] - df['prev_exposure']
print("Signal changes:", df['signal_change'].value_counts())
