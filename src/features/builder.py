import pandas as pd
from src.signals.fdi import FDI
from src.signals.advanced_stochastic import AdvancedStochastic
from src.signals.kalman_rsi import KalmanRSI
from src.signals.fourier_supertrend import AdaptiveFourierSupertrend
from src.signals.trend_strength import TrendStrengthIndex
from src.signals.quantile_dema import QuantileDEMA


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
        self.quantile_dema = QuantileDEMA(dynamic_lookback=dynamic_lookback)

    def build_matrix(self, data: pd.DataFrame, onchain_df: pd.DataFrame = None) -> pd.DataFrame:
        """
        Computes all registered technical indicators and constructs the feature matrix.

        Args:
            data (pd.DataFrame): OHLCV data.
            onchain_df (pd.DataFrame, optional): On-chain metrics dataframe.

        Returns:
            pd.DataFrame: Feature matrix of indicator scores with shape (T, N_features).
        """
        fdi_scores = self.fdi.compute(data)
        stoch_scores = self.advanced_stochastic.compute(data)
        krsi_scores = self.kalman_rsi.compute(data)
        fourier_scores = self.fourier_supertrend.compute(data)
        ts_scores = self.trend_strength.compute(data)
        qdema_scores = self.quantile_dema.compute(data)

        matrix = pd.DataFrame(
            {
                "FDI": fdi_scores,
                "AdvancedStochastic": stoch_scores,
                "KalmanRSI": krsi_scores,
                "FourierSupertrend": fourier_scores,
                "TrendStrengthIndex": ts_scores,
                "QuantileDEMA": qdema_scores,
            },
            index=data.index,
        )

        onchain_cols = ["sth_mvrv", "sth_nupl", "sth_sopr_24h", "sth_supply_in_profit"]
        onchain_source = None
        if onchain_df is not None:
            onchain_source = onchain_df
        else:
            if any(c in data.columns for c in onchain_cols):
                onchain_source = data

        if onchain_source is not None:
            for col in onchain_cols:
                if col in onchain_source.columns:
                    col_series = onchain_source[col].reindex(data.index).ffill().bfill()
                    matrix[col] = col_series
                    matrix[f"{col}_roc_7"] = ((col_series - col_series.shift(7)) / col_series.shift(7)).fillna(0.0)

        return matrix
