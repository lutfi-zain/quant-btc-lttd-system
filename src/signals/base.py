import abc
import pandas as pd


class CausalFilter(abc.ABC):
    """
    Abstract base class for all Technical Indicators in the Signal Engine layer.

    This enforces strict causality to eliminate lookahead bias.
    All subclasses must mathematically guarantee they only process current
    and historical observations (t, t-1, ...). No symmetric windows or
    future index referencing is allowed (e.g., scipy.signal.savgol_filter).

    Reference: pi_final_research_lttd_01.md regarding the elimination of lookahead bias.
    """

    @abc.abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): The input OHLCV data.

        Returns:
            pd.Series: Indicator scores standardized to {-1, +1} at the bar level.
        """
        pass
