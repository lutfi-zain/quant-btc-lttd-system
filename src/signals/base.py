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

    def __init__(self, dynamic_lookback=None):
        """
        Args:
            dynamic_lookback (pd.Series or callable or int, optional):
                Lookback window size(s) for the indicator.
                If pd.Series: contains pre-calculated daily lookback window sizes.
                If callable: a function/callback that maps data to lookbacks (e.g., calling Layer 3).
                If int/float: static baseline window size (clamped or direct).
        """
        self.dynamic_lookback = dynamic_lookback

    def _resolve_lookback(
        self, data: pd.DataFrame, default_lookback: int = 200
    ) -> pd.Series:
        """
        Resolves the dynamic_lookback parameter/callback/value into a pd.Series
        of lookback windows (integers) aligned with the data index.
        Clamps the lookback values to [120, 350] range.
        """
        if self.dynamic_lookback is None:
            resolved = pd.Series(default_lookback, index=data.index)
        elif isinstance(self.dynamic_lookback, pd.Series):
            resolved = (
                self.dynamic_lookback.reindex(data.index)
                .ffill()
                .fillna(default_lookback)
            )
        elif callable(self.dynamic_lookback):
            res = self.dynamic_lookback(data)
            if isinstance(res, pd.Series):
                resolved = res.reindex(data.index).ffill().fillna(default_lookback)
            else:
                resolved = pd.Series(res, index=data.index)
        else:
            resolved = pd.Series(self.dynamic_lookback, index=data.index)

        # Clamp to [120, 350] range and round to integer
        resolved = resolved.clip(120, 350).round().astype(int)
        return resolved

    @abc.abstractmethod
    def compute(self, data: pd.DataFrame) -> pd.Series:
        """
        Compute the indicator score based on OHLCV data.

        Args:
            data (pd.DataFrame): The input OHLCV data.

        Returns:
            pd.Series: Indicator intensities bounded in [0.0, 1.0] at the bar level.
        """
        pass
