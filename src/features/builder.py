import pandas as pd
from src.signals.fdi import FDI
from src.signals.advanced_stochastic import AdvancedStochastic
from src.signals.kalman_rsi import KalmanRSI
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend
from src.signals.trend_strength import TrendStrengthIndex


class FeatureMatrixBuilder:
    """
    Layer 3 Feature Matrix Builder.
    Computes and aggregates technical indicator scores into a feature matrix.
    """

    def __init__(self, dynamic_lookback=None):
        self.fdi = FDI(dynamic_lookback=dynamic_lookback)
        self.advanced_stochastic = AdvancedStochastic(dynamic_lookback=dynamic_lookback)
        self.kalman_rsi = KalmanRSI(dynamic_lookback=dynamic_lookback)
        self.fourier_supertrend = AdaptiveFourierSupertrend(
            dynamic_lookback=dynamic_lookback
        )
        self.trend_strength = TrendStrengthIndex(dynamic_lookback=dynamic_lookback)

    def build_matrix(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Computes all registered technical indicators and constructs the feature matrix.

        Args:
            data (pd.DataFrame): OHLCV data.

        Returns:
            pd.DataFrame: Feature matrix of indicator scores with shape (T, N_features).
        """
        fdi_scores = self.fdi.compute(data)
        stoch_scores = self.advanced_stochastic.compute(data)
        krsi_scores = self.kalman_rsi.compute(data)
        fourier_scores = self.fourier_supertrend.compute(data)
        ts_scores = self.trend_strength.compute(data)

        matrix = pd.DataFrame(
            {
                "FDI": fdi_scores,
                "AdvancedStochastic": stoch_scores,
                "KalmanRSI": krsi_scores,
                "FourierSupertrend": fourier_scores,
                "TrendStrengthIndex": ts_scores,
            },
            index=data.index,
        )

        # 7-day rate of change (momentum) for on-chain metrics
        for name in ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]:
            if name in data.columns:
                matrix[f"{name}_roc_7"] = data[name].diff(7).fillna(0.0)

        return matrix
