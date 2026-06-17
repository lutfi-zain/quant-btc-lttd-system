import pytest
import sys
import pandas as pd
import numpy as np
from src.backtest.runner import main

def test_runner_main(mocker):
    mocker.patch.object(sys, 'argv', ['runner.py', '--start', '2018-01-01', '--end', '2021-02-01'])
    
    dates = pd.date_range("2018-01-01", "2021-02-01", tz="UTC")
    df = pd.DataFrame({
        "open": np.random.normal(100, 1, len(dates)),
        "high": np.random.normal(105, 1, len(dates)),
        "low": np.random.normal(95, 1, len(dates)),
        "close": np.random.normal(100, 1, len(dates)),
        "volume": np.random.normal(1000, 10, len(dates))
    }, index=dates)
    
    mocker.patch("src.backtest.runner.ohlcv_pipeline", return_value=df)
    
    class MockOnChainFeed:
        def __init__(self, *args, **kwargs):
            pass
        def fetch_historical_bulk(self, *args, **kwargs):
            return pd.DataFrame({
                "stamp": dates,
                "sth_mvrv": np.random.normal(1, 0.1, len(dates)),
                "sth_nupl": np.random.normal(0.5, 0.1, len(dates))
            }, index=dates)
            
    mocker.patch("src.backtest.runner.OnChainFeed", new=MockOnChainFeed)
    
    # Run the main function
    main()
