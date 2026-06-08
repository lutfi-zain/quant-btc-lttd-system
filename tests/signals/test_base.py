import pandas as pd
import numpy as np
import pytest
from src.signals.base import CausalFilter
from tests.signals.utils import test_no_lookahead

class DummyCausalIndicator(CausalFilter):
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # Simple causal feature: diff of close price, mapped to -1 / +1
        diff = data['close'].diff()
        # fillna(0) to handle the first NaN, then map 0 to 1 so it's in {-1, 1}
        sign = np.sign(diff).fillna(0)
        sign[sign == 0] = 1
        return sign

class DummyLookaheadIndicator(CausalFilter):
    def compute(self, data: pd.DataFrame) -> pd.Series:
        # Intentional lookahead: uses shift(-1) to look into the future
        diff = data['close'].shift(-1) - data['close']
        sign = np.sign(diff).fillna(0)
        sign[sign == 0] = 1
        return sign

@pytest.fixture
def sample_data():
    np.random.seed(42)
    dates = pd.date_range("2020-01-01", periods=100)
    closes = np.cumsum(np.random.randn(100)) + 100
    return pd.DataFrame({'close': closes}, index=dates)

def test_dummy_causal_indicator(sample_data):
    indicator = DummyCausalIndicator()
    # Test at index 50
    test_no_lookahead(indicator, sample_data, 50)

def test_dummy_lookahead_indicator(sample_data):
    indicator = DummyLookaheadIndicator()
    with pytest.raises(AssertionError, match="Lookahead bias detected"):
        test_no_lookahead(indicator, sample_data, 50)
