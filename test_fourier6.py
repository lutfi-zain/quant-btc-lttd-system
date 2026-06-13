import sqlite3
import pandas as pd
from src.backtest.runner import BacktestRunner
from src.data.pipeline import ohlcv_pipeline

df = ohlcv_pipeline()

runner = BacktestRunner(legacy_fixed_window=False)
records = runner.run(df)["records"]

scores = [r['indicator_scores']['FourierSupertrend'] for r in records]
import numpy as np
print("Unique FourierSupertrend values in runner.run():", np.unique(scores))
