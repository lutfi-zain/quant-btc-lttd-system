from datetime import datetime, timezone
import pandas as pd
from src.data.exchange_adapter import BinanceAdapter

def main():
    try:
        adapter = BinanceAdapter()
        # Fetch OHLCV around Aug 2017
        df = adapter.fetch_ohlcv(
            start_time=datetime(2017, 8, 1, tzinfo=timezone.utc),
            end_time=datetime(2017, 8, 10, tzinfo=timezone.utc)
        )
        print("BinanceAdapter result:")
        print(df.to_string())
    except Exception as e:
        print("Error running BinanceAdapter:", e)

if __name__ == '__main__':
    main()
