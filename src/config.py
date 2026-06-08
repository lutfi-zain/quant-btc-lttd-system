import os

BTC_DATA_SOURCE = os.getenv("BTC_DATA_SOURCE", "binance")
EXCHANGE_API_KEY = os.getenv("EXCHANGE_API_KEY", "")
DB_PATH = os.getenv("DB_PATH", "database/lttd.db")
