import pandas as pd
from src.features.vif import prune_multicollinear_indicators
from src.features.pca import CausalPCA


class FeatureProcessor:
    """
    FeatureProcessor orchestrates VIF pruning, causal standardization (via PCA),
    and PCA transformation.
    PCA is strictly applied only to the 6 core Technical Indicators,
    while On-Chain Metrics (like sth_*_roc_7 or sth_*) bypass PCA.
    """

    def __init__(self, vif_threshold: float = 10.0, pca_variance_threshold: float = 0.85):
        self.vif_threshold = vif_threshold
        self.pca_variance_threshold = pca_variance_threshold
        self.pca = None
        self.kept_tech_cols = None
        self.tech_indicators_list = [
            "FDI",
            "AdvancedStochastic",
            "KalmanRSI",
            "FourierSupertrend",
            "TrendStrengthIndex",
        ]

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series = None):
        if X_train.empty:
            raise ValueError("Training data cannot be empty.")

        # 1. Run VIF pruning on ALL features (technicals + on-chain)
        X_pruned = prune_multicollinear_indicators(
            X_train, y_train, vif_threshold=self.vif_threshold
        )

        # 2. Separate remaining pruned technical indicators
        remaining_tech = [
            c for c in X_pruned.columns if c in self.tech_indicators_list
        ]
        self.kept_tech_cols = remaining_tech

        # 3. Fit CausalPCA strictly on the remaining technical indicators only
        if remaining_tech:
            self.pca = CausalPCA(variance_threshold=self.pca_variance_threshold)
            self.pca.fit(X_pruned[remaining_tech])
        else:
            self.pca = None

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if self.kept_tech_cols is None:
            raise ValueError("FeatureProcessor must be fitted before calling transform.")

        if X.empty:
            return pd.DataFrame(index=X.index)

        # 1. Technical indicators: select the pruned columns and transform via PCA
        if self.pca is not None:
            X_tech = X[self.kept_tech_cols]
            X_pca = self.pca.transform(X_tech)
        else:
            X_pca = pd.DataFrame(index=X.index)

        # 2. On-Chain indicators: bypass PCA completely
        onchain_cols = [c for c in X.columns if c not in self.tech_indicators_list]
        X_onchain = X[onchain_cols]

        # 3. Return the merged dataframe
        return X_pca.join(X_onchain, how="left")
