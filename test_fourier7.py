import sqlite3
import pandas as pd
from src.backtest.runner import BacktestRunner
from src.data.pipeline import ohlcv_pipeline

df = ohlcv_pipeline()

runner = BacktestRunner(legacy_fixed_window=False)
res = runner.run(df)
records = res["raw_records"]

scores = [r['indicator_scores']['FourierSupertrend'] for r in records]
import numpy as np
import collections
print("FourierSupertrend Variance:", np.var(scores))
print("Sample scores:", scores[-10:])
