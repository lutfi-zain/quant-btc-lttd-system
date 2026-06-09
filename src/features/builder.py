import pandas as pd
from src.signals.fdi import FDI
from src.signals.quantile_dema import QuantileDEMA
from src.signals.advanced_stochastic import AdvancedStochastic


class FeatureMatrixBuilder:
    """
    Layer 3 Feature Matrix Builder.
    Computes and aggregates technical indicator scores into a feature matrix.
    """

    def __init__(self, dynamic_lookback=None):
        self.fdi = FDI(dynamic_lookback=dynamic_lookback)
        self.quantile_dema = QuantileDEMA(dynamic_lookback=dynamic_lookback)
        self.advanced_stochastic = AdvancedStochastic(dynamic_lookback=dynamic_lookback)

    def build_matrix(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Computes all registered technical indicators and constructs the feature matrix.

        Args:
            data (pd.DataFrame): OHLCV data.

        Returns:
            pd.DataFrame: Feature matrix of indicator scores with shape (T, N_features).
        """
        fdi_scores = self.fdi.compute(data)
        qdema_scores = self.quantile_dema.compute(data)
        stoch_scores = self.advanced_stochastic.compute(data)

        matrix = pd.DataFrame(
            {
                "FDI": fdi_scores,
                "QuantileDEMA": qdema_scores,
                "AdvancedStochastic": stoch_scores,
            },
            index=data.index,
        )
        return matrix
