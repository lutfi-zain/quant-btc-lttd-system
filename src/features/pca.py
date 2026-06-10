import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler


class CausalPCA:
    """
    Strictly causal PCA transformer.
    Fits scaling and PCA projection matrix on training window,
    and transforms training/validation/test windows without lookahead bias.
    Applies sign-alignment to prevent axis flipping.
    """

    def __init__(self, variance_threshold: float = 0.85):
        self.variance_threshold = variance_threshold
        self.scaler = StandardScaler()
        self.pca = None
        self.n_components_ = None
        self.sign_flips_ = None

    def fit(self, X_train: pd.DataFrame):
        if X_train.empty:
            raise ValueError("Training data cannot be empty.")

        # 1. Fit StandardScaler on training data
        self.scaler.fit(X_train)
        X_scaled = self.scaler.transform(X_train)

        # 2. Fit full PCA to determine required components
        pca_temp = PCA(random_state=42)
        pca_temp.fit(X_scaled)

        # 3. Determine number of components to capture >85% variance
        cum_var = np.cumsum(pca_temp.explained_variance_ratio_)
        n_components = np.searchsorted(cum_var, self.variance_threshold) + 1
        self.n_components_ = int(min(n_components, X_train.shape[1]))

        # 4. Fit actual PCA with selected number of components
        self.pca = PCA(n_components=self.n_components_, random_state=42)
        self.pca.fit(X_scaled)

        # 5. Apply sign-alignment heuristic
        X_projected = self.pca.transform(X_scaled)

        # Baseline trend: row-wise mean of X_train (since indicators are trend/momentum signals)
        baseline = X_train.mean(axis=1).values

        self.sign_flips_ = np.ones(self.n_components_)
        for j in range(self.n_components_):
            pc_vals = X_projected[:, j]
            if np.std(pc_vals) > 0 and np.std(baseline) > 0:
                corr = np.corrcoef(pc_vals, baseline)[0, 1]
                if corr < 0:
                    self.sign_flips_[j] = -1.0

        # Adjust the components_ matrix to align signs permanently
        self.pca.components_ = self.pca.components_ * self.sign_flips_[:, np.newaxis]

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        if self.pca is None:
            raise ValueError("CausalPCA must be fitted before calling transform.")

        if X.empty:
            return pd.DataFrame(index=X.index)

        X_scaled = self.scaler.transform(X)
        X_projected = np.dot(X_scaled, self.pca.components_.T)

        cols = [f"PC{i+1}" for i in range(self.n_components_)]
        return pd.DataFrame(X_projected, index=X.index, columns=cols)
