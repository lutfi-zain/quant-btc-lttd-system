import pytest
import pandas as pd
from datetime import datetime, timezone
from src.data.exchange_adapter import BinanceAdapter

def test_binance_adapter_fetch_ohlcv(mocker):
    adapter = BinanceAdapter()
    
    mock_requests = mocker.patch("requests.get")
    mock_response = mocker.MagicMock()
    mock_response.json.return_value = [
        [1609459200000, "29000", "29500", "28500", "29200", "1000", 1609545599999, "29000000", 100, "500", "14500000", "0"],
        [1609545600000, "29200", "30000", "29000", "29800", "1500", 1609631999999, "44000000", 150, "750", "22000000", "0"]
    ]
    mock_response.raise_for_status.return_value = None
    mock_requests.return_value = mock_response
    
    start = datetime(2021, 1, 1, tzinfo=timezone.utc)
    end = datetime(2021, 1, 2, tzinfo=timezone.utc)
    
    df = adapter.fetch_ohlcv(start_time=start, end_time=end)
    
    assert len(df) == 2
    assert "close" in df.columns
    assert df.index[0] == pd.to_datetime("2021-01-01", utc=True)
    assert df.iloc[0]["close"] == 29200.0
