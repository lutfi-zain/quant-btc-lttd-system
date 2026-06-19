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
            "AdvancedStochastic",
            "RSI-50",
            "FourierSupertrend",
            "TrendStrengthIndex",
            "Ichimoku",
        ]

    def fit(self, X_train: pd.DataFrame, y_train: pd.Series = None):
        if X_train.empty:
            raise ValueError("Training data cannot be empty.")

        # 1. Extract technical indicators present in the training set
        tech_cols = [c for c in X_train.columns if c in self.tech_indicators_list]
        X_tech = X_train[tech_cols]

        # 2. Run VIF pruning strictly on technical indicators only
        X_tech_pruned = prune_multicollinear_indicators(
            X_tech, y_train, vif_threshold=self.vif_threshold
        )

        remaining_tech = X_tech_pruned.columns.tolist()
        self.kept_tech_cols = remaining_tech

        # 3. Fit CausalPCA strictly on the remaining technical indicators only
        if remaining_tech:
            self.pca = CausalPCA(variance_threshold=self.pca_variance_threshold)
            self.pca.fit(X_tech_pruned)
        else:
            self.pca = None

        # 4. Run VIF pruning on On-Chain indicators (excluding HMM probs)
        onchain_cols = [c for c in X_train.columns if c not in self.tech_indicators_list and c not in ["p_bull", "p_bear", "p_sideways"]]
        X_onchain = X_train[onchain_cols]
        X_onchain_pruned = prune_multicollinear_indicators(
            X_onchain, y_train, vif_threshold=self.vif_threshold
        )
        self.kept_onchain_cols = X_onchain_pruned.columns.tolist()

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

        # 2. On-Chain indicators: bypass PCA completely but use pruned columns
        X_onchain = X[self.kept_onchain_cols] if hasattr(self, 'kept_onchain_cols') else X[[c for c in X.columns if c not in self.tech_indicators_list and c not in ["p_bull", "p_bear", "p_sideways"]]]

        # 3. Add back HMM probs
        prob_cols = [c for c in X.columns if c in ["p_bull", "p_bear", "p_sideways"]]
        X_probs = X[prob_cols]

        # 4. Return the merged dataframe
        return X_pca.join(X_onchain, how="left").join(X_probs, how="left")
