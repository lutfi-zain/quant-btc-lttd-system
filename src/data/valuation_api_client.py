import logging
import requests
from typing import Dict, Any, Optional
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class ValuationApiClient:
    """
    Client for fetching the Composite Oscillator value from the local
    quant-btc-valuation-system API.
    """

    def __init__(self, base_url: str = "http://localhost:5173"):
        self.base_url = base_url.rstrip("/")
        self._cache_date: Optional[str] = None
        self._cached_value: float = 0.0
        self._historical_cache: Optional[pd.DataFrame] = None

    def get_latest_composite_value(self, timeout: int = 15) -> float:
        """
        Fetches the latest composite oscillator value.
        Uses a basic cache to avoid repeatedly fetching the same data on the same day.
        Returns 0.0 on failure.
        """
        today_str = datetime.utcnow().strftime("%Y-%m-%d")
        
        # Return cached value if we already fetched it today
        if self._cache_date == today_str:
            return self._cached_value

        try:
            response = requests.get(f"{self.base_url}/api/composite", timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            if not data:
                logger.warning("Valuation API returned empty data. Defaulting composite to 0.0.")
                return 0.0
                
            # The API returns a list of dictionaries with 'date' and 'composite_value'
            # We want the most recent one. Sort by date just in case.
            df = pd.DataFrame(data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date', ascending=True)
            
            latest_val = float(df.iloc[-1]['composite_value'])
            
            # Cache it
            self._cache_date = today_str
            self._cached_value = latest_val
            
            return latest_val

        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to fetch from Valuation API: {e}. Defaulting composite to 0.0.")
            return 0.0
        except (KeyError, ValueError, IndexError) as e:
            logger.warning(f"Failed to parse Valuation API response: {e}. Defaulting composite to 0.0.")
            return 0.0

    def get_composite_value_for_date(self, target_date: pd.Timestamp, timeout: int = 15) -> float:
        """
        Fetches the composite oscillator value exactly as of or immediately prior to the given target_date.
        """
        try:
            if self._historical_cache is None:
                response = requests.get(f"{self.base_url}/api/composite", timeout=timeout)
                response.raise_for_status()
                
                data = response.json()
                if not data:
                    self._historical_cache = pd.DataFrame(columns=['date', 'composite_value'])
                    return 0.0
                    
                df = pd.DataFrame(data)
                df['date'] = pd.to_datetime(df['date'], utc=True)
                df = df.sort_values('date', ascending=True)
                self._historical_cache = df
            
            df = self._historical_cache
            
            # If cache is empty due to API failure, return 0.0
            if df.empty:
                return 0.0
            
            # Ensure target_date is UTC for comparison
            if target_date.tzinfo is None:
                target_date = target_date.tz_localize('UTC')
            else:
                target_date = target_date.tz_convert('UTC')
                
            df_past = df[df['date'] <= target_date]
            if df_past.empty:
                return 0.0
                
            return float(df_past.iloc[-1]['composite_value'])

        except Exception as e:
            logger.warning(f"Failed to fetch historical composite value for {target_date}: {e}. Defaulting to 0.0.")
            if self._historical_cache is None:
                self._historical_cache = pd.DataFrame(columns=['date', 'composite_value'])
            return 0.0
