from abc import ABC, abstractmethod
import pandas as pd
from datetime import datetime
import time
import requests
import logging
from src.config import EXCHANGE_API_KEY

logger = logging.getLogger(__name__)


class ExchangeAdapter(ABC):
    @abstractmethod
    def fetch_ohlcv(
        self, start_time: datetime = None, end_time: datetime = None
    ) -> pd.DataFrame:
        pass


class BRKExchangeAdapter(ExchangeAdapter):
    def fetch_ohlcv(
        self, start_time: datetime = None, end_time: datetime = None
    ) -> pd.DataFrame:
        from brk_client import BrkClient
        from datetime import timezone
        import numpy as np

        client = BrkClient(base_url="https://bitview.space")
        metrics = ["price_open", "price_high", "price_low", "price"]
        data = {}
        
        # We need a common start_idx and end_idx
        # Fetch price first as the anchor
        res_price = client.get_series("price", index="day1")
        start_idx = res_price["start"]
        end_idx = res_price["end"] - 1
        
        data["price"] = pd.Series(res_price["data"])
        
        for m in ["price_open", "price_high", "price_low"]:
            res = client.get_series(m, index="day1")
            data[m] = pd.Series(res["data"])

        idx_range = range(start_idx, end_idx + 1)
        dates = [pd.Timestamp("2009-01-01", tz="UTC") + pd.Timedelta(days=i) for i in idx_range]

        df = pd.DataFrame({
            "open": data["price_open"].values,
            "high": data["price_high"].values,
            "low": data["price_low"].values,
            "close": data["price"].values,
            "volume": 0.0
        }, index=pd.DatetimeIndex([datetime(d.year, d.month, d.day, tzinfo=timezone.utc) for d in dates]))

        # Filter 0s and NaNs which are present in early 2009-2010 for price columns
        price_cols = ["open", "high", "low", "close"]
        df[price_cols] = df[price_cols].replace(0, np.nan)
        df = df.dropna(subset=price_cols)

        if start_time:
            df = df[df.index >= start_time]
        if end_time:
            df = df[df.index <= end_time]

        return df


class BinanceAdapter(ExchangeAdapter):
    def fetch_ohlcv(
        self, start_time: datetime = None, end_time: datetime = None
    ) -> pd.DataFrame:
        base_url = "https://data-api.binance.vision/api/v3/klines"
        params = {"symbol": "BTCUSDT", "interval": "1d", "limit": 1000}
        headers = {}
        if EXCHANGE_API_KEY:
            headers["X-MBX-APIKEY"] = EXCHANGE_API_KEY
        if start_time:
            params["startTime"] = int(start_time.timestamp() * 1000)
        if end_time:
            params["endTime"] = int(end_time.timestamp() * 1000)

        all_df = []
        max_retries = 5

        while True:
            for attempt in range(max_retries):
                try:
                    response = requests.get(
                        base_url, params=params, headers=headers, timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    break
                except requests.exceptions.RequestException as e:
                    if attempt == max_retries - 1:
                        raise
                    sleep_time = 2**attempt
                    logger.warning(f"Fetch failed: {e}. Retrying in {sleep_time}s...")
                    time.sleep(sleep_time)

            if not data:
                break

            df = pd.DataFrame(
                data,
                columns=[
                    "open_time",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                    "close_time",
                    "quote_asset_volume",
                    "number_of_trades",
                    "taker_buy_base_asset_volume",
                    "taker_buy_quote_asset_volume",
                    "ignore",
                ],
            )
            all_df.append(df)

            if len(data) < params["limit"]:
                break

            params["startTime"] = data[-1][6] + 1
            time.sleep(0.5)

        if not all_df:
            return pd.DataFrame()

        final_df = pd.concat(all_df, ignore_index=True)
        final_df["timestamp"] = pd.to_datetime(
            final_df["open_time"], unit="ms", utc=True
        )
        final_df.set_index("timestamp", inplace=True)
        final_df = final_df[["open", "high", "low", "close", "volume"]].astype(float)

        return final_df
