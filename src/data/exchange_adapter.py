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


class BinanceAdapter(ExchangeAdapter):
    def fetch_ohlcv(
        self, start_time: datetime = None, end_time: datetime = None
    ) -> pd.DataFrame:
        base_url = "https://api.binance.com/api/v3/klines"
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
