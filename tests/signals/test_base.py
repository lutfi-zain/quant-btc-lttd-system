import pandas as pd
import numpy as np
import pytest
from src.signals.base import CausalFilter
from tests.signals.utils import test_no_lookahead


class DummyCausalIndicator(CausalFilter):
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # Simple causal feature: diff of close price, mapped to -1 / +1
        diff = data["close"].diff()
        # fillna(0) to handle the first NaN, then map 0 to 1 so it's in {-1, 1}
        sign = np.sign(diff).fillna(0)
        sign[sign == 0] = 1
        return sign


class DummyLookaheadIndicator(CausalFilter):
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # Intentional lookahead: uses shift(-1) to look into the future
        diff = data["close"].shift(-1) - data["close"]
        sign = np.sign(diff).fillna(0)
        sign[sign == 0] = 1
        return sign


class DummyDynamicIndicator(CausalFilter):
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # Resolves lookback dynamically
        lookbacks = self._resolve_lookback(data, default_lookback=200)
        closes = data["close"].values
        result = pd.Series(index=data.index, dtype=float)
        
        # Strictly causal lookup: for each bar i, look back l bars
        for i in range(len(data)):
            l = lookbacks.iloc[i]
            if i >= l:
                result.iloc[i] = closes[i] - closes[i - l]
            else:
                result.iloc[i] = np.nan
                
        sign = np.sign(result).fillna(0)
        sign[sign == 0] = 1
        return sign


@pytest.fixture
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=500)
    closes = np.cumsum(np.random.randn(500)) + 100
    return pd.DataFrame({"close": closes}, index=dates)


def test_dummy_causal_indicator(sample_data):
    indicator = DummyCausalIndicator()
    # Test at index 50
    test_no_lookahead(indicator, sample_data, 50)


def test_dummy_lookahead_indicator(sample_data):
    indicator = DummyLookaheadIndicator()
    # Find an index where the next day close is lower (diff is negative)
    # close.shift(-1) - close < 0 => close.diff(-1) > 0
    diff = sample_data["close"].diff(-1)
    neg_indices = np.where(diff > 0)[0]
    t_idx = neg_indices[0]
    
    with pytest.raises(AssertionError, match="Lookahead bias detected"):
        test_no_lookahead(indicator, sample_data, int(t_idx))


def test_dynamic_lookback_resolution(sample_data):
    # Test integer lookback
    indicator_int = DummyDynamicIndicator(dynamic_lookback=150)
    resolved_int = indicator_int._resolve_lookback(sample_data)
    assert (resolved_int == 150).all()

    # Test clamping limits: 100 -> 120, 400 -> 350
    indicator_clamp = DummyDynamicIndicator(dynamic_lookback=100)
    resolved_clamp = indicator_clamp._resolve_lookback(sample_data)
    assert (resolved_clamp == 120).all()

    indicator_clamp_high = DummyDynamicIndicator(dynamic_lookback=400)
    resolved_clamp_high = indicator_clamp_high._resolve_lookback(sample_data)
    assert (resolved_clamp_high == 350).all()

    # Test pd.Series dynamic lookbacks
    dyn_series = pd.Series(100, index=sample_data.index)
    dyn_series.iloc[250:] = 400
    indicator_series = DummyDynamicIndicator(dynamic_lookback=dyn_series)
    resolved_series = indicator_series._resolve_lookback(sample_data)
    assert resolved_series.iloc[0] == 120
    assert resolved_series.iloc[250] == 350

    # Test callable lookback
    indicator_call = DummyDynamicIndicator(dynamic_lookback=lambda df: pd.Series(200, index=df.index))
    resolved_call = indicator_call._resolve_lookback(sample_data)
    assert (resolved_call == 200).all()


def test_dynamic_indicator_no_lookahead(sample_data):
    # Create a dynamic lookback Series that changes over time
    dyn_series = pd.Series(150, index=sample_data.index)
    dyn_series.iloc[250:] = 300
    
    indicator = DummyDynamicIndicator(dynamic_lookback=dyn_series)
    
    # Verify no lookahead at different indices
    test_no_lookahead(indicator, sample_data, 200)
    test_no_lookahead(indicator, sample_data, 300)
    test_no_lookahead(indicator, sample_data, 450)
