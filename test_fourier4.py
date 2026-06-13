import sqlite3
import pandas as pd
from src.features.builder import FeatureMatrixBuilder
from src.backtest.runner import WFOEnsemble
import numpy as np

conn = sqlite3.connect("database/lttd.db")
df_ohlcv = pd.read_sql("SELECT timestamp as date, open, high, low, close, volume FROM ohlcv", conn).drop_duplicates("date").set_index("date")
df_ohlcv.index = pd.to_datetime(df_ohlcv.index)
df_ohlcv = df_ohlcv.sort_index()

wfo_ens = WFOEnsemble()
log_prices = np.log(df_ohlcv["close"])
dynamic_lookback = wfo_ens.run_wfo_calibration(
    log_prices,
    df_ohlcv.index[0],
    df_ohlcv.index[-1],
    legacy_fixed_window=False
)

builder = FeatureMatrixBuilder(dynamic_lookback=dynamic_lookback)
fm = builder.build_matrix(df_ohlcv)
print(fm["FourierSupertrend"].value_counts())
